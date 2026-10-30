# JAGA SAWAH

Penulis: Hilmi (https://master-hilmi.vercel.app/)

## Description

JAGA SAWAH adalah peringatan dini alih fungsi Lahan Sawah yang Dilindungi (LSD) di Bali. Aplikasi ini memadukan citra satelit Sentinel-1 dan Sentinel-2, model random forest, dan verifikasi Claude. Hasilnya peta kandidat alih fungsi beserta alasannya, untuk ditinjau petugas Pemda dan subak. Versi ini mencakup seluruh Kabupaten Badung (8.599 ha LSD), periode 2018 ke 2023.

## Problem & Target User

Sawah di Bali terus beralih menjadi villa, perumahan, dan jalan, termasuk di dalam LSD yang dilindungi Perpres 4/2026 dan Perda Bali 4/2026. Pengawasan masih bergantung pada laporan dan pengecekan manual, sehingga pelanggaran sering baru diketahui setelah bangunan berdiri.

Pengguna:

- Dinas Pertanian dan Dinas PUPR kabupaten: daftar kandidat per periode, siap ditinjau.
- Subak dan warga: melihat apakah sawah di sekitarnya masuk LSD dan apakah ada kandidat alih fungsi.

## Key Features

- Peta LSD dan kandidat alih fungsi dengan empat status: terverifikasi AI, perlu tinjau petugas, belum diverifikasi, ditolak AI.
- Detail tiap kandidat: luas, periode, putusan AI dengan tingkat keyakinan, alasan dalam bahasa Indonesia, dan potongan citra Sentinel-2 2018, 2023, 2025.
- Ringkasan luas bangunan baru di LSD menurut Open Buildings Temporal, dan perkiraan tahun bangunan muncul per kandidat.

## Tech Stack

- Frontend: Next.js 16 (App Router), React 19, Tailwind CSS 4, MapLibre GL JS 6 lewat react-map-gl 8, basemap OpenFreeMap.
- Pipeline data (offline, Python): Microsoft Planetary Computer STAC, `odc-stac`, `xarray`, `scikit-learn`, `geopandas`, DuckDB.
- AI: embedding AlphaEarth Foundations dan random forest (scikit-learn) untuk deteksi; Claude (`claude-opus-5-5`) lewat Anthropic Message Batches API untuk verifikasi.

## AI Implementation

1. **Deteksi.** Random forest pada 241 fitur dua waktu. Pertama, embedding tahunan AlphaEarth (Google Satellite Embedding V1, 64 dimensi) untuk 2018 dan 2023, selisihnya, dan kemiripan kosinusnya. Kedua, enam band Sentinel-2, NDVI median, sebaran, dan persentil 90, NDBI, MNDWI, BSI, ditambah VV, VH, sebaran VV, dan rasio dari Sentinel-1 RTC, untuk 2018 dan 2023 serta selisihnya. Label dari Google Open Buildings 2.5D Temporal (keberadaan bangunan per tahun) untuk semua piksel, diambil lewat Earth Engine dalam skrip batch.
2. **Verifikasi.** Setiap kandidat dikirim ke Claude sebagai satu gambar tiga tahun ditambah nilai indeks. Claude menjawab dalam JSON dengan enum verdict tetap (`conversion`, `already_built`, `harvest_or_fallow`, `flooding`, `cloud_artifact`, `unclear`), keyakinan, dan alasan. Claude tidak pernah melihat label referensi.
3. **Hasil uji di seluruh Badung.** Validasi silang per tile 5 km, jadi setiap tile dinilai oleh model yang tidak pernah melihatnya, pada semua piksel LSD dengan prevalensi asli 1%. Hasilnya presisi 0,55, recall 0,61, dan average precision 0,57. Menurut Open Buildings Temporal, ada 87 ha bangunan baru di LSD Badung 2018 ke 2023. Claude menandai 26 petak sebagai sudah bangunan sejak 2018, yaitu kesalahan peta LSD. Biaya verifikasi 292 petak US$1,20.
4. **Hasil uji awal di Kuta Utara.** Validasi silang blok spasial 1 km, dinilai pada semua piksel LSD dengan prevalensi asli 4,7%. Untuk "bangunan baru 2018 ke 2023" menurut Open Buildings Temporal, hasilnya presisi 0,58, recall 0,73, dan average precision 0,65. Tanpa AlphaEarth, angkanya presisi 0,51 dan average precision 0,57. Sebagian besar sisa "alarm palsu" kehilangan vegetasi sama seperti alih fungsi yang benar (NDVI 0,68 ke 0,19), dan 68% di antaranya sudah punya sebagian bangunan. Jadi sebagian besar kemungkinan alih fungsi yang belum menjadi bangunan penuh. Claude tidak menaikkan presisi pada model ini. Perannya memberi alasan per kandidat, menandai "sudah bangunan sejak 2018", dan memilah kandidat yang perlu ditinjau petugas. Biayanya kurang dari US$0,01 per kandidat.

## Architecture / Data Flow

```
Sentinel-1/2, AlphaEarth, Open Buildings (Earth Engine, batch per tile 5 km) -> fitur dua waktu
   -> random forest -> petak kandidat di dalam LSD -> Claude (Batches API) -> verdict + alasan
   -> GeoJSON statis -> Next.js + MapLibre (peta, detail, ringkasan)
```

Pipeline berjalan offline. Aplikasi web hanya membaca file hasil, sehingga tidak memanggil layanan citra saat juri membuka aplikasi.

## Installation / Run Instructions

```
npm install
npm run dev
```

Data hasil pipeline ada di `public/data/` dan tidak di-commit, karena ketentuan redistribusi peta LSD dari BIG belum jelas. Skrip pipeline ada di folder `experiments/qt01-kuta-utara/` di workspace proyek. Salin `.env.example` ke `.env.local` jika fitur yang memakai API sudah aktif.

## Deployment URL

Belum ada.

## Demo Account

Tidak diperlukan.

## Known Limitations

- Resolusi 10 m: bangunan kecil dan piksel campuran di tepi permukiman sering diberi status "perlu tinjau".
- Label referensi hanya mengukur bangunan sampai 2023. Tanah urug, jalan, dan bangunan 2024 sampai 2025 tidak terhitung sebagai alih fungsi oleh referensi.
- Peta LSD BIG (metadata 2021) memuat sebagian rumah yang sudah ada sebelumnya.
- Hasil adalah indikasi, bukan putusan hukum. Setiap kandidat wajib ditinjau petugas.

## Third-party Resources / Credits

- Contains modified Copernicus Sentinel data (2018 to 2025), lewat Microsoft Planetary Computer.
- Peta Lahan Sawah yang Dilindungi: BIG Satu Peta, layer 59.
- Bangunan per tahun: Google Open Buildings 2.5D Temporal (CC BY 4.0), lewat Google Earth Engine (nonkomersial).
- Embedding citra: Google Satellite Embedding V1 (AlphaEarth Foundations), lewat Google Earth Engine.
- Footprint bangunan untuk uji awal: Overture Maps Foundation (ODbL), berisi Google Open Buildings (CC BY 4.0), Microsoft Building Footprints (ODbL), dan OpenStreetMap (ODbL).
- Basemap: OpenFreeMap, OpenMapTiles, data OpenStreetMap.
- Batas kecamatan: OpenStreetMap lewat Nominatim.

## Team Members

- Hilmi (https://master-hilmi.vercel.app/)
