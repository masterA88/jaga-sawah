import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { z } from "zod";
import { ATURAN, ATURAN_IDS, aturanTeks } from "@/lib/aturan";
import { cekBatas, ipDari } from "@/lib/batas";
import { client, MODEL, pesanGalat } from "@/lib/claude";
import { konteksLokasi } from "@/lib/lokasi";

const Jawaban = z.object({
  status_lokasi: z.enum(["luar_badung", "luar_lsd", "lsd_tanpa_kandidat", "lsd_ada_kandidat"]),
  ringkasan: z.string(),
  pasal: z.array(z.enum(ATURAN_IDS)),
  saran: z.string(),
});

const SYSTEM = `Kamu asisten JAGA SAWAH untuk petugas Pemda Badung, subak, dan warga.
Kamu menerima fakta tentang satu titik di peta: apakah di dalam Kabupaten Badung, apakah di dalam Lahan Sawah
yang Dilindungi (LSD), dan kandidat alih fungsi di dekatnya hasil model satelit dan verifikasi AI.
Jelaskan arti fakta itu dalam 2 sampai 4 kalimat bahasa Indonesia yang sederhana. Jangan menambah fakta yang
tidak ada di data. Hasil model adalah indikasi, bukan putusan hukum; katakan itu bila ada kandidat.
Kamu tidak tahu apakah lahan sudah ditetapkan sebagai LP2B atau berada di zona pertanian RTRW/RDTR, karena data itu
belum ada. Jangan menyimpulkan bahwa suatu pasal pasti berlaku atau pasti tidak berlaku. Untuk pasal yang punya
syarat, sebut syaratnya di ringkasan. Titik di luar LSD masih bisa dilindungi Perda Bali 4/2026 Pasal 13 jika
berzona pertanian, jadi jangan katakan titik itu bebas dibangun.
Pilih pasal hanya dari daftar berikut, dan hanya yang relevan; boleh kosong:
${aturanTeks()}
saran: satu kalimat langkah berikutnya yang wajar, misalnya cek status LSD, LP2B, dan zona RTRW/RDTR ke Dinas
Pertanian dan Pangan atau Dinas PUPR Badung sebelum membangun atau membeli lahan, atau sampaikan ke subak.
Jangan menyarankan bahwa tidak perlu tindakan.`;

export async function POST(req: Request) {
  const body = (await req.json().catch(() => null)) as { lat?: unknown; lon?: unknown } | null;
  const lat = Number(body?.lat), lon = Number(body?.lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
    return Response.json({ galat: "Koordinat tidak valid." }, { status: 400 });
  }
  const konteks = konteksLokasi(lat, lon);
  const batas = cekBatas(ipDari(req));
  if (!batas.ok) return Response.json({ konteks, galat: batas.alasan }, { status: 429 });
  try {
    const res = await client.messages.parse({
      model: MODEL,
      max_tokens: 1500,
      system: SYSTEM,
      output_config: { effort: "low", format: zodOutputFormat(Jawaban) },
      messages: [{ role: "user", content: `Titik: ${lat.toFixed(6)}, ${lon.toFixed(6)}\nFakta: ${JSON.stringify(konteks)}` }],
    });
    if (res.stop_reason === "refusal" || !res.parsed_output) {
      return Response.json({ konteks, galat: "AI tidak memberi jawaban untuk titik ini." }, { status: 502 });
    }
    const out = res.parsed_output;
    return Response.json({
      konteks,
      jawaban: { ...out, pasal: out.pasal.map((id) => ATURAN.find((a) => a.id === id)) },
    });
  } catch (e) {
    const g = pesanGalat(e);
    return Response.json({ konteks, galat: g.pesan }, { status: g.status });
  }
}
