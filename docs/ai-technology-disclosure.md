# AI & Technology Disclosure: JAGA SAWAH

Penulis: Hilmi (https://master-hilmi.vercel.app/)

Format mengikuti Lampiran C Panduan Peserta AI Web Innovation Challenge Bali DigiFest 2026.

| Komponen | Isi |
|---|---|
| Nama Produk | JAGA SAWAH, pemantauan alih fungsi Lahan Sawah yang Dilindungi (LSD) di Kabupaten Badung dengan citra satelit dan AI |
| Framework / Frontend | Next.js 16 (App Router), React 19, Tailwind CSS 4, MapLibre GL JS 6 lewat react-map-gl 8 |
| Backend / Runtime | Next.js Route Handlers (Node.js) di Vercel. Pipeline data offline dengan Python 3.12: scikit-learn, xarray, geopandas, rasterio, earthengine-api, odc-stac, DuckDB |
| Database / Storage | GeoJSON dan PNG statis hasil pipeline, disajikan dari folder publik aplikasi. Poligon LSD hanya disimpan di sisi server dan tidak disajikan ke browser. Belum memakai database |
| Hosting / Deployment | Vercel (paket Hobby) |
| AI Model / API / Method | (1) Google Satellite Embedding V1 (AlphaEarth Foundations), embedding tahunan 64 dimensi, sebagai fitur. (2) Random forest (scikit-learn) pada 241 fitur dua waktu dari Sentinel-1, Sentinel-2, dan AlphaEarth, dilatih dengan label Google Open Buildings 2.5D Temporal. (3) Claude (`claude-opus-5-5`, Anthropic API) dengan output terstruktur: verifikasi kandidat lewat Message Batches API, penjelasan lokasi, dan penyaringan laporan foto warga secara langsung |
| Peran AI dalam Produk | Mendeteksi petak LSD yang berubah menjadi bangunan (random forest dan AlphaEarth). Memverifikasi dan menjelaskan kandidat seluas minimal 1.000 m² dalam bahasa Indonesia, termasuk memberi putusan "mungkin sudah bangunan sejak 2018" yang perlu dicek petugas (Claude, batch). Menjawab pertanyaan "lokasi ini statusnya apa" dengan dasar pasal dari daftar tetap beserta syarat berlakunya (Claude, langsung). Menyaring laporan foto warga dan memberi prioritas (Claude, langsung) |
| Dataset / Data Source | Copernicus Sentinel-1 dan Sentinel-2 (ESA), lewat Google Earth Engine (nonkomersial) dan Microsoft Planetary Computer. Cloud Score+ (Google) untuk masker awan Sentinel-2. Google Satellite Embedding V1. Google Open Buildings 2.5D Temporal (CC BY 4.0), yang dibuat Google dari citra Sentinel-2. Peta Lahan Sawah yang Dilindungi, BIG Satu Peta layer 59. IO LULC annual v02 (Impact Observatory, Microsoft, dan Esri; CC BY 4.0) dan Overture Maps buildings (ODbL) untuk uji awal. Batas wilayah dari OpenStreetMap (ODbL) lewat Nominatim. Teks Perpres 4/2026 (peraturan.bpk.go.id) dan Perda Provinsi Bali 4/2026 (JDIH Provinsi Bali) |
| Open-source Libraries | maplibre-gl, react-map-gl, next, react, tailwindcss, zod, @anthropic-ai/sdk; Python: scikit-learn, numpy, xarray, geopandas, shapely, rasterio, rioxarray, odc-stac, pystac-client, planetary-computer, earthengine-api, duckdb, matplotlib |
| Template / Boilerplate | `create-next-app` 16.4.3 sebagai kerangka awal |
| AI Coding Assistant | Claude Code (Anthropic) dipakai untuk membantu menulis kode, skrip pipeline, dan dokumentasi. Semua keputusan desain, data, dan klaim diperiksa oleh tim |
| Pre-existing Components | Tidak ada. Seluruh produk dikembangkan untuk kompetisi ini, mulai 29 Oktober 2026 |
| Third-party Assets / Credits | Basemap OpenFreeMap dan OpenMapTiles dengan data OpenStreetMap. "Contains modified Copernicus Sentinel data (2018 to 2025)". Google Open Buildings Temporal (CC BY 4.0). "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind." IO LULC annual v02: Impact Observatory, Microsoft, dan Esri (CC BY 4.0). Peta LSD: Badan Informasi Geospasial |

**Catatan penggunaan data**

- Hasil JAGA SAWAH adalah indikasi dari citra satelit dan AI, bukan putusan hukum. Setiap kandidat wajib ditinjau petugas.
- Data yang dikirim ke Claude: potongan citra Sentinel-2, koordinat, nilai indeks, fakta lokasi, dan foto laporan warga beserta catatannya. Metadata foto (EXIF dan XMP, termasuk lokasi GPS, kamera, dan waktu) dihapus di server sebelum dikirim. Foto laporan tidak disimpan oleh aplikasi.
- Angka akurasi di aplikasi adalah kecocokan dengan Google Open Buildings Temporal, bukan akurasi terhadap kondisi lapangan.
- Earth Engine dipakai hanya di skrip batch offline, tidak dipanggil oleh pengguna aplikasi.

**Pernyataan**

Kami menyatakan bahwa informasi di atas benar dan lengkap. Kami bertanggung jawab atas penggunaan teknologi, source code, data, library, API, model AI, dan aset yang digunakan pada produk.
