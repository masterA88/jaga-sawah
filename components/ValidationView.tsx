"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Case = {
  key: string;
  title: string;
  news: string;
  links: string[];
  lsd_ha: number;
  kandidat_2018_2023: { n: number; ha: number; terverifikasi: number };
  kandidat_2023_2025: { n: number; ha: number };
};

type Data = {
  headline: {
    precision: number;
    recall: number;
    average_precision: number;
    prevalence: number;
    obt_new_building_ha: number;
    lsd_ha: number;
    precision_at_0_9: number;
    recall_at_0_9: number;
    folds: { precision: number; recall: number; tiles: number }[];
  };
  method: string[];
  baselines: { name: string; result: string }[];
  claude: { verified: number; verdicts: Record<string, number>; cost_usd: number; status_n: Record<string, number> };
  cases: Case[];
  badung_share: { kandidat_2018_2023_pct: number };
  review: Record<string, { n: number; share_alih_fungsi_of_decided: number }> | null;
  limits: string[];
};

const pct = (v: number) => `${Math.round(v * 100)}%`;
const id = (v: number, d = 1) => v.toLocaleString("id-ID", { maximumFractionDigits: d });

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 p-4">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-green-900">{value}</div>
      <div className="mt-1 text-xs text-neutral-600">{note}</div>
    </div>
  );
}

