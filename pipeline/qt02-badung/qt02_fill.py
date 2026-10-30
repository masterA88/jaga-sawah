"""QT-02 step 1b: fill 2018 Sentinel-2 gaps.

The dry-season 2018 composite has no cloud-free observation for 1.8% of the LSD, mostly around Munggu, and
those pixels came back as -inf, so the model silently skipped them. For each tile with gaps, a fallback
composite over January 2018 to June 2019 (Cloud Score+ cs_cdf >= 0.5) fills only the missing pixels.
Tiles are rewritten in place; a copy of each original goes to tiles_orig/.
"""
import glob
import os
import shutil
import warnings

import ee
import numpy as np

import qt02_features as F

warnings.filterwarnings("ignore")


def s2_window(start, end, cs_min, region):
    cs = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate(start, end)
           .linkCollection(cs, ["cs_cdf"])
           .map(lambda im: im.updateMask(im.select("cs_cdf").gte(cs_min))
                .select(["B2", "B3", "B4", "B8", "B11", "B12"]).divide(10000)
                .addBands(im.normalizedDifference(["B8", "B4"]).rename("NDVI"))))
    med = col.select(["B2", "B3", "B4", "B8", "B11", "B12"]).median()
    ndvi = col.select("NDVI")
    b = {k: med.select(k) for k in ["B2", "B3", "B4", "B8", "B11", "B12"]}
    return (med.addBands(ndvi.median().rename("NDVI")).addBands(ndvi.reduce(ee.Reducer.stdDev()).rename("NDVI_sd"))
            .addBands(ndvi.reduce(ee.Reducer.percentile([90])).rename("NDVI_p90"))
            .addBands(b["B11"].subtract(b["B8"]).divide(b["B11"].add(b["B8"])).rename("NDBI"))
            .addBands(b["B3"].subtract(b["B11"]).divide(b["B3"].add(b["B11"])).rename("MNDWI"))
            .addBands(b["B11"].add(b["B4"]).subtract(b["B8"].add(b["B2"]))
                      .divide(b["B11"].add(b["B4"]).add(b["B8"]).add(b["B2"])).rename("BSI"))
            .select(F.S2_NAMES))


os.makedirs("tiles_orig", exist_ok=True)
for path in sorted(glob.glob("tiles/*.npz")):
    d = dict(np.load(path))
    a = d["s2s1_2018"].astype(np.float32)
    bad = (~np.isfinite(a[:12])).any(0)
    if not bad.any():
        continue
    shutil.copy(path, path.replace("tiles/", "tiles_orig/"))
    x0, y1 = d["origin"]
    tfm = [10, 0, float(x0), 0, -10, float(y1)]
    region = ee.Geometry.Rectangle([float(x0), float(y1) - 5000, float(x0) + 5000, float(y1)], "EPSG:32750", False)
    fb = F.fetch(s2_window("2018-01-01", "2019-06-30", 0.5, region), tfm, 12)
    a[:12, bad] = fb[:, bad]
    still = (~np.isfinite(a[:12])).any(0)
    d["s2s1_2018"] = a.astype(np.float16)
    np.savez_compressed(path, **d)
    lsd = d["lsd"]
    print(os.path.basename(path), "filled", int(bad.sum()), "px, LSD", int((bad & lsd).sum()), "left", int(still.sum()), flush=True)
