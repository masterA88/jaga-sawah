# JAGA SAWAH

**Pemantauan alih fungsi Lahan Sawah yang Dilindungi dengan citra satelit dan AI**

AI Web Innovation Challenge, Bali DigiFest 2026, kategori Mahasiswa/Umum

Tim: [nama tim]
Anggota: Hilmi (https://master-hilmi.vercel.app/)
Instansi: [asal instansi]
URL MVP: https://jaga-sawah.vercel.app
Repository: https://github.com/masterA88/jaga-sawah

---

## 1. Problem & Background

Sawah Bali terus beralih menjadi vila, perumahan, dan jalan, termasuk di Lahan Sawah yang Dilindungi (LSD). Perpres 4/2026 menyatakan LSD yang belum masuk penetapan lahan pertanian pangan berkelanjutan "tidak dapat" dialihfungsikan sebelum ada rekomendasi menteri (Pasal 17 ayat 1). Perda Provinsi Bali 4/2026 lebih tegas: lahan produktif dalam rencana tata ruang "dilarang dialihfungsikan" (Pasal 13 ayat 2). Pelanggarnya dikenai sanksi sampai pembongkaran bangunan (Pasal 20 ayat 2).

Aturannya sudah ada, tetapi pengawasan tertinggal. Perda Bali 4/2026 mewajibkan pengawasan paling sedikit sekali dalam enam bulan (Pasal 18 ayat 1). Kenyataannya, pelanggaran biasanya baru diketahui setelah bangunan berdiri, lewat laporan warga atau berita. Contohnya sedikitnya tujuh bangunan yang diduga berdiri di LSD Subak Munggu, yang pemiliknya dipanggil Satpol PP Badung pada September 2026, dan kurang lebih 30 vila di Babakan Canggu yang dihentikan Pansus TRAP DPRD Bali pada akhir Desember 2025.

Menurut data bangunan tahunan Google (Open Buildings Temporal), sekitar 87 ha piksel LSD Badung menjadi bangunan antara 2018 dan 2023. Angka ini bergantung pada ambang keyakinan data itu (35 sampai 218 ha untuk ambang 0,5 sampai 0,1) dan hanya mencakup bangunan yang terdeteksi, belum tanah urug dan jalan. Jadi angka ini adalah bagian alih fungsi berupa bangunan di dalam LSD, bukan seluruh alih fungsi sawah di Badung. Di Kuta Utara, luas bangunan yang baru muncul di LSD menurut data yang sama naik setiap tahun, dari 2,4 ha pada 2019 menjadi 19,7 ha pada 2023.

## 2. Target User

| Pengguna | Kebutuhan | Kesulitan saat ini |
|---|---|---|
| Dinas Pertanian dan Pangan, Dinas PUPR, Satpol PP Kabupaten Badung | Daftar lokasi untuk dicek, dengan bukti dan dasar aturan | Wilayah luas, petugas terbatas, pengecekan manual, informasi datang terlambat |
| Subak dan Desa Adat (tim pengawasan menurut Perda Bali 4/2026 Pasal 24) | Tahu apakah sawah di wilayahnya masuk LSD dan apakah ada yang berubah; cara melapor | Tidak punya akses peta LSD dan citra satelit, tidak tahu harus melapor ke mana |
| Warga | Mengecek status suatu lokasi sebelum membeli atau menyewa lahan; melaporkan pembangunan di sawah | Status LSD sulit dicari, laporan tidak terstruktur |

## 3. Proposed Solution

JAGA SAWAH adalah peta web yang menunjukkan petak LSD yang kemungkinan sudah beralih fungsi, beserta penjelasan dan dasar aturannya. Permen ATR/BPN 2/2024 Pasal 19 sudah mengatur pemantauan LSD dengan tumpang susun peta dan interpretasi citra satelit. JAGA SAWAH mengotomatiskan langkah interpretasi citra itu untuk seluruh LSD Badung, lalu menyerahkan hasilnya kepada petugas untuk dicek.

Alur utama:

1. Petugas membuka peta Badung. Kandidat alih fungsi tampil dengan empat status: terverifikasi AI, perlu tinjau petugas, belum diverifikasi, atau ditolak AI. Petugas bisa memilih periode 2018 ke 2023 atau periode terbaru 2023 ke 2025 (eksperimental).
2. Petugas mengklik kandidat. Panel menampilkan luas, putusan AI dengan tingkat keyakinan, alasan dalam bahasa Indonesia, dan citra Sentinel-2 tahun 2018, 2023, dan 2025.
3. Siapa pun bisa memakai mode **Cek lokasi**: klik titik mana pun, lalu AI menjelaskan apakah titik itu di dalam LSD, apakah ada kandidat di dekatnya, pasal mana yang relevan beserta syaratnya, dan langkah berikutnya.
4. Warga atau subak memakai mode **Lapor**: pilih lokasi, unggah foto lapangan, dan AI menyaring laporan itu menjadi kategori dan prioritas.
5. Halaman **Validasi** menunjukkan cara kami mengukur hasilnya, angka yang didapat, dan batasannya.

## 4. AI Implementation

JAGA SAWAH memakai tiga lapis AI. Masalah ini butuh AI karena perubahan petak seluas beberapa ratus meter persegi di ribuan hektar tidak mungkin dipantau manual, dan citra satelit 10 m sulit dibaca orang awam.

| Lapis | Metode | Input | Output |
|---|---|---|---|
| Representasi | Google Satellite Embedding V1 (AlphaEarth Foundations) | Citra multisensor tahunan | Vektor 64 dimensi per piksel 10 m, tahun 2018, 2023, 2025 |
| Deteksi | Random forest pada 241 fitur dua waktu | Sentinel-2 (6 band dan indeks NDVI, NDBI, MNDWI, BSI), Sentinel-1 (VV, VH), embedding AlphaEarth, untuk dua tahun dan selisihnya | Probabilitas alih fungsi per piksel, lalu petak kandidat |
| Verifikasi dan penjelasan | Model bahasa besar multimodal lewat API, dengan output JSON terstruktur (model dan penyedia dicantumkan di bagian 9) | Chip citra tiga tahun dan nilai indeks; fakta lokasi; foto warga | Verdict dari enum tetap (`conversion`, `already_built`, `harvest_or_fallow`, `flooding`, `cloud_artifact`, `unclear`), alasan, prioritas, dan pasal dari daftar tetap |

Model deteksi dilatih dengan label dari Google Open Buildings 2.5D Temporal, yaitu keberadaan bangunan per tahun. Kandidat berukuran minimal 1.000 m² (315 dari 997 kandidat) diverifikasi AI sebagai pekerjaan batch, dengan biaya sekitar US$1,3 per putaran menurut hitungan token. Kandidat yang lebih kecil tetap tampil dengan status belum diverifikasi. Fitur Cek lokasi dan Lapor memanggil model yang sama secara langsung. Pasal hanya boleh dipilih dari daftar yang dikutip dari teks resmi Perpres 4/2026 dan Perda Bali 4/2026, dan setiap pasal bersyarat ditampilkan bersama syaratnya. Penjelasan dan saran tetap teks bebas, jadi tetap harus dibaca sebagai indikasi.

**Akurasi, dan apa artinya.** Pembandingnya Google Open Buildings 2.5D Temporal, data bangunan tahunan yang dibuat Google dari citra Sentinel-2 dengan model lain. Model kami dinilai pada tile 5 km yang tidak dipakai saat pelatihan, di semua piksel LSD Badung, padahal hanya sekitar 1% yang berubah. Kecocokannya dengan data itu: **presisi 0,56** (selang 95% antar-tile 0,52 sampai 0,58) dan **recall 0,60** (0,47 sampai 0,67). Angka ini mengukur kecocokan dengan data Google, bukan akurasi terhadap kondisi lapangan, dan bergantung pada ambang yang dipakai untuk menyebut piksel OBT sebagai bangunan. Di tile dengan perubahan rendah, yang mencakup 71% LSD, presisinya 0,50 dan recall-nya 0,49. Per petak, sembilan dari sepuluh kandidat menyentuh bangunan baru menurut data Google, dan dua dari tiga sebagian besar berisi bangunan baru. Jika hanya alarm dengan probabilitas minimal 0,9 yang dipakai, presisinya naik menjadi 0,65, tetapi recall turun menjadi 0,42. Foundation model AlphaEarth menaikkan average precision dari 0,57 ke 0,65 pada uji di Kuta Utara.

AI verifikasi tidak menaikkan presisi deteksi, dan kami tidak mengklaimnya. Nilainya ada di penjelasan per kandidat dan penyaringan laporan. AI verifikasi memberi 26 petak putusan sudah bangunan sejak 2018. Data Google tidak mendukung putusan ini untuk hampir semua petak itu, jadi petak tersebut perlu dicek petugas sebelum dianggap kesalahan peta LSD.

## 5. MVP & Key Features

Fitur berikut berfungsi di URL MVP:

- Peta seluruh LSD Badung dengan 997 kandidat periode 2018 ke 2023, dengan filter status dan pemilih periode.
- Periode 2023 ke 2025 dengan 652 kandidat, ditandai eksperimental: belum ada data pembanding untuk periode ini, jadi belum ada angka akurasinya, dan kandidatnya belum diverifikasi AI.
- Panel detail kandidat: putusan dan alasan AI, serta citra tiga tahun.
- Cek lokasi dengan AI, termasuk dasar aturan dan syarat berlakunya.
- Lapor dengan foto, disaring AI menjadi kategori dan prioritas. Metadata foto (lokasi GPS, kamera, waktu) dihapus di server sebelum foto dikirim ke AI, dan foto tidak disimpan.
- Halaman Validasi: angka, cara ukur, pengaruh ambang data pembanding, pembanding lain, dua studi kasus dari berita, dan batasan.
- Batas pemakaian AI per perangkat dan per hari, agar kuota cukup selama penjurian.

## 6. Technical Architecture

```
[Pipeline offline, dijalankan per periode]
Earth Engine: Sentinel-1, Sentinel-2, AlphaEarth, Open Buildings
  -> fitur per tile 5 km -> random forest -> petak kandidat
  -> AI verifikasi (batch) -> GeoJSON + chip PNG

[Aplikasi web, Vercel]
Browser (Next.js, MapLibre) -> peta, detail, validasi (file statis)
Browser -> /api/cek-lokasi -> data LSD di server -> AI -> penjelasan + pasal dan syaratnya
Browser -> /api/lapor (foto) -> hapus metadata -> AI (vision) -> kategori + prioritas
```

Earth Engine hanya dipakai di pipeline offline. Aplikasi membaca file hasil, sehingga tidak bergantung pada layanan citra saat juri membuka aplikasi. Kunci API disimpan sebagai environment variable di server dan tidak pernah dikirim ke browser. Pipeline sudah dijalankan sekali untuk setiap periode; penjadwalan rutin belum ada.

## 7. Innovation & Differentiation

| Pembanding | Yang dilakukan | Perbedaan JAGA SAWAH |
|---|---|---|
| Pengawasan manual Dinas dan Satpol PP | Berbasis laporan dan patroli | Daftar kandidat dari seluruh LSD kabupaten sekaligus, dari citra satelit |
| IDMAI (Bappenas, 2025) | Pemantauan sawah tingkat nasional; modul alih fungsinya mengukur perubahan terhadap lahan baku sawah (LBS) selama minimal tiga tahun; akurasinya tidak dilaporkan | Bekerja di dalam poligon LSD kabupaten; alasan AI per kandidat; pasal dari Perpres 4/2026 dan Perda Bali 4/2026; laporan warga; validasi terbuka |
| MapBiomas Indonesia | Peta tutupan lahan tahunan berbasis Landsat dengan kelas sawah dan peta transisi | Resolusi 10 m, di dalam poligon LSD, dengan kandidat per petak dan penjelasan |
| Peta tutupan lahan global (misalnya IO LULC 10 m) | Kelas tutupan lahan tahunan | Pada uji di Kuta Utara, peta ini menyebut 70% LSD sudah bangunan pada 2023, jadi tidak bisa dipakai sebagai label |

Sejauh pencarian kami, belum ada pemenang lomba yang menggabungkan deteksi perubahan dari citra, LLM untuk verifikasi dan penjelasan, dan peta web dalam satu produk untuk pengawasan sawah.

## 8. Impact & Development Potential

**Dampak.** Satu putaran untuk seluruh Badung butuh sekitar 30 menit komputasi fitur di Earth Engine, ditambah verifikasi AI batch yang biasanya selesai dalam satu jam, dengan biaya AI sekitar US$1,3 menurut hitungan token. JAGA SAWAH memindai seluruh LSD Badung sekaligus, sehingga Pemda tidak perlu menunggu laporan warga atau berita untuk tahu di mana harus mengecek. Subak dan Desa Adat, yang menurut Perda Bali 4/2026 menjadi bagian tim pengawasan, mendapat alat untuk menjalankan peran itu.

**Pengembangan.**

- Tumpang susun peta LP2B dan rencana tata ruang, seperti diatur Permen ATR/BPN 2/2024 Pasal 19, agar syarat Perpres 17 ayat 1 dan Perda 13 ayat 2 bisa ditentukan per titik.
- Sampel acuan berstrata (600 sampai 2.000 piksel) dari citra resolusi tinggi berlisensi atau cek lapangan Dinas, agar luas dan akurasi terhadap kondisi lapangan bisa dihitung dengan selangnya.
- Perluasan ke kabupaten lain di Bali dengan pipeline yang sama, dan pembaruan terjadwal setelah citra baru tersedia.
- Basis data laporan warga dengan alur tindak lanjut petugas, dan konfirmasi petugas sebagai label baru untuk melatih ulang model.

**Keterbatasan MVP.**

- Angka akurasi adalah kecocokan dengan data Google yang juga dibuat dari Sentinel-2. Akurasi terhadap kondisi lapangan belum diukur.
- Resolusi 10 m membuat bangunan kecil dan tepi permukiman sulit dinilai. Bangunan tunggal di bawah sekitar 150 sampai 300 m² kemungkinan besar terlewat (perkiraan dari aturan label, belum diukur).
- Model hanya menandai perubahan yang sudah menjadi bangunan menurut data pembanding. Tanah urug dan jalan belum terukur.
- Peta di aplikasi dibuat oleh model yang dilatih di semua tile Badung. Angka validasi silang berlaku untuk wilayah yang belum pernah dilihat model.
- Periode 2023 ke 2025 belum punya angka akurasi.
- Studi kasus dicocokkan di tingkat desa karena berita tidak memuat koordinat.
- Hasil adalah indikasi, bukan putusan hukum.

## 9. Technology Disclosure

| Komponen | Isi |
|---|---|
| Framework | Next.js 16 (App Router), React 19, Tailwind CSS 4, MapLibre GL JS 6 lewat react-map-gl 8 |
| Database | Belum memakai database. Hasil pipeline disajikan sebagai GeoJSON dan PNG statis; poligon LSD hanya disimpan di server |
| AI model / API | Claude (`claude-opus-5-5`, Anthropic API) untuk verifikasi batch, cek lokasi, dan penyaringan foto; Google Satellite Embedding V1 (AlphaEarth Foundations); random forest (scikit-learn) |
| Library | maplibre-gl, react-map-gl, next, react, tailwindcss, zod, @anthropic-ai/sdk; Python: scikit-learn, numpy, xarray, geopandas, shapely, rasterio, rioxarray, odc-stac, pystac-client, planetary-computer, earthengine-api, duckdb, matplotlib |
| Dataset | Copernicus Sentinel-1 dan Sentinel-2; Cloud Score+; Google Satellite Embedding V1; Google Open Buildings 2.5D Temporal (CC BY 4.0); peta LSD BIG Satu Peta layer 59; IO LULC annual v02 (uji awal); Overture Maps buildings (uji awal); OpenStreetMap |
| Hosting | Vercel (paket Hobby); pipeline di Google Earth Engine (nonkomersial) dan Microsoft Planetary Computer |
| AI coding assistant | Claude Code (Anthropic) |

Rincian lengkap ada di AI & Technology Disclosure (Lampiran B).

## 10. Submission Links

| Item | Tautan |
|---|---|
| GitHub Repository | https://github.com/masterA88/jaga-sawah |
| Deployment URL | https://jaga-sawah.vercel.app |
| Demo Account | Tidak diperlukan |
| Commit Hash / Release Tag | `v1.0-submission` [hash commit diisi saat tag dibuat] |

---

**Lampiran**

- A. Halaman Validasi (tangkapan layar) dan angka per kelompok tile
- B. AI & Technology Disclosure
- C. Sumber berita studi kasus: Bali Post 6 September 2026 dan 2 Januari 2026; Warta Bali 25 September 2026
