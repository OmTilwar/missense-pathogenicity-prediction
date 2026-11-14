"""Step 9 - Exploratory analysis of the dataset for the study guide.

Writes results/analysis/*.csv|json and results/figures/eda_*.png:
  funnel.csv            ClinVar 2026-09 filtering funnel (how 3M rows become 202k variants)
  feature_stats.csv     per feature: missing %, median in P vs B, single-feature AUROC
  top_genes.csv         genes with most labelled variants and their pathogenic fraction
  examples.csv          full feature vectors of example variants
  esm_example.json      ESM-2 input/output worked example for TP53 position 175
"""
import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import BIO, ESM, FIG, GROUPS, ROOT, auroc

OUT = ROOT / "results/analysis"
OUT.mkdir(parents=True, exist_ok=True)
INK, INK2, GRID, BLUE, ORANGE = "#0b0b0b", "#52514e", "#e6e5e0", "#2a78d6", "#eb6834"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "figure.dpi": 150, "savefig.bbox": "tight"})

# ---------------------------------------------------------------- 1. filtering funnel (2026-09)
POS = {"Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic"}
NEG = {"Benign", "Likely benign", "Benign/Likely benign"}
STARS = {"criteria provided, single submitter", "criteria provided, multiple submitters, no conflicts",
         "reviewed by expert panel", "practice guideline"}
MIS = re.compile(r"\(p\.([A-Z][a-z]{2})\d+([A-Z][a-z]{2})\)$")
counts = dict.fromkeys(["all rows", "GRCh38 assembly", "single-nucleotide variant", "P/LP or B/LB label",
                        ">= 1 review star", "missense protein change"], 0)
sig_dist, star_dist = {}, {}
for ch in pd.read_csv(ROOT / "data/raw/variant_summary_2026-09.txt.gz", sep="\t", dtype=str, chunksize=500_000,
                      usecols=["Type", "Name", "ClinicalSignificance", "ReviewStatus", "Assembly"]):
    counts["all rows"] += len(ch)
    ch = ch[ch.Assembly == "GRCh38"]; counts["GRCh38 assembly"] += len(ch)
    ch = ch[ch.Type == "single nucleotide variant"]; counts["single-nucleotide variant"] += len(ch)
    for k, v in ch.ClinicalSignificance.value_counts().items():
        sig_dist[k] = sig_dist.get(k, 0) + v
    ch = ch[ch.ClinicalSignificance.isin(POS | NEG)]; counts["P/LP or B/LB label"] += len(ch)
    for k, v in ch.ReviewStatus.value_counts().items():
        star_dist[k] = star_dist.get(k, 0) + v
    ch = ch[ch.ReviewStatus.isin(STARS)]; counts[">= 1 review star"] += len(ch)
    m = ch.Name.str.extract(MIS)
    counts["missense protein change"] += int(((m[0].notna()) & (m[0] != m[1]) & (m[1] != "Ter")).sum())
counts["final (deduplicated, valid alleles)"] = len(pd.read_parquet(ROOT / "data/interim/clinvar_2026-09.parquet"))
pd.Series(counts).to_csv(OUT / "funnel.csv", header=["rows"])
pd.Series(sig_dist).sort_values(ascending=False).head(15).to_csv(OUT / "clinsig_distribution_snv.csv", header=["rows"])
pd.Series(star_dist).sort_values(ascending=False).to_csv(OUT / "review_status_PB_snv.csv", header=["rows"])
print(pd.Series(counts).to_string())

# ---------------------------------------------------------------- 2. per-feature statistics
df = pd.read_parquet(ROOT / "data/processed/variants.parquet")
lab = df[df.label_new.notna()].copy()
y = lab.label_new.values.astype(int)
group_of = {f: g for g, fs in GROUPS.items() for f in fs}
rows = []
for f in BIO + ESM + [c for c in df if c.startswith("bl_")]:
    x = lab[f].astype(float).values
    m = ~np.isnan(x)
    a = auroc(y[m], x[m]) if m.sum() > 100 and len(np.unique(x[m])) > 1 else np.nan
    rows.append({"feature": f, "group": group_of.get(f, "baseline"), "missing_pct": 100 * (1 - m.mean()),
                 "median_pathogenic": np.nanmedian(x[y == 1]), "median_benign": np.nanmedian(x[y == 0]),
                 "mean_pathogenic": np.nanmean(x[y == 1]), "mean_benign": np.nanmean(x[y == 0]),
                 "auroc_raw": a, "auroc_best_direction": max(a, 1 - a) if a == a else np.nan,
                 "higher_means": "pathogenic" if a > 0.5 else "benign"})
fs = pd.DataFrame(rows)
fs.to_csv(OUT / "feature_stats.csv", index=False)
print(fs[~fs.feature.str.match(r"(ref|alt)_[A-Z]$")].round(3).to_string(index=False))

