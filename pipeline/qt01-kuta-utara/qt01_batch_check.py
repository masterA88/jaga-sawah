"""QT-01 step 9b: check batch verdicts against Overture footprints (share of each patch covered by buildings)."""
import json, warnings
import geopandas as gpd, pandas as pd
warnings.filterwarnings("ignore")
g = gpd.read_file("../../public/data/kandidat_kuta_utara.geojson").to_crs(32750)
g = g[g.luas_m2 >= 1000]
b = pd.read_parquet("overture_buildings_kuta_utara.parquet")
b = gpd.GeoDataFrame(b, geometry=gpd.GeoSeries.from_wkb(b.geometry), crs=4326).to_crs(32750)
inter = gpd.overlay(g[["patch_id", "geometry"]], b[["geometry"]], how="intersection")
cov = inter.dissolve("patch_id").area.rename("bld_m2")
g = g.set_index("patch_id").join(cov).fillna({"bld_m2": 0})
g["cover"] = g.bld_m2 / g.area
out = g.groupby("verdict").agg(n=("cover", "size"), cover_median=("cover", "median"),
                               share_ge_20pct=("cover", lambda s: (s >= 0.2).mean())).round(3)
print(out)
json.dump(out.reset_index().to_dict("records"), open("qt01_batch_check.json", "w"), indent=1)
