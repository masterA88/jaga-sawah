"""QT-02 step 3: Badung candidate patches, Claude batch verification, scoring against OBT, web export.

  python qt02_export.py patches   # patches >= 3 px from pred/, chips for patches >= 1000 m2
  python qt02_export.py submit    # Claude batch (same prompt and schema as QT-01; billing: the `ant` profile)
  python qt02_export.py collect   # wait, merge verdicts, score stages against OBT, write web GeoJSON
Patches are built per tile, so a patch that crosses a tile edge is split in two.
"""
import base64
import glob
import json
import os
import sys
import time
import warnings

import anthropic
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
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, "../qt01-kuta-utara")
from qt01_claude_verify import MODEL, SCHEMA, SYSTEM  # noqa: E402

# BIG Satu Peta layer 59 (LSD) for Badung, downloaded by ../get_lsd.py; never committed (bible Q-09)
LSD_BADUNG = os.environ.get("LSD_BADUNG_GEOJSON", "../../data/lsd_badung_layer59.geojson")

warnings.filterwarnings("ignore")
DATA = "../../public/data"
CHIPS = f"{DATA}/chips_badung"
TIER = {"conversion": "terverifikasi", "unclear": "perlu_tinjau"}
THR = json.load(open("qt02_cv.json"))["threshold_median"]
TILES = sorted(os.path.basename(p)[:-4] for p in glob.glob("pred/*.npy"))


def tile_tr(name):
    x0, y1 = np.load(f"tiles/{name}.npz")["origin"]
    return Affine(10, 0, float(x0), 0, -10, float(y1))


def rgb(d, yr):
    a = d[f"s2s1_{yr}"].astype(np.float32)
    return np.clip(np.dstack([a[2], a[1], a[0]]) / 0.18, 0, 1) ** 0.8


def patches():
    os.makedirs(CHIPS, exist_ok=True)
    rows, targets = [], []
    for n in TILES:
        p = np.load(f"pred/{n}.npy")
        d = np.load(f"tiles/{n}.npz")
        tr = tile_tr(n)
        change = p >= THR
        cc, k = ndimage.label(change, structure=np.ones((3, 3)))
        if not k:
            continue
        sizes = ndimage.sum(change, cc, range(1, k + 1))
        cc = np.where(np.isin(cc, np.flatnonzero(sizes >= 3) + 1), cc, 0)
        ims = {yr: rgb(d, yr) for yr in (2018, 2023, 2025)}
        parts = {}
        for geom, pid in features.shapes(cc.astype(np.int32), mask=cc > 0, transform=tr):
            parts.setdefault(int(pid), []).append(shape(geom))   # 8-connected patches can split into several polygons
        for pid, geoms in parts.items():
            g = unary_union(geoms)
            pid_s = f"BD-{n[1:]}-{int(pid):04d}"
            px = cc == pid
            rows.append({"patch_id": pid_s, "tile": n, "geometry": g, "prob": round(float(p[px].mean()), 3)})
            if g.area >= 1000:
                c, r = ~tr * (g.representative_point().x, g.representative_point().y)
                r, c = int(r), int(c)
                fig, ax = plt.subplots(1, 3, figsize=(7.5, 2.8))
                for axi, (yr, im) in zip(ax, ims.items()):
                    r0, c0 = min(max(r - 20, 0), 459), min(max(c - 20, 0), 459)
                    axi.imshow(im[r0:r0 + 41, c0:c0 + 41], interpolation="nearest")
                    axi.add_patch(Rectangle((c - c0 - 1.5, r - r0 - 1.5), 3, 3, fill=False, ec="red", lw=1.5))
                    axi.set_title(str(yr), fontsize=9)
                    axi.axis("off")
                plt.tight_layout()
                plt.savefig(f"{CHIPS}/{pid_s}.png", dpi=110)
                plt.close()
                a18, a23, a25 = (d[f"s2s1_{yr}"].astype(np.float32) for yr in (2018, 2023, 2025))
                targets.append({"patch_id": pid_s, "vals": [(yr, float(a[8, r, c]), float(a[5, r, c]))
                                                            for yr, a in ((2018, a18), (2023, a23), (2025, a25))]})
    g = gpd.GeoDataFrame(rows, crs=32750).dissolve("patch_id", aggfunc="first").reset_index()
    g["luas_m2"] = g.area.round(0)
    g.to_file("patches_badung.gpkg", driver="GPKG")
    json.dump(targets, open("targets.json", "w"))
    print("patches", len(g), "ha", round(g.area.sum() / 1e4, 1), "to verify", len(targets))


