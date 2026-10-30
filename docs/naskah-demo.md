# Naskah demo JAGA SAWAH (3 menit)

Penulis: Hilmi (https://master-hilmi.vercel.app/)

Urutan ini mengikuti bobot rubrik final: AI 25%, fungsionalitas 25%, masalah dan solusi 15%, inovasi 15%. Angka diambil dari halaman `/validasi`; kalau angkanya berubah, ikuti halaman itu.

## 0:00 sampai 0:30 · Masalah

> "Bali kehilangan sawah ke villa dan perumahan, termasuk di Lahan Sawah yang Dilindungi. Pemda baru tahu setelah bangunan berdiri, biasanya dari laporan warga atau berita. Contohnya Subak Munggu bulan September lalu dan sekitar 30 vila di Babakan Canggu yang dihentikan akhir Desember 2025."

Tampilkan peta Badung di halaman utama.

## 0:30 sampai 1:30 · Produk

1. Peta dibuka pada seluruh LSD Badung (8.599 ha). Titik merah berarti terverifikasi AI, oranye perlu ditinjau petugas.
   > "Setiap titik adalah kandidat: petak sawah yang kemungkinan berubah antara 2018 dan 2023, untuk dicek petugas."
2. Zoom ke Canggu, lalu klik satu titik merah. Panel menampilkan luas, putusan AI, alasan dalam bahasa Indonesia, dan citra 2018, 2023, 2025.
   > "Petugas tidak perlu membaca citra satelit. AI menjelaskan apa yang berubah dan menandai mana yang perlu dicek."
3. Ganti periode ke 2023 ke 2025.
   > "Model yang sama menghasilkan kandidat 2023 ke 2025. Periode ini masih eksperimental karena belum ada data pembanding, jadi belum ada angka akurasinya."

## 1:30 sampai 2:30 · Apakah bisa dipercaya

Buka `/validasi`.

> "Pembandingnya data bangunan tahunan Google, yang juga dibuat dari Sentinel-2, dan setiap wilayah dinilai oleh model yang belum pernah melihatnya. Dari 10 alarm, sekitar 6 cocok dengan bangunan baru di data Google. Ini kecocokan dengan data pembanding, bukan akurasi lapangan, dan kami tampilkan juga bagaimana angkanya berubah kalau ambangnya diubah. Per petak, sembilan dari sepuluh kandidat menyentuh bangunan baru menurut data itu. Dua desa yang kasusnya diberitakan menonjol di peta kami: Canggu sekitar 6 kali rata-rata Badung."

Tunjukkan gambar studi kasus Canggu.

## 2:30 sampai 3:00 · AI dan dampak

> "Ada tiga lapis AI: foundation model AlphaEarth dari Google DeepMind, model deteksi perubahan dengan Sentinel-1 dan Sentinel-2, dan model bahasa besar untuk verifikasi dan penjelasan. Satu putaran untuk seluruh Badung butuh sekitar 30 menit komputasi ditambah verifikasi batch, dengan biaya AI sekitar Rp20 ribu. Metadata foto laporan dihapus sebelum dikirim ke AI."

Tutup dengan:

> "JAGA SAWAH memindai seluruh LSD Badung sekaligus, sehingga Pemda tidak perlu menunggu laporan warga atau berita untuk tahu di mana harus mengecek."

## Pertanyaan juri yang mungkin muncul

| Pertanyaan | Jawaban singkat |
|---|---|
| Kenapa presisi hanya sekitar 56%? | Itu kecocokan dengan data bangunan Google, dinilai di semua piksel, dengan hanya 1% yang berubah. Tebakan acak benar 1%. Sebagian besar alarm yang tidak cocok sudah kehilangan vegetasi dan berada di petak yang juga berisi bangunan baru; apakah itu tanah urug atau bangunan belum selesai belum diukur. Jika hanya alarm dengan probabilitas minimal 0,9 yang dipakai, presisinya sekitar 65% dengan recall 42%. |
| Apakah AI verifikasi menaikkan akurasi? | Tidak, dan kami tidak mengklaimnya. AI verifikasi menjelaskan setiap kandidat dan memilah mana yang perlu dicek petugas. |
| Kenapa tidak menampilkan data Google itu langsung? | Untuk 2018 ke 2023 bisa, dan model kami memang meniru data itu. Data Google berhenti di 2023, sedangkan model kami juga dijalankan untuk 2023 ke 2025, dan pipeline yang sama bisa dipakai di kabupaten lain. |
| Seberapa akurat di lapangan? | Belum diukur. Langkah berikutnya adalah sampel acuan berstrata dari citra resolusi tinggi berlisensi atau cek lapangan Dinas. |
| Bagaimana dengan IDMAI Bappenas? | IDMAI memantau sawah secara nasional dan mengukur alih fungsi terhadap lahan baku sawah, tanpa angka akurasi yang dilaporkan. JAGA SAWAH bekerja per kabupaten di dalam poligon LSD, dengan alasan AI per kandidat dan validasi terbuka, dan mengotomatiskan interpretasi citra dalam pemantauan LSD menurut Permen ATR/BPN 2/2024 Pasal 19. |
| Data apa saja, dan berbayar? | Semua data gratis: Sentinel-1 dan Sentinel-2, AlphaEarth, dan Open Buildings lewat Earth Engine (nonkomersial), serta peta LSD BIG. Biaya hanya untuk API model bahasa, sekitar US$1,3 per putaran Badung. Rincian model ada di AI & Technology Disclosure. |
| Apakah ini putusan hukum? | Bukan. Indikasi untuk ditinjau petugas. |

Catatan kurs: US$1,29 per putaran batch AI verifikasi untuk Badung, kurs sekitar Rp16.000 per dolar [perlu sumber: kurs saat presentasi].
