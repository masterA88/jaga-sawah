# JAGA SAWAH

Penulis: Hilmi (https://master-hilmi.vercel.app/)

## Description

JAGA SAWAH adalah peringatan dini alih fungsi Lahan Sawah yang Dilindungi (LSD) di Bali. Aplikasi ini memadukan citra satelit Sentinel-1 dan Sentinel-2, model random forest, dan verifikasi Claude. Hasilnya peta kandidat alih fungsi beserta alasannya, untuk ditinjau petugas Pemda dan subak. Versi ini adalah demo untuk Kecamatan Kuta Utara, Kabupaten Badung, periode 2018 ke 2023.

## Problem & Target User

Sawah di Bali terus beralih menjadi villa, perumahan, dan jalan, termasuk di dalam LSD yang dilindungi Perpres 4/2026 dan Perda Bali 4/2026. Pengawasan masih bergantung pada laporan dan pengecekan manual, sehingga pelanggaran sering baru diketahui setelah bangunan berdiri.

Pengguna:

- Dinas Pertanian dan Dinas PUPR kabupaten: daftar kandidat per periode, siap ditinjau.
- Subak dan warga: melihat apakah sawah di sekitarnya masuk LSD dan apakah ada kandidat alih fungsi.

## Key Features

- Peta LSD dan kandidat alih fungsi dengan empat status: terverifikasi AI, perlu tinjau petugas, belum diverifikasi, ditolak AI.
- Detail tiap kandidat: luas, periode, putusan AI dengan tingkat keyakinan, alasan dalam bahasa Indonesia, dan potongan citra Sentinel-2 2018, 2023, 2025.
- Ringkasan luas alih fungsi LSD dengan selang kepercayaan (estimator Olofsson).

## Tech Stack

- Frontend: Next.js 16 (App Router), React 19, Tailwind CSS 4, MapLibre GL JS 6 lewat react-map-gl 8, basemap OpenFreeMap.
- Pipeline data (offline, Python): Microsoft Planetary Computer STAC, `odc-stac`, `xarray`, `scikit-learn`, `geopandas`, DuckDB.
- AI: random forest (scikit-learn) untuk deteksi; Claude (`claude-opus-5-5`) lewat Anthropic Message Batches API untuk verifikasi.

## AI Implementation

1. **Deteksi.** Random forest pada 48 fitur dua waktu: enam band Sentinel-2, NDVI median, sebaran, dan persentil 90, NDBI, MNDWI, BSI, ditambah VV, VH, sebaran VV, dan rasio dari Sentinel-1 RTC, untuk 2018 dan 2023 serta selisihnya. Label referensi dari footprint bangunan Overture Maps (Google Open Buildings, Microsoft, OSM).
2. **Verifikasi.** Setiap kandidat dikirim ke Claude sebagai satu gambar tiga tahun ditambah nilai indeks. Claude menjawab dalam JSON dengan enum verdict tetap (`conversion`, `already_built`, `harvest_or_fallow`, `flooding`, `cloud_artifact`, `unclear`), keyakinan, dan alasan. Claude tidak pernah melihat label referensi.
3. **Hasil uji di Kuta Utara** (validasi silang blok spasial 1 km): presisi alih fungsi di dalam LSD 0,88 dan recall 0,91. Setelah verifikasi Claude, presisi kandidat terverifikasi naik menjadi 0,92. Biaya verifikasi kurang dari US$0,01 per kandidat. Batasannya dicatat di bagian Known Limitations.

## Architecture / Data Flow

```
Sentinel-1/2 (Planetary Computer) -> composite musim kemarau per tahun -> fitur dua waktu
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
- Label referensi berasal dari footprint bangunan dari citra sekitar 2022 sampai 2023. Bangunan 2024 sampai 2025 belum tercakup, dan sampel referensi hanya memuat piksel yang jelas.
- Peta LSD BIG (metadata 2021) memuat sebagian rumah yang sudah ada sebelumnya.
- Hasil adalah indikasi, bukan putusan hukum. Setiap kandidat wajib ditinjau petugas.

## Third-party Resources / Credits

- Contains modified Copernicus Sentinel data (2018 to 2025), lewat Microsoft Planetary Computer.
- Peta Lahan Sawah yang Dilindungi: BIG Satu Peta, layer 59.
- Footprint bangunan: Overture Maps Foundation (ODbL), berisi Google Open Buildings (CC BY 4.0), Microsoft Building Footprints (ODbL), dan OpenStreetMap (ODbL).
- Basemap: OpenFreeMap, OpenMapTiles, data OpenStreetMap.
- Batas kecamatan: OpenStreetMap lewat Nominatim.

## Team Members

- Hilmi (https://master-hilmi.vercel.app/)
