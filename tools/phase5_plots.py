"""Regenerate reliability diagrams and confusion matrices from results/predictions.csv.

Replaces the scatter-style plots from the Colab notebook with binned reliability
diagrams (accuracy per confidence bin, with counts) and annotated confusion matrices.
Writes results/plots/{reliability,confusion}_{oof,test}.png
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
PLOTS = os.path.join(RES, "plots")
os.makedirs(PLOTS, exist_ok=True)
CLASSES = ["dry_joint", "incorrect_installation", "pcb_damage", "short_circuit", "normal"]
SHORT = ["dry joint", "incorrect\ninstall.", "pcb\ndamage", "short\ncircuit", "normal"]
d = pd.read_csv(os.path.join(RES, "predictions.csv"))
d["ok"] = (d.predicted_label == d.ground_truth_label).astype(float)


def binned(conf, ok, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    xs, ys, ns = [], [], []
    for i in range(bins):
        m = (conf >= edges[i]) & ((conf < edges[i + 1]) if i < bins - 1 else (conf <= edges[i + 1]))
        if m.any():
            xs.append(conf[m].mean()); ys.append(ok[m].mean()); ns.append(int(m.sum()))
    return np.array(xs), np.array(ys), ns


def ece(conf, ok, bins=10):
    edges = np.linspace(0, 1, bins + 1); tot = 0.0
    for i in range(bins):
        m = (conf >= edges[i]) & ((conf < edges[i + 1]) if i < bins - 1 else (conf <= edges[i + 1]))
        if m.any():
            tot += m.mean() * abs(ok[m].mean() - conf[m].mean())
    return 100 * tot


for split in ["oof", "test"]:
    g = d[d.source == split]
    fig, ax = plt.subplots(figsize=(5.2, 5.2), dpi=130)
    ax.plot([0, 1], [0, 1], "--", color="grey", label="perfect calibration")
    for col, name, color in [("raw_confidence", "raw (T=1)", "#e11d48"), ("calibrated_confidence", "calibrated", "#2563eb")]:
        x, y, n = binned(g[col].values, g.ok.values)
        ax.plot(x, y, "o-", color=color, label=f"{name}, ECE {ece(g[col].values, g.ok.values):.1f}%")
        if col == "calibrated_confidence":
            for xi, yi, ni in zip(x, y, n):
                ax.annotate(str(ni), (xi, yi), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=7, color=color)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.08)
    ax.set_xlabel("confidence (bin mean)"); ax.set_ylabel("accuracy in bin")
    ax.set_title(f"Reliability, {split.upper()} (n={len(g)}), numbers = frames per bin", fontsize=9)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, f"reliability_{split}.png")); plt.close(fig)

    cm = np.zeros((5, 5), int)
    for t, p in zip(g.ground_truth_label, g.predicted_label):
        cm[CLASSES.index(t), CLASSES.index(p)] += 1
    fig, ax = plt.subplots(figsize=(5.6, 5.0), dpi=130)
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(5)); ax.set_xticklabels(SHORT, fontsize=8)
    ax.set_yticks(range(5)); ax.set_yticklabels(SHORT, fontsize=8)
    for i in range(5):
        for j in range(5):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=10,
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_xlabel("predicted"); ax.set_ylabel("true")
    ax.set_title(f"Confusion matrix, {split.upper()} (n={len(g)})", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(PLOTS, f"confusion_{split}.png")); plt.close(fig)
print("plots written to", PLOTS)
