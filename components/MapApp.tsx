"use client";

import { useEffect, useMemo, useState } from "react";
import Map, { Layer, NavigationControl, Source, type MapLayerMouseEvent } from "react-map-gl/maplibre";
import { setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

type Status = "terverifikasi" | "perlu_tinjau" | "belum_diverifikasi" | "ditolak";

type Props = {
  patch_id: string;
  status: Status;
  verdict: string | null;
  confidence: number | null;
  alasan: string | null;
  chip: string | null;
  luas_m2: number;
  periode: string;
  tahun_bangunan: number | null;
};

type FC = GeoJSON.FeatureCollection<GeoJSON.Geometry, Props>;

const STATUS: Record<Status, { label: string; color: string }> = {
  terverifikasi: { label: "Terverifikasi AI", color: "#dc2626" },
  perlu_tinjau: { label: "Perlu tinjau petugas", color: "#f59e0b" },
  belum_diverifikasi: { label: "Belum diverifikasi", color: "#6b7280" },
  ditolak: { label: "Ditolak AI", color: "#2563eb" },
};

const VERDICT: Record<string, string> = {
  conversion: "Alih fungsi",
  already_built: "Sudah bangunan sejak 2018",
  harvest_or_fallow: "Masih sawah (panen atau bera)",
  flooding: "Genangan",
  cloud_artifact: "Awan atau cacat citra",
  unclear: "Belum jelas",
};

export default function MapApp() {
  const [kandidat, setKandidat] = useState<FC | null>(null);
  const [lsd, setLsd] = useState<GeoJSON.FeatureCollection | null>(null);
  const [batas, setBatas] = useState<GeoJSON.FeatureCollection | null>(null);
  const [show, setShow] = useState<Record<Status, boolean>>({
    terverifikasi: true,
    perlu_tinjau: true,
    belum_diverifikasi: true,
    ditolak: false,
  });
  const [picked, setPicked] = useState<Props | null>(null);

  useEffect(() => {
    const get = (f: string) => fetch(`/data/${f}`).then((r) => (r.ok ? r.json() : null));
    get("kandidat_badung.geojson").then(setKandidat);
    get("lsd_badung.geojson").then(setLsd);
    get("batas_badung.geojson").then(setBatas);
  }, []);

  const stats = useMemo(() => {
    const s = {} as Record<Status, { n: number; ha: number }>;
    (Object.keys(STATUS) as Status[]).forEach((k) => (s[k] = { n: 0, ha: 0 }));
    kandidat?.features.forEach((f) => {
      const st = s[f.properties.status];
      st.n += 1;
      st.ha += f.properties.luas_m2 / 1e4;
    });
    return s;
  }, [kandidat]);

  // patches are a few hundred m2, invisible at regency zoom; show them as points until zoom 13
  const points = useMemo<GeoJSON.FeatureCollection | null>(() => {
    if (!kandidat) return null;
    return {
      type: "FeatureCollection",
      features: kandidat.features.map((f) => {
        const g = f.geometry;
        const ring = (g.type === "Polygon" ? g.coordinates[0] : g.type === "MultiPolygon" ? g.coordinates[0][0] : []) as number[][];
        const lon = ring.reduce((a, c) => a + c[0], 0) / Math.max(ring.length, 1);
        const lat = ring.reduce((a, c) => a + c[1], 0) / Math.max(ring.length, 1);
        return { type: "Feature", properties: f.properties, geometry: { type: "Point", coordinates: [lon, lat] } };
      }),
    };
  }, [kandidat]);

  const filter = useMemo(
    () => ["in", ["get", "status"], ["literal", (Object.keys(show) as Status[]).filter((k) => show[k])]],
    [show],
  );

  const onClick = (e: MapLayerMouseEvent) => {
    const f = e.features?.[0];
    setPicked(f ? (f.properties as unknown as Props) : null);
  };

  return (
    <div className="flex h-dvh flex-col md:flex-row">
      <aside className="w-full shrink-0 overflow-y-auto border-b border-neutral-200 bg-white p-4 text-sm text-neutral-800 md:h-full md:w-96 md:border-r md:border-b-0">
        <h1 className="text-xl font-bold text-green-800">JAGA SAWAH</h1>
        <p className="mt-1 text-neutral-600">
          Peringatan dini alih fungsi Lahan Sawah yang Dilindungi (LSD). Wilayah: Kabupaten Badung, periode 2018 ke
          2023.
        </p>

        <div className="mt-4 rounded-lg bg-green-50 p-3">
          <div className="text-xs uppercase tracking-wide text-green-800">Bangunan baru di LSD, 2018 ke 2023</div>
          <div className="text-2xl font-semibold text-green-900">± 87 ha</div>
          <div className="text-xs text-neutral-600">
            dari 8.599 ha LSD Badung, menurut Google Open Buildings Temporal. Belum termasuk tanah urug dan bangunan
            2024 sampai 2025.
          </div>
        </div>

        <h2 className="mt-4 font-semibold">Kandidat per status</h2>
        <ul className="mt-2 space-y-1">
          {(Object.keys(STATUS) as Status[]).map((k) => (
            <li key={k}>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={show[k]}
                  onChange={() => setShow({ ...show, [k]: !show[k] })}
                />
                <span className="inline-block h-3 w-3 rounded-sm" style={{ background: STATUS[k].color }} />
                <span className="flex-1">{STATUS[k].label}</span>
                <span className="tabular-nums text-neutral-500">
                  {stats[k].n} · {stats[k].ha.toFixed(1)} ha
                </span>
              </label>
            </li>
          ))}
        </ul>

        {picked ? (
          <div className="mt-4 rounded-lg border border-neutral-200 p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs">{picked.patch_id}</span>
              <span
                className="rounded px-2 py-0.5 text-xs text-white"
                style={{ background: STATUS[picked.status].color }}
              >
                {STATUS[picked.status].label}
              </span>
            </div>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              <dt className="text-neutral-500">Luas</dt>
              <dd>{Math.round(picked.luas_m2).toLocaleString("id-ID")} m²</dd>
              <dt className="text-neutral-500">Periode</dt>
              <dd>{picked.periode}</dd>
              {picked.tahun_bangunan != null && (
                <>
                  <dt className="text-neutral-500">Bangunan muncul</dt>
                  <dd>sekitar {picked.tahun_bangunan} (Open Buildings Temporal)</dd>
                </>
              )}
              {picked.verdict && (
                <>
                  <dt className="text-neutral-500">Putusan AI</dt>
                  <dd>
                    {VERDICT[picked.verdict] ?? picked.verdict}
                    {picked.confidence != null && ` (keyakinan ${Math.round(picked.confidence * 100)}%)`}
                  </dd>
                </>
              )}
            </dl>
            {picked.alasan && <p className="mt-2 text-neutral-700">{picked.alasan}</p>}
            {picked.chip && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`/data/chips_badung/${picked.chip}`}
                alt={`Citra Sentinel-2 2018, 2023, 2025 untuk ${picked.patch_id}`}
                className="mt-2 w-full rounded"
              />
            )}
          </div>
        ) : (
          <p className="mt-4 text-neutral-500">Klik sebuah kandidat di peta untuk melihat detail dan citra.</p>
        )}

        <p className="mt-4 text-xs text-neutral-500">
          Hasil ini indikasi dari citra satelit 10 m dan AI, bukan putusan hukum. Setiap kandidat wajib ditinjau
          petugas sebelum ada tindakan. Citra: Copernicus Sentinel (2018 sampai 2025). Peta LSD: BIG Satu Peta.
          Bangunan: Google Open Buildings Temporal (CC BY 4.0).
        </p>
      </aside>

      <main className="relative min-h-[60vh] flex-1">
        <Map
          initialViewState={{ longitude: 115.19, latitude: -8.53, zoom: 11 }}
          mapStyle="https://tiles.openfreemap.org/styles/liberty"
          interactiveLayerIds={["kandidat-fill", "kandidat-pt"]}
          onClick={onClick}
          cursor="pointer"
        >
          <NavigationControl position="top-right" />
          {lsd && (
            <Source id="lsd" type="geojson" data={lsd}>
              <Layer id="lsd-fill" type="fill" paint={{ "fill-color": "#16a34a", "fill-opacity": 0.18 }} />
              <Layer id="lsd-line" type="line" paint={{ "line-color": "#15803d", "line-width": 0.6 }} />
            </Source>
          )}
          {batas && (
            <Source id="batas" type="geojson" data={batas}>
              <Layer id="batas-line" type="line" paint={{ "line-color": "#111827", "line-width": 2 }} />
            </Source>
          )}
          {kandidat && (
            <Source id="kandidat" type="geojson" data={kandidat}>
              <Layer
                id="kandidat-fill"
                type="fill"
                filter={filter as never}
                paint={{
                  "fill-color": [
                    "match",
                    ["get", "status"],
                    "terverifikasi", STATUS.terverifikasi.color,
                    "perlu_tinjau", STATUS.perlu_tinjau.color,
                    "ditolak", STATUS.ditolak.color,
                    STATUS.belum_diverifikasi.color,
                  ],
                  "fill-opacity": 0.75,
                }}
              />
            </Source>
          )}
          {points && (
            <Source id="kandidat-titik" type="geojson" data={points}>
              <Layer
                id="kandidat-pt"
                type="circle"
                maxzoom={13}
                filter={filter as never}
                paint={{
                  "circle-radius": ["interpolate", ["linear"], ["zoom"], 9, 2.5, 13, 5],
                  "circle-color": [
                    "match",
                    ["get", "status"],
                    "terverifikasi", STATUS.terverifikasi.color,
                    "perlu_tinjau", STATUS.perlu_tinjau.color,
                    "ditolak", STATUS.ditolak.color,
                    STATUS.belum_diverifikasi.color,
                  ],
                  "circle-stroke-color": "#ffffff",
                  "circle-stroke-width": 0.8,
                }}
              />
            </Source>
          )}
        </Map>
      </main>
    </div>
  );
}
