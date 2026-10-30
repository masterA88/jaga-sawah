"""QT-01 step 0: Kuta Utara boundary (OpenStreetMap via Nominatim) and the LSD clipped to it.
Run ../get_lsd.py first. Writes kuta_utara_nominatim.geojson and lsd_kuta_utara.geojson here (gitignored).
"""
import os

import geopandas as gpd
import requests

LSD_BADUNG = os.environ.get("LSD_BADUNG_GEOJSON", "../../data/lsd_badung_layer59.geojson")
r = requests.get("https://nominatim.openstreetmap.org/search",
                 params={"q": "Kuta Utara, Badung, Bali", "format": "geojson", "polygon_geojson": 1, "limit": 1},
                 headers={"User-Agent": "jaga-sawah (https://master-hilmi.vercel.app/)"}, timeout=60)
open("kuta_utara_nominatim.geojson", "w").write(r.text)
aoi = gpd.read_file("kuta_utara_nominatim.geojson")
lsd = gpd.clip(gpd.read_file(LSD_BADUNG), aoi)
lsd.to_file("lsd_kuta_utara.geojson", driver="GeoJSON")
print("LSD polygons in Kuta Utara:", len(lsd), "| ha:", round(lsd.to_crs(32750).area.sum() / 1e4, 1))
