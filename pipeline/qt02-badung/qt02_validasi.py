"""QT-02 step 5: data for the app's /validasi page (jaga-sawah/public/data/validasi.json and images).

Every number on the page comes from the result files written by the pipeline, so the page cannot drift
from the experiments: qt02_cv.json, qt02_scores.json, qt02_cases.json, the QT-01 summaries, and two files
from the independent review of 30 Oct 2026 that re-ran the tile CV: qt02_cv_extra.json (tile bootstrap,
OBT threshold sweep, low-change tiles) and qt02_patch_level.json (agreement per candidate patch).
"""
import json
import os
import shutil

Q1 = "../qt01-kuta-utara"
OUT = "../../public/data"
os.makedirs(f"{OUT}/validasi", exist_ok=True)

cv = json.load(open("qt02_cv.json"))
sc = json.load(open("qt02_scores.json"))
cases = json.load(open("qt02_cases.json"))
ae = json.load(open(f"{Q1}/qt01_alphaearth.json"))
obt1 = json.load(open(f"{Q1}/qt01_obt.json"))
io = json.load(open(f"{Q1}/qt01_summary.json"))
extra = json.load(open("qt02_cv_extra.json"))
patch = json.load(open("qt02_patch_level.json"))
# Hilmi's blind review (30 Oct 2026) agreed with only 10 of 20 control items, so it cannot grade the model
# and stays off the page; bible 6.6 and TJ-12 record why.
review = None
for k in ("munggu", "canggu"):
    shutil.copy(f"case_{k}.png", f"{OUT}/validasi/case_{k}.png")

