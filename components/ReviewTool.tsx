"use client";

import { useEffect, useState } from "react";

type Item = { id: string; img: string; lat: number; lon: number };
type Answer = "alih_fungsi" | "masih_hijau" | "sudah_bangunan_2018" | "ragu";

const CHOICES: { key: Answer; label: string; hint: string }[] = [
  { key: "alih_fungsi", label: "1 · Alih fungsi", hint: "hijau pada 2018, lalu bangunan, tanah urug, jalan, atau perkerasan" },
  { key: "masih_hijau", label: "2 · Masih sawah / hijau", hint: "tetap lahan bervegetasi, termasuk panen atau bera" },
  { key: "sudah_bangunan_2018", label: "3 · Sudah bangunan sejak 2018", hint: "kotak sudah berisi atap atau permukiman pada 2018" },
  { key: "ragu", label: "4 · Ragu", hint: "tidak bisa diputuskan dari citra 10 m" },
];
const STORE = "jaga-sawah-tinjau-v1";

function load(): Record<string, Answer> {
  try {
    return JSON.parse(localStorage.getItem(STORE) ?? "{}");
  } catch {
    return {};
  }
}

export default function ReviewTool() {
  const [items, setItems] = useState<Item[]>([]);
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [i, setI] = useState(0);

  useEffect(() => {
    fetch("/data/tinjau/items.json")
      .then((r) => (r.ok ? r.json() : []))
      .then((d: Item[]) => {
        const saved = load();
        setItems(d);
        setAnswers(saved);
        const first = d.findIndex((it) => !saved[it.id]);
        setI(first === -1 ? 0 : first);
      });
  }, []);

  const answer = (a: Answer) => {
    const it = items[i];
    if (!it) return;
    const next = { ...answers, [it.id]: a };
    setAnswers(next);
    try {
      localStorage.setItem(STORE, JSON.stringify(next));
    } catch {
      // storage can be blocked; answers stay in memory and can still be downloaded
    }
    setI((v) => Math.min(v + 1, items.length - 1));
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const n = Number(e.key);
      if (n >= 1 && n <= 4) answer(CHOICES[n - 1].key);
      if (e.key === "ArrowLeft") setI((v) => Math.max(v - 1, 0));
      if (e.key === "ArrowRight") setI((v) => Math.min(v + 1, items.length - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const download = () => {
    const blob = new Blob([JSON.stringify(answers, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "tinjau_hasil.json";
    a.click();
  };

  if (!items.length) return <p className="p-6 text-sm text-neutral-500">Memuat data tinjauan...</p>;
  const it = items[i];
  const done = Object.keys(answers).length;

  return (
    <div className="mx-auto max-w-4xl p-4 text-neutral-800">
      <h1 className="text-xl font-bold text-green-800">Tinjau kandidat JAGA SAWAH</h1>
      <p className="mt-1 text-sm text-neutral-600">
        Lihat kotak merah pada citra Sentinel-2 2018, 2023, dan 2025, lalu pilih jawaban. Tombol keyboard 1 sampai 4
        juga bisa dipakai, panah kiri dan kanan untuk berpindah. Jangan memakai Google Earth atau Google Maps untuk
        mengecek.
      </p>
      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="font-mono">
          {it.id} · {i + 1} / {items.length}
        </span>
        <span>
          Terjawab {done} / {items.length}
        </span>
      </div>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={it.img} alt={`Citra Sentinel-2 untuk ${it.id}`} className="mt-2 w-full rounded border" />
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {CHOICES.map((c) => (
          <button
            key={c.key}
            onClick={() => answer(c.key)}
            className={`rounded-lg border p-3 text-left ${
              answers[it.id] === c.key ? "border-green-700 bg-green-50" : "border-neutral-300 hover:bg-neutral-50"
            }`}
          >
            <div className="font-semibold">{c.label}</div>
            <div className="text-xs text-neutral-500">{c.hint}</div>
          </button>
        ))}
      </div>
      <div className="mt-4 flex gap-2">
        <button onClick={() => setI(Math.max(i - 1, 0))} className="rounded border px-3 py-1 text-sm">
          Sebelumnya
        </button>
        <button onClick={() => setI(Math.min(i + 1, items.length - 1))} className="rounded border px-3 py-1 text-sm">
          Berikutnya
        </button>
        <button
          onClick={download}
          className="ml-auto rounded bg-green-700 px-3 py-1 text-sm text-white disabled:opacity-50"
          disabled={!done}
        >
          Unduh hasil ({done})
        </button>
      </div>
    </div>
  );
}
