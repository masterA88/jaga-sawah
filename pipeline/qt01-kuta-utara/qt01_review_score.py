"""QT-01 step 13b: score Hilmi's blind review (tinjau_hasil.json from /tinjau) against the hidden groups.

  python qt01_review_score.py ~/Downloads/tinjau_hasil.json
Reports, per group, how the reviewer labelled the items. The controls show how far a 10 m review can be
trusted; the obt_negatif group gives the share of OBT "false alarms" that are conversion without a full building.
"""
import json
import sys
from collections import Counter

ans = json.load(open(sys.argv[1]))
key = json.load(open("review_key.json"))
out = {}
for grp in ("obt_negatif", "obt_positif", "stabil"):
    ids = [k["id"] for k in key if k["grp"] == grp]
    c = Counter(ans.get(i, "belum") for i in ids)
    decided = c["alih_fungsi"] + c["masih_hijau"] + c["sudah_bangunan_2018"]
    out[grp] = {"n": len(ids), **c, "share_alih_fungsi_of_decided": round(c["alih_fungsi"] / max(decided, 1), 3)}
print(json.dumps(out, indent=1))
json.dump(out, open("qt01_review_score.json", "w"), indent=1)
