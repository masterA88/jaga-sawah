"""QT-01 step 4b: leakage check. Same footprint labels, RF without any NDVI-derived feature."""
import runpy, sys, io, contextlib, json
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import GroupKFold
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ns = runpy.run_path("qt01_building_labels.py")
X, yv, g, fn, lsd_s = ns["X"], ns["yv"], ns["g"], ns["fn"], ns["lsd_s"]
keep = [i for i, n in enumerate(fn) if not n.startswith("NDVI")]
res = {}
for name, cols in [("tanpa NDVI", keep), ("hanya B11 B12 NDBI BSI", [i for i, n in enumerate(fn) if n.split("_")[0] in ("B11", "B12", "NDBI", "BSI")])]:
    oof = np.zeros_like(yv)
    for trn, te in GroupKFold(5).split(X, yv, g):
        rf = RandomForestClassifier(300, min_samples_leaf=2, n_jobs=-1, random_state=0, class_weight="balanced").fit(X[trn][:, cols], yv[trn])
        oof[te] = rf.predict(X[te][:, cols])
    cm = confusion_matrix(yv, oof, labels=[0, 1, 2]); cml = confusion_matrix(yv[lsd_s], oof[lsd_s], labels=[0, 1, 2])
    p = cml[1, 1] / max(cml[:, 1].sum(), 1); r = cml[1, 1] / max(cml[1].sum(), 1)
    res[name] = {"n_fitur": len(cols), "akurasi": round(float(np.trace(cm) / cm.sum()), 3), "lsd_alih_precision": round(float(p), 3), "lsd_alih_recall": round(float(r), 3), "cm_lsd": cml.tolist()}
print(json.dumps(res, indent=1))
json.dump(res, open("qt01_ablation.json", "w"), indent=1)
