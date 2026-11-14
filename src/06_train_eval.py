"""Step 6 - Experiments A-D under three levels of honest testing, with calibration, CIs,
ablation, circularity analysis and SHAP.

Scenarios
    random    : 2026-09 labels, stratified 80/20 split
    gene      : 2026-09 labels, 5-fold GroupKFold by gene (no gene in both train and test)
    temporal  : train on 2023-01 labels -> test on variants first labelled after 2023-01  (PRIMARY)
Models
    B_LR      : logistic regression, biological features
    C_XGB     : XGBoost, biological features
    D_XGB_ESM : XGBoost, biological features + ESM-2 (scalars + 16 PCs of residue embedding)
    ESM2_LLR  : zero-shot ESM-2 log-likelihood ratio (replication of Brandes et al. 2023)
    + existing tools (baselines, never features)
Every trained model is calibrated with isotonic regression on a gene-disjoint 15% slice of its
own training data. PCA for ESM embeddings is fit on the training fold only.
"""
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import roc_curve, precision_recall_curve
from sklearn.model_selection import GroupKFold, train_test_split

from common import (BIO, ESM, FIG, GROUPS, N_PC, ROOT, SEED, TAB, VariantModel, auprc, auroc, ece,
                    evaluate, load_data)

warnings.filterwarnings("ignore")
BASELINES = {"bl_alphamissense": "AlphaMissense", "bl_revel": "REVEL", "bl_cadd": "CADD", "bl_esm1b": "ESM1b",
             "bl_primateai": "PrimateAI", "bl_clinpred": "ClinPred*", "bl_metarnn": "MetaRNN*", "bl_varity": "VARITY*"}
CIRCULAR = {"bl_clinpred", "bl_metarnn", "bl_varity"}  # trained on ClinVar labels

# colours: reference palette, fixed order (our models), muted ink for external tools
C = {"B_LR": "#eb6834", "C_XGB": "#1baf7a", "D_XGB_ESM": "#2a78d6", "ESM2_LLR": "#4a3aa7",
     "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#a3a29c", "grid": "#e6e5e0"}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": C["ink2"], "axes.labelcolor": C["ink"], "xtick.color": C["ink2"],
                     "ytick.color": C["ink2"], "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.6,
                     "figure.dpi": 150, "savefig.bbox": "tight", "lines.linewidth": 2})

df, emb = load_data()


MODELS = {"B_LR": ("lr", BIO, False), "C_XGB": ("xgb", BIO, False), "D_XGB_ESM": ("xgb", BIO + ESM, True)}


def run_models(train, ytr, test, keep=None):
    preds, fitted = {}, {}
    for name, (kind, feats, pcs) in MODELS.items():
        m = VariantModel(kind, feats, pcs, emb).fit(train, ytr)
        preds[name] = m.predict(test)
        preds[name + "_raw"] = m.predict(test, calibrated=False)
        fitted[name] = m
    return preds, fitted


def score_table(test, y, preds, scenario, subset="all", n_boot=1000):
    rows = []
    for name in MODELS:
        rows.append({"scenario": scenario, "subset": subset, "method": name, "type": "ours",
                     **evaluate(y, preds[name], prob=True, n_boot=n_boot)})
    rows.append({"scenario": scenario, "subset": subset, "method": "ESM2_LLR", "type": "zero-shot (ours)",
                 **evaluate(y, -test.esm_llr.values, n_boot=n_boot)})
    for col, nm in BASELINES.items():
        rows.append({"scenario": scenario, "subset": subset, "method": nm,
                     "type": "baseline (ClinVar-trained, circular)" if col in CIRCULAR else "baseline",
                     **evaluate(y, test[col].values, n_boot=n_boot)})
    return rows


results, store = [], {}

# ------------------------------------------------------------- scenario 1: random split
lab = df[df.label_new.notna()].reset_index(drop=True)
y_all = lab.label_new.values.astype(int)
tr, te = train_test_split(np.arange(len(lab)), test_size=0.2, stratify=y_all, random_state=SEED)
p, _ = run_models(lab.iloc[tr], y_all[tr], lab.iloc[te])
results += score_table(lab.iloc[te], y_all[te], p, "random", n_boot=300)
print("random split done", flush=True)

