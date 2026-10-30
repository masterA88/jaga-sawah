"""QT-01 step 2: weak labels from IO LULC, random forest, spatial-block cross-validation.

Classes: 0 sawah tetap (agri both years), 1 alih fungsi (agri -> built), 2 bangunan tetap (built both years).
Reference is IO LULC 10 m (Impact Observatory, CC BY 4.0), so the scores measure agreement with that
map, not field truth. A human-labelled sample is still needed before any accuracy claim.
"""
import json
import warnings

import geopandas as gpd
import numpy as np
import rioxarray
import xarray as xr
from rasterio import features
from scipy import ndimage
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")
rng = np.random.default_rng(42)
T1, T2, T3 = 2018, 2023, 2025
AGRI = [4, 5, 11]   # IO LULC: flooded vegetation, crops, rangeland
BUILT = 7
NAMES = ["sawah tetap", "alih fungsi", "bangunan tetap"]
PER_CLASS = 600     # pooled sample; each GroupKFold fold trains on about 480 per class
BLOCK = 1000        # metres, spatial block for CV


def feats(a, b):
    keys = ["B02", "B03", "B04", "B08", "B11", "B12", "NDVI", "NDVI_sd", "NDVI_p90", "NDBI", "MNDWI", "BSI"]
    layers, names = [], []
    for k in keys:
        layers += [a[k].values, b[k].values, b[k].values - a[k].values]
        names += [f"{k}_t1", f"{k}_t2", f"{k}_d"]
    return np.stack(layers, -1), names


s = {y: xr.open_dataset(f"stack_{y}.nc") for y in (T1, T2, T3)}
lc1 = rioxarray.open_rasterio(f"lulc_{T1}.tif").squeeze().values
lc2 = rioxarray.open_rasterio(f"lulc_{T2}.tif").squeeze().values
ref = s[T1]
H, W = lc1.shape
transform = ref.odc.geobox.transform if hasattr(ref, "odc") else None
if transform is None:
    from affine import Affine
    x, y = ref.x.values, ref.y.values
    transform = Affine(x[1] - x[0], 0, x[0] - (x[1] - x[0]) / 2, 0, y[1] - y[0], y[0] - (y[1] - y[0]) / 2)

aoi = gpd.read_file("kuta_utara_nominatim.geojson").to_crs(32750)
lsd = gpd.read_file("lsd_kuta_utara.geojson").to_crs(32750)
in_aoi = features.rasterize(aoi.geometry, (H, W), transform=transform).astype(bool)
in_lsd = features.rasterize(lsd.geometry, (H, W), transform=transform).astype(bool)

a1, a2 = np.isin(lc1, AGRI), np.isin(lc2, AGRI)
b1, b2 = lc1 == BUILT, lc2 == BUILT
lab = np.full((H, W), -1, np.int8)
lab[a1 & a2] = 0
lab[a1 & b2] = 1
lab[b1 & b2] = 2
# pure pixels only: the 3x3 neighbourhood carries the same label
pure = (ndimage.minimum_filter(lab, 3) == ndimage.maximum_filter(lab, 3)) & (lab >= 0)
X_all, fnames = feats(s[T1], s[T2])
valid = in_aoi & pure & np.isfinite(X_all).all(-1)

