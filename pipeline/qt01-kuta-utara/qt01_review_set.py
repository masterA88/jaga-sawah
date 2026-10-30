"""QT-01 step 13: blind review set for Hilmi (bible plan step 24).

50 items, shuffled, groups hidden from the reviewer:
  30 verified patches that OBT does not count as new buildings (the group we want to measure)
  10 verified patches that OBT does count (positive control)
  10 stable LSD points, RF probability < 0.1 (negative control)
Chips are larger than Claude's (Sentinel-2 RGB 2018, 2023, 2025, 410 m wide). Google and Esri imagery must not
be used for this (bible 6.5). Output: jaga-sawah/public/data/tinjau/ (gitignored) and review_key.json here.
"""
import json
import os
import warnings

import geopandas as gpd
import matplotlib
import numpy as np
import xarray as xr
from affine import Affine
from rasterio import features

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

warnings.filterwarnings("ignore")
rng = np.random.default_rng(29)
OUT = "../../public/data/tinjau"
os.makedirs(OUT, exist_ok=True)
stacks = {yr: xr.open_dataset(f"stack_{yr}.nc") for yr in (2018, 2023, 2025)}
a = stacks[2018]
x, y = a.x.values, a.y.values
tr = Affine(x[1] - x[0], 0, x[0] - (x[1] - x[0]) / 2, 0, y[1] - y[0], y[0] - (y[1] - y[0]) / 2)
H, W = a.B04.shape
pres = np.load("obt_presence.npy")
pos = (pres[2] < 0.1) & (pres[7] >= 0.3)

g = gpd.read_file("../../public/data/kandidat_kuta_utara.geojson").to_crs(32750)
g = g[g.status == "terverifikasi"].reset_index(drop=True)
pid_r = features.rasterize(((geom, i + 1) for i, geom in enumerate(g.geometry)), (H, W), transform=tr, dtype=np.int32)
share = np.array([pos[pid_r == i + 1].mean() if (pid_r == i + 1).any() else np.nan for i in range(len(g))])
inv = ~tr


def point_of(geom):
    p = geom.representative_point()
    c, r = inv * (p.x, p.y)
    return int(r), int(c)


items = []
for grp, sel, n in (("obt_negatif", share < 0.25, 30), ("obt_positif", share >= 0.5, 10)):
    for i in rng.choice(np.flatnonzero(sel), min(n, int(sel.sum())), replace=False):
        r, c = point_of(g.geometry[i])
        items.append({"grp": grp, "patch_id": g.patch_id[i], "row": r, "col": c})
lsd = features.rasterize(gpd.read_file("lsd_kuta_utara.geojson").to_crs(32750).geometry, (H, W), transform=tr).astype(bool)
stable = lsd & (np.load("v2_proba.npy") < 0.1) & (pres.max(0) < 0.05)
stable[:25], stable[-25:], stable[:, :25], stable[:, -25:] = False, False, False, False
for k in rng.choice(np.flatnonzero(stable.ravel()), 10, replace=False):
    r, c = divmod(int(k), W)
    items.append({"grp": "stabil", "patch_id": None, "row": r, "col": c})
rng.shuffle(items)

rgb = {yr: np.clip(np.dstack([s.B04.values, s.B03.values, s.B02.values]) / 0.18, 0, 1) ** 0.8 for yr, s in stacks.items()}
public = []
for k, it in enumerate(items):
    it["id"] = f"T{k + 1:02d}"
    r, c = it["row"], it["col"]
    fig, ax = plt.subplots(1, 3, figsize=(10.5, 3.7))
    for axi, (yr, im) in zip(ax, rgb.items()):
        r0, c0 = max(r - 20, 0), max(c - 20, 0)
        axi.imshow(im[r0:r0 + 41, c0:c0 + 41], interpolation="nearest")
        axi.add_patch(Rectangle((c - c0 - 1.5, r - r0 - 1.5), 3, 3, fill=False, ec="red", lw=1.8))
        axi.set_title(str(yr), fontsize=11)
        axi.axis("off")
    plt.tight_layout()
    plt.savefig(f"{OUT}/{it['id']}.png", dpi=120)
    plt.close()
    lon, lat = gpd.GeoSeries(gpd.points_from_xy([x[c]], [y[r]]), crs=32750).to_crs(4326).iloc[0].coords[0]
    public.append({"id": it["id"], "img": f"/data/tinjau/{it['id']}.png", "lat": round(lat, 6), "lon": round(lon, 6)})
json.dump(public, open(f"{OUT}/items.json", "w"), indent=1)
json.dump(items, open("review_key.json", "w"), indent=1)
print({gname: sum(i["grp"] == gname for i in items) for gname in ("obt_negatif", "obt_positif", "stabil")})
