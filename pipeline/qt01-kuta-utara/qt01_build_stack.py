"""QT-01 step 1: build dry-season Sentinel-2 composites and IO LULC reference for Kuta Utara.

Source route: Microsoft Planetary Computer STAC (fallback path in bible 6.1), no login needed.
Output: stack_<year>.nc (median bands + indices + NDVI std) and lulc_<year>.tif on one 10 m grid.
"""
import sys
import warnings

import geopandas as gpd
import numpy as np
import odc.stac
import planetary_computer as pc
import pystac_client
import rioxarray  # noqa: F401  registers .rio
import xarray as xr

warnings.filterwarnings("ignore")
odc.stac.configure_rio(cloud_defaults=True, GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="2",
                       GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR")
CRS = "EPSG:32750"
RES = 10
BANDS = ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"]
YEARS = [int(y) for y in sys.argv[1:]] or [2018, 2023, 2025]

aoi = gpd.read_file("kuta_utara_nominatim.geojson")
bbox = list(aoi.total_bounds)
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")


def composite(year):
    items = list(cat.search(collections=["sentinel-2-l2a"], bbox=bbox,
                            datetime=f"{year}-05-01/{year}-10-31",
                            query={"eo:cloud_cover": {"lt": 50}}).items())
    items = [pc.sign(i) for i in items]  # sign just before reading, tokens last about an hour
    ds = odc.stac.load(items, pool=16, bands=BANDS, bbox=bbox, crs=CRS, resolution=RES,
                       groupby="solar_day")
    # SCL keep: 4 vegetation, 5 bare, 6 water, 7 unclassified, 11 snow; drop cloud, shadow, cirrus
    ok = ds.SCL.isin([4, 5, 6, 7])
    refl = ds[BANDS[:-1]].where(ok).astype("float32")
    # processing baseline 04.00 (from 2022-01-25) adds a +1000 offset
    late = refl.time >= np.datetime64("2022-01-25")
    refl = xr.where(late, refl - 1000, refl) / 10000.0
    b = {k: refl[k] for k in BANDS[:-1]}
    ndvi = (b["B08"] - b["B04"]) / (b["B08"] + b["B04"])
    out = refl.median("time")
    out["NDVI"] = ndvi.median("time")
    out["NDVI_sd"] = ndvi.std("time")      # rice cycles make NDVI swing within a season
    out["NDVI_p90"] = ndvi.quantile(0.9, "time").drop_vars("quantile")
    m = out
    out["NDBI"] = (m.B11 - m.B08) / (m.B11 + m.B08)
    out["MNDWI"] = (m.B03 - m.B11) / (m.B03 + m.B11)
    out["BSI"] = ((m.B11 + m.B04) - (m.B08 + m.B02)) / ((m.B11 + m.B04) + (m.B08 + m.B02))
    out["n_clear"] = ok.sum("time").astype("int16")
    out = out.compute()
    out.attrs["n_scenes"] = len(items)
    out.to_netcdf(f"stack_{year}.nc")
    print(year, "scenes", len(items), "median clear obs", int(out.n_clear.median()), flush=True)
    return out


import os
for y in YEARS:
    ref = xr.open_dataset(f"stack_{y}.nc") if os.path.exists(f"stack_{y}.nc") else composite(y)
    if y <= 2023:
        it = list(cat.search(collections=["io-lulc-annual-v02"], bbox=bbox, datetime=f"{y}").items())
        it = [pc.sign(i) for i in it]
        lc = odc.stac.load(it, bands=["data"], like=ref, resampling="nearest").data.max("time")
        lc.rio.write_crs(CRS).rio.to_raster(f"lulc_{y}.tif")
        vals, cnt = np.unique(lc.values, return_counts=True)
        print(y, "IO LULC classes", dict(zip(vals.tolist(), cnt.tolist())), flush=True)
