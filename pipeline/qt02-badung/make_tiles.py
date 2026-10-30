"""QT-02 step 0: 5 km tiles (EPSG:32750) covering every LSD polygon in Badung. Writes tiles.geojson.
Run ../get_lsd.py first.
"""
import os

import geopandas as gpd
import numpy as np
from shapely.geometry import box

LSD_BADUNG = os.environ.get("LSD_BADUNG_GEOJSON", "../../data/lsd_badung_layer59.geojson")
S = 5000
lsd = gpd.read_file(LSD_BADUNG).to_crs(32750)
x0, y0, x1, y1 = lsd.total_bounds
rows = []
for x in np.arange(np.floor(x0 / S) * S, x1, S):
    for y in np.arange(np.floor(y0 / S) * S, y1, S):
        b = box(x, y, x + S, y + S)
        ha = lsd.clip(b).area.sum() / 1e4
        if ha > 1:
            rows.append({"tile": f"T{int(x / 1000)}_{int(y / 1000)}", "lsd_ha": round(ha, 1), "geometry": b})
gpd.GeoDataFrame(rows, crs=32750).to_file("tiles.geojson", driver="GeoJSON")
print(len(rows), "tiles covering", round(sum(r["lsd_ha"] for r in rows)), "ha of LSD")