export default function ValidationView() {
  const [d, setD] = useState<Data | null>(null);
  useEffect(() => {
    fetch("/data/validasi.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setD);
  }, []);
  if (!d) return <p className="p-6 text-sm text-neutral-500">Memuat validasi...</p>;
  const h = d.headline;
  const share = d.badung_share.kandidat_2018_2023_pct;

  return (
    <main className="mx-auto max-w-5xl p-4 pb-16 text-neutral-800">
      <Link href="/" className="text-sm text-green-800 underline">
        ← Kembali ke peta
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-green-800">Seberapa bisa dipercaya JAGA SAWAH?</h1>
      <p className="mt-1 text-neutral-600">
        Semua angka di halaman ini diukur terhadap data yang tidak dipakai untuk membuat model, di seluruh{" "}
        {id(h.lsd_ha, 0)} ha Lahan Sawah yang Dilindungi (LSD) Kabupaten Badung, periode 2018 ke 2023.
      </p>

      <section className="mt-6 grid gap-3 sm:grid-cols-3">
        <Stat
          label="Presisi"
          value={pct(h.precision)}
          note={`dari setiap 10 alarm, sekitar ${Math.round(h.precision * 10)} terbukti bangunan baru (batas bawah)`}
        />
        <Stat
          label="Recall"
          value={pct(h.recall)}
          note={`sekitar ${Math.round(h.recall * 10)} dari 10 bangunan baru di LSD tertangkap`}
        />
        <Stat
          label="Bangunan baru di LSD"
          value={`± ${id(h.obt_new_building_ha, 0)} ha`}
          note="2018 ke 2023, menurut Google Open Buildings Temporal"
        />
      </section>
      <p className="mt-2 text-xs text-neutral-500">
        Average precision {id(h.average_precision, 2)}. Untuk daftar prioritas petugas (ambang 0,9): presisi{" "}
        {pct(h.precision_at_0_9)}, recall {pct(h.recall_at_0_9)}. Hanya {pct(h.prevalence)} piksel LSD yang berubah
        menjadi bangunan, jadi tebakan acak hanya benar sekitar {pct(h.prevalence)} kali.
      </p>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Cara mengukur</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
          {d.method.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ol>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-neutral-500">
              <tr>
                <th className="py-1 pr-4 font-normal">Kelompok wilayah uji</th>
                <th className="py-1 pr-4 font-normal">Tile</th>
                <th className="py-1 pr-4 font-normal">Presisi</th>
                <th className="py-1 font-normal">Recall</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {h.folds.map((f, i) => (
                <tr key={i} className="border-t border-neutral-100">
                  <td className="py-1 pr-4">Kelompok {i + 1}</td>
                  <td className="py-1 pr-4">{f.tiles}</td>
                  <td className="py-1 pr-4">{pct(f.precision)}</td>
                  <td className="py-1">{pct(f.recall)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Dibandingkan dengan apa?</h2>
        <ul className="mt-2 space-y-2 text-sm">
          {d.baselines.map((b) => (
            <li key={b.name} className="rounded border border-neutral-200 p-3">
              <div className="font-medium">{b.name}</div>
              <div className="text-neutral-600">{b.result}</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Cocok dengan kasus yang diberitakan</h2>
        <p className="mt-1 text-sm text-neutral-600">
          Rata-rata Badung: kandidat 2018 ke 2023 mencakup {id(share, 2)}% LSD. Dua desa yang kasusnya diberitakan
          menonjol jauh di atas rata-rata.
        </p>
        <div className="mt-3 space-y-6">
          {d.cases.map((c) => {
            const p1 = (100 * c.kandidat_2018_2023.ha) / c.lsd_ha;
            const p2 = (100 * c.kandidat_2023_2025.ha) / c.lsd_ha;
            return (
              <div key={c.key} className="rounded-lg border border-neutral-200 p-4">
                <h3 className="font-semibold">{c.title}</h3>
                <p className="mt-1 text-sm text-neutral-700">{c.news}</p>
                <div className="mt-1 flex flex-wrap gap-3 text-xs">
                  {c.links.map((l) => (
                    <a key={l} href={l} target="_blank" rel="noreferrer" className="text-green-800 underline">
                      sumber berita
                    </a>
                  ))}
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                  <div>
                    <dt className="text-neutral-500">LSD di desa</dt>
                    <dd>{id(c.lsd_ha)} ha</dd>
                  </div>
                  <div>
                    <dt className="text-neutral-500">Kandidat 2018 ke 2023</dt>
                    <dd>
                      {c.kandidat_2018_2023.n} petak, {id(p1)}% LSD ({id(p1 / share)}× rata-rata)
                    </dd>
                  </div>
                  <div>
                    <dt className="text-neutral-500">Terverifikasi AI</dt>
                    <dd>{c.kandidat_2018_2023.terverifikasi} petak</dd>
                  </div>
                  <div>
                    <dt className="text-neutral-500">Kandidat 2023 ke 2025</dt>
                    <dd>
                      {c.kandidat_2023_2025.n} petak, {id(p2)}% LSD
                    </dd>
                  </div>
                </dl>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`/data/validasi/case_${c.key}.png`}
                  alt={`Citra Sentinel-2 ${c.title} 2018, 2023, 2025 dengan kandidat`}
                  className="mt-3 w-full rounded border"
                />
              </div>
            );
          })}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Peran AI verifikasi</h2>
        <p className="mt-1 text-sm text-neutral-700">
          {d.claude.verified} kandidat diperiksa AI verifikasi (biaya US${d.claude.cost_usd.toFixed(2)}). Hasilnya:{" "}
          {d.claude.verdicts.conversion} alih fungsi, {d.claude.verdicts.unclear} perlu tinjau,{" "}
          {d.claude.verdicts.already_built} sudah bangunan sejak 2018 (kesalahan peta LSD), dan sisanya ditolak.
          AI verifikasi menjelaskan setiap kandidat dalam bahasa Indonesia dan memilah mana yang perlu dicek petugas.
          Langkah ini tidak menaikkan presisi deteksi, dan kami tidak mengklaimnya.
        </p>
      </section>

      {d.review && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">Tinjauan manusia (buta)</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {Object.entries(d.review).map(([k, v]) => (
              <li key={k}>
                {k}: {v.n} item, {pct(v.share_alih_fungsi_of_decided)} dinilai alih fungsi
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-8">
        <h2 className="text-lg font-semibold">Batasan yang kami ketahui</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
          {d.limits.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
