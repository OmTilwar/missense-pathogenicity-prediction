"""Step 10 - Grimm et al. 2015 analysis: performance on 'pure' vs 'mixed' genes.

A gene is 'pure' if all its labelled variants (ClinVar 2026-09) share one class, 'mixed' otherwise.
Type-2 circularity inflates scores on pure genes; Grimm recommends reporting the mixed-gene result.
Bins of the gene's pathogenic fraction reproduce their Figure 3. Uses the time-travel test predictions.
"""
import numpy as np
import pandas as pd

from common import PROC, TAB, auroc

df = pd.read_parquet(PROC / "variants.parquet")
pred = pd.read_parquet(TAB / "temporal_test_predictions.parquet")
lab = df[df.label_new.notna()]
frac = lab.groupby("gene").label_new.mean()
pred = pred.merge(df[["key", "esm_llr"] + [c for c in df if c.startswith("bl_")]], on="key")
pred["gene_frac_path"] = pred.gene.map(frac)
pred["purity"] = np.where(pred.gene_frac_path.isin([0, 1]), "pure", "mixed")
bins = [("pure", lambda f: f.isin([0, 1])), ("mixed (0,1)", lambda f: (f > 0) & (f < 1)),
        ("mixed [0.2,0.8]", lambda f: (f >= 0.2) & (f <= 0.8)), ("mixed [0.4,0.6]", lambda f: (f >= 0.4) & (f <= 0.6))]
methods = {"D_XGB_ESM": "Model D (ours)", "C_XGB": "Model C (ours)", "bl_revel": "REVEL", "bl_alphamissense": "AlphaMissense",
           "bl_cadd": "CADD", "bl_esm1b": "ESM1b", "bl_clinpred": "ClinPred*", "bl_metarnn": "MetaRNN*"}
rows = []
for name, sel in bins:
    m = sel(pred.gene_frac_path).values
    y = pred.label.values[m]
    r = {"gene_bin": name, "variants": int(m.sum()), "pathogenic": int(y.sum()), "genes": pred.gene[m].nunique()}
    for col, nm in methods.items():
        s = pred[col].values[m]; ok = ~np.isnan(s)
        r[nm] = auroc(y[ok], s[ok]) if 0 < y[ok].sum() < ok.sum() else np.nan
    rows.append(r)
out = pd.DataFrame(rows)
out.to_csv(TAB / "pure_vs_mixed_genes.csv", index=False)
pd.set_option("display.width", 220)
print(out.round(3).to_string(index=False))
