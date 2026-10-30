"""QT-01 step 10: evaluation against Google Open Buildings 2.5D Temporal (Earth Engine, offline).

Building presence per year 2016 to 2023 (CC BY 4.0, R-D21) is averaged onto the same 10 m grid as the
Sentinel stacks and saved as obt_presence.npy (8, H, W). OBT is itself derived from Sentinel-2 by another
model, so it is a reference map, not ground truth; scores against it measure agreement with OBT. It grades
the S2+S1 map and Claude's verdicts that were built on Overture labels. It also gives a year of change.
Earth Engine is used only here, in a batch script, never by the web app (KD-009).
"""
import os
import io
import json
import warnings
import zipfile

import ee
import geopandas as gpd
import numpy as np
import rasterio
import requests
import xarray as xr
from rasterio import features

warnings.filterwarnings("ignore")
ee.Initialize(project=os.environ["EE_PROJECT"])  # your Earth Engine Cloud project id
YEARS = list(range(2016, 2024))

ref = xr.open_dataset("stack_2018.nc")
x, y = ref.x.values, ref.y.values
dx, dy = float(x[1] - x[0]), float(y[1] - y[0])
H, W = len(y), len(x)
transform = [dx, 0, float(x[0] - dx / 2), 0, dy, float(y[0] - dy / 2)]
col = ee.ImageCollection("GOOGLE/Research/open-buildings-temporal/v1")
region = ee.Geometry.Rectangle([115.12, -8.69, 115.19, -8.59])

stack = []
for yr in YEARS:
    img = (col.filterDate(f"{yr}-01-01", f"{yr + 1}-01-01").filterBounds(region).mosaic()
           .select("building_presence").unmask(0))
    # resample to 2.5 m first (the product's effective resolution is about 4 m), then average to 10 m
    img = img.reproject(crs="EPSG:32750", scale=2.5).reduceResolution(ee.Reducer.mean(), maxPixels=64)
    url = img.getDownloadURL({"crs": "EPSG:32750", "crs_transform": transform, "dimensions": [W, H],
                              "format": "GEO_TIFF"})
    r = requests.get(url, timeout=300)
    if not r.ok:
        raise SystemExit(r.text[:500])
    data = r.content
    if data[:2] == b"PK":
        data = zipfile.ZipFile(io.BytesIO(data)).read(zipfile.ZipFile(io.BytesIO(data)).namelist()[0])
    with rasterio.MemoryFile(data) as m, m.open() as src:
        arr = src.read(1).astype(np.float32)
    stack.append(arr)
    print(yr, arr.shape, "mean presence", round(float(arr.mean()), 3), flush=True)
pres = np.stack(stack)
np.save("obt_presence.npy", pres)

# reference classes from OBT (derived from Sentinel-2, so not independent): built when mean presence >= 0.5 in the 10 m cell
from affine import Affine  # noqa: E402
tr = Affine(dx, 0, x[0] - dx / 2, 0, dy, y[0] - dy / 2)
lsd = gpd.read_file("lsd_kuta_utara.geojson").to_crs(32750)
in_lsd = features.rasterize(lsd.geometry, (H, W), transform=tr).astype(bool)
p18, p23 = pres[YEARS.index(2018)], pres[YEARS.index(2023)]
ref_conv = (p18 < 0.2) & (p23 >= 0.5)
ref_stable = (pres.max(0) < 0.1)
ref_old = p18 >= 0.5
year_built = np.full((H, W), 0, np.int16)
for i, yr in enumerate(YEARS):
    year_built[(year_built == 0) & (pres[i] >= 0.5)] = yr
np.save("obt_year_built.npy", year_built)

pred = np.load("pred_lsd_2018_2023_best.npy")
m = in_lsd & (pred >= 0) & (ref_conv | ref_stable)
tp = int((m & (pred == 1) & ref_conv).sum()); fp = int((m & (pred == 1) & ref_stable).sum())
fn = int((m & (pred != 1) & ref_conv).sum()); tn = int((m & (pred != 1) & ref_stable).sum())
out = {
    "obt_ha_in_lsd": {"alih_fungsi_2018_2023": round(float((in_lsd & ref_conv).sum()) / 100, 1),
                      "tetap_tanpa_bangunan": round(float((in_lsd & ref_stable).sum()) / 100, 1),
                      "sudah_bangunan_2018": round(float((in_lsd & ref_old).sum()) / 100, 1)},
    "map_vs_obt_pixels_in_lsd": {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                                 "precision": round(tp / max(tp + fp, 1), 3), "recall": round(tp / max(tp + fn, 1), 3)},
}

# Claude verdicts per patch vs OBT: share of patch pixels that OBT calls converted, and the median change year
g = gpd.read_file("../../public/data/kandidat_kuta_utara.geojson").to_crs(32750)
pid_r = features.rasterize(((geom, i + 1) for i, geom in enumerate(g.geometry)), (H, W), transform=tr, dtype=np.int32)
rows = []
for i, row in g.iterrows():
    px = pid_r == i + 1
    n = int(px.sum())
    if not n:
        rows.append((None, None, None)); continue
    yrs = year_built[px & (year_built >= 2019)]
    rows.append((float(ref_conv[px].mean()), float(ref_old[px].mean()), int(np.median(yrs)) if yrs.size else None))
g["obt_conv_share"] = [r[0] for r in rows]
g["obt_old_share"] = [r[1] for r in rows]
g["tahun_bangunan"] = [r[2] for r in rows]
big = g[g.luas_m2 >= 1000]
by = big.groupby("status").agg(n=("patch_id", "size"), median_conv_share=("obt_conv_share", "median"),
                              share_patches_conv_ge_25pct=("obt_conv_share", lambda s: float((s >= 0.25).mean())),
                              median_old_share=("obt_old_share", "median"))
print(by.round(3))
out["claude_status_vs_obt"] = by.round(3).reset_index().to_dict("records")
out["tahun_bangunan_terverifikasi"] = big[big.status == "terverifikasi"].tahun_bangunan.value_counts().sort_index().to_dict()
json.dump(out, open("qt01_obt.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k != "claude_status_vs_obt"}, indent=1, default=str))

g = g.to_crs(4326)
g["tahun_bangunan"] = g["tahun_bangunan"].astype("Int64")
g.drop(columns=["obt_old_share"]).to_file("../../public/data/kandidat_kuta_utara.geojson", driver="GeoJSON")
