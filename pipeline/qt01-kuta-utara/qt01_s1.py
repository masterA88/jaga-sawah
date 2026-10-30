"""QT-01 step 6: Sentinel-1 RTC (VV, VH) dry-season median in dB, same 10 m grid as the Sentinel-2 stacks.

Source: Planetary Computer sentinel-1-rtc (radiometrically terrain corrected, gamma0). Radar sees through
cloud and responds to buildings (double bounce raises VV), which optical bands confuse with bare soil.
"""
import os
import sys
import warnings

import numpy as np
import odc.stac
import planetary_computer as pc
import pystac_client
import xarray as xr

warnings.filterwarnings("ignore")
odc.stac.configure_rio(cloud_defaults=True, GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="2",
                       GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR")
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
ref = xr.open_dataset("stack_2018.nc")
bbox = [115.1243, -8.6842, 115.1824, -8.6004]

for year in [int(y) for y in sys.argv[1:]] or [2018, 2023]:
    if os.path.exists(f"s1_{year}.nc"):
        continue
    items = list(cat.search(collections=["sentinel-1-rtc"], bbox=bbox, datetime=f"{year}-05-01/{year}-10-31").items())
    items = [pc.sign(i) for i in items]
    ds = odc.stac.load(items, bands=["vv", "vh"], bbox=bbox, crs="EPSG:32750", resolution=10,
                       groupby="solar_day", pool=16)
    ds = ds.where(ds > 0)
    out = xr.Dataset({
        "VV": 10 * np.log10(ds.vv.median("time")),
        "VH": 10 * np.log10(ds.vh.median("time")),
        "VV_sd": (10 * np.log10(ds.vv)).std("time"),
    })
    out["VVVH"] = out.VV - out.VH
    out = out.interp(x=ref.x, y=ref.y, method="nearest").compute()
    out.to_netcdf(f"s1_{year}.nc")
    print(year, "S1 scenes", len(items), "median VV dB", float(out.VV.median()), flush=True)
