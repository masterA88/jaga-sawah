"""Download the Lahan Sawah yang Dilindungi (LSD) polygons for Kabupaten Badung from BIG Satu Peta, layer 59.

The layer is public but carries no licence text, so the file is written to ../data/ (gitignored) and is
never committed or served to browsers. Output: ../data/lsd_badung_layer59.geojson (2,126 polygons as of
29 October 2026).
"""
import json
import os

import requests

URL = "https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/SUMBER_DAYA_ALAM_DAN_LINGKUNGAN/MapServer/59/query"
OUT = os.environ.get("LSD_BADUNG_GEOJSON", "../data/lsd_badung_layer59.geojson")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

features, offset = [], 0
while True:
    r = requests.get(URL, params={"where": "wadmkk='Badung'", "outFields": "*", "outSR": 4326, "f": "geojson",
                                  "resultOffset": offset, "resultRecordCount": 1000, "orderByFields": "objectid"}, timeout=300)
    r.raise_for_status()
    batch = r.json().get("features", [])
    features += batch
    if len(batch) < 1000:
        break
    offset += 1000
json.dump({"type": "FeatureCollection", "features": features}, open(OUT, "w"))
print(len(features), "polygons ->", OUT)
