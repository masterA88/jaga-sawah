"""QT-02 step 4: recent period 2023 to 2025, and the case-study villages from the news.

The v3 Badung model (trained on 2018 to 2023 OBT labels) is applied to the 2023 and 2025 feature pairs.
There is no OBT label after 2023, so this period has no accuracy figure; it is marked experimental and
the threshold is the same as for 2018 to 2023. Then counts candidates in Desa Munggu (Subak Munggu case,
Bali Post 6 Sep 2026) and Desa Canggu (30 villas sealed in Babakan Canggu, Bali Post 2 Jan 2026) for both
periods, and draws a case-study figure per village.
  python qt02_recent.py predict
  python qt02_recent.py cases
"""
import glob
import json
import os
import sys
import warnings

import geopandas as gpd
import matplotlib
import numpy as np
import requests
from affine import Affine
from rasterio import features
from scipy import ndimage
from shapely.geometry import shape
from shapely.ops import unary_union

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from qt02_model import fit, samples, TILES  # noqa: E402

# BIG Satu Peta layer 59 (LSD) for Badung, downloaded by ../get_lsd.py; never committed (bible Q-09)
LSD_BADUNG = os.environ.get("LSD_BADUNG_GEOJSON", "../../data/lsd_badung_layer59.geojson")

warnings.filterwarnings("ignore")
THR = json.load(open("qt02_cv.json"))["threshold_median"]
UA = {"User-Agent": "jaga-sawah-qt02 (https://master-hilmi.vercel.app/)"}


def feats(d, t1, t2):
    a, b = d[f"s2s1_{t1}"].astype(np.float32), d[f"s2s1_{t2}"].astype(np.float32)
    e1, e2 = d[f"ae_{t1}"].astype(np.float32), d[f"ae_{t2}"].astype(np.float32)
    return np.concatenate([a, b, b - a, e1, e2, e2 - e1, (e1 * e2).sum(0)[None]]).reshape(241, -1).T


def tile_tr(d):
    x0, y1 = d["origin"]
    return Affine(10, 0, float(x0), 0, -10, float(y1))


def predict():
    rf = fit(*samples(TILES, np.random.default_rng(11))[:2])
    os.makedirs("pred_recent", exist_ok=True)
    rows = []
    for n in TILES:
        d = np.load(f"tiles/{n}.npz")
        X, lsd = feats(d, 2023, 2025), d["lsd"].ravel()
        obt23 = d["obt"][1].astype(np.float32).ravel()
        ok = lsd & np.isfinite(X).all(1) & (obt23 < 0.1)   # skip pixels already built in 2023
        p = np.zeros(lsd.size, np.float32)
        if ok.any():
            p[ok] = rf.predict_proba(X[ok])[:, 1]
        p = p.reshape(500, 500)
        np.save(f"pred_recent/{n}.npy", p)
        change = p >= THR
        cc, k = ndimage.label(change, structure=np.ones((3, 3)))
        if not k:
            continue
        sizes = ndimage.sum(change, cc, range(1, k + 1))
        cc = np.where(np.isin(cc, np.flatnonzero(sizes >= 3) + 1), cc, 0)
        parts = {}
        for geom, pid in features.shapes(cc.astype(np.int32), mask=cc > 0, transform=tile_tr(d)):
            parts.setdefault(int(pid), []).append(shape(geom))
        for pid, geoms in parts.items():
            rows.append({"patch_id": f"BR-{n[1:]}-{pid:04d}", "geometry": unary_union(geoms),
                         "prob": round(float(p[cc == pid].mean()), 3)})
    g = gpd.GeoDataFrame(rows, crs=32750)
    g["luas_m2"] = g.area.round(0)
    g.to_file("patches_recent.gpkg", driver="GPKG")
    print("recent patches", len(g), "ha", round(g.area.sum() / 1e4, 1))


def village(q):
    r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "geojson",
                     "polygon_geojson": 1, "limit": 1}, headers=UA, timeout=60)
    return gpd.GeoDataFrame.from_features(r.json()["features"], crs=4326).to_crs(32750)


def cases():
    lsd = gpd.read_file(LSD_BADUNG).to_crs(32750)
    old = gpd.read_file("patches_badung.gpkg")
    web = gpd.read_file("../../public/data/kandidat_badung.geojson").to_crs(32750)[["patch_id", "status"]]
    old = old.merge(web, on="patch_id", how="left")
    new = gpd.read_file("patches_recent.gpkg")
    out = {}
    for key, q in (("munggu", "Munggu, Mengwi, Badung"), ("canggu", "Canggu, Kuta Utara, Badung")):
        v = village(q)
        poly = v.geometry.iloc[0]
        lsd_v = lsd.clip(poly)
        o, n = old[old.intersects(poly)], new[new.intersects(poly)]
        out[key] = {"desa_ha": round(poly.area / 1e4, 1), "lsd_ha": round(lsd_v.area.sum() / 1e4, 1),
                    "kandidat_2018_2023": {"n": len(o), "ha": round(o.area.sum() / 1e4, 2),
                                           "terverifikasi": int((o.status == "terverifikasi").sum())},
                    "kandidat_2023_2025": {"n": len(n), "ha": round(n.area.sum() / 1e4, 2)}}
        # figure: 2018, 2023, 2025 RGB of the village with LSD and candidates
        tiles = [t for t in TILES if gpd.GeoSeries([poly]).intersects(
            gpd.GeoSeries.from_xy([np.load(f"tiles/{t}.npz")["origin"][0] + 2500], [np.load(f"tiles/{t}.npz")["origin"][1] - 2500]).buffer(3600, cap_style=3)).any()]
        x0, y0, x1, y1 = poly.bounds
        fig, ax = plt.subplots(1, 3, figsize=(15, 5.6))
        for axi, yr in zip(ax, (2018, 2023, 2025)):
            for t in tiles:
                d = np.load(f"tiles/{t}.npz")
                a = d[f"s2s1_{yr}"].astype(np.float32)
                im = np.clip(np.dstack([a[2], a[1], a[0]]) / 0.18, 0, 1) ** 0.8
                ox, oy = d["origin"]
                axi.imshow(im, extent=[ox, ox + 5000, oy - 5000, oy])
            lsd_v.boundary.plot(ax=axi, color="yellow", lw=0.5)
            gpd.GeoSeries([poly]).boundary.plot(ax=axi, color="white", lw=1.2)
            if yr >= 2023 and len(o):
                o.boundary.plot(ax=axi, color="red", lw=1.0)
            if yr == 2025 and len(n):
                n.boundary.plot(ax=axi, color="magenta", lw=1.2)
            axi.set_xlim(x0 - 100, x1 + 100); axi.set_ylim(y0 - 100, y1 + 100); axi.axis("off")
            axi.set_title({2018: "2018", 2023: "2023 (merah: kandidat 2018 ke 2023)",
                           2025: "2025 (ungu: kandidat 2023 ke 2025)"}[yr], fontsize=10)
        plt.suptitle(f"Desa {key.capitalize()}: LSD kuning, batas desa putih", fontsize=11)
        plt.tight_layout()
        plt.savefig(f"case_{key}.png", dpi=90)
        plt.close()
    json.dump(out, open("qt02_cases.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"predict": predict, "cases": cases}[sys.argv[1]]()
