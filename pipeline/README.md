# Pipeline JAGA SAWAH

Penulis: Hilmi (https://master-hilmi.vercel.app/)

Skrip Python yang menghasilkan data aplikasi: deteksi alih fungsi, verifikasi AI, dan semua uji akurasi yang dirangkum di [README utama](../README.md#pengujian). Pipeline berjalan offline (batch); aplikasi web hanya membaca hasilnya.

Yang di-commit hanya skrip dan ringkasan metrik di [`results/`](results/). Citra, embedding, prediksi, chip, dan apa pun yang diturunkan dari peta LSD tetap lokal, karena ketentuan redistribusi peta LSD dari BIG belum jelas.

## Persiapan

```
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
earthengine authenticate          # akun Google dengan proyek Earth Engine nonkomersial
export EE_PROJECT=<id proyek Cloud Earth Engine Anda>
python get_lsd.py                  # LSD Badung dari BIG Satu Peta layer 59 -> ../data/ (tidak di-commit)
```

Verifikasi AI memakai Anthropic API. SDK membaca `ANTHROPIC_API_KEY` atau profil `ant auth login`.

## QT-02: seluruh Badung (dipakai aplikasi)

Jalankan dari `qt02-badung/`, berurutan:

| Langkah | Skrip | Isi | Waktu dan biaya |
|---|---|---|---|
| 0 | `make_tiles.py` | 27 tile 5 km yang mencakup seluruh LSD | detik |
| 1 | `qt02_features.py` | Per tile di Earth Engine: Sentinel-2 (Cloud Score+), Sentinel-1, AlphaEarth untuk 2018, 2023, 2025; Open Buildings Temporal 2018 dan 2023 | sekitar 3 menit per tile |
| 1b | `qt02_fill.py` | Isi celah awan Sentinel-2 2018 dengan komposit Januari 2018 sampai Juni 2019 | sekitar 3 menit |
| 2 | `qt02_model.py cv` | Validasi silang dengan tile utuh, pada semua piksel LSD | sekitar 2 menit |
| 3 | `qt02_model.py predict` | Model final, probabilitas per piksel LSD | sekitar 1 menit |
| 4 | `qt02_export.py patches` lalu `submit` lalu `collect` | Petak kandidat, chip citra, verifikasi AI lewat Message Batches API, skor terhadap Open Buildings, GeoJSON untuk aplikasi | batch biasanya kurang dari 1 jam; sekitar US$1,3 |
| 5 | `qt02_recent.py predict` lalu `cases` | Periode 2023 ke 2025 dan studi kasus Munggu dan Canggu | sekitar 2 menit |
| 6 | `qt02_validasi.py` | `validasi.json` untuk halaman `/validasi` | detik |

## QT-01: uji di Kuta Utara (riwayat metode)

Jalankan dari `qt01-kuta-utara/`. Uji ini merekam metode yang dicoba sebelum QT-02, termasuk yang gagal; hasilnya ada di README utama, bagian Pengujian.

| Skrip | Uji |
|---|---|
| `prepare_area.py` | Batas Kuta Utara (OpenStreetMap) dan LSD di dalamnya |
| `qt01_build_stack.py` | Komposit Sentinel-2 dari Planetary Computer, 2018, 2023, 2025 |
| `qt01_train_eval.py` | Uji A: label dari peta global IO LULC (gagal) |
| `qt01_label_kit.py` | Strata perubahan spektral dan kit label 300 titik |
| `qt01_building_labels.py`, `qt01_ablation.py` | Label dari footprint Overture, uji kebocoran fitur |
| `qt01_s1.py`, `qt01_s1_area.py`, `qt01_ablation_s1.py` | Sentinel-1, estimasi luas (kemudian ditarik) |
| `qt01_claude_verify.py`, `qt01_batch_patches.py`, `qt01_batch_check.py` | Verifikasi AI pada kandidat |
| `qt01_obt.py` | Uji B: evaluasi v1 terhadap Open Buildings Temporal |
| `qt01_obt_retrain.py`, `qt01_v2_pipeline.py` | Uji C: model v2 (tambah `--ae` untuk v3) |
| `qt01_alphaearth.py` | Uji D dan E: embedding AlphaEarth |
| `qt01_export_web.py` | Ekspor data Kuta Utara untuk versi awal aplikasi |
| `qt01_review_set.py`, `qt01_review_score.py` | Tinjauan manusia buta (hasilnya tidak sah, lihat README utama) |

`qt01_build_stack.py` harus dijalankan sebelum skrip QT-01 lain. Beberapa skrip memanggil skrip sebelumnya lewat `runpy`, jadi urutan di tabel juga urutan menjalankannya. Skrip yang dipanggil lewat `runpy` hanya menulis file hasilnya jika dijalankan langsung, sehingga file hasil tidak tertimpa oleh skrip lain.

## Ringkasan hasil

| File di `results/` | Isi |
|---|---|
| `qt02_cv.json` | Uji F: presisi, recall, average precision Badung, per kelompok tile |
| `qt02_scores.json` | Verdict AI dan skor tiap tahap terhadap Open Buildings Temporal, Badung |
| `qt02_cases.json` | Studi kasus Munggu dan Canggu |
| `qt01_alphaearth.json` | Uji C, D, E |
| `qt01_obt.json`, `qt01_obt_retrain.json` | Uji B dan C |
| `v2_scores.json`, `v3_scores.json` | AI verifikasi pada kandidat v2 dan v3 |
| `qt01_summary.json` | Uji A |
| `qt01_building_summary.json`, `qt01_ablation*.json`, `qt01_s1_area.json` | Uji dengan label footprint (v1, **ditarik**). Angka di file ini, termasuk estimasi luas, dinilai hanya pada piksel jelas dan tidak boleh dikutip. Versi di repo ditulis ulang oleh rantai `runpy` sebelum skrip diberi pengaman, jadi isinya (presisi 0,87, 152,5 ha) sedikit berbeda dari catatan awal (0,88, 161 ha) |
| `qt01_review_score.json` | Tinjauan manusia buta |

## Lisensi data

Contains modified Copernicus Sentinel data. Google Satellite Embedding V1 dan Open Buildings 2.5D Temporal diakses lewat Earth Engine (nonkomersial); Open Buildings Temporal berlisensi CC BY 4.0. Overture Maps (ODbL). Peta LSD milik Badan Informasi Geospasial dan tidak didistribusikan ulang di repo ini.
