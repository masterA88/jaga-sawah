// Regulation excerpts Claude may cite. Claude can only pick ids from this list (enum in the output schema),
// so the article ids are fixed; the free-text fields of an answer are not. Perpres 4/2026: official PDF from
// peraturan.bpk.go.id (Details/347928), checked against the scanned pages. Perda Bali 4/2026: certified copy
// (Lembaran Daerah Provinsi Bali 2026 Nomor 4) from JDIH Provinsi Bali. Every quote was matched to its text;
// [...] marks an omitted cross-reference or clause. `syarat` states when an article applies, so the panel never
// shows a conditional article as if it applied to every point.

export type Aturan = { id: string; sumber: string; pasal: string; isi: string; syarat?: string };

export const ATURAN: Aturan[] = [
  {
    id: "perpres4_2026_p1_1",
    sumber: "Perpres 4/2026",
    pasal: "Pasal 1 angka 1",
    isi: "Lahan Sawah adalah areal tanah pertanian basah dan/atau kering yang digenangi air secara periodik dan/atau terus menerus ditanami padi dan/atau diselingi dengan tanaman semusim lainnya.",
  },
  {
    id: "perpres4_2026_p1_2",
    sumber: "Perpres 4/2026",
    pasal: "Pasal 1 angka 2",
    isi: "Alih Fungsi Lahan Sawah adalah perubahan Lahan Sawah menjadi bukan Lahan Sawah baik secara tetap maupun sementara.",
  },
  {
    id: "perpres4_2026_p17_1",
    sumber: "Perpres 4/2026",
    pasal: "Pasal 17 ayat (1)",
    isi: "Terhadap Lahan Sawah yang masuk dalam peta Lahan Sawah yang dilindungi [...] namun belum ditetapkan sebagai bagian dari penetapan kawasan/lahan pertanian pangan berkelanjutan dalam rencana tata ruang [...], tidak dapat dialihfungsikan sebelum mendapat rekomendasi perubahan penggunaan tanah dari menteri yang menyelenggarakan urusan pemerintahan di bidang pertanahan dan suburusan tata ruang yang merupakan lingkup urusan pemerintahan di bidang pekerjaan umum.",
    syarat: "Berlaku untuk LSD yang belum ditetapkan sebagai LP2B dalam rencana tata ruang. JAGA SAWAH belum memuat peta LP2B, jadi status ini perlu dicek ke Dinas.",
  },
  {
    id: "perpres4_2026_p23_3",
    sumber: "Perpres 4/2026",
    pasal: "Pasal 23 ayat (3)",
    isi: "Bupati/wali kota melakukan pembinaan dan pengawasan mengenai Pengendalian Alih Fungsi Lahan Sawah kepada masyarakat.",
  },
  {
    id: "perpres4_2026_p23_5",
    sumber: "Perpres 4/2026",
    pasal: "Pasal 23 ayat (5)",
    isi: "Pengawasan sebagaimana dimaksud pada ayat (1), ayat (2), dan ayat (3) dilakukan melalui pemantauan dan evaluasi.",
  },
  {
    id: "perdabali4_2026_p1_12",
    sumber: "Perda Bali 4/2026",
    pasal: "Pasal 1 angka 12",
    isi: "Alih Fungsi Lahan Produktif adalah perubahan fungsi lahan pertanian menjadi bukan lahan pertanian baik secara tetap maupun sementara.",
  },
  {
    id: "perdabali4_2026_p13_2",
    sumber: "Perda Bali 4/2026",
    pasal: "Pasal 13 ayat (1) dan (2)",
    isi: "Pemerintah Daerah wajib melindungi Lahan Produktif yang telah ditetapkan dalam rencana tata ruang. Lahan Produktif sebagaimana dimaksud pada ayat (1), dilarang dialihfungsikan.",
    syarat: "Menurut Penjelasan ayat (1), yang dilindungi adalah lahan berzona tanaman pangan, hortikultura, atau perkebunan dalam RTRW dan RDTR kabupaten. Zona ini tidak sama dengan LSD dan belum ada di JAGA SAWAH, jadi perlu dicek ke Dinas, termasuk untuk titik di luar LSD.",
  },
  {
    id: "perdabali4_2026_p13_3",
    sumber: "Perda Bali 4/2026",
    pasal: "Pasal 13 ayat (3)",
    isi: "Larangan alih fungsi sebagaimana dimaksud pada ayat (2), dikecualikan bagi: a. kebijakan nasional yang bersifat strategis; b. pengadaan tanah untuk kepentingan umum; dan/atau c. pengadaan tanah untuk relokasi akibat bencana alam.",
  },
  {
    id: "perdabali4_2026_p13_4",
    sumber: "Perda Bali 4/2026",
    pasal: "Pasal 13 ayat (4)",
    isi: "Larangan alih fungsi sebagaimana dimaksud pada ayat (3) yang dikecualikan dapat berlaku pada pemilik tanah yang kurang lahan untuk dibangun hanya difungsikan sebagai tempat tinggal.",
    syarat: "Relevan jika bangunannya rumah tinggal milik pemilik tanah yang kurang lahan. Citra satelit tidak bisa menentukan hal ini.",
  },
  {
    id: "perdabali4_2026_p17_2",
    sumber: "Perda Bali 4/2026",
    pasal: "Pasal 17 ayat (2) dan Pasal 18 ayat (1)",
    isi: "Pengawasan sebagaimana dimaksud pada ayat (1), meliputi: a. pemantauan dan evaluasi; dan b. pelaporan. Pengawasan [...] dilakukan paling sedikit 1 (satu) kali dalam 6 (enam) bulan.",
    syarat: "Pengawasan ini dikoordinasikan oleh dinas terkait yang diberi penugasan di bidangnya (Pasal 17 ayat (1)), dan hasilnya dilaporkan kepada Gubernur (Pasal 18 ayat (2)).",
  },
  {
    id: "perdabali4_2026_p20",
    sumber: "Perda Bali 4/2026",
    pasal: "Pasal 20 ayat (1), (2), dan (5)",
    isi: "Setiap Orang yang melanggar ketentuan sebagaimana dimaksud dalam Pasal 13 ayat (2) dan/atau Pasal 14, dikenai sanksi administratif. Sanksi administratif sebagaimana dimaksud pada ayat (1), berupa: a. peringatan tertulis; b. penghentian sementara kegiatan; c. penutupan lokasi; d. pencabutan izin; e. pembatalan izin; f. pembongkaran bangunan; g. pemulihan fungsi lahan; h. pencabutan Insentif; dan/atau i. denda administratif. Selain sanksi administratif [...], dapat dikenakan sanksi pidana sesuai dengan ketentuan peraturan perundang-undangan.",
    syarat: "Sanksi hanya berlaku jika terbukti melanggar Pasal 13 ayat (2) atau Pasal 14, jadi syarat zona pada Pasal 13 ayat (2) ikut berlaku.",
  },
  {
    id: "perdabali4_2026_p24",
    sumber: "Perda Bali 4/2026",
    pasal: "Pasal 24 ayat (1) dan (2)",
    isi: "Subak dan Desa Adat berperan serta dalam Pengendalian Alih Fungsi Lahan Produktif dan Larangan Alih Kepemilikan Lahan secara Nomine. Peran serta Subak dan Desa Adat menjadi tim pengawasan sebagaimana dimaksud dalam Pasal 19.",
  },
];

export const ATURAN_IDS = ATURAN.map((a) => a.id) as [string, ...string[]];

export function aturanTeks(): string {
  return ATURAN.map((a) => `[${a.id}] ${a.sumber} ${a.pasal}: "${a.isi}"${a.syarat ? ` Syarat: ${a.syarat}` : ""}`).join("\n");
}
