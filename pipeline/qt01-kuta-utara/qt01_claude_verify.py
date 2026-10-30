"""QT-01 step 5: Claude verification of RF alarms inside LSD, blind to the footprint reference.

Input: out-of-fold RF predictions from qt01_building_labels.py. Every pixel inside LSD that the RF calls
"alih fungsi" goes to Claude as one image (Sentinel-2 RGB 2018, 2023, 2025, 410 m wide, target in a box)
plus its index values. Claude returns a verdict from a fixed enum. We then compare with the footprint
reference: how many false alarms are rejected, how many true alarms are kept.
Billing: the `ant auth login` profile (Hilmi's org). Run with --count to measure tokens only, --s1 to verify the S2+S1 model alarms.
"""
import base64
import contextlib
import io
import json
import runpy
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor

import anthropic
import matplotlib
import numpy as np
import xarray as xr

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

warnings.filterwarnings("ignore")
MODEL = "claude-opus-5-5"
VERDICTS = ["conversion", "already_built", "harvest_or_fallow", "flooding", "cloud_artifact", "unclear"]
SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": VERDICTS},
        "confidence": {"type": "number"},
        "alasan": {"type": "string"},
    },
    "required": ["verdict", "confidence", "alasan"],
    "additionalProperties": False,
}
SYSTEM = """Kamu memverifikasi alarm alih fungsi sawah dari model satelit untuk Pemda Badung, Bali.
Setiap gambar berisi tiga potongan Sentinel-2 warna asli (10 m per piksel, lebar 410 m) untuk musim kemarau
2018, 2023, dan 2025. Kotak merah menandai piksel sasaran (30 m x 30 m) di dalam Lahan Sawah yang Dilindungi.
Pilih satu verdict:
- conversion: sawah atau lahan hijau pada 2018 menjadi bangunan, jalan, beton, atau tanah urug pada 2023 atau 2025.
- already_built: sasaran sudah berupa bangunan atau permukiman pada 2018 (peta LSD memuat rumah lama).
- harvest_or_fallow: masih sawah; hanya terlihat cokelat atau gundul karena panen, bera, atau olah tanah.
- flooding: genangan air.
- cloud_artifact: awan, bayangan, atau cacat composite.
- unclear: resolusi tidak cukup untuk memutuskan.
Atap baru biasanya putih, oranye, atau abu terang dan bentuknya persegi; sawah panen berwarna cokelat merata dan
mengikuti petak. Jika ragu antara conversion dan yang lain, pilih unclear. confidence 0 sampai 1.
alasan: satu kalimat bahasa Indonesia tentang apa yang terlihat di kotak."""


def load_alarms():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ns = runpy.run_path("qt01_s1_area.py" if "--s1" in sys.argv else "qt01_building_labels.py")
    idx, yv, oof, lsd_s, W = ns["idx"], ns["yv"], ns["oof"], ns["lsd_s"], ns["W"]
    sel = np.flatnonzero(lsd_s & (oof == 1))
    alarms = []
    for k in sel:
        r, c = divmod(int(idx[k]), W)
        alarms.append({"k": int(k), "row": r, "col": c, "ref": int(yv[k])})
    return alarms, ns


def chip(alarm, stacks, path):
    r, c = alarm["row"], alarm["col"]
    fig, ax = plt.subplots(1, 3, figsize=(7.5, 2.8))
    for axi, (yr, s) in zip(ax, stacks.items()):
        im = np.clip(np.dstack([s.B04.values, s.B03.values, s.B02.values]) / 0.18, 0, 1) ** 0.8
        r0, c0 = max(r - 20, 0), max(c - 20, 0)
        axi.imshow(im[r0:r0 + 41, c0:c0 + 41], interpolation="nearest")
        axi.add_patch(Rectangle((c - c0 - 1.5, r - r0 - 1.5), 3, 3, fill=False, ec="red", lw=1.5))
        axi.set_title(str(yr), fontsize=9)
        axi.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close()


def request(alarm, stacks, path):
    r, c = alarm["row"], alarm["col"]
    vals = {yr: (float(s.NDVI_p90.values[r, c]), float(s.B12.values[r, c])) for yr, s in stacks.items()}
    text = "Nilai piksel sasaran (NDVI p90, SWIR B12): " + "; ".join(
        f"{yr}: {v[0]:.2f}, {v[1]:.3f}" for yr, v in vals.items())
    data = base64.standard_b64encode(open(path, "rb").read()).decode()
    return dict(
        model=MODEL, max_tokens=2000, system=SYSTEM,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
            {"type": "text", "text": text}]}])


def main():
    import os
    tag = "_s1" if "--s1" in sys.argv else ""
    os.makedirs("verify_chips" + tag, exist_ok=True)
    alarms, _ = load_alarms()
    stacks = {y: xr.open_dataset(f"stack_{y}.nc") for y in (2018, 2023, 2025)}
    for i, a in enumerate(alarms):
        a["chip"] = f"verify_chips{tag}/A{i:03d}.png"
        chip(a, stacks, a["chip"])
    client = anthropic.Anthropic()
    req0 = request(alarms[0], stacks, alarms[0]["chip"])
    ct = client.messages.count_tokens(model=MODEL, system=req0["system"], messages=req0["messages"],
                                      output_config={"format": req0["output_config"]["format"]})
    n_tp = sum(a["ref"] == 1 for a in alarms)
    print(f"alarms {len(alarms)} (ref alih fungsi {n_tp}, ref sawah tetap {len(alarms) - n_tp}); "
          f"input tokens per request {ct.input_tokens}", flush=True)
    if "--count" in sys.argv:
        return

    def run(a):
        resp = client.messages.create(**request(a, stacks, a["chip"]))
        if resp.stop_reason == "refusal":
            return {**a, "verdict": "refusal", "confidence": 0, "alasan": ""}
        out = json.loads(next(b.text for b in resp.content if b.type == "text"))
        return {**a, **out, "in_tok": resp.usage.input_tokens, "out_tok": resp.usage.output_tokens}

    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(run, alarms))
    json.dump(res, open(f"qt01_claude_verify{tag}.json", "w"), indent=1)
    tin = sum(r.get("in_tok", 0) for r in res); tout = sum(r.get("out_tok", 0) for r in res)
    cost = tin / 1e6 * 4 + tout / 1e6 * 20
    print(f"tokens in {tin}, out {tout}, cost about US${cost:.3f}")
    from collections import Counter
    for ref in (1, 0):
        print("ref", {1: "alih fungsi", 0: "sawah tetap"}[ref], Counter(r["verdict"] for r in res if r["ref"] == ref))
    keep = [r for r in res if r["verdict"] == "conversion"]
    tp_k = sum(r["ref"] == 1 for r in keep)
    print(f"RF precision {n_tp / len(alarms):.3f} -> after Claude {tp_k / max(len(keep), 1):.3f}; "
          f"true alarms kept {tp_k}/{n_tp}; false alarms rejected {len(alarms) - n_tp - (len(keep) - tp_k)}/{len(alarms) - n_tp}")


if __name__ == "__main__":
    main()
