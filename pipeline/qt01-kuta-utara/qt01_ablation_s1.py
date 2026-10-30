"""QT-01 step 7b: leakage check for S2+S1, with every NDVI-derived feature removed."""
import contextlib, io, json, runpy, warnings
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import GroupKFold
warnings.filterwarnings("ignore")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ns = runpy.run_path("qt01_s1_area.py")
XA, names = ns["sets"]["S2+S1"]
keep = [i for i, n in enumerate(names) if not n.startswith("NDVI")]
idx, yv, g, lsd_s = ns["idx"], ns["yv"], ns["g"], ns["lsd_s"]
X = XA.reshape(-1, XA.shape[-1])[idx][:, keep]
ok = np.isfinite(X).all(1)
oof = np.full_like(yv, -1)
for trn, te in GroupKFold(5).split(X[ok], yv[ok], g[ok]):
    a, b = np.flatnonzero(ok)[trn], np.flatnonzero(ok)[te]
    oof[b] = RandomForestClassifier(300, min_samples_leaf=2, n_jobs=-1, random_state=0, class_weight="balanced").fit(X[a], yv[a]).predict(X[b])
m = ok & lsd_s
cm = confusion_matrix(yv[m], oof[m], labels=[0, 1, 2])
out = {"n_fitur": len(keep), "akurasi": round(float((oof[ok] == yv[ok]).mean()), 3),
       "lsd_alih_precision": round(float(cm[1, 1] / cm[:, 1].sum()), 3), "lsd_alih_recall": round(float(cm[1, 1] / cm[1].sum()), 3), "cm_lsd": cm.tolist()}
print(json.dumps(out)); json.dump(out, open("qt01_ablation_s1.json", "w"))
