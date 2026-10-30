"""QT-01 step 7: does Sentinel-1 help, and how much LSD was converted 2018 to 2023 (Olofsson estimate)?

Same footprint labels and spatial-block CV as qt01_building_labels.py. Feature sets: S2 only, S1 only,
S2 plus S1. Then the best set maps the whole grid, and the converted area inside LSD is estimated with the
stratified estimator of Olofsson et al. 2014 (R-D37), using held-out labelled pixels per map stratum.
Limit: labelled pixels are the clear ones, so the reference sample is not a probability sample of all LSD.
"""
import contextlib
import io
import json
import runpy
import warnings

import numpy as np
import xarray as xr
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")
rng = np.random.default_rng(11)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ns = runpy.run_path("qt01_building_labels.py")
X2, fn, lab, idx, in_lsd, in_aoi, block = (ns[k] for k in ("X_all", "fn", "lab", "idx", "in_lsd", "in_aoi", "block"))
H, W = lab.shape
s1 = {y: xr.open_dataset(f"s1_{y}.nc") for y in (2018, 2023)}
L, N = [], []
for k in ("VV", "VH", "VV_sd", "VVVH"):
    a, b = s1[2018][k].values, s1[2023][k].values
    L += [a, b, b - a]
    N += [f"{k}_t1", f"{k}_t2", f"{k}_d"]
X1 = np.stack(L, -1)
sets = {"S2": (X2, fn), "S1": (X1, N), "S2+S1": (np.concatenate([X2, X1], -1), fn + N)}

yv = lab.ravel()[idx]
g = block.ravel()[idx]
lsd_s = in_lsd.ravel()[idx]
res = {}
for name, (XA, names) in sets.items():
    X = XA.reshape(-1, XA.shape[-1])[idx]
    ok = np.isfinite(X).all(1)
    oof = np.full_like(yv, -1)
    for trn, te in GroupKFold(5).split(X[ok], yv[ok], g[ok]):
        tr_i, te_i = np.flatnonzero(ok)[trn], np.flatnonzero(ok)[te]
        rf = RandomForestClassifier(300, min_samples_leaf=2, n_jobs=-1, random_state=0, class_weight="balanced")
        oof[te_i] = rf.fit(X[tr_i], yv[tr_i]).predict(X[te_i])
    m = ok & lsd_s
    cm = confusion_matrix(yv[m], oof[m], labels=[0, 1, 2])
    acc = float(np.trace(confusion_matrix(yv[ok], oof[ok], labels=[0, 1, 2])) / ok.sum())
    res[name] = {"n_fitur": len(names), "akurasi": round(acc, 3),
                 "lsd_alih_precision": round(float(cm[1, 1] / max(cm[:, 1].sum(), 1)), 3),
                 "lsd_alih_recall": round(float(cm[1, 1] / max(cm[1].sum(), 1)), 3), "cm_lsd": cm.tolist()}
    print(name, res[name], flush=True)

best = max(res, key=lambda k: res[k]["lsd_alih_precision"] + res[k]["lsd_alih_recall"])
XA, names = sets[best]
X = XA.reshape(-1, XA.shape[-1])[idx]
ok = np.isfinite(X).all(1)
rf = RandomForestClassifier(300, min_samples_leaf=2, n_jobs=-1, random_state=0, class_weight="balanced").fit(X[ok], yv[ok])
flat = XA.reshape(-1, XA.shape[-1])
okf = np.isfinite(flat).all(1) & in_lsd.ravel()
pred = np.full(flat.shape[0], -1, np.int8)
pred[okf] = rf.predict(flat[okf])
# Other QT-01 scripts load this file with runpy for its variables; only a direct run writes the outputs,
# so those scripts can no longer overwrite the recorded results.
if __name__ == "__main__":
    np.save("pred_lsd_2018_2023_best.npy", pred.reshape(H, W))

# Olofsson: strata = mapped change (1) vs mapped no change; reference = footprint label, change = class 1
lsd_pix = okf
mapped = pred == 1
A = lsd_pix.sum()
W_h = {1: (lsd_pix & mapped).sum() / A, 0: (lsd_pix & ~mapped).sum() / A}
train = np.zeros(flat.shape[0], bool)
train[idx] = True
refl = lab.ravel()
p_change, var = 0.0, 0.0
detail = {}
for h, wgt in W_h.items():
    pool = np.flatnonzero(lsd_pix & (mapped if h == 1 else ~mapped) & (refl >= 0) & ~train)
    smp = rng.choice(pool, min(300, pool.size), replace=False)
    p = float((refl[smp] == 1).mean())
    p_change += wgt * p
    var += wgt ** 2 * p * (1 - p) / (len(smp) - 1)
    detail[f"stratum_{h}"] = {"bobot": round(float(wgt), 4), "n": int(len(smp)), "p_ref_alih": round(p, 3)}
ha_total = A / 100
est = p_change * ha_total
ci = 1.96 * np.sqrt(var) * ha_total
area = {"fitur_terbaik": best, "lsd_ha_terpetakan": round(float(ha_total), 1),
        "peta_alih_fungsi_ha": round(float((lsd_pix & mapped).sum() / 100), 1),
        "estimasi_alih_fungsi_ha": round(float(est), 1), "ci95_ha": round(float(ci), 1), "strata": detail}
print(json.dumps(area, indent=1))
if __name__ == "__main__":
    json.dump({"feature_sets": res, "area_olofsson": area}, open("qt01_s1_area.json", "w"), indent=1)