# ---------------------------------------------------------------- 3. genes
g = lab.groupby("gene").label_new.agg(["size", "mean"]).rename(columns={"size": "n_variants", "mean": "frac_pathogenic"})
g.sort_values("n_variants", ascending=False).head(25).to_csv(OUT / "top_genes.csv")
gs = {"n_genes": int(len(g)), "median_variants_per_gene": float(g.n_variants.median()),
      "genes_with_1_variant": int((g.n_variants == 1).sum()),
      "share_variants_in_top_100_genes": float(g.n_variants.sort_values(ascending=False).head(100).sum() / len(lab)),
      "genes_all_benign": int((g.frac_pathogenic == 0).sum()), "genes_all_pathogenic": int((g.frac_pathogenic == 1).sum()),
      "variants_in_single_class_genes": float(lab.gene.map(g.frac_pathogenic).isin([0, 1]).mean())}
json.dump(gs, open(OUT / "gene_stats.json", "w"), indent=1)
print(gs)

# amino-acid change table
aa = lab.groupby(["aa_ref", "aa_alt"]).label_new.agg(["size", "mean"]).reset_index()
aa.sort_values("size", ascending=False).head(20).to_csv(OUT / "top_aa_changes.csv", index=False)
ref_rate = lab.groupby("aa_ref").label_new.mean().sort_values(ascending=False)
ref_rate.to_csv(OUT / "pathogenic_rate_by_ref_aa.csv")

# allele-frequency bins
maxaf = 10 ** lab[["af_ex", "af_ge", "af_ex_popmax", "af_ge_popmax"]].max(axis=1) - 1e-7
bins = pd.cut(maxaf, [-1, 0, 1e-5, 1e-4, 1e-3, 1e-2, 1.1], labels=["absent", "<1e-5", "1e-5–1e-4", "1e-4–1e-3", "1e-3–1e-2", "≥1%"])
afb = pd.crosstab(bins, lab.label_new).rename(columns={0.0: "benign", 1.0: "pathogenic"})
afb["frac_pathogenic"] = afb.pathogenic / afb.sum(axis=1)
afb.to_csv(OUT / "af_bins.csv")
print(afb)

# ---------------------------------------------------------------- 4. example variants (full vectors)
ex_keys = {"TP53 R175H (pathogenic)": "17-7675088-C-T"}
ben = lab[(lab.label_new == 0) & (lab.gene == "BRCA1") & lab.esm_llr.notna() & lab.af_plddt.notna()].sort_values("af_ex", ascending=False)
ex_keys[f"BRCA1 {ben.aa_ref.iloc[0]}{ben.aa_pos.iloc[0]}{ben.aa_alt.iloc[0]} (benign, common)"] = ben.key.iloc[0]
cols = ["key", "gene", "aa_ref", "aa_pos", "aa_alt", "label_old", "label_new"] + BIO + ESM + [c for c in df if c.startswith("bl_")]
ex = df[df.key.isin(ex_keys.values())][cols].set_index("key").T
ex.columns = [k for k, v in ex_keys.items() for c in ex.columns if c == v]
ex.to_csv(OUT / "examples.csv")

# ---------------------------------------------------------------- 5. ESM-2 worked example
import torch
from transformers import AutoTokenizer, EsmForMaskedLM
import importlib, sys
sys.path.insert(0, str(ROOT / "src"))
esm_mod = importlib.import_module("04_esm2_features")
seqs = json.load(open(ROOT / "data/interim/uniprot_seqs.json"))
seq = seqs["P04637"]
tok = AutoTokenizer.from_pretrained(esm_mod.MODEL)
model = EsmForMaskedLM.from_pretrained(esm_mod.MODEL, torch_dtype=torch.float16).cuda().eval()
enc = tok(seq, return_tensors="pt")
with torch.no_grad():
    outp = model(**enc.to("cuda"), output_hidden_states=True)
lp = torch.log_softmax(outp.logits[0].float(), -1)
aa_ids = [tok.convert_tokens_to_ids(a) for a in esm_mod.AAS]
pos_lp = lp[175, aa_ids].cpu().numpy()  # token index 175 = residue 175 (index 0 is <cls>)
probs = np.exp(pos_lp) / np.exp(pos_lp).sum()
order = np.argsort(-probs)
esm_ex = {"protein": "TP53 (UniProt P04637)", "length": len(seq), "sequence_first_60": seq[:60],
          "window_around_175": seq[164:186], "residue_175": seq[174],
          "token_ids_first_12": enc["input_ids"][0][:12].tolist(),
          "tokens_first_12": tok.convert_ids_to_tokens(enc["input_ids"][0][:12].tolist()),
          "n_tokens": int(enc["input_ids"].shape[1]), "logits_shape": list(outp.logits.shape),
          "hidden_shape": list(outp.hidden_states[-1].shape),
          "top5_at_175": [(esm_mod.AAS[i], round(float(probs[i]), 4)) for i in order[:5]],
          "p_R": round(float(probs[esm_mod.AAS.index('R')]), 5), "p_H": round(float(probs[esm_mod.AAS.index('H')]), 6),
          "logp_R": round(float(pos_lp[esm_mod.AAS.index('R')]), 3), "logp_H": round(float(pos_lp[esm_mod.AAS.index('H')]), 3),
          "llr_R175H": round(float(pos_lp[esm_mod.AAS.index('H')] - pos_lp[esm_mod.AAS.index('R')]), 3),
          "entropy_175": round(float(-(probs * np.log(probs + 1e-12)).sum()), 4),
          "embedding_first5_at_175": [round(float(v), 4) for v in outp.hidden_states[-1][0, 175, :5].float().cpu()]}
