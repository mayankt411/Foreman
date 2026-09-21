"""Phase 5 evaluation on results/predictions.csv. Writes results/phase5_eval.json.

Questions answered honestly on 189 images (153 out-of-fold + 36 locked test):
1. Which RPI component finds model errors? (AUROC, bootstrap CI)
2. Does the full RPI beat its parts and confidence alone at the same review budget?
3. Are learned weights better than 0.35/0.35/0.30? (weights fit on OOF, judged on test)
4. Per-class ECE with sample counts.
"""
import json, os
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
rng = np.random.default_rng(42)
d = pd.read_csv(os.path.join(RES, "predictions.csv"))
d["wrong"] = (d.predicted_label != d.ground_truth_label).astype(int)
d["missed_defect"] = ((d.ground_truth_label != "normal") & (d.predicted_label == "normal")).astype(int)
d["unfaith"] = 1 - d.faithfulness_score
W = (0.35, 0.35, 0.30)
d["rpi_full"] = W[0]*d.u_calib + W[1]*d.severity_score + W[2]*d.unfaith
BUDGET = 0.15  # review the top 15% by score, same as the deployed threshold

variants = {
    "confidence_only (1-raw)": 1 - d.raw_confidence,
    "U only": d.u_calib,
    "Severity only": d.severity_score,
    "Unfaithfulness only": d.unfaith,
    "U + Unfaith": d.u_calib + d.unfaith,
    "U + Severity": d.u_calib + d.severity_score,
    "Full RPI 0.35/0.35/0.30": d.rpi_full,
    "cam_peak low (no truth box)": -d.cam_peak,
    "U + cam_peak low (no truth box)": d.u_calib + (d.cam_peak.max() - d.cam_peak) / d.cam_peak.max(),
}

def budget_stats(score, wrong, missed, budget=BUDGET):
    k = int(round(len(score) * budget))
    top = np.argsort(-np.asarray(score))[:k]
    return {
        "errors_caught": float(np.asarray(wrong)[top].sum() / max(1, np.asarray(wrong).sum())),
        "misses_caught": float(np.asarray(missed)[top].sum() / max(1, np.asarray(missed).sum())),
        "precision": float(np.asarray(wrong)[top].mean()),
    }

def boot(fn, n=1000):
    vals = []
    idx = np.arange(len(d))
    for _ in range(n):
        s = rng.choice(idx, len(idx), replace=True)
        try:
            vals.append(fn(s))
        except ValueError:
            pass
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]

wrong = d.wrong.values; missed = d.missed_defect.values
abl = {}
for name, sc in variants.items():
    sc = np.asarray(sc, float)
    row = {"auroc_error": float(roc_auc_score(wrong, sc))}
    row["auroc_error_ci95"] = boot(lambda s: roc_auc_score(wrong[s], sc[s]))
    row.update(budget_stats(sc, wrong, missed))
    row["errors_caught_ci95"] = boot(lambda s: budget_stats(sc[s], wrong[s], missed[s])["errors_caught"])
    abl[name] = row
rand = {"errors_caught": BUDGET, "misses_caught": BUDGET, "precision": float(wrong.mean())}

# learned weights: fit on OOF rows only, evaluate on locked test rows
feats = np.c_[d.u_calib, d.severity_score, d.unfaith]
oof = (d.source == "oof").values; test = ~oof
clf = LogisticRegression(C=1.0, class_weight="balanced").fit(feats[oof], wrong[oof])
coef = clf.coef_[0]; wts = np.clip(coef, 0, None); wts = wts / wts.sum() if wts.sum() > 0 else np.array(W)
learned = feats @ wts
learn_res = {
    "raw_coef_[U,S,Unfaith]": [float(c) for c in coef],
    "normalised_nonneg_weights": [float(w) for w in wts],
    "test_auroc_learned": float(roc_auc_score(wrong[test], learned[test])),
    "test_auroc_default": float(roc_auc_score(wrong[test], d.rpi_full.values[test])),
    "test_errors_caught_learned": budget_stats(learned[test], wrong[test], missed[test])["errors_caught"],
    "test_errors_caught_default": budget_stats(d.rpi_full.values[test], wrong[test], missed[test])["errors_caught"],
    "n_test": int(test.sum()),
}

# per-class ECE (10 bins, percent) on calibrated confidence, grouped by predicted class
def ece(conf, ok, bins=10):
    edges = np.linspace(0, 1, bins + 1); tot = 0.0
    for i in range(bins):
        m = (conf >= edges[i]) & ((conf < edges[i+1]) if i < bins - 1 else (conf <= edges[i+1]))
        if m.any():
            tot += m.mean() * abs(ok[m].mean() - conf[m].mean())
    return float(100 * tot)
ok = 1 - wrong
per_class = {}
for c, g in d.groupby("predicted_label"):
    i = g.index.values
    per_class[c] = {"n_predicted": int(len(g)), "accuracy": float(ok[i].mean()),
                    "mean_conf": float(g.calibrated_confidence.mean()),
                    "ece_percent": ece(g.calibrated_confidence.values, ok[i]),
                    "reliable": bool(len(g) >= 30)}

out = {"n": int(len(d)), "review_budget": BUDGET, "error_rate": float(wrong.mean()),
       "n_missed_defects": int(missed.sum()), "random_baseline": rand,
       "ablation": abl, "learned_weights": learn_res, "per_class_ece": per_class,
       "notes": [
                 "faithfulness_score uses the ground-truth box, so unfaithfulness is an oracle signal. It is not available at deployment. Its AUROC is inflated.","Scores judged on model errors (pred != truth), not on defect severity.",
                 "OOF predictions come from held-out folds; test is the locked split.",
                 "Per-class ECE with fewer than 30 predictions is not reliable."]}
json.dump(out, open(os.path.join(RES, "phase5_eval.json"), "w"), indent=2)
print(json.dumps({k: v for k, v in out.items() if k != "ablation"}, indent=1)[:2500])
for k, v in abl.items():
    print(f"{k:28s} AUROC {v['auroc_error']:.3f} {np.round(v['auroc_error_ci95'],3)}  caught {v['errors_caught']:.2f}  misses {v['misses_caught']:.2f}")