# ------------------------------------------------------------- scenario 2: gene-disjoint CV
oof = {k: np.full(len(lab), np.nan) for name in MODELS for k in (name, name + "_raw")}
for f, (tr, te) in enumerate(GroupKFold(5).split(lab, y_all, lab.gene)):
    p, _ = run_models(lab.iloc[tr], y_all[tr], lab.iloc[te])
    for k in oof:
        oof[k][te] = p[k]
results += score_table(lab, y_all, oof, "gene_disjoint", n_boot=300)
print("gene-disjoint CV done", flush=True)

# ------------------------------------------------------------- scenario 3: time-travel (primary)
train = df[df.label_old.notna()].reset_index(drop=True)
ytr = train.label_old.values.astype(int)
test = df[df.temporal_test == 1].reset_index(drop=True)
yte = test.label_new.values.astype(int)
p_t, fitted_t = run_models(train, ytr, test)
for subset, mask in {"all": np.ones(len(test), bool), "new_genes": test.temporal_newgene.values == 1,
                     "rare": test.rare.values == 1,
                     "rare_new_genes": (test.rare.values == 1) & (test.temporal_newgene.values == 1)}.items():
    results += score_table(test[mask], yte[mask], {k: v[mask] for k, v in p_t.items()}, "temporal", subset)
# common subset: every baseline available -> fair head-to-head
common = test[list(BASELINES)].notna().all(axis=1).values & test.esm_llr.notna().values
results += score_table(test[common], yte[common], {k: v[common] for k, v in p_t.items()}, "temporal", "common_subset")
print("temporal done", flush=True)

res = pd.DataFrame(results)
res.to_csv(TAB / "main_results.csv", index=False)
pred_out = test[["key", "gene", "aa_ref", "aa_pos", "aa_alt", "rare", "temporal_newgene"]].assign(label=yte, **{k: v for k, v in p_t.items()})
pred_out.to_parquet(TAB / "temporal_test_predictions.parquet", index=False)

# ------------------------------------------------------------- circularity (Grimm 2015 replication)
# Same tools scored on (a) variants already in ClinVar 2023 (possible training data of circular tools)
# vs (b) variants labelled only after 2023.
circ = []
for col, nm in {**BASELINES, "esm_llr": "ESM2_LLR"}.items():
    s_old = train[col].values * (-1 if col == "esm_llr" else 1)
    s_new = test[col].values * (-1 if col == "esm_llr" else 1)
    a, b = evaluate(ytr, s_old, n_boot=200), evaluate(yte, s_new, n_boot=200)
    circ.append({"method": nm, "circular": col in CIRCULAR, "auroc_known_2023": a["auroc"], "auroc_new_after_2023": b["auroc"],
                 "drop": a["auroc"] - b["auroc"]})
circ = pd.DataFrame(circ).sort_values("drop", ascending=False)
circ.to_csv(TAB / "circularity.csv", index=False)

# ------------------------------------------------------------- ablation (temporal, model D)
abl = []
for mode in ("drop", "only"):
    for g in GROUPS:
        if mode == "drop":
            feats = [f for f in BIO + ESM if f not in GROUPS[g]]; pcs = g != "esm2"
        else:
            feats = GROUPS[g]; pcs = g == "esm2"
        m = VariantModel("xgb", feats, pcs, emb).fit(train, ytr)
        s = m.predict(test)
        r = evaluate(yte, s, prob=True, n_boot=200)
        rare_m = test.rare.values == 1
        abl.append({"mode": mode, "group": g, "auroc": r["auroc"], "auroc_lo": r["auroc_lo"], "auroc_hi": r["auroc_hi"],
                    "auprc": r["auprc"], "brier": r["brier"], "auroc_rare": auroc(yte[rare_m], s[rare_m])})
abl = pd.DataFrame(abl)
full = res.query("scenario=='temporal' and subset=='all' and method=='D_XGB_ESM'").iloc[0]
abl["delta_auroc_vs_full"] = abl.auroc - full.auroc
abl.to_csv(TAB / "ablation.csv", index=False)
print("ablation done", flush=True)

