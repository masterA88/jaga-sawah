"use client";

import { useState } from "react";

type Pasal = { id: string; sumber: string; pasal: string; isi: string; syarat?: string };
type Konteks = { dalam_badung: boolean; dalam_lsd: boolean; kandidat: { periode: string; status: string }[] };
type Cek = { konteks?: Konteks; jawaban?: { status_lokasi: string; ringkasan: string; pasal: Pasal[]; saran: string }; galat?: string };
type Lapor = {
  konteks?: Konteks;
  triase?: { kategori: string; tanda_terlihat: string[]; keyakinan: number; alasan: string; prioritas: string };
  galat?: string;
};

export type Mode = "lihat" | "cek" | "lapor";

const KATEGORI: Record<string, string> = {
  indikasi_alih_fungsi: "Ada indikasi alih fungsi",
  sawah_normal: "Sawah normal",
  bukan_sawah: "Bukan lahan sawah",
  foto_tidak_jelas: "Foto tidak bisa dinilai",
};
const PRIORITAS: Record<string, string> = { tinggi: "bg-red-600", sedang: "bg-amber-500", rendah: "bg-neutral-500" };

function Fakta({ k }: { k: Konteks }) {
  return (
    <ul className="mt-2 space-y-0.5 text-xs text-neutral-600">
      <li>{k.dalam_badung ? "Di dalam Kabupaten Badung" : "Di luar Kabupaten Badung"}</li>
      <li>{k.dalam_lsd ? "Di dalam Lahan Sawah yang Dilindungi" : "Di luar Lahan Sawah yang Dilindungi"}</li>
      <li>{k.kandidat.length ? `${k.kandidat.length} kandidat alih fungsi di dekatnya` : "Tidak ada kandidat di dekatnya"}</li>
    </ul>
  );
}

export function PasalList({ pasal }: { pasal: Pasal[] }) {
  if (!pasal.length) return null;
  return (
    <details className="mt-2 text-xs">
      <summary className="cursor-pointer text-green-800">Dasar aturan ({pasal.length})</summary>
      <ul className="mt-1 space-y-1">
        {pasal.map((p) => (
          <li key={p.id} className="rounded bg-neutral-50 p-2">
            <div className="font-semibold">
              {p.sumber}, {p.pasal}
            </div>
            <div className="text-neutral-700">&ldquo;{p.isi}&rdquo;</div>
            {p.syarat && <div className="mt-1 text-amber-800">Syarat: {p.syarat}</div>}
          </li>
        ))}
      </ul>
    </details>
  );
}

export async function mintaCek(titik: { lat: number; lon: number }): Promise<Cek> {
  try {
    const r = await fetch("/api/cek-lokasi", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(titik),
    });
    return await r.json();
  } catch {
    return { galat: "Tidak bisa menghubungi server." };
  }
}

export type { Cek };

type PanelProps = { mode: Mode; titik: { lat: number; lon: number } | null; cek: Cek | null; cekLoading: boolean };

export default function AiPanel({ mode, titik, cek, cekLoading }: PanelProps) {
  const [lapor, setLapor] = useState<Lapor | null>(null);
  const [loading, setLoading] = useState(false);
  const [foto, setFoto] = useState<File | null>(null);
  const [catatan, setCatatan] = useState("");

  const kirim = async () => {
    if (!titik || !foto) return;
    setLoading(true);
    setLapor(null);
    const fd = new FormData();
    fd.set("foto", foto);
    fd.set("lat", String(titik.lat));
    fd.set("lon", String(titik.lon));
    fd.set("catatan", catatan);
    try {
      setLapor(await (await fetch("/api/lapor", { method: "POST", body: fd })).json());
    } catch {
      setLapor({ galat: "Tidak bisa menghubungi server." });
    } finally {
      setLoading(false);
    }
  };

  if (mode === "lihat") return null;
  const loc = titik ? `${titik.lat.toFixed(5)}, ${titik.lon.toFixed(5)}` : null;

  return (
    <div className="mt-4 rounded-lg border border-green-700 p-3">
      {mode === "cek" ? (
        <>
          <div className="font-semibold">Cek lokasi dengan AI</div>
          <p className="text-xs text-neutral-600">Klik titik mana pun di peta. AI menjelaskan statusnya dan dasar aturannya.</p>
          {loc && <div className="mt-1 font-mono text-xs">{loc}</div>}
          {cekLoading && <p className="mt-2 text-sm text-neutral-500">AI sedang menilai...</p>}
          {cek?.konteks && <Fakta k={cek.konteks} />}
          {cek?.jawaban && (
            <>
              <p className="mt-2 text-sm">{cek.jawaban.ringkasan}</p>
              <p className="mt-1 text-sm font-medium">{cek.jawaban.saran}</p>
              <PasalList pasal={cek.jawaban.pasal} />
            </>
          )}
          {cek?.galat && <p className="mt-2 text-sm text-red-700">{cek.galat}</p>}
        </>
      ) : (
        <>
          <div className="font-semibold">Lapor dugaan alih fungsi</div>
          <p className="text-xs text-neutral-600">
            Klik lokasi di peta, unggah foto lapangan, lalu kirim. AI menyaring laporan dan memberi prioritas. Foto
            tidak disimpan.
          </p>
          <div className="mt-1 font-mono text-xs">{loc ?? "Belum ada lokasi"}</div>
          <label className="mt-2 flex cursor-pointer items-center justify-between gap-2 rounded-lg border border-dashed border-green-700 px-3 py-2 text-sm text-green-800 hover:bg-green-50">
            <span className="truncate">{foto ? foto.name : "Pilih foto lapangan"}</span>
            <span className="shrink-0 text-xs text-neutral-500">JPG, PNG, WebP, maks. 4 MB</span>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(e) => setFoto(e.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>
          <textarea
            value={catatan}
            onChange={(e) => setCatatan(e.target.value)}
            maxLength={500}
            placeholder="Catatan (opsional), misalnya: ada truk tanah sejak minggu lalu"
            className="mt-2 w-full rounded border border-neutral-300 p-2 text-xs"
            rows={2}
          />
          <button
            onClick={kirim}
            disabled={!titik || !foto || loading}
            className="mt-2 w-full rounded bg-green-700 px-3 py-1.5 text-sm text-white disabled:opacity-50"
          >
            {loading ? "AI sedang menilai..." : "Kirim laporan"}
          </button>
          {lapor?.triase && (
            <div className="mt-3 text-sm">
              <div className="flex items-center gap-2">
                <span className={`rounded px-2 py-0.5 text-xs text-white ${PRIORITAS[lapor.triase.prioritas] ?? "bg-neutral-500"}`}>
                  Prioritas {lapor.triase.prioritas}
                </span>
                <span className="font-medium">{KATEGORI[lapor.triase.kategori] ?? lapor.triase.kategori}</span>
              </div>
              <p className="mt-1">{lapor.triase.alasan}</p>
              {!!lapor.triase.tanda_terlihat.length && (
                <ul className="mt-1 list-disc pl-4 text-xs text-neutral-600">
                  {lapor.triase.tanda_terlihat.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              )}
              {lapor.konteks && <Fakta k={lapor.konteks} />}
            </div>
          )}
          {lapor?.galat && <p className="mt-2 text-sm text-red-700">{lapor.galat}</p>}
        </>
      )}
    </div>
  );
}
