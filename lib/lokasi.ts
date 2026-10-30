// Server-side lookup of a point against the LSD polygons (data/, never served publicly, bible Q-09) and the
// candidate patches (public/data). Only the answer for one point leaves the server, never the polygons.
import { readFileSync } from "node:fs";
import path from "node:path";

type Ring = number[][];
type Poly = Ring[];
type Feat = { props: Record<string, unknown>; polys: Poly[]; bbox: [number, number, number, number] };

function toFeats(file: string): Feat[] {
  const fc = JSON.parse(readFileSync(file, "utf8")) as GeoJSON.FeatureCollection;
  const out: Feat[] = [];
  for (const f of fc.features) {
    const g = f.geometry as GeoJSON.Geometry | null;
    // skip empty or non-areal geometries (simplification can leave empty rings)
    if (!g || (g.type !== "Polygon" && g.type !== "MultiPolygon")) continue;
    const polys = ((g.type === "Polygon" ? [g.coordinates] : g.coordinates) as Poly[]).filter((p) => p.length && p[0]?.length);
    if (!polys.length) continue;
    let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
    for (const p of polys) for (const [x, y] of p[0]) {
      x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
    }
    out.push({ props: (f.properties ?? {}) as Record<string, unknown>, polys, bbox: [x0, y0, x1, y1] });
  }
  return out;
}

function inRing(x: number, y: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function inFeat(x: number, y: number, f: Feat, pad = 0): boolean {
  const [x0, y0, x1, y1] = f.bbox;
  if (x < x0 - pad || x > x1 + pad || y < y0 - pad || y > y1 + pad) return false;
  return f.polys.some((p) => inRing(x, y, p[0]) && !p.slice(1).some((h) => inRing(x, y, h)));
}

let cache: { lsd: Feat[]; batas: Feat[]; kandidat: Record<string, Feat[]> } | null = null;

function load() {
  if (!cache) {
    const root = process.cwd();
    cache = {
      lsd: toFeats(path.join(root, "data", "lsd_badung.geojson")),
      batas: toFeats(path.join(root, "public", "data", "batas_badung.geojson")),
      kandidat: {
        "2018-2023": toFeats(path.join(root, "public", "data", "kandidat_badung.geojson")),
        "2023-2025": toFeats(path.join(root, "public", "data", "kandidat_badung_2023_2025.geojson")),
      },
    };
  }
  return cache;
}

export type KonteksLokasi = {
  dalam_badung: boolean;
  dalam_lsd: boolean;
  kandidat: { periode: string; patch_id: unknown; status: unknown; verdict: unknown; alasan: unknown; luas_m2: unknown }[];
};

export function konteksLokasi(lat: number, lon: number): KonteksLokasi {
  const d = load();
  const pad = 0.0005; // about 50 m: a click near a patch still counts
  const kandidat: KonteksLokasi["kandidat"] = [];
  for (const [periode, feats] of Object.entries(d.kandidat)) {
    for (const f of feats) {
      if (dekat(lon, lat, f, pad)) {
        const p = f.props;
        kandidat.push({ periode, patch_id: p.patch_id, status: p.status, verdict: p.verdict, alasan: p.alasan, luas_m2: p.luas_m2 });
      }
    }
  }
  return {
    dalam_badung: d.batas.some((f) => inFeat(lon, lat, f)),
    dalam_lsd: d.lsd.some((f) => inFeat(lon, lat, f)),
    kandidat: kandidat.slice(0, 5),
  };
}

// within the patch's bounding box plus pad; patches are small, so this is close enough for "near a candidate"
function dekat(x: number, y: number, f: Feat, pad: number): boolean {
  const [x0, y0, x1, y1] = f.bbox;
  return x >= x0 - pad && x <= x1 + pad && y >= y0 - pad && y <= y1 + pad;
}
