"""QT-02 step 1: per-tile features for all Badung LSD tiles, computed in Earth Engine (batch only, KD-009).

For each 5 km tile (tiles.geojson, 500 x 500 px at 10 m, EPSG:32750) and each year 2018, 2023, 2025:
  Sentinel-2 SR harmonized, dry season May to October, Cloud Score+ cs_cdf >= 0.6:
    median B2 B3 B4 B8 B11 B12, NDVI median, NDVI sd, NDVI p90, NDBI, MNDWI, BSI      (12 bands)
  Sentinel-1 GRD IW, same season: median VV, median VH (dB), VV sd, VV minus VH      (4 bands)
  AlphaEarth Satellite Embedding V1 annual                                           (64 bands)
plus Open Buildings Temporal building_presence 2018 and 2023 (2.5 m mean to 10 m).
Saved as tiles/<tile>.npz (float16). Skips tiles already done, so it can be rerun after a failure.
"""
import io
import os
import sys
import time
import warnings

import ee
import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio import features

# BIG Satu Peta layer 59 (LSD) for Badung, downloaded by ../get_lsd.py; never committed (bible Q-09)
LSD_BADUNG = os.environ.get("LSD_BADUNG_GEOJSON", "../../data/lsd_badung_layer59.geojson")

warnings.filterwarnings("ignore")
ee.Initialize(project=os.environ["EE_PROJECT"])  # your Earth Engine Cloud project id
YEARS = (2018, 2023, 2025)
PX = 500
S2_NAMES = ["B2", "B3", "B4", "B8", "B11", "B12", "NDVI", "NDVI_sd", "NDVI_p90", "NDBI", "MNDWI", "BSI"]
S1_NAMES = ["VV", "VH", "VV_sd", "VVVH"]
LSD = gpd.read_file(LSD_BADUNG).to_crs(32750)
os.makedirs("tiles", exist_ok=True)


def s2_year(yr, region):
    cs = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region)
           .filterDate(f"{yr}-05-01", f"{yr}-10-31").linkCollection(cs, ["cs_cdf"])
           .map(lambda im: im.updateMask(im.select("cs_cdf").gte(0.6))
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
            .select(S2_NAMES))


def s1_year(yr, region):
    col = (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(region).filterDate(f"{yr}-05-01", f"{yr}-10-31")
           .filter(ee.Filter.eq("instrumentMode", "IW"))
           .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH")).select(["VV", "VH"]))
    vv, vh = col.select("VV").median(), col.select("VH").median()
    return (vv.rename("VV").addBands(vh.rename("VH")).addBands(col.select("VV").reduce(ee.Reducer.stdDev()).rename("VV_sd"))
            .addBands(vv.subtract(vh).rename("VVVH")))


def fetch(img, tfm, nbands):
    """Download one image as float32 (bands, PX, PX), splitting bands to stay under the 50 MB request limit."""
    names = img.bandNames().getInfo()
    out = []
    for k in range(0, len(names), 16):
        sub = img.select(names[k:k + 16]).toFloat()
        for attempt in range(4):
            try:
                url = sub.getDownloadURL({"crs": "EPSG:32750", "crs_transform": tfm, "dimensions": [PX, PX],
                                          "format": "GEO_TIFF"})
                r = requests.get(url, timeout=600)
                if r.ok:
                    break
                err = r.text[:300]
            except Exception as e:  # network or EE hiccup: retry
                err = str(e)[:300]
            time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError(err)
        with rasterio.MemoryFile(r.content) as m, m.open() as src:
            out.append(src.read().astype(np.float32))
    arr = np.concatenate(out)
    assert arr.shape[0] == nbands, (arr.shape, nbands)
    return arr


def do_tile(row):
    path = f"tiles/{row.tile}.npz"
    if os.path.exists(path):
        return
    x0, y0, x1, y1 = row.geometry.bounds
    tfm = [10, 0, x0, 0, -10, y1]
    region = ee.Geometry.Rectangle([x0, y0, x1, y1], "EPSG:32750", False)
    data = {}
    for yr in YEARS:
        data[f"s2s1_{yr}"] = fetch(s2_year(yr, region).addBands(s1_year(yr, region)), tfm, 16).astype(np.float16)
        ae = (ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterDate(f"{yr}-01-01", f"{yr + 1}-01-01")
              .filterBounds(region).mosaic())
        data[f"ae_{yr}"] = fetch(ae, tfm, 64).astype(np.float16)
    obt = ee.ImageCollection("GOOGLE/Research/open-buildings-temporal/v1")
    pres = []
    for yr in (2018, 2023):
        img = (obt.filterDate(f"{yr}-01-01", f"{yr + 1}-01-01").filterBounds(region).mosaic().select("building_presence")
               .unmask(0).reproject(crs="EPSG:32750", scale=2.5).reduceResolution(ee.Reducer.mean(), maxPixels=64))
        pres.append(fetch(img, tfm, 1)[0])
    data["obt"] = np.stack(pres).astype(np.float16)
    from affine import Affine
    tr = Affine(10, 0, x0, 0, -10, y1)
    clip = LSD.clip(row.geometry)
    data["lsd"] = features.rasterize(clip.geometry, (PX, PX), transform=tr).astype(bool) if len(clip) else np.zeros((PX, PX), bool)
    data["origin"] = np.array([x0, y1])
    np.savez_compressed(path, **data)


if __name__ == "__main__":
    tiles = gpd.read_file("tiles.geojson")
    only = sys.argv[1:]
    for i, row in tiles.iterrows():
        if only and row.tile not in only:
            continue
        t = time.time()
        do_tile(row)
        print(f"{i + 1}/{len(tiles)} {row.tile} lsd {row.lsd_ha} ha, {time.time() - t:.0f}s", flush=True)