# ------------------------------------------------------------- figures
def fig_roc_pr():
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    tools = [("D_XGB_ESM", p_t["D_XGB_ESM"], C["D_XGB_ESM"], "-"), ("C_XGB", p_t["C_XGB"], C["C_XGB"], "-"),
             ("B_LR", p_t["B_LR"], C["B_LR"], "-"), ("ESM2_LLR", -test.esm_llr.values, C["ESM2_LLR"], "-"),
             ("AlphaMissense", test.bl_alphamissense.values, C["ink"], "--"), ("REVEL", test.bl_revel.values, C["ink2"], "--"),
             ("CADD", test.bl_cadd.values, C["muted"], "--")]
    for nm, s, col, ls in tools:
        m = ~np.isnan(s)
        fpr, tpr, _ = roc_curve(yte[m], s[m]); pr, rc, _ = precision_recall_curve(yte[m], s[m])
        ax[0].plot(fpr, tpr, color=col, ls=ls, label=f"{nm} ({auroc(yte[m], s[m]):.3f})")
        ax[1].plot(rc, pr, color=col, ls=ls, label=f"{nm} ({auprc(yte[m], s[m]):.3f})")
    ax[0].plot([0, 1], [0, 1], color=C["grid"], lw=1)
    ax[0].set(xlabel="False positive rate", ylabel="True positive rate", title="ROC — time-travel test")
    ax[1].set(xlabel="Recall", ylabel="Precision", title="Precision–recall — time-travel test")
    for a in ax:
        a.legend(frameon=False, fontsize=8, title="AUROC" if a is ax[0] else "AUPRC", title_fontsize=8)
    fig.savefig(FIG / "roc_pr_temporal.png"); plt.close(fig)


def fig_reliability():
    fig, ax = plt.subplots(figsize=(5, 4.6))
    for nm, s, col, ls in [("D raw", p_t["D_XGB_ESM_raw"], C["muted"], "--"), ("D calibrated", p_t["D_XGB_ESM"], C["D_XGB_ESM"], "-")]:
        bins = np.linspace(0, 1, 11); idx = np.clip(np.digitize(s, bins) - 1, 0, 9)
        xs = [s[idx == b].mean() for b in range(10) if (idx == b).sum() > 20]
        ys = [yte[idx == b].mean() for b in range(10) if (idx == b).sum() > 20]
        ax.plot(xs, ys, marker="o", ms=5, color=col, ls=ls, label=f"{nm} (ECE {ece(yte, s):.3f})")
    ax.plot([0, 1], [0, 1], color=C["grid"], lw=1)
    ax.set(xlabel="Predicted probability", ylabel="Observed fraction pathogenic", title="Reliability — time-travel test")
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(FIG / "reliability_temporal.png"); plt.close(fig)


def fig_splits():
    sub = res[(res.subset == "all") & res.method.isin(list(MODELS) + ["ESM2_LLR", "AlphaMissense", "REVEL", "ClinPred*"])]
    order = ["random", "gene_disjoint", "temporal"]
    methods = ["B_LR", "C_XGB", "D_XGB_ESM", "ESM2_LLR", "AlphaMissense", "REVEL", "ClinPred*"]
    cols = [C["B_LR"], C["C_XGB"], C["D_XGB_ESM"], C["ESM2_LLR"], C["ink"], C["ink2"], C["muted"]]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    w = 0.8 / len(methods)
    for i, (m, col) in enumerate(zip(methods, cols)):
        vals = [sub[(sub.scenario == s) & (sub.method == m)].auroc.values[0] for s in order]
        ax.bar(np.arange(3) + i * w, vals, w * 0.9, color=col, label=m)
    ax.set_xticks(np.arange(3) + w * (len(methods) - 1) / 2, ["Random 80/20", "Gene-disjoint (5-fold)", "Time-travel (primary)"])
    ax.set(ylim=(0.5, 1.0), ylabel="AUROC", title="Performance under three levels of testing")
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="lower left")
    ax.grid(axis="x", visible=False)
    fig.savefig(FIG / "auroc_by_split.png"); plt.close(fig)


