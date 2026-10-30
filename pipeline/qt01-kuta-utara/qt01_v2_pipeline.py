"""QT-01 step 12: pipeline v2. RF trained on Open Buildings Temporal labels (all pixels), Claude batch
verification of every patch >= 1000 m2, and a wall-to-wall score against OBT at each stage.

  python qt01_v2_pipeline.py map      # final RF, candidate patches, chips, writes v2 GeoJSON
  python qt01_v2_pipeline.py submit   # Claude batch (billing: the `ant` profile)
  python qt01_v2_pipeline.py collect  # wait, merge verdicts, score each stage against OBT
Add --ae for v3: AlphaEarth embeddings (2018, 2023, difference, cosine) join the S2+S1 features
(qt01_alphaearth.py measured AP 0.57 -> 0.65). v3 files carry a v3_ prefix and KU3- patch ids.
"""
import base64
import contextlib
import io
import json
import os
import runpy
import sys
import time
import warnings

import anthropic
import geopandas as gpd
import numpy as np
import xarray as xr
from affine import Affine
from rasterio import features
from scipy import ndimage
from shapely.geometry import shape
from sklearn.ensemble import RandomForestClassifier

from qt01_claude_verify import MODEL, SCHEMA, SYSTEM, chip

warnings.filterwarnings("ignore")
DATA = "../../public/data"
GJ = f"{DATA}/kandidat_kuta_utara.geojson"
TIER = {"conversion": "terverifikasi", "unclear": "perlu_tinjau"}
AE = "--ae" in sys.argv
V = "v3" if AE else "v2"
THR = json.load(open("qt01_alphaearth.json"))["S2+S1+AlphaEarth"]["threshold"] if AE else json.load(open("qt01_obt_retrain.json"))["threshold"]
a = xr.open_dataset("stack_2018.nc")
x, y = a.x.values, a.y.values
TR = Affine(x[1] - x[0], 0, x[0] - (x[1] - x[0]) / 2, 0, y[1] - y[0], y[0] - (y[1] - y[0]) / 2)
pres = np.load("obt_presence.npy")
POS = (pres[2] < 0.1) & (pres[7] >= 0.3)
OLD = pres[2] >= 0.1


def score(mask, in_lsd):
    """Pixel precision and recall against OBT inside LSD, pixels already built in 2018 excluded."""
    m = in_lsd & ~OLD
    tp = int((mask & m & POS).sum())
    return {"ha": round(float((mask & m).sum()) / 100, 1), "precision": round(tp / max(int((mask & m).sum()), 1), 3),
            "recall": round(tp / max(int((m & POS).sum()), 1), 3)}


def do_map():
    with contextlib.redirect_stdout(io.StringIO()):
        ns = runpy.run_path("qt01_s1_area.py")
    XA = ns["sets"]["S2+S1"][0]
    if AE:
        a18, a23 = (np.load(f"ae_{yr}.npy").astype(np.float32) for yr in (2018, 2023))
        XA = np.concatenate([XA, np.concatenate([a18, a23, a23 - a18, (a18 * a23).sum(0)[None]]).transpose(1, 2, 0)], -1)
    in_lsd, in_aoi = ns["in_lsd"], ns["in_aoi"]
    H, W = in_lsd.shape
    rng = np.random.default_rng(5)
    Xf = XA.reshape(-1, XA.shape[-1])
    ok = (in_aoi & ~OLD & np.isfinite(XA).all(-1)).ravel()
    yf = POS.ravel()
    p_i, n_i = np.flatnonzero(ok & yf), np.flatnonzero(ok & ~yf)
    smp = np.concatenate([rng.choice(p_i, min(3750, p_i.size), replace=False), rng.choice(n_i, 7500, replace=False)])
    rf = RandomForestClassifier(300, min_samples_leaf=3, n_jobs=-1, random_state=0).fit(Xf[smp], yf[smp])
    sel = (in_lsd & np.isfinite(XA).all(-1)).ravel()
    proba = np.zeros(H * W, np.float32)
    proba[sel] = rf.predict_proba(Xf[sel])[:, 1]
    proba = proba.reshape(H, W)
    np.save(f"{V}_proba.npy", proba)
    change = (proba >= THR) & in_lsd
    cc, n = ndimage.label(change, structure=np.ones((3, 3)))
    sizes = ndimage.sum(change, cc, range(1, n + 1))
    cc = np.where(np.isin(cc, np.flatnonzero(sizes >= 3) + 1), cc, 0)
    np.save(f"{V}_patches.npy", cc)
    rows = []
    for geom, pid in features.shapes(cc.astype(np.int32), mask=cc > 0, transform=TR):
        px = cc == pid
        rows.append({"patch_id": f"KU{V[1]}-{int(pid):05d}", "geometry": shape(geom), "prob": round(float(proba[px].mean()), 3),
                     "status": "belum_diverifikasi", "verdict": None, "confidence": None, "alasan": None, "chip": None})
    g = gpd.GeoDataFrame(rows, crs=32750).dissolve("patch_id", aggfunc="first").reset_index()
    g["luas_m2"] = g.area.round(0)
    g["periode"] = "2018-2023"
    yb = np.load("obt_year_built.npy")
    g["tahun_bangunan"] = None
    stacks = {yr: xr.open_dataset(f"stack_{yr}.nc") for yr in (2018, 2023, 2025)}
    inv = ~TR
    targets = []
    for i, r in g.iterrows():
        if r.luas_m2 >= 1000:
            p = r.geometry.representative_point()
            c, rr = inv * (p.x, p.y)
            t = {"patch_id": r.patch_id, "row": int(rr), "col": int(c)}
            chip(t, stacks, f"{DATA}/chips/{r.patch_id}.png")
            targets.append(t)
    json.dump(targets, open(f"{V}_targets.json", "w"))
    if os.path.exists(GJ) and AE and not os.path.exists("kandidat_v2.geojson"):
        os.rename(GJ, "kandidat_v2.geojson")
    elif os.path.exists(GJ) and not AE and not os.path.exists("kandidat_v1.geojson"):
        os.rename(GJ, "kandidat_v1.geojson")
    g.to_crs(4326).to_file(GJ, driver="GeoJSON")
    print(V, "patches", len(g), "ha", round(g.area.sum() / 1e4, 1), "to verify", len(targets))
    print("RF", V, "map vs OBT", score(change, in_lsd))


