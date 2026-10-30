"""QT-01 step 14: AlphaEarth Satellite Embedding V1 (annual, 64 dims, 10 m) as features.

Downloads 2018, 2023 and 2025 onto the Sentinel stack grid (Earth Engine, batch only, KD-009), then runs the
same honest evaluation as qt01_obt_retrain.py (OBT labels, 1 km spatial blocks, natural prevalence in LSD,
threshold from training folds) for three feature sets: S2+S1, AlphaEarth, S2+S1+AlphaEarth.
  python qt01_alphaearth.py download
  python qt01_alphaearth.py eval
"""
import contextlib
import io
import json
import os
import runpy
import sys
import warnings

import numpy as np
import rasterio
import requests
import xarray as xr
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve

warnings.filterwarnings("ignore")
YEARS = (2018, 2023, 2025)


def download():
    import ee
    ee.Initialize(project=os.environ["EE_PROJECT"])  # your Earth Engine Cloud project id
    ref = xr.open_dataset("stack_2018.nc")
    x, y = ref.x.values, ref.y.values
    dx, dy = float(x[1] - x[0]), float(y[1] - y[0])
    H, W = len(y), len(x)
    tfm = [dx, 0, float(x[0] - dx / 2), 0, dy, float(y[0] - dy / 2)]
    col = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL")
    region = ee.Geometry.Rectangle([115.12, -8.69, 115.19, -8.59])
    for yr in YEARS:
        if os.path.exists(f"ae_{yr}.npy"):
            continue
        img = col.filterDate(f"{yr}-01-01", f"{yr + 1}-01-01").filterBounds(region).mosaic()
        parts = []
        for k in range(0, 64, 16):   # 16 bands per request keeps each download under the size limit
            bands = [f"A{i:02d}" for i in range(k, k + 16)]
            url = img.select(bands).toFloat().getDownloadURL({"crs": "EPSG:32750", "crs_transform": tfm,
                                                    "dimensions": [W, H], "format": "GEO_TIFF"})
            r = requests.get(url, timeout=600)
            if not r.ok:
                raise SystemExit(r.text[:400])
            with rasterio.MemoryFile(r.content) as m, m.open() as src:
                parts.append(src.read().astype(np.float32))
        arr = np.concatenate(parts)
        np.save(f"ae_{yr}.npy", arr.astype(np.float16))
        print(yr, arr.shape, "mean |v|", round(float(np.sqrt((arr ** 2).sum(0)).mean()), 3), flush=True)


def evaluate():
    rng = np.random.default_rng(3)
    with contextlib.redirect_stdout(io.StringIO()):
        ns = runpy.run_path("qt01_s1_area.py")
    XS, _ = ns["sets"]["S2+S1"]
    in_lsd, in_aoi, block = ns["in_lsd"], ns["in_aoi"], ns["block"]
    a18, a23 = (np.load(f"ae_{y}.npy").astype(np.float32) for y in (2018, 2023))
    cos = (a18 * a23).sum(0)[None]   # embeddings are unit length, so the dot product is cosine similarity
    XE = np.concatenate([a18, a23, a23 - a18, cos]).transpose(1, 2, 0)
    pres = np.load("obt_presence.npy")
    pos = (pres[2] < 0.1) & (pres[7] >= 0.3)
    sets = {"S2+S1": XS, "AlphaEarth": XE, "S2+S1+AlphaEarth": np.concatenate([XS, XE], -1)}
    valid = in_aoi & (pres[2] < 0.1) & np.isfinite(sets["S2+S1+AlphaEarth"]).all(-1)
    yf, vf, lf, bf = pos.ravel().astype(np.int8), valid.ravel(), in_lsd.ravel(), block.ravel()
    ub = np.unique(bf[vf])
    rng.shuffle(ub)
    fold_of = {b: i % 5 for i, b in enumerate(ub)}
    fold = np.array([fold_of.get(b, -1) for b in bf])
    res = {}
    for name, XA in sets.items():
        Xf = XA.reshape(-1, XA.shape[-1])
        r2 = np.random.default_rng(3)
        proba = np.full(yf.shape, np.nan, np.float32)
        thrs = []
        for k in range(5):
            tr_idx = np.flatnonzero(vf & (fold != k) & (fold >= 0))
            te_idx = np.flatnonzero(vf & (fold == k))
            p_i, n_i = tr_idx[yf[tr_idx] == 1], tr_idx[yf[tr_idx] == 0]
            smp = np.concatenate([r2.choice(p_i, min(3000, p_i.size), replace=False), r2.choice(n_i, 6000, replace=False)])
            rf = RandomForestClassifier(300, min_samples_leaf=3, n_jobs=-1, random_state=0).fit(Xf[smp], yf[smp])
            cal = r2.choice(tr_idx, min(60000, tr_idx.size), replace=False)
            pr, rc, th = precision_recall_curve(yf[cal], rf.predict_proba(Xf[cal])[:, 1])
            f1 = 2 * pr * rc / np.maximum(pr + rc, 1e-9)
            thrs.append(float(th[np.argmax(f1[:-1])]))
            proba[te_idx] = rf.predict_proba(Xf[te_idx])[:, 1]
        m = vf & lf & np.isfinite(proba)
        yt, pt = yf[m], proba[m]
        thr = float(np.median(thrs))
        pred = pt >= thr
        tp = int((pred & (yt == 1)).sum())
        res[name] = {"n_features": XA.shape[-1], "average_precision": round(float(average_precision_score(yt, pt)), 3),
                     "threshold": round(thr, 3), "precision": round(tp / max(int(pred.sum()), 1), 3),
                     "recall": round(tp / max(int(yt.sum()), 1), 3), "mapped_ha": round(float(pred.sum()) / 100, 1)}
        for t in (0.8, 0.9):
            pp = pt >= t
            res[name][f"at_{t}"] = {"precision": round(float((pp & (yt == 1)).sum() / max(pp.sum(), 1)), 3),
                                    "recall": round(float((pp & (yt == 1)).sum() / max(yt.sum(), 1)), 3)}
        print(name, res[name], flush=True)
        np.save(f"ae_eval_proba_{name.replace('+', '_')}.npy", np.where(m.reshape(in_lsd.shape), proba.reshape(in_lsd.shape), np.nan))
    json.dump(res, open("qt01_alphaearth.json", "w"), indent=1)


if __name__ == "__main__":
    {"download": download, "eval": evaluate}[sys.argv[1]]()