rows, cols = np.mgrid[0:H, 0:W]
block = (rows * 10 // BLOCK) * 1000 + (cols * 10 // BLOCK)
counts = {NAMES[c]: int((valid & (lab == c)).sum()) for c in range(3)}
counts_lsd = {NAMES[c]: int((valid & in_lsd & (lab == c)).sum()) for c in range(3)}
print("pure pixels in AOI", counts, "inside LSD", counts_lsd)

idx = []
for c in range(3):
    pool = np.flatnonzero((valid & (lab == c)).ravel())
    idx.append(rng.choice(pool, min(PER_CLASS, pool.size), replace=False))
idx = np.concatenate(idx)
X = X_all.reshape(-1, X_all.shape[-1])[idx]
y = lab.ravel()[idx]
g = block.ravel()[idx]
lsd_flag = in_lsd.ravel()[idx]

oof = np.zeros_like(y)
for tr, te in GroupKFold(5).split(X, y, g):
    rf = RandomForestClassifier(300, min_samples_leaf=2, n_jobs=-1, random_state=0, class_weight="balanced")
    rf.fit(X[tr], y[tr])
    oof[te] = rf.predict(X[te])

cm = confusion_matrix(y, oof, labels=[0, 1, 2])
rep = classification_report(y, oof, target_names=NAMES, output_dict=True, digits=3)
cm_lsd = confusion_matrix(y[lsd_flag], oof[lsd_flag], labels=[0, 1, 2])
print("confusion (rows ref, cols pred)\n", cm)
print(classification_report(y, oof, target_names=NAMES, digits=3))
print("inside LSD only\n", cm_lsd)

# rule baseline: NDVI drop and NDBI rise, thresholds tuned on the same sample (optimistic for the rule)
d_ndvi = X[:, fnames.index("NDVI_d")]
d_ndbi = X[:, fnames.index("NDBI_d")]
best = max(((t1, t2, (((d_ndvi < t1) & (d_ndbi > t2)) == (y == 1)).mean())
            for t1 in np.arange(-0.4, 0.0, 0.02) for t2 in np.arange(0, 0.3, 0.02)), key=lambda r: r[2])
rule = (d_ndvi < best[0]) & (d_ndbi > best[1])
sub = y != 2
tp = (rule & (y == 1)).sum(); fp = (rule & (y == 0)).sum(); fn = (~rule & (y == 1)).sum()
print(f"rule baseline on sawah-vs-alih-fungsi: precision {tp/(tp+fp):.3f} recall {tp/(tp+fn):.3f}")

# final model on all samples, then map T1->T2 and T2->T3 inside LSD
rf = RandomForestClassifier(300, min_samples_leaf=2, n_jobs=-1, random_state=0, class_weight="balanced").fit(X, y)
imp = sorted(zip(rf.feature_importances_, fnames), reverse=True)[:10]


def predict(Xs):
    flat = Xs.reshape(-1, Xs.shape[-1])
    ok = np.isfinite(flat).all(-1)
    out = np.full(flat.shape[0], -1, np.int8)
    proba = np.zeros(flat.shape[0], np.float32)
    p = rf.predict_proba(flat[ok])
    out[ok] = p.argmax(1)
    proba[ok] = p[:, 1]
    return out.reshape(H, W), proba.reshape(H, W)


pred12, p12 = predict(X_all)
X23, _ = feats(s[T2], s[T3])
pred23, p23 = predict(X23)
np.save("pred_2018_2023.npy", pred12)
np.save("pred_2023_2025.npy", pred23)
np.save("p_alih_2023_2025.npy", p23)
np.save("in_lsd.npy", in_lsd)
ha = lambda m: round(float(m.sum()) * 100 / 1e4, 1)
lsd_ha = ha(in_lsd & in_aoi)
summary = {
    "pure_pixels_aoi": counts, "pure_pixels_lsd": counts_lsd,
    "sample_per_class": {NAMES[c]: int((y == c).sum()) for c in range(3)},
    "blocks_m": BLOCK, "folds": 5,
    "confusion_all": cm.tolist(), "confusion_lsd": cm_lsd.tolist(),
    "report": {k: v for k, v in rep.items() if k in NAMES + ["accuracy", "macro avg"]},
    "rule_baseline": {"ndvi_d_lt": round(best[0], 2), "ndbi_d_gt": round(best[1], 2),
                      "precision": round(tp / (tp + fp), 3), "recall": round(tp / (tp + fn), 3)},
    "top_features": [(n, round(float(v), 3)) for v, n in imp],
    "lsd_ha_raster": lsd_ha,
    "ref_io_alih_fungsi_in_lsd_ha_2018_2023": ha(in_lsd & (lab == 1)),
    "ref_io_built_in_lsd_2023_ha": ha(in_lsd & b2),
    "pred_alih_fungsi_in_lsd_ha_2018_2023": ha(in_lsd & (pred12 == 1)),
    "pred_alih_fungsi_in_lsd_ha_2023_2025": ha(in_lsd & (pred23 == 1)),
    "pred_alih_fungsi_in_lsd_ha_2023_2025_p_ge_0.7": ha(in_lsd & (p23 >= 0.7)),
}
json.dump(summary, open("qt01_summary.json", "w"), indent=1)
print(json.dumps({k: summary[k] for k in list(summary)[-7:]}, indent=1))