def fig_ablation():
    d = abl[abl["mode"] == "drop"].sort_values("delta_auroc_vs_full")
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.barh(d.group, d.delta_auroc_vs_full, color=C["D_XGB_ESM"], height=0.6)
    for y_, v in enumerate(d.delta_auroc_vs_full):
        ax.text(v - 0.0005, y_, f"{v:+.3f}", va="center", ha="right", fontsize=8, color=C["ink"])
    ax.axvline(0, color=C["ink2"], lw=1)
    ax.set(xlabel="Δ AUROC when the group is removed", title="Ablation — Model D, time-travel test")
    ax.grid(axis="y", visible=False)
    fig.savefig(FIG / "ablation.png"); plt.close(fig)


fig_roc_pr(); fig_reliability(); fig_splits(); fig_ablation()

# ------------------------------------------------------------- SHAP (model D, temporal)
mD = fitted_t["D_XGB_ESM"]
samp = test.sample(min(4000, len(test)), random_state=SEED)
Xs = mD._X(samp)
expl = shap.TreeExplainer(mD.clf)
sv = expl.shap_values(Xs)
plt.figure()
shap.summary_plot(sv, Xs, feature_names=mD.names, max_display=20, show=False)
plt.title("SHAP — top 20 features (Model D, time-travel test)")
plt.savefig(FIG / "shap_beeswarm.png"); plt.close()

group_of = {f: g for g, fs in GROUPS.items() for f in fs}
gimp = pd.Series(np.abs(sv).mean(0), index=mD.names).groupby(lambda f: group_of.get(f, "esm2")).sum().sort_values()
fig, ax = plt.subplots(figsize=(6.5, 3.4))
ax.barh(gimp.index, gimp.values, color=C["D_XGB_ESM"], height=0.6)
ax.set(xlabel="Sum of mean |SHAP| (log-odds)", title="Feature-group importance"); ax.grid(axis="y", visible=False)
fig.savefig(FIG / "shap_groups.png"); plt.close(fig)
gimp.to_csv(TAB / "shap_group_importance.csv")

# local explanation: TP53 p.Arg175His (deck example) + top-scoring new pathogenic variant
examples = {"TP53_R175H": df[df.key == "17-7675088-C-T"]}
new_path = test[(yte == 1)].assign(p=p_t["D_XGB_ESM"][yte == 1]).sort_values("p").iloc[[-1]]
examples[f"{new_path.gene.iloc[0]}_{new_path.aa_ref.iloc[0]}{new_path.aa_pos.iloc[0]}{new_path.aa_alt.iloc[0]}_new"] = new_path
for nm, row in examples.items():
    if len(row) == 0:
        continue
    X1 = mD._X(row.iloc[[0]])
    e = shap.Explanation(expl.shap_values(X1)[0], expl.expected_value, X1[0], feature_names=mD.names)
    plt.figure()
    shap.plots.waterfall(e, max_display=12, show=False)
    plt.title(f"{nm}: calibrated P(pathogenic) = {mD.predict(row.iloc[[0]])[0]:.3f}")
    plt.savefig(FIG / f"shap_waterfall_{nm}.png", bbox_inches="tight"); plt.close()

# persist the primary model for the CLI
import joblib
joblib.dump({"feats": mD.feats, "names": mD.names, "pca": mD.pca, "clf": mD.clf, "iso": mD.iso,
             "groups": GROUPS, "n_pc": N_PC}, ROOT / "results/model_D_temporal.joblib")

pd.set_option("display.width", 200)
print(res.query("subset=='all'")[["scenario", "method", "n", "auroc", "auroc_lo", "auroc_hi", "auprc", "brier", "ece"]].round(3).to_string(index=False))
print(res.query("scenario=='temporal' and subset!='all'")[["subset", "method", "n", "auroc", "auprc"]].round(3).to_string(index=False))
print(circ.round(3).to_string(index=False))
print(abl.round(3).to_string(index=False))
