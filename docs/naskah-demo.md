# Naskah demo JAGA SAWAH (3 menit)

Penulis: Hilmi (https://master-hilmi.vercel.app/)

Urutan ini mengikuti bobot rubrik final: AI 25%, fungsionalitas 25%, masalah dan solusi 15%, inovasi 15%. Angka diambil dari halaman `/validasi`; kalau angkanya berubah, ikuti halaman itu.

## 0:00 sampai 0:30 · Masalah

> "Bali kehilangan sawah ke villa dan perumahan, termasuk di Lahan Sawah yang Dilindungi. Pemda baru tahu setelah bangunan berdiri, biasanya dari laporan warga atau berita. Contohnya Subak Munggu bulan September lalu dan 30 villa di Babakan Canggu awal tahun ini."

Tampilkan peta Badung di halaman utama.

## 0:30 sampai 1:30 · Produk

1. Peta dibuka pada seluruh LSD Badung (8.599 ha). Titik merah berarti terverifikasi AI, oranye perlu ditinjau petugas.
   > "Setiap titik adalah petak sawah yang berubah antara 2018 dan 2023."
2. Zoom ke Canggu, lalu klik satu titik merah. Panel menampilkan luas, putusan AI, alasan dalam bahasa Indonesia, dan citra 2018, 2023, 2025.
   > "Petugas tidak perlu membaca citra satelit. Claude menjelaskan apa yang berubah dan menandai mana yang perlu dicek."
3. Ganti periode ke 2023 ke 2025.
   > "Model yang sama menghasilkan alarm terbaru. Ini yang dipakai petugas setiap bulan."

## 1:30 sampai 2:30 · Apakah bisa dipercaya

Buka `/validasi`.

> "Kami tidak menilai model dengan data kami sendiri. Pembandingnya data bangunan tahunan Google, dan setiap wilayah dinilai oleh model yang belum pernah melihatnya. Dari 10 alarm, sekitar 6 terbukti bangunan baru, dan itu batas bawah, karena tanah urug belum tercatat sebagai bangunan. Dua desa yang kasusnya diberitakan menonjol di peta kami: Canggu sekitar 6 kali rata-rata Badung."

Tunjukkan gambar studi kasus Canggu.

## 2:30 sampai 3:00 · AI dan dampak

> "Ada tiga lapis AI: foundation model AlphaEarth dari Google DeepMind, model deteksi perubahan dengan Sentinel-1 dan Sentinel-2, dan Claude untuk verifikasi dan penjelasan. Satu putaran untuk seluruh Badung butuh sekitar 30 menit dan biaya AI sekitar Rp20 ribu. Claude juga menemukan 26 petak yang ternyata sudah berupa bangunan sejak 2018, artinya peta LSD sendiri perlu dikoreksi."

Tutup dengan:

> "JAGA SAWAH memberi Pemda daftar prioritas sebelum sawah hilang, bukan setelahnya."

## Pertanyaan juri yang mungkin muncul

| Pertanyaan | Jawaban singkat |
|---|---|
| Kenapa presisi hanya sekitar 56%? | Itu untuk bangunan baru saja dan dinilai di semua piksel, dengan hanya 1% yang berubah. Tebakan acak benar 1%. Sisa alarm kebanyakan lahan yang sudah kehilangan vegetasi (tanah urug, bangunan belum selesai). Untuk daftar prioritas, ambang 0,9 memberi presisi sekitar 65%. |
| Apakah Claude menaikkan akurasi? | Tidak, dan kami tidak mengklaimnya. Claude menjelaskan, memilah, dan menemukan kesalahan peta LSD. |
| Bagaimana dengan IDMAI Bappenas? | IDMAI memetakan dugaan alih fungsi secara nasional. JAGA SAWAH bekerja per kabupaten di dalam poligon LSD, dengan verifikasi AI, alasan per kandidat, dan validasi terbuka. |
| Data apa saja, dan berbayar? | Semua gratis: Sentinel-1 dan Sentinel-2, AlphaEarth, dan Open Buildings lewat Earth Engine (nonkomersial), peta LSD BIG, dan Claude API. |
| Apakah ini putusan hukum? | Bukan. Indikasi untuk ditinjau petugas. |

Catatan kurs: US$1,29 per putaran batch Claude untuk Badung, kurs sekitar Rp16.000 per dolar [perlu sumber: kurs saat presentasi].
