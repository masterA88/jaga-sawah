"""QT-01 step 11: retrain on Open Buildings Temporal labels over ALL pixels, evaluate at natural prevalence.

Step 10 showed the S2+S1 model trained on clear pixels over-flags mixed pixels across the whole LSD
(precision 0.06 to 0.30 against OBT). Here every AOI pixel gets a label from OBT, mixed ones included:
  positive (new building 2018 to 2023): presence 2018 < 0.1 and presence 2023 >= 0.3
  negative: everything else with presence 2018 < 0.1
Pixels already built in 2018 are left out. Spatial 1 km blocks split into 5 folds; inside each fold the
model trains on a balanced sample and is scored on ALL held-out LSD pixels, so precision reflects the real
share of conversion. The probability threshold is picked on the training folds only.
"""
import contextlib
import io
import json
import runpy
import warnings

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve

warnings.filterwarnings("ignore")
rng = np.random.default_rng(3)
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path("qt01_s1_area.py")
XA, names = ns["sets"]["S2+S1"]
in_lsd, in_aoi, block = ns["in_lsd"], ns["in_aoi"], ns["block"]
H, W = in_lsd.shape
pres = np.load("obt_presence.npy")
p18, p23 = pres[2], pres[7]
pos = (p18 < 0.1) & (p23 >= 0.3)
valid = in_aoi & (p18 < 0.1) & np.isfinite(XA).all(-1)
Xf = XA.reshape(-1, XA.shape[-1])
yf = pos.ravel().astype(np.int8)
vf, lf, bf = valid.ravel(), in_lsd.ravel(), block.ravel()
ub = np.unique(bf[vf])
rng.shuffle(ub)
fold_of = {b: i % 5 for i, b in enumerate(ub)}
fold = np.array([fold_of.get(b, -1) for b in bf])

proba = np.full(yf.shape, np.nan, np.float32)
thr_by_fold = []
for k in range(5):
    tr_idx = np.flatnonzero(vf & (fold != k) & (fold >= 0))
    te_idx = np.flatnonzero(vf & (fold == k))
    p_i, n_i = tr_idx[yf[tr_idx] == 1], tr_idx[yf[tr_idx] == 0]
    smp = np.concatenate([rng.choice(p_i, min(3000, p_i.size), replace=False), rng.choice(n_i, 6000, replace=False)])
    rf = RandomForestClassifier(300, min_samples_leaf=3, n_jobs=-1, random_state=0).fit(Xf[smp], yf[smp])
    # threshold: maximise F1 on a natural-prevalence sample of the TRAINING folds
    cal = rng.choice(tr_idx, min(60000, tr_idx.size), replace=False)
    pc = rf.predict_proba(Xf[cal])[:, 1]
    pr, rc, th = precision_recall_curve(yf[cal], pc)
    f1 = 2 * pr * rc / np.maximum(pr + rc, 1e-9)
    thr_by_fold.append(float(th[np.argmax(f1[:-1])]))
    proba[te_idx] = rf.predict_proba(Xf[te_idx])[:, 1]

m = vf & lf & np.isfinite(proba)
yt, pt = yf[m], proba[m]
thr = float(np.median(thr_by_fold))
pred = pt >= thr
tp, fp, fn = int((pred & (yt == 1)).sum()), int((pred & (yt == 0)).sum()), int((~pred & (yt == 1)).sum())
res = {"label_rule": "p18 < 0.1 and p23 >= 0.3", "lsd_pixels_scored": int(m.sum()),
       "lsd_positive_ha": round(float(yt.sum()) / 100, 1), "prevalence": round(float(yt.mean()), 4),
       "average_precision": round(float(average_precision_score(yt, pt)), 3), "threshold": round(thr, 3),
       "precision": round(tp / max(tp + fp, 1), 3), "recall": round(tp / max(tp + fn, 1), 3),
       "mapped_ha": round(float(pred.sum()) / 100, 1)}
for t in (0.5, 0.7, 0.8, 0.9):
    pp = pt >= t
    res[f"at_{t}"] = {"precision": round(float((pp & (yt == 1)).sum() / max(pp.sum(), 1)), 3),
                      "recall": round(float((pp & (yt == 1)).sum() / max(yt.sum(), 1)), 3),
                      "mapped_ha": round(float(pp.sum()) / 100, 1)}
print(json.dumps(res, indent=1))
full = np.full((H, W), np.nan, np.float32)
full.ravel()[m] = pt
np.save("obt_retrain_proba_lsd.npy", full)
json.dump(res, open("qt01_obt_retrain.json", "w"), indent=1)