def submit():
    stacks = {yr: xr.open_dataset(f"stack_{yr}.nc") for yr in (2018, 2023, 2025)}
    reqs = []
    for t in json.load(open(f"{V}_targets.json")):
        r, c = t["row"], t["col"]
        text = "Nilai piksel sasaran (NDVI p90, SWIR B12): " + "; ".join(
            f"{yr}: {float(s.NDVI_p90.values[r, c]):.2f}, {float(s.B12.values[r, c]):.3f}" for yr, s in stacks.items())
        data = base64.standard_b64encode(open(f"{DATA}/chips/{t['patch_id']}.png", "rb").read()).decode()
        reqs.append({"custom_id": t["patch_id"], "params": {
            "model": MODEL, "max_tokens": 2000, "system": SYSTEM,
            "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
                {"type": "text", "text": text}]}]}})
    b = anthropic.Anthropic().messages.batches.create(requests=reqs)
    open(f"{V}_batch_id.txt", "w").write(b.id)
    print("submitted", len(reqs), "batch", b.id)


def collect():
    client = anthropic.Anthropic()
    bid = open(f"{V}_batch_id.txt").read().strip()
    while client.messages.batches.retrieve(bid).processing_status != "ended":
        time.sleep(60)
    res, tin, tout = {}, 0, 0
    for r in client.messages.batches.results(bid):
        if r.result.type != "succeeded":
            continue
        msg = r.result.message
        tin, tout = tin + msg.usage.input_tokens, tout + msg.usage.output_tokens
        if msg.stop_reason != "refusal":
            res[r.custom_id] = json.loads(next(b.text for b in msg.content if b.type == "text"))
    json.dump(res, open(f"{V}_batch.json", "w"), indent=1)
    g = gpd.read_file(GJ)
    for i, pid in enumerate(g.patch_id):
        if pid in res:
            v = res[pid]
            g.loc[i, ["verdict", "status", "confidence", "alasan", "chip"]] = [
                v["verdict"], TIER.get(v["verdict"], "ditolak"), round(v["confidence"], 2), v["alasan"], f"{pid}.png"]
    # change year from OBT: median first-built year of the patch pixels (2019 to 2023)
    gm = g.to_crs(32750)
    H, W = POS.shape
    pid_r = features.rasterize(((geom, i + 1) for i, geom in enumerate(gm.geometry)), (H, W), transform=TR, dtype=np.int32)
    yb = np.load("obt_year_built.npy")
    yrs = []
    for i in range(len(g)):
        v = yb[(pid_r == i + 1) & (yb >= 2019)]
        yrs.append(int(np.median(v)) if v.size else None)
    g["tahun_bangunan"] = yrs
    g["tahun_bangunan"] = g["tahun_bangunan"].astype("Int64")
    g.to_file(GJ, driver="GeoJSON")
    lsd = features.rasterize(gpd.read_file("lsd_kuta_utara.geojson").to_crs(32750).geometry, (H, W), transform=TR).astype(bool)
    st = {s: np.isin(pid_r, np.flatnonzero(g.status.values == s) + 1) for s in ["terverifikasi", "perlu_tinjau", "ditolak", "belum_diverifikasi"]}
    big = np.isin(pid_r, np.flatnonzero(g.luas_m2.values >= 1000) + 1)
    out = {"batch_cost_usd": round((tin / 1e6 * 4 + tout / 1e6 * 20) / 2, 3), "n_verified": len(res),
           "verdicts": {k: sum(v["verdict"] == k for v in res.values()) for k in SCHEMA["properties"]["verdict"]["enum"]},
           "rf_all_patches": score(pid_r > 0, lsd), "rf_patches_ge_1000": score(big, lsd),
           "terverifikasi": score(st["terverifikasi"], lsd),
           "terverifikasi_plus_tinjau": score(st["terverifikasi"] | st["perlu_tinjau"], lsd),
           "ditolak": score(st["ditolak"], lsd), "obt_new_building_ha_in_lsd": round(float((lsd & ~OLD & POS).sum()) / 100, 1)}
    json.dump(out, open(f"{V}_scores.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"map": do_map, "submit": submit, "collect": collect}[sys.argv[1]]()
