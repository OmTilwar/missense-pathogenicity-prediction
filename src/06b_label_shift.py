"""Step 6b - Label-shift correction for calibration over time (improvement).

The P/LP fraction changes between ClinVar eras (2023 train: ~39%, later variants: ~24%), so
probabilities calibrated on the training era are too high on new variants. Saerens et al. (2002)
EM re-estimates the new class prior from the model's *unlabelled* test predictions and rescales
the posteriors. No test labels are used; labels are only used afterwards to score the result.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import FIG, TAB, ece

pred = pd.read_parquet(TAB / "temporal_test_predictions.parquet")
train_prior = pd.read_parquet(TAB.parents[1] / "data/processed/variants.parquet", columns=["label_old"]).label_old.mean()


def adjust(p, old, new):
    a = p * new / old
    b = (1 - p) * (1 - new) / (1 - old)
    return a / (a + b)


def em_prior(p, old, iters=200):
    new = old
    for _ in range(iters):
        nxt = adjust(p, old, new).mean()
        if abs(nxt - new) < 1e-7:
            break
        new = nxt
    return new


rows, y = [], pred.label.values
for model in ("B_LR", "C_XGB", "D_XGB_ESM"):
    p = pred[model].values
    est = em_prior(p, train_prior)
    q = adjust(p, train_prior, est)
    for name, s in (("isotonic (train-era)", p), ("isotonic + EM label-shift", q)):
        rows.append({"model": model, "calibration": name, "estimated_prior": est if "EM" in name else train_prior,
                     "true_prior": y.mean(), "brier": np.mean((s - y) ** 2), "ece": ece(y, s)})
    if model == "D_XGB_ESM":
        pred["D_XGB_ESM_shift"] = q
out = pd.DataFrame(rows)
out.to_csv(TAB / "label_shift_calibration.csv", index=False)
pred.to_parquet(TAB / "temporal_test_predictions.parquet", index=False)
print(out.round(4).to_string(index=False))

fig, ax = plt.subplots(figsize=(5, 4.6))
for nm, s, col, ls in [("Train-era isotonic", pred.D_XGB_ESM.values, "#a3a29c", "--"),
                       ("+ EM label-shift", pred.D_XGB_ESM_shift.values, "#2a78d6", "-")]:
    bins = np.linspace(0, 1, 11); idx = np.clip(np.digitize(s, bins) - 1, 0, 9)
    keep = [b for b in range(10) if (idx == b).sum() > 20]
    ax.plot([s[idx == b].mean() for b in keep], [y[idx == b].mean() for b in keep], marker="o", ms=5, color=col, ls=ls,
            label=f"{nm} (ECE {ece(y, s):.3f})")
ax.plot([0, 1], [0, 1], color="#e6e5e0", lw=1)
ax.set(xlabel="Predicted probability", ylabel="Observed fraction pathogenic", title="Model D calibration on time-travel test")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, fontsize=8)
fig.savefig(FIG / "reliability_label_shift.png", dpi=150, bbox_inches="tight")