lsd_ha = 8599
data = {
    "headline": {
        "precision": cv["precision"], "recall": cv["recall"], "average_precision": cv["average_precision"],
        "prevalence": cv["prevalence"], "obt_new_building_ha": cv["lsd_new_building_ha"], "lsd_ha": lsd_ha,
        "precision_at_0_9": cv["at_0.9"]["precision"], "recall_at_0_9": cv["at_0.9"]["recall"],
        "folds": [{"precision": f["precision"], "recall": f["recall"], "tiles": len(f["tiles"])} for f in cv["folds"]],
        "precision_ci95": extra["tile_bootstrap_ci95"]["precision"], "recall_ci95": extra["tile_bootstrap_ci95"]["recall"],
        "low_change": extra["low_vs_high_prevalence_tiles"]["prev_lt_0.5pct"],
        "threshold": [{"obt": k, "ha": v["obt_new_ha"], "precision": v["precision"], "recall": v["recall"]}
                      for k, v in extra["label_threshold_sensitivity"].items()],
        "patch_any_obt": patch["share_with_any_obt_new_px"], "patch_mostly_obt": patch["share_with_ge50pct_obt_new"],
    },
    "method": [
        "Pembanding: Google Open Buildings 2.5D Temporal (OBT), data bangunan tahunan yang dibuat Google dari citra Sentinel-2 dengan model lain. OBT juga menjadi label latih. Karena sumber citranya sama, angka di halaman ini mengukur kecocokan dengan OBT, bukan akurasi terhadap kondisi lapangan.",
        "Piksel dihitung bangunan baru jika keyakinan OBT di bawah 0,1 pada 2018 dan minimal 0,3 pada 2023. Ambang ini pilihan kami, dan angka presisi, recall, serta luas berubah jika ambangnya diubah (tabel di bawah).",
        "Dinilai di semua piksel LSD Badung (prevalensi asli, sekitar 1% piksel menjadi bangunan baru), bukan hanya contoh yang mudah.",
        "Validasi silang per tile 5 km: setiap wilayah dinilai oleh model yang tidak pernah melihat wilayah itu saat dilatih.",
        "Ambang keputusan dipilih hanya dari wilayah latih, tidak dari wilayah uji.",
    ],
    "baselines": [
        {"name": "Peta tutupan lahan global (IO LULC 10 m)", "result": f"menyebut {round(io['ref_io_built_in_lsd_2023_ha'])} dari 799 ha LSD Kuta Utara sudah bangunan pada 2023; jelas salah, tidak bisa dipakai"},
        {"name": "Model v1, dilatih hanya di piksel jelas", "result": f"presisi {obt1['map_vs_obt_pixels_in_lsd']['precision']} di seluruh LSD Kuta Utara; kami tarik"},
        {"name": "Sentinel-1 dan Sentinel-2 (Kuta Utara)", "result": f"average precision {ae['S2+S1']['average_precision']}, presisi {ae['S2+S1']['precision']}"},
        {"name": "Ditambah AlphaEarth (Kuta Utara)", "result": f"average precision {ae['S2+S1+AlphaEarth']['average_precision']}, presisi {ae['S2+S1+AlphaEarth']['precision']}"},
    ],
    "claude": {"verified": sc["n_verified"], "verdicts": sc["verdicts"], "cost_usd": sc["batch_cost_usd"],
               "status_ha": sc["status_ha"], "status_n": sc["status_n"]},
    "cases": [
        {"key": "munggu", "title": "Subak Munggu, Desa Munggu (Mengwi)",
         "news": "Satpol PP Badung memanggil pemilik sedikitnya tujuh bangunan yang diduga berdiri di LSD Subak Munggu (Bali Post, 6 September 2026). Belasan bangunan komersial di kawasan itu disebut masuk LSD dan LP2B (Warta Bali, 25 September 2026).",
         "links": ["https://www.balipost.com/news/2026/09/06/579511/Diduga-Bangun-Vila-di-Lahan...html",
                   "https://wartabalionline.com/2026/09/25/bapenda-pajaki-villa-di-sawah-lsd-subak-munggu/"],
         **cases["munggu"]},
        {"key": "canggu", "title": "Babakan Canggu, Desa Canggu (Kuta Utara)",
         "news": "Pansus TRAP DPRD Bali menghentikan kurang lebih 30 vila di Babakan Canggu yang berdiri di atas LSD dan LP2B pada akhir Desember 2025 (Bali Post, 2 Januari 2026).",
         "links": ["https://www.balipost.com/news/2026/01/02/517301/30-Vila-di-Canggu-Disegel...html"],
         **cases["canggu"]},
    ],
    "badung_share": {"kandidat_2018_2023_pct": round(100 * sc["scores_vs_obt"]["semua"]["ha"] / lsd_ha, 2)},
    "review": review,
    "limits": [
        "Resolusi 10 m: bangunan kecil dan tepi permukiman sering masuk 'perlu tinjau'.",
        "Pembanding hanya mencatat bangunan sampai 2023; tanah urug, jalan, dan bangunan 2024 sampai 2025 tidak terhitung. Sebagian alarm mungkin tanah urug atau bangunan yang belum selesai, tetapi hal ini belum diukur.",
        "Belum ada sampel lapangan atau citra resolusi tinggi berlisensi, jadi akurasi terhadap kondisi lapangan belum diketahui.",
        "Peta di aplikasi dibuat oleh model yang dilatih di semua tile Badung. Angka validasi silang di atas berlaku untuk wilayah yang belum pernah dilihat model, misalnya kabupaten lain.",
        "Periode 2023 ke 2025 belum punya pembanding, jadi belum ada angka akurasinya.",
        "Studi kasus dicocokkan di tingkat desa, karena berita tidak menyebut koordinat bangunan.",
        "AI verifikasi tidak menaikkan presisi; perannya menjelaskan setiap kandidat dan memilah tinjauan. Hanya kandidat seluas minimal 1.000 m² yang diverifikasi.",
        "Hasil adalah indikasi, bukan putusan hukum; setiap kandidat wajib ditinjau petugas.",
    ],
}
json.dump(data, open(f"{OUT}/validasi.json", "w"), indent=1, ensure_ascii=False)
print("validasi.json written")
