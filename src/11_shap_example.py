"""Step 11 - SHAP waterfall for one variant using the FINAL model (the one predict.py uses),
so the presentation figure matches the live demo exactly.

Usage: python src/11_shap_example.py [key] [name]   (default: TP53 R175H)
"""
import sys

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shap

from common import FIG, ROOT, load_data

key = sys.argv[1] if len(sys.argv) > 1 else "17-7675088-C-T"
name = sys.argv[2] if len(sys.argv) > 2 else "TP53_R175H"

df, emb = load_data()
row = df[df.key == key].iloc[[0]]
b = joblib.load(ROOT / "results/models/D_XGB_ESM_final.joblib")
b["clf"].set_params(device="cpu")
pcs = b["pca"].transform(emb[[int(row.emb_row.iloc[0])]])
X = np.hstack([row[b["feats"]].astype(float).values, pcs])
raw = float(b["clf"].predict_proba(X)[:, 1][0])
cal = float(b["iso"].predict([raw])[0])
expl = shap.TreeExplainer(b["clf"])
e = shap.Explanation(expl.shap_values(X)[0], expl.expected_value, X[0], feature_names=b["names"])
plt.figure()
shap.plots.waterfall(e, max_display=10, show=False)
plt.title(f"{name.replace('_', ' ')} (final model): calibrated P(pathogenic) = {cal:.3f}")
out = FIG / f"shap_waterfall_{name}_final.png"
plt.savefig(out, bbox_inches="tight", dpi=150)
print(f"raw={raw:.4f} calibrated={cal:.4f} -> {out}")
for f, v in sorted(zip(b["names"], e.values), key=lambda t: -abs(t[1]))[:6]:
    print(f"  {f:<16} {v:+.3f}")
