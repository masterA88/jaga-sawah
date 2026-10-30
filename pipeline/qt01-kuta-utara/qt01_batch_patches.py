"""QT-01 step 9: verify every unverified candidate patch of at least 1000 m2 with the Message Batches API.

Same prompt, schema and chip as qt01_claude_verify.py (the method measured in bible 6.6), with the target
box on a point inside the patch. Batches cost half the standard price. Billing: the `ant` profile.
  python qt01_batch_patches.py submit   # builds chips, submits, writes batch_id.txt
  python qt01_batch_patches.py collect  # waits for the batch, merges verdicts into the web GeoJSON
"""
import base64
import json
import os
import sys
import time
import warnings

import anthropic
import geopandas as gpd
import numpy as np
import xarray as xr
from affine import Affine

from qt01_claude_verify import MODEL, SCHEMA, SYSTEM, chip

warnings.filterwarnings("ignore")
GJ = "../../public/data/kandidat_kuta_utara.geojson"
CHIPS = "../../public/data/chips"
TIER = {"conversion": "terverifikasi", "unclear": "perlu_tinjau"}
client = anthropic.Anthropic()


def targets():
    g = gpd.read_file(GJ)
    sel = g[(g.status == "belum_diverifikasi") & (g.luas_m2 >= 1000)].copy()
    a = xr.open_dataset("stack_2018.nc")
    x, y = a.x.values, a.y.values
    inv = ~Affine(x[1] - x[0], 0, x[0] - (x[1] - x[0]) / 2, 0, y[1] - y[0], y[0] - (y[1] - y[0]) / 2)
    pts = sel.to_crs(32750).geometry.representative_point()
    out = []
    for pid, p in zip(sel.patch_id, pts):
        c, r = inv * (p.x, p.y)
        out.append({"patch_id": pid, "row": int(r), "col": int(c)})
    return out


def submit():
    stacks = {yr: xr.open_dataset(f"stack_{yr}.nc") for yr in (2018, 2023, 2025)}
    reqs = []
    for t in targets():
        path = f"{CHIPS}/{t['patch_id']}.png"
        chip(t, stacks, path)
        r, c = t["row"], t["col"]
        text = "Nilai piksel sasaran (NDVI p90, SWIR B12): " + "; ".join(
            f"{yr}: {float(s.NDVI_p90.values[r, c]):.2f}, {float(s.B12.values[r, c]):.3f}" for yr, s in stacks.items())
        data = base64.standard_b64encode(open(path, "rb").read()).decode()
        reqs.append({"custom_id": t["patch_id"], "params": {
            "model": MODEL, "max_tokens": 2000, "system": SYSTEM,
            "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
                {"type": "text", "text": text}]}]}})
    b = client.messages.batches.create(requests=reqs)
    open("batch_id.txt", "w").write(b.id)
    print("submitted", len(reqs), "requests, batch", b.id, flush=True)


def collect():
    bid = open("batch_id.txt").read().strip()
    while True:
        b = client.messages.batches.retrieve(bid)
        if b.processing_status == "ended":
            break
        print("status", b.processing_status, b.request_counts.processing, "processing", flush=True)
        time.sleep(60)
    res, tin, tout = {}, 0, 0
    for r in client.messages.batches.results(bid):
        if r.result.type != "succeeded":
            continue
        m = r.result.message
        tin += m.usage.input_tokens
        tout += m.usage.output_tokens
        if m.stop_reason == "refusal":
            continue
        res[r.custom_id] = json.loads(next(x.text for x in m.content if x.type == "text"))
    json.dump(res, open("qt01_batch_patches.json", "w"), indent=1)
    g = gpd.read_file(GJ)
    for i, pid in enumerate(g.patch_id):
        if pid in res:
            v = res[pid]
            g.loc[i, ["verdict", "status", "confidence", "alasan", "chip"]] = [
                v["verdict"], TIER.get(v["verdict"], "ditolak"), round(v["confidence"], 2), v["alasan"], f"{pid}.png"]
    g.to_file(GJ, driver="GeoJSON")
    cost = (tin / 1e6 * 4 + tout / 1e6 * 20) / 2
    print(f"results {len(res)}, tokens in {tin} out {tout}, batch cost about US${cost:.3f}")
    print(g.status.value_counts().to_dict())
    big = g[g.luas_m2 >= 1000]
    print("patches >= 1000 m2 by status (ha):", (big.groupby("status").luas_m2.sum() / 1e4).round(1).to_dict())


if __name__ == "__main__":
    {"submit": submit, "collect": collect}[sys.argv[1]]()