# a tolerant position for contrast: the residue with highest entropy in TP53
ent = -(torch.softmax(outp.logits[0, 1:-1].float()[:, aa_ids], -1) * torch.log_softmax(outp.logits[0, 1:-1].float()[:, aa_ids], -1)).sum(-1).cpu().numpy()
esm_ex["most_tolerant_position"] = int(ent.argmax() + 1)
esm_ex["most_tolerant_residue"] = seq[int(ent.argmax())]
esm_ex["most_tolerant_entropy"] = round(float(ent.max()), 3)
json.dump(esm_ex, open(OUT / "esm_example.json", "w"), indent=1)
print(json.dumps(esm_ex, indent=1))

# ---------------------------------------------------------------- 6. figures
def dist_plot(ax, f, title, xlabel, clip=None):
    for lbl, col, nm in ((0, BLUE, "Benign"), (1, ORANGE, "Pathogenic")):
        x = lab.loc[lab.label_new == lbl, f].dropna().values
        if clip:
            x = np.clip(x, *clip)
        ax.hist(x, bins=60, density=True, histtype="step", lw=2, color=col, label=nm)
    ax.set(title=title, xlabel=xlabel, ylabel="density")
    ax.legend(frameon=False, fontsize=8)

fig, ax = plt.subplots(2, 3, figsize=(14, 7.5))
dist_plot(ax[0, 0], "af_ex_popmax", "gnomAD popmax AF (log10)", "log10(AF + 1e-7); -7 = absent")
dist_plot(ax[0, 1], "phylop_100", "phyloP 100-way conservation", "score (high = conserved)")
dist_plot(ax[0, 2], "esm_llr", "ESM-2 log-likelihood ratio", "log p(alt) − log p(ref)")
dist_plot(ax[1, 0], "grantham", "Grantham distance", "physicochemical distance ref→alt")
dist_plot(ax[1, 1], "af_plddt", "AlphaFold pLDDT at residue", "confidence 0–100 (high = ordered)")
dist_plot(ax[1, 2], "af_contacts", "AlphaFold Cα contacts (burial)", "neighbours within 10 Å")
fig.suptitle("How key features separate pathogenic from benign (ClinVar 2026-09, 202,015 variants)", x=0.01, ha="left")
fig.tight_layout(); fig.savefig(FIG / "eda_feature_distributions.png"); plt.close(fig)

top = fs[(fs.group != "baseline") & ~fs.feature.str.match(r"(ref|alt)_[A-Z]$")].sort_values("auroc_best_direction").tail(25)
cmap = {"population": "#2a78d6", "conservation": "#1baf7a", "protein_context": "#eda100", "structure": "#e87ba4",
        "aa_properties": "#eb6834", "esm2": "#4a3aa7"}
fig, ax = plt.subplots(figsize=(8, 7))
ax.barh(top.feature, top.auroc_best_direction - 0.5, left=0.5, color=[cmap[g] for g in top.group], height=0.7)
for gname, col in cmap.items():
    ax.barh([], [], color=col, label=gname)
ax.set(xlim=(0.5, 0.95), xlabel="AUROC of the feature on its own (0.5 = useless)", title="Single-feature predictive power (top 25)")
ax.legend(frameon=False, fontsize=8, loc="lower right"); ax.grid(axis="y", visible=False)
fig.savefig(FIG / "eda_single_feature_auroc.png"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
ax[0].bar(afb.index.astype(str), afb.frac_pathogenic, color=BLUE)
for i, (v, n) in enumerate(zip(afb.frac_pathogenic, afb[["benign", "pathogenic"]].sum(axis=1))):
    ax[0].text(i, v + 0.01, f"{v:.0%}\nn={n:,}", ha="center", fontsize=8)
ax[0].set(ylim=(0, 0.8), ylabel="fraction pathogenic", xlabel="max gnomAD allele frequency", title="Common variants are almost never pathogenic")
tg = g.sort_values("n_variants", ascending=False).head(15)
ax[1].barh(tg.index[::-1], tg.n_variants[::-1], color=BLUE)
for i, (n, fp) in enumerate(zip(tg.n_variants[::-1], tg.frac_pathogenic[::-1])):
    ax[1].text(n, i, f" {fp:.0%} P", va="center", fontsize=8)
ax[1].set(xlabel="labelled missense variants", title="Top 15 genes (label = % pathogenic)"); ax[1].grid(axis="y", visible=False)
fig.tight_layout(); fig.savefig(FIG / "eda_af_and_genes.png"); plt.close(fig)

miss = fs[(fs.group != "baseline") & ~fs.feature.str.match(r"(ref|alt)_[A-Z]$")].groupby("group").missing_pct.mean()
print("mean missing % by group:\n", miss.round(1))
