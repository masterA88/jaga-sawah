"""QT-01 step 4: reference labels from building footprints (Overture Maps), then RF with spatial CV.

Footprints come from Google Open Buildings, Microsoft and OSM merged by Overture (ODbL for the theme).
They show where a building stands now (imagery roughly 2022 to 2023 for the ML sources), so the change
period is 2018 to 2023 and the features use stack_2018 and stack_2023.
Label rules (10 m pixel):
  alih fungsi    building cover >= 30% now, and the 2018 pixel was green (NDVI p90 >= 0.55)
  sawah tetap    no building within 20 m, green in 2023 (NDVI p90 >= 0.55)
  bangunan lama  building cover >= 30% now, and the 2018 pixel was not green (NDVI p90 < 0.45)
The "built now" half is independent of Sentinel-2; the 2018 greenness half is not, which is stated in
the bible as a limit.
"""
import json
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from affine import Affine
from rasterio import features
from scipy import ndimage
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold

warnings.filterwarnings("ignore")
rng = np.random.default_rng(42)
NAMES = ["sawah tetap", "alih fungsi", "bangunan lama"]

a, b = xr.open_dataset("stack_2018.nc"), xr.open_dataset("stack_2023.nc")
x, y = a.x.values, a.y.values
tr = Affine(x[1] - x[0], 0, x[0] - (x[1] - x[0]) / 2, 0, y[1] - y[0], y[0] - (y[1] - y[0]) / 2)
H, W = a.B04.shape

bld = pd.read_parquet("overture_buildings_kuta_utara.parquet")
bld = gpd.GeoDataFrame(bld, geometry=gpd.GeoSeries.from_wkb(bld.geometry), crs=4326).to_crs(32750)
print("buildings", len(bld), bld.src.value_counts().to_dict())

# building cover fraction per 10 m pixel: rasterize at 2 m and average 5x5
tr2 = Affine(tr.a / 5, 0, tr.c, 0, tr.e / 5, tr.f)
fine = features.rasterize(bld.geometry, (H * 5, W * 5), transform=tr2).astype(np.float32)
cover = fine.reshape(H, 5, W, 5).mean((1, 3))
near = ndimage.maximum_filter(cover > 0, size=5)   # any building within about 20 m

aoi = gpd.read_file("kuta_utara_nominatim.geojson").to_crs(32750)
lsd = gpd.read_file("lsd_kuta_utara.geojson").to_crs(32750)
in_aoi = features.rasterize(aoi.geometry, (H, W), transform=tr).astype(bool)
in_lsd = features.rasterize(lsd.geometry, (H, W), transform=tr).astype(bool)
g18, g23 = a.NDVI_p90.values, b.NDVI_p90.values

lab = np.full((H, W), -1, np.int8)
lab[~near & (g23 >= 0.55)] = 0
lab[(cover >= 0.3) & (g18 >= 0.55)] = 1
lab[(cover >= 0.3) & (g18 < 0.45)] = 2
lab[~in_aoi] = -1
ha = lambda m: round(float(m.sum()) / 100, 1)
print("label area in LSD (ha)", {NAMES[c]: ha(in_lsd & (lab == c)) for c in range(3)})

# 1) how well do the spectral strata from step 3 agree with the footprint reference?
st = pd.read_csv("label_points_strata.csv")
st["ref"] = [int(lab[r, c]) for r, c in zip(st.row, st.col)]
st["cover"] = [round(float(cover[r, c]), 2) for r, c in zip(st.row, st.col)]
tab = pd.crosstab(st.stratum, st.ref.map({-1: "tak berlabel", 0: NAMES[0], 1: NAMES[1], 2: NAMES[2]}))
print(tab)
st.to_csv("label_points_ref_buildings.csv", index=False)


# 2) RF with the footprint labels, spatial block CV
def feats(p, q):
    keys = ["B02", "B03", "B04", "B08", "B11", "B12", "NDVI", "NDVI_sd", "NDVI_p90", "NDBI", "MNDWI", "BSI"]
    L, N = [], []
    for k in keys:
        L += [p[k].values, q[k].values, q[k].values - p[k].values]
        N += [f"{k}_t1", f"{k}_t2", f"{k}_d"]
    return np.stack(L, -1), N


X_all, fn = feats(a, b)
ok = np.isfinite(X_all).all(-1) & (lab >= 0)
rows, cols = np.mgrid[0:H, 0:W]
block = (rows // 100) * 1000 + (cols // 100)
idx = np.concatenate([rng.choice(np.flatnonzero((ok & (lab == c)).ravel()),
                                 min(600, int((ok & (lab == c)).sum())), replace=False) for c in range(3)])
X, yv, g = X_all.reshape(-1, X_all.shape[-1])[idx], lab.ravel()[idx], block.ravel()[idx]
lsd_s = in_lsd.ravel()[idx]
oof = np.zeros_like(yv)
for trn, te in GroupKFold(5).split(X, yv, g):
    rf = RandomForestClassifier(300, min_samples_leaf=2, n_jobs=-1, random_state=0, class_weight="balanced").fit(X[trn], yv[trn])
    oof[te] = rf.predict(X[te])
cm = confusion_matrix(yv, oof, labels=[0, 1, 2])
rep = classification_report(yv, oof, target_names=NAMES, output_dict=True)
print("confusion (rows ref, cols pred)\n", cm)
print(classification_report(yv, oof, target_names=NAMES, digits=3))
cm_lsd = confusion_matrix(yv[lsd_s], oof[lsd_s], labels=[0, 1, 2])
print("inside LSD\n", cm_lsd)

# binary view that matters for the product: alih fungsi vs sawah tetap
m = yv != 2
tp = int(((oof == 1) & (yv == 1)).sum()); fp = int(((oof == 1) & (yv == 0)).sum()); fnn = int(((oof != 1) & (yv == 1)).sum())
out = {"buildings": int(len(bld)), "sources": bld.src.value_counts().to_dict(),
       "label_ha_lsd": {NAMES[c]: ha(in_lsd & (lab == c)) for c in range(3)},
       "strata_vs_ref": tab.to_dict(), "confusion": cm.tolist(), "confusion_lsd": cm_lsd.tolist(),
       "report": {k: v for k, v in rep.items() if k in NAMES + ["accuracy", "macro avg"]},
       "alih_vs_all": {"precision": round(tp / max(tp + fp, 1), 3), "recall": round(tp / max(tp + fnn, 1), 3)},
       "n_per_class": {NAMES[c]: int((yv == c).sum()) for c in range(3)}}
# Other QT-01 scripts load this file with runpy for its variables; only a direct run writes the outputs,
# so those scripts can no longer overwrite the recorded results.
if __name__ == "__main__":
    json.dump(out, open("qt01_building_summary.json", "w"), indent=1, default=str)
print(json.dumps(out["alih_vs_all"]))
