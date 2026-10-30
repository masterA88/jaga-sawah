"""QT-01 step 8: export results for the web app (jaga-sawah/public/data/, which is gitignored).

- kandidat_kuta_utara.geojson: connected patches of mapped conversion inside LSD (S2+S1 RF, 2018 to 2023),
  at least 3 pixels (300 m2), with area, mean RF probability, and Claude's verdict when a verified alarm
  falls inside the patch.
- lsd_kuta_utara.geojson: LSD outlines, for local development only until Q-09 (redistribution) is answered.
"""
import json
import os
import shutil
import warnings
from collections import Counter

import geopandas as gpd
import numpy as np
import xarray as xr
from affine import Affine
from rasterio import features
from scipy import ndimage
from shapely.geometry import shape

warnings.filterwarnings("ignore")
OUT = "../../public/data"
os.makedirs(OUT, exist_ok=True)
TIER = {"conversion": "terverifikasi", "unclear": "perlu_tinjau"}

a = xr.open_dataset("stack_2018.nc")
x, y = a.x.values, a.y.values
tr = Affine(x[1] - x[0], 0, x[0] - (x[1] - x[0]) / 2, 0, y[1] - y[0], y[0] - (y[1] - y[0]) / 2)
pred = np.load("pred_lsd_2018_2023_best.npy")
change = pred == 1
lab_cc, n = ndimage.label(change, structure=np.ones((3, 3)))
sizes = ndimage.sum(change, lab_cc, range(1, n + 1))
keep = np.isin(lab_cc, np.flatnonzero(sizes >= 3) + 1)
lab_cc = np.where(keep, lab_cc, 0)

ver = json.load(open("qt01_claude_verify_s1.json"))
by_patch = {}
for v in ver:
    pid = int(lab_cc[v["row"], v["col"]])
    if pid:
        by_patch.setdefault(pid, []).append(v)

rows = []
for geom, pid in features.shapes(lab_cc.astype(np.int32), mask=lab_cc > 0, transform=tr):
    pid = int(pid)
    vs = by_patch.get(pid, [])
    if vs:
        top = Counter(v["verdict"] for v in vs).most_common(1)[0][0]
        best = max((v for v in vs if v["verdict"] == top), key=lambda v: v["confidence"])
        status, alasan, conf = TIER.get(top, "ditolak"), best["alasan"], round(best["confidence"], 2)
        chip = os.path.basename(best["chip"])
        shutil.copy(best["chip"], f"{OUT}/chips/{chip}") if os.path.isdir(f"{OUT}/chips") else None
    else:
        top, status, alasan, conf, chip = None, "belum_diverifikasi", None, None, None
    rows.append({"patch_id": f"KU-{pid:05d}", "geometry": shape(geom), "verdict": top, "status": status,
                 "confidence": conf, "alasan": alasan, "chip": chip})
gdf = gpd.GeoDataFrame(rows, crs=32750).dissolve("patch_id", aggfunc="first").reset_index()
gdf["luas_m2"] = gdf.area.round(0)
gdf["periode"] = "2018-2023"
gdf = gdf.to_crs(4326)
gdf.to_file(f"{OUT}/kandidat_kuta_utara.geojson", driver="GeoJSON")
print("patches", len(gdf), "total ha", round(gdf.to_crs(32750).area.sum() / 1e4, 1), gdf.status.value_counts().to_dict())

lsd = gpd.read_file("lsd_kuta_utara.geojson")[["objectid", "luasha", "geometry"]]
lsd.to_file(f"{OUT}/lsd_kuta_utara.geojson", driver="GeoJSON")
gpd.read_file("kuta_utara_nominatim.geojson")[["geometry"]].to_file(f"{OUT}/batas_kuta_utara.geojson", driver="GeoJSON")