def submit():
    reqs = []
    for t in json.load(open("targets.json")):
        text = "Nilai piksel sasaran (NDVI p90, SWIR B12): " + "; ".join(f"{yr}: {nd:.2f}, {b12:.3f}" for yr, nd, b12 in t["vals"])
        data = base64.standard_b64encode(open(f"{CHIPS}/{t['patch_id']}.png", "rb").read()).decode()
        reqs.append({"custom_id": t["patch_id"], "params": {
            "model": MODEL, "max_tokens": 2000, "system": SYSTEM,
            "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
                {"type": "text", "text": text}]}]}})
    b = anthropic.Anthropic().messages.batches.create(requests=reqs)
    open("batch_id.txt", "w").write(b.id)
    print("submitted", len(reqs), "batch", b.id)


def collect():
    client = anthropic.Anthropic()
    bid = open("batch_id.txt").read().strip()
    while client.messages.batches.retrieve(bid).processing_status != "ended":
        time.sleep(60)
    res, tin, tout = {}, 0, 0
    for r in client.messages.batches.results(bid):
        if r.result.type != "succeeded":
            continue
        m = r.result.message
        tin, tout = tin + m.usage.input_tokens, tout + m.usage.output_tokens
        if m.stop_reason != "refusal":
            res[r.custom_id] = json.loads(next(b.text for b in m.content if b.type == "text"))
    json.dump(res, open("batch_results.json", "w"), indent=1)
    g = gpd.read_file("patches_badung.gpkg")
    g["status"], g["verdict"], g["confidence"], g["alasan"], g["chip"] = "belum_diverifikasi", None, None, None, None
    for i, pid in enumerate(g.patch_id):
        if pid in res:
            v = res[pid]
            g.loc[i, ["verdict", "status", "confidence", "alasan", "chip"]] = [
                v["verdict"], TIER.get(v["verdict"], "ditolak"), round(v["confidence"], 2), v["alasan"], f"{pid}.png"]
    g["periode"] = "2018-2023"
    # score each stage against OBT, pixel level inside LSD, pixels built by 2018 excluded
    acc = {s: [0, 0] for s in ("semua", "terverifikasi", "terverifikasi_plus_tinjau")}
    tot_pos = 0
    for n in TILES:
        d = np.load(f"tiles/{n}.npz")
        obt = d["obt"].astype(np.float32)
        m = d["lsd"] & (obt[0] < 0.1)
        pos = m & (obt[1] >= 0.3)
        tot_pos += int(pos.sum())
        sub = g[g.tile == n]
        for s, sel in (("semua", sub), ("terverifikasi", sub[sub.status == "terverifikasi"]),
                       ("terverifikasi_plus_tinjau", sub[sub.status.isin(["terverifikasi", "perlu_tinjau"])])):
            if len(sel):
                mk = features.rasterize(sel.geometry, (500, 500), transform=tile_tr(n)).astype(bool) & m
                acc[s][0] += int((mk & pos).sum()); acc[s][1] += int(mk.sum())
    scores = {s: {"ha": round(v[1] / 100, 1), "precision": round(v[0] / max(v[1], 1), 3),
                  "recall": round(v[0] / max(tot_pos, 1), 3)} for s, v in acc.items()}
    out = {"batch_cost_usd": round((tin / 1e6 * 4 + tout / 1e6 * 20) / 2, 3), "n_verified": len(res),
           "verdicts": {k: sum(v["verdict"] == k for v in res.values()) for k in SCHEMA["properties"]["verdict"]["enum"]},
           "obt_new_building_ha_in_lsd": round(tot_pos / 100, 1), "scores_vs_obt": scores,
           "status_ha": (g.groupby("status").luas_m2.sum() / 1e4).round(1).to_dict(),
           "status_n": g.status.value_counts().to_dict()}
    json.dump(out, open("qt02_scores.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
    g.drop(columns=["tile"]).to_crs(4326).to_file(f"{DATA}/kandidat_badung.geojson", driver="GeoJSON")
    lsd = gpd.read_file(LSD_BADUNG)[["objectid", "luasha", "geometry"]]
    lsd["geometry"] = lsd.to_crs(32750).simplify(2).to_crs(4326)
    lsd.to_file(f"{DATA}/lsd_badung.geojson", driver="GeoJSON", COORDINATE_PRECISION=6)
    r = requests.get("https://nominatim.openstreetmap.org/search", params={"q": "Kabupaten Badung, Bali", "format": "geojson",
                     "polygon_geojson": 1, "limit": 1}, headers={"User-Agent": "jaga-sawah-qt02 (https://master-hilmi.vercel.app/)"}, timeout=60)
    open(f"{DATA}/batas_badung.geojson", "w").write(r.text)


if __name__ == "__main__":
    {"patches": patches, "submit": submit, "collect": collect}[sys.argv[1]]()
