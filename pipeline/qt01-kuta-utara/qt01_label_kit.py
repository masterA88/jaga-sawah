"""QT-01 step 3: change-candidate strata inside LSD and a stratified point sample for human labelling.

IO LULC failed as a reference here (it calls most of Kuta Utara built in 2023), so accuracy has to come
from human labels. Strata follow a spectral change score between the 2018 and 2025 dry-season
composites; sampling per stratum allows an Olofsson-style area estimate later.
Output: label_points.csv, label_points.kml (Google Earth Pro, use the historical imagery slider),
label_chips/*.png (2018 vs 2025 Sentinel-2 chips) and candidates_2018_2025.png.
"""
import os
import warnings

import geopandas as gpd
import matplotlib
import numpy as np
import xarray as xr
from rasterio import features
from rasterio.transform import xy

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
rng = np.random.default_rng(7)
N_PER_STRATUM = {"kandidat kuat": 100, "kandidat lemah": 100, "stabil hijau": 100}

a, b = xr.open_dataset("stack_2018.nc"), xr.open_dataset("stack_2025.nc")
x, y = a.x.values, a.y.values
from affine import Affine  # noqa: E402
tr = Affine(x[1] - x[0], 0, x[0] - (x[1] - x[0]) / 2, 0, y[1] - y[0], y[0] - (y[1] - y[0]) / 2)
H, W = a.B04.shape
lsd = gpd.read_file("lsd_kuta_utara.geojson").to_crs(32750)
in_lsd = features.rasterize(lsd.geometry, (H, W), transform=tr).astype(bool)

# change score: vegetation lost (NDVI p90 drop) plus SWIR brightening (roofs, concrete, bare soil)
d_ndvi = (b.NDVI_p90 - a.NDVI_p90).values
d_b12 = (b.B12 - a.B12).values
score = np.nan_to_num(-d_ndvi / 0.3 + d_b12 / 0.06)
strong = in_lsd & (score > 2.0)
weak = in_lsd & (score > 1.0) & ~strong
stable = in_lsd & (score < 0.0) & (b.NDVI_p90.values > 0.6)
strata = {"kandidat kuat": strong, "kandidat lemah": weak, "stabil hijau": stable}
ha = {k: round(v.sum() * 100 / 1e4, 1) for k, v in strata.items()}
ha["LSD total"] = round(in_lsd.sum() * 100 / 1e4, 1)
print("area per stratum (ha)", ha)

rows = []
for name, m in strata.items():
    pool = np.flatnonzero(m.ravel())
    for i in rng.choice(pool, min(N_PER_STRATUM[name], pool.size), replace=False):
        r, c = divmod(int(i), W)
        rows.append((name, r, c, *xy(tr, r, c)))
pts = gpd.GeoDataFrame(rows, columns=["stratum", "row", "col", "x", "y"],
                       geometry=gpd.points_from_xy([p[3] for p in rows], [p[4] for p in rows]), crs=32750)
pts = pts.sample(frac=1, random_state=1).reset_index(drop=True)   # shuffle so labellers do not see strata
pts["id"] = [f"P{i:03d}" for i in range(len(pts))]
ll = pts.to_crs(4326)
pts["lon"], pts["lat"] = ll.geometry.x.round(6), ll.geometry.y.round(6)
pts["score"] = [round(float(score[r, c]), 2) for r, c in zip(pts.row, pts.col)]
pts["label"] = ""   # alih_fungsi | sawah_tetap | lainnya | ragu
pts["tahun_berubah"] = ""
pts["catatan"] = ""
pts[["id", "lat", "lon", "label", "tahun_berubah", "catatan"]].to_csv("label_points_blind.csv", index=False)
pts[["id", "stratum", "score", "lat", "lon", "row", "col"]].to_csv("label_points_strata.csv", index=False)
with open("label_points.kml", "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>')
    for p in pts.itertuples():
        f.write(f"<Placemark><name>{p.id}</name><Point><coordinates>{p.lon},{p.lat}</coordinates></Point></Placemark>")
    f.write("</Document></kml>")


def rgb(s):
    return np.clip(np.dstack([s.B04, s.B03, s.B02]) / 0.18, 0, 1) ** 0.8


ra, rb = rgb(a), rgb(b)
os.makedirs("label_chips", exist_ok=True)
for p in pts.itertuples():
    r0, c0 = max(p.row - 15, 0), max(p.col - 15, 0)
    fig, ax = plt.subplots(1, 2, figsize=(4, 2.1))
    for axi, im, t in zip(ax, (ra, rb), ("2018", "2025")):
        axi.imshow(im[r0:r0 + 31, c0:c0 + 31], interpolation="nearest")
        axi.plot(p.col - c0, p.row - r0, "+", color="red", ms=10, mew=1.5)
        axi.set_title(f"{p.id} {t}", fontsize=7)
        axi.axis("off")
    plt.tight_layout()
    plt.savefig(f"label_chips/{p.id}.png", dpi=110)
    plt.close()

aoi = gpd.read_file("kuta_utara_nominatim.geojson").to_crs(32750)
ext = [x.min(), x.max(), y.min(), y.max()]
fig, ax = plt.subplots(1, 2, figsize=(16, 10))
for axi, im, t in zip(ax, (ra, rb), ("2018", "2025")):
    axi.imshow(im, extent=ext)
    lsd.boundary.plot(ax=axi, color="yellow", lw=0.3)
    axi.set_title(t)
ov = np.zeros((H, W, 4))
ov[strong] = [1, 0, 0, 0.9]
ov[weak] = [1, 0.6, 0, 0.7]
ax[1].imshow(ov, extent=ext)
for axi in ax:
    axi.set_xlim(aoi.total_bounds[[0, 2]]); axi.set_ylim(aoi.total_bounds[[1, 3]]); axi.axis("off")
ax[1].set_title("2025, merah = kandidat kuat, oranye = kandidat lemah (di dalam LSD)")
plt.tight_layout()
plt.savefig("candidates_2018_2025.png", dpi=80)
print("points", pts.stratum.value_counts().to_dict())
