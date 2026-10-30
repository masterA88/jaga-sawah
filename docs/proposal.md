# JAGA SAWAH

**Peringatan dini alih fungsi Lahan Sawah yang Dilindungi dengan citra satelit dan AI**

AI Web Innovation Challenge, Bali DigiFest 2026, kategori Mahasiswa/Umum

Tim: [nama tim]
Anggota: Hilmi (https://master-hilmi.vercel.app/), [anggota 2], [anggota 3]
Instansi: [asal instansi]
URL MVP: [URL produksi]
Repository: [URL repository]

---

## 1. Problem & Background

Sawah Bali terus beralih menjadi vila, perumahan, dan jalan, termasuk di Lahan Sawah yang Dilindungi (LSD). Perpres 4/2026 menyatakan LSD yang belum masuk penetapan lahan pertanian pangan berkelanjutan "tidak dapat" dialihfungsikan sebelum ada rekomendasi menteri (Pasal 17 ayat 1). Perda Provinsi Bali 4/2026 lebih tegas: lahan produktif dalam rencana tata ruang "dilarang dialihfungsikan" (Pasal 13 ayat 2). Pelanggarnya dikenai sanksi sampai pembongkaran bangunan (Pasal 20 ayat 2).

Aturannya sudah ada, tetapi pengawasan tertinggal. Perda Bali 4/2026 mewajibkan pengawasan paling sedikit sekali dalam enam bulan (Pasal 18 ayat 1). Kenyataannya, pelanggaran biasanya baru diketahui setelah bangunan berdiri, lewat laporan warga atau berita. Contohnya tujuh bangunan di LSD Subak Munggu yang pemiliknya dipanggil Satpol PP Badung pada September 2026, dan 30 vila di Babakan Canggu yang dihentikan Pansus TRAP DPRD Bali pada Desember 2025.

Ukuran masalahnya di Badung: menurut data bangunan tahunan Google (Open Buildings Temporal), sekitar 87 ha dari 8.599 ha LSD Badung menjadi bangunan antara 2018 dan 2023. Di Kuta Utara, petak yang berubah melonjak sejak 2021.

## 2. Target User

| Pengguna | Kebutuhan | Kesulitan saat ini |
|---|---|---|
| Dinas Pertanian dan Pangan, Dinas PUPR, Satpol PP Kabupaten Badung | Daftar lokasi prioritas untuk dicek, dengan bukti dan dasar aturan | Wilayah luas, petugas terbatas, pengecekan manual, informasi datang terlambat |
| Subak dan Desa Adat (tim pengawasan menurut Perda Bali 4/2026 Pasal 24) | Tahu apakah sawah di wilayahnya masuk LSD dan apakah ada yang berubah; cara melapor | Tidak punya akses peta LSD dan citra satelit, tidak tahu harus melapor ke mana |
| Warga | Mengecek status suatu lokasi sebelum membeli atau menyewa lahan; melaporkan pembangunan di sawah | Status LSD sulit dicari, laporan tidak terstruktur |

## 3. Proposed Solution

JAGA SAWAH adalah peta web yang menunjukkan petak LSD yang kemungkinan sudah beralih fungsi, beserta penjelasan dan dasar aturannya.

Alur utama:

1. Petugas membuka peta Badung. Kandidat alih fungsi tampil dengan tiga status: terverifikasi AI, perlu tinjau petugas, atau ditolak AI. Petugas bisa memilih periode 2018 ke 2023 atau periode terbaru 2023 ke 2025.
2. Petugas mengklik kandidat. Panel menampilkan luas, putusan AI dengan tingkat keyakinan, alasan dalam bahasa Indonesia, dan citra Sentinel-2 tahun 2018, 2023, dan 2025.
3. Siapa pun bisa memakai mode **Cek lokasi**: klik titik mana pun, lalu AI menjelaskan apakah titik itu di dalam LSD, apakah ada kandidat di dekatnya, pasal mana yang relevan, dan langkah berikutnya.
4. Warga atau subak memakai mode **Lapor**: pilih lokasi, unggah foto lapangan, dan AI menyaring laporan itu menjadi kategori dan prioritas.
5. Halaman **Validasi** menunjukkan seberapa akurat sistem ini dan bagaimana mengukurnya.

## 4. AI Implementation

JAGA SAWAH memakai tiga lapis AI. Masalah ini butuh AI karena perubahan petak seluas beberapa ratus meter persegi di ribuan hektar tidak mungkin dipantau manual setiap bulan, dan citra satelit 10 m sulit dibaca orang awam.

| Lapis | Metode | Input | Output |
|---|---|---|---|
| Representasi | Google Satellite Embedding V1 (AlphaEarth Foundations) | Citra multisensor tahunan | Vektor 64 dimensi per piksel 10 m, tahun 2018, 2023, 2025 |
| Deteksi | Random forest pada 241 fitur dua waktu | Sentinel-2 (6 band dan indeks NDVI, NDBI, MNDWI, BSI), Sentinel-1 (VV, VH), embedding AlphaEarth, untuk dua tahun dan selisihnya | Probabilitas alih fungsi per piksel, lalu petak kandidat |
| Verifikasi dan penjelasan | Model bahasa besar multimodal lewat API, dengan output JSON terstruktur (model dan penyedia dicantumkan di AI & Technology Disclosure) | Chip citra tiga tahun dan nilai indeks; fakta lokasi; foto warga | Verdict dari enum tetap (`conversion`, `already_built`, `harvest_or_fallow`, `flooding`, `cloud_artifact`, `unclear`), alasan, prioritas, dan pasal dari daftar tetap |

Model deteksi dilatih dengan label dari Google Open Buildings 2.5D Temporal, yaitu keberadaan bangunan per tahun. Verifikasi seluruh kandidat Badung berjalan sebagai pekerjaan batch (315 kandidat, sekitar US$1,3 per putaran). Fitur Cek lokasi dan Lapor memanggil model yang sama secara langsung. Model hanya boleh memilih pasal dari daftar yang dikutip dari teks resmi Perpres 4/2026 dan Perda Bali 4/2026, sehingga tidak bisa mengarang pasal.

**Akurasi, diukur dengan jujur.** Pembandingnya Open Buildings Temporal, data yang tidak memakai citra kami. Penilaian dilakukan pada semua piksel LSD Badung, padahal hanya sekitar 1% yang berubah. Validasi silang dibagi per tile 5 km, sehingga setiap wilayah dinilai oleh model yang tidak pernah melihatnya. Hasilnya **presisi 0,56 dan recall 0,60**. Dari setiap 10 alarm, sekitar 6 terbukti bangunan baru, dan angka ini batas bawah karena tanah urug dan bangunan yang belum selesai belum tercatat sebagai bangunan. Untuk daftar prioritas (ambang 0,9), presisinya 0,65. Foundation model AlphaEarth menaikkan average precision dari 0,57 ke 0,65 pada uji di Kuta Utara.

AI verifikasi tidak menaikkan presisi deteksi, dan kami tidak mengklaimnya. Nilainya ada di penjelasan per kandidat, penyaringan laporan, dan temuan 26 petak yang ternyata sudah berupa bangunan sejak 2018. Temuan terakhir ini berarti peta LSD sendiri perlu dikoreksi.

## 5. MVP & Key Features

Semua fitur berikut sudah berfungsi di URL MVP:

- Peta seluruh LSD Badung dengan 997 kandidat periode 2018 ke 2023 dan 652 kandidat periode 2023 ke 2025, dengan filter status dan pemilih periode.
- Panel detail kandidat: putusan dan alasan AI, serta citra tiga tahun.
- Cek lokasi dengan AI, termasuk dasar aturan.
- Lapor dengan foto, disaring AI menjadi kategori dan prioritas. Foto tidak disimpan.
- Halaman Validasi: angka akurasi, cara ukur, pembanding, dua studi kasus dari berita, dan batasan.
- Batas pemakaian AI per perangkat dan per hari, supaya kuota cukup selama penjurian.

## 6. Technical Architecture

```
[Pipeline offline, bulanan]
Earth Engine: Sentinel-1, Sentinel-2, AlphaEarth, Open Buildings
  -> fitur per tile 5 km -> random forest -> petak kandidat
  -> AI verifikasi (batch) -> GeoJSON + chip PNG

[Aplikasi web, Vercel]
Browser (Next.js, MapLibre) -> peta, detail, validasi (file statis)
Browser -> /api/cek-lokasi -> data LSD di server -> AI -> penjelasan + pasal
Browser -> /api/lapor (foto) -> AI (vision) -> kategori + prioritas
```

Earth Engine hanya dipakai di pipeline offline. Aplikasi membaca file hasil, sehingga tidak bergantung pada layanan citra saat juri membuka aplikasi. Kunci API disimpan sebagai environment variable di server dan tidak pernah dikirim ke browser.

## 7. Innovation & Differentiation

| Pembanding | Yang dilakukan | Perbedaan JAGA SAWAH |
|---|---|---|
| Pengawasan manual Dinas dan Satpol PP | Berbasis laporan dan patroli | Daftar prioritas seluruh LSD kabupaten, diperbarui dari citra satelit |
| IDMAI (Bappenas, 2025) | Peta dugaan alih fungsi sawah tingkat nasional dari Sentinel-1 | Fokus di dalam poligon LSD kabupaten; verifikasi dan alasan AI per kandidat; pasal dari Perpres 4/2026 dan Perda Bali 4/2026; laporan warga; validasi terbuka |
| Peta tutupan lahan global (misalnya IO LULC 10 m) | Kelas tutupan lahan tahunan | Gagal di Bali: menyebut 70% LSD Kuta Utara sudah bangunan pada 2023. JAGA SAWAH dinilai terhadap data independen |

Sejauh pencarian kami, belum ada pemenang lomba yang menggabungkan deteksi perubahan dari citra, LLM untuk verifikasi dan penjelasan, dan peta web dalam satu produk untuk pengawasan sawah.

## 8. Impact & Development Potential

**Dampak.** Satu putaran untuk seluruh Badung butuh sekitar 30 menit komputasi dan biaya AI sekitar US$1,3. Pemda mendapat daftar prioritas sebelum bangunan selesai, bukan sesudahnya. Subak dan Desa Adat, yang menurut Perda Bali 4/2026 menjadi bagian tim pengawasan, mendapat alat untuk menjalankan peran itu. Temuan "sudah bangunan sejak 2018" membantu koreksi peta LSD.

**Pengembangan.** Perluasan ke kabupaten lain di Bali dengan pipeline yang sama. Pembaruan bulanan. Citra resolusi tinggi untuk verifikasi kandidat prioritas. Basis data laporan warga dengan alur tindak lanjut petugas. Konfirmasi petugas sebagai label baru untuk melatih ulang model.

**Keterbatasan MVP.**

- Resolusi 10 m membuat bangunan kecil dan tepi permukiman sulit dinilai.
- Pembanding akurasi hanya mencatat bangunan sampai 2023, jadi periode 2023 ke 2025 belum punya angka akurasi.
- Studi kasus dicocokkan di tingkat desa karena berita tidak memuat koordinat.
- Hasil adalah indikasi, bukan putusan hukum.

---

**Lampiran**

- A. Halaman Validasi (tangkapan layar) dan angka per kelompok tile
- B. AI & Technology Disclosure
- C. Sumber berita studi kasus: Bali Post 6 September 2026 dan 2 Januari 2026; Warta Bali 25 September 2026
