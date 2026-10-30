"""QT-02 step 2: Badung model v3 (S2+S1+AlphaEarth, Earth Engine features), honest evaluation, LSD map.

Labels from Open Buildings Temporal: positive = presence 2018 < 0.1 and 2023 >= 0.3; negative = other pixels
with presence 2018 < 0.1; pixels already built in 2018 are left out. Training draws a balanced sample per
tile. Evaluation: 5 folds of whole 5 km tiles, so every score comes from tiles the model never saw, on ALL
held-out LSD pixels at natural prevalence. Threshold picked on a natural-prevalence sample of training tiles.
  python qt02_model.py cv        # cross-validation report -> qt02_cv.json
  python qt02_model.py predict   # final model, LSD probability per tile -> pred/<tile>.npy
"""
import glob
import json
import os
import sys
import warnings

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve

warnings.filterwarnings("ignore")
TILES = sorted(os.path.basename(p)[:-4] for p in glob.glob("tiles/*.npz"))
N_POS, N_NEG, N_CAL = 1500, 3000, 3000


def tile_features(name):
    d = np.load(f"tiles/{name}.npz")
    a, b = d["s2s1_2018"].astype(np.float32), d["s2s1_2023"].astype(np.float32)
    e1, e2 = d["ae_2018"].astype(np.float32), d["ae_2023"].astype(np.float32)
    X = np.concatenate([a, b, b - a, e1, e2, e2 - e1, (e1 * e2).sum(0)[None]]).reshape(241, -1).T
    obt = d["obt"].astype(np.float32).reshape(2, -1)
    valid = (obt[0] < 0.1) & np.isfinite(X).all(1)
    y = (obt[1] >= 0.3).astype(np.int8)
    return X, y, valid, d["lsd"].ravel()


def samples(names, rng):
    Xs, ys, Xc, yc = [], [], [], []
    for n in names:
        X, y, v, _ = tile_features(n)
        p, q = np.flatnonzero(v & (y == 1)), np.flatnonzero(v & (y == 0))
        idx = np.concatenate([rng.choice(p, min(N_POS, p.size), replace=False), rng.choice(q, min(N_NEG, q.size), replace=False)])
        Xs.append(X[idx]); ys.append(y[idx])
        c = rng.choice(np.flatnonzero(v), min(N_CAL, int(v.sum())), replace=False)
        Xc.append(X[c]); yc.append(y[c])
    return np.concatenate(Xs), np.concatenate(ys), np.concatenate(Xc), np.concatenate(yc)


def fit(X, y):
    return RandomForestClassifier(300, min_samples_leaf=3, n_jobs=-1, random_state=0).fit(X, y)


def best_threshold(rf, Xc, yc):
    pr, rc, th = precision_recall_curve(yc, rf.predict_proba(Xc)[:, 1])
    f1 = 2 * pr * rc / np.maximum(pr + rc, 1e-9)
    return float(th[np.argmax(f1[:-1])])


def cv():
    rng = np.random.default_rng(7)
    order = rng.permutation(TILES)
    folds = [order[k::5].tolist() for k in range(5)]
    yt_all, pt_all, pred_all, thrs, per_fold = [], [], [], [], []
    for k, test in enumerate(folds):
        train = [t for t in TILES if t not in test]
        X, y, Xc, yc = samples(train, rng)
        rf = fit(X, y)
        thr = best_threshold(rf, Xc, yc)
        thrs.append(thr)
        yt_f, pt_f = [], []
        for n in test:
            Xt, yt, v, lsd = tile_features(n)
            m = v & lsd
            if m.any():
                yt_f.append(yt[m]); pt_f.append(rf.predict_proba(Xt[m])[:, 1])
        yt_f, pt_f = np.concatenate(yt_f), np.concatenate(pt_f)
        pred = pt_f >= thr
        tp = int((pred & (yt_f == 1)).sum())
        per_fold.append({"fold": k, "tiles": test, "thr": round(thr, 3), "prevalence": round(float(yt_f.mean()), 4),
                         "precision": round(tp / max(int(pred.sum()), 1), 3), "recall": round(tp / max(int(yt_f.sum()), 1), 3)})
        print(per_fold[-1], flush=True)
        yt_all.append(yt_f); pt_all.append(pt_f); pred_all.append(pred)
    yt, pt, pred = np.concatenate(yt_all), np.concatenate(pt_all), np.concatenate(pred_all)
    tp = int((pred & (yt == 1)).sum())
    res = {"lsd_pixels": int(yt.size), "lsd_new_building_ha": round(float(yt.sum()) / 100, 1),
           "prevalence": round(float(yt.mean()), 4), "average_precision": round(float(average_precision_score(yt, pt)), 3),
           "threshold_median": round(float(np.median(thrs)), 3), "precision": round(tp / max(int(pred.sum()), 1), 3),
           "recall": round(tp / max(int(yt.sum()), 1), 3), "mapped_ha": round(float(pred.sum()) / 100, 1)}
    for t in (0.8, 0.9):
        pp = pt >= t
        res[f"at_{t}"] = {"precision": round(float((pp & (yt == 1)).sum() / max(pp.sum(), 1)), 3),
                          "recall": round(float((pp & (yt == 1)).sum() / max(yt.sum(), 1)), 3)}
    res["folds"] = per_fold
    print(json.dumps({k: v for k, v in res.items() if k != "folds"}, indent=1))
    json.dump(res, open("qt02_cv.json", "w"), indent=1)


def predict():
    rng = np.random.default_rng(11)
    X, y, Xc, yc = samples(TILES, rng)
    rf = fit(X, y)
    thr = json.load(open("qt02_cv.json"))["threshold_median"]
    os.makedirs("pred", exist_ok=True)
    for n in TILES:
        Xt, _, _, lsd = tile_features(n)
        p = np.zeros(lsd.size, np.float32)
        ok = lsd & np.isfinite(Xt).all(1)
        if ok.any():
            p[ok] = rf.predict_proba(Xt[ok])[:, 1]
        np.save(f"pred/{n}.npy", p.reshape(500, 500))
    print("predicted", len(TILES), "tiles, threshold", thr)


if __name__ == "__main__":
    {"cv": cv, "predict": predict}[sys.argv[1]]()
