# Results: Leakage-Controlled Prediction of Pathogenic Missense Variants

Week 1 results, generated 5 Oct 2026. Every number below comes from `results/tables/*.csv`,
and every figure is in `results/figures/`.

## 1. Data

| | ClinVar 2023-01 (train era) | ClinVar 2026-09 (latest) |
|---|---|---|
| Missense SNVs, ≥1★, P/LP or B/LB | 91,261 | 202,015 |
| Pathogenic / Likely pathogenic | 35,243 (38.6%) | 61,611 (30.5%) |
| Genes | 8,199 | 15,264 |

- **Time-travel test set:** 124,139 variants that first received a confident label after Jan 2023.
  - 30,333 are pathogenic (24.4%).
  - 26,268 are in genes with no labelled variant in 2023. Only 405 of those are pathogenic.
  - 71,570 are rare (gnomAD AF < 1e-4).
- **Feature coverage:**

  | Source | Coverage |
  |---|---|
  | gnomAD / dbNSFP | 100% |
  | phyloP | 99.9% |
  | UniProt reference residue match | 93% |
  | ESM-2 | 93% |
  | AlphaFold | 81% |

- **Label flips:** only 15 variants switched between P and B across the two releases.

## 2. Main result: three levels of honest testing (AUROC, 95% bootstrap CI)

| Method | Random 80/20 | Gene-disjoint 5-fold | **Time-travel (primary)** | Time-travel AUPRC |
|---|---|---|---|---|
| B: Logistic regression | 0.981 | 0.980 | 0.974 (0.973–0.975) | 0.929 |
| C: XGBoost | 0.990 | 0.985 | 0.984 (0.983–0.985) | 0.960 |
| **D: XGBoost + ESM-2** | **0.992** | **0.988** | **0.987 (0.986–0.987)** | **0.967** |
| ESM-2 LLR zero-shot (ours) | 0.905 | 0.906 | 0.916 | 0.841 |
| AlphaMissense | 0.961 | 0.962 | 0.966 | 0.904 |
| REVEL | 0.971 | 0.972 | 0.975 | 0.936 |
| CADD | 0.928 | 0.929 | 0.939 | 0.799 |
| ESM1b | 0.933 | 0.933 | 0.940 | 0.855 |
| PrimateAI | 0.886 | 0.887 | 0.890 | 0.673 |
| ClinPred* | 0.984 | 0.983 | 0.980 | 0.941 |
| MetaRNN* | 0.987 | 0.987 | 0.985 | 0.957 |
| VARITY* | 0.968 | 0.969 | 0.974 | 0.928 |

\* Trained on ClinVar labels, so these scores are circular and can't be compared fairly.
Figures: `auroc_by_split.png`, `roc_pr_temporal.png`.

**Findings**
1. Model D is the best non-circular method on the primary time-travel test.
   - Its AUROC of 0.987 beats REVEL (0.975) and AlphaMissense (0.966). The confidence intervals do not overlap.
   - The ranking is the same on the subset where every tool has a score (n = 102,384): D 0.987, REVEL 0.977, AlphaMissense 0.967.
2. Each added component helps: LR → XGBoost (+0.010), then + ESM-2 (+0.003 AUROC, +0.007 AUPRC).
3. The model loses very little performance from random to gene-disjoint to time-travel testing
   (0.992 → 0.988 → 0.987). The features describe the variant, not the gene's identity.
4. **Rare variants** (AF < 1e-4, n = 71,570): D reaches AUROC 0.983 and AUPRC 0.975, ahead of REVEL (0.973) and
   AlphaMissense (0.963). The model does not depend only on the allele-frequency shortcut.
5. **New genes** (n = 26,268, only 405 pathogenic): this is the hardest setting.
   - D has AUROC 0.973 but the best AUPRC of any non-circular tool: 0.813, against 0.759 for AlphaMissense and 0.646 for REVEL.
   - AlphaMissense (0.986) and CADD (0.989) rank better by AUROC here, so cross-gene generalisation is our weak spot (see §6).

## 3. Replications

| Paper | What we replicated | Our result | Verdict |
|---|---|---|---|
| Brandes 2023 (ESM1b LLR) | Zero-shot PLM log-likelihood ratio, wild-type marginals, sliding windows, using ESM-2 650M | AUROC 0.906 on all ClinVar 2026 missense; dbNSFP's ESM1b scores 0.933 on the same variants | ✅ Reproduced: a strong zero-shot signal; the larger ESM1b is a little better |
| Grimm 2015 (circularity) | AUROC on variants already in ClinVar 2023 vs. variants labelled later | All 6 tools not trained on ClinVar **gain** 0.017–0.041 on newer variants. ClinVar-trained ClinPred and MetaRNN **lose** 0.005–0.006 | ✅ Circularity is visible: ClinVar-trained tools are inflated on old variants (`circularity.csv`) |
| Pejaver 2022 (PP3/BP4) | Local-posterior thresholds for REVEL, prior 0.0441 | PP3 0.732 / 0.854 / 0.982; BP4 0.406 / 0.271 / 0.081. Published: 0.644 / 0.773 / 0.932 and 0.290 / 0.183 / 0.016 | ⚠️ Partial: same structure, but our pathogenic thresholds are stricter (different ClinVar era, no removal of REVEL training variants, rare-only subset). Published REVEL thresholds still meet every target on our time-travel set |

## 4. Ablation (Model D, time-travel test)

Two experiments: remove one feature group at a time, and train on one group alone. Source: `ablation.csv`, `ablation.png`.

| Feature group | AUROC when removed (Δ) | AUROC alone | AUROC alone, rare variants |
|---|---|---|---|
| Conservation | 0.978 (−0.008) | 0.926 | 0.924 |
| Population frequency | 0.980 (−0.007) | 0.860 | **0.756** |
| ESM-2 | 0.984 (−0.003) | **0.946** | **0.948** |
| Protein context | 0.985 (−0.002) | 0.854 | 0.856 |
| AA properties | 0.986 (−0.001) | 0.768 | 0.764 |
| Structure (AlphaFold) | 0.986 (−0.000) | 0.778 | 0.781 |

- Conservation and population frequency are the most important groups and are not redundant with the others.
- ESM-2 is the strongest single group. Supervised ESM-2 features (0.946) beat the zero-shot LLR alone (0.916).
- Population frequency alone falls to 0.756 on rare variants. Most of its power comes from the
  BA1/BS1 "common means benign" rule that ClinVar curators also apply.
- Structure and amino-acid properties are informative alone (0.78) but mostly redundant once ESM-2 and conservation are present.

## 5. Interpretability (SHAP)

Figures: `shap_beeswarm.png`, `shap_groups.png`, `shap_waterfall_*.png`.

- The top features are:
  1. gnomAD popmax AF
  2. gnomAD exome AF
  3. ESM-2 LLR
  4. protein length
  5. ESM-2 log p(alt)
  6. gnomAD genome AF
  7. phyloP-100
  8. AlphaFold contact density (burial)
- **Protein length:** long proteins push toward benign. This works as a gene-level proxy for
  proteins such as TTN and other large genes with many benign variants. It is a mild form of Grimm's type-2 circularity. We keep it
  because it is a legitimate biological feature, and report it as a known bias.
- **Example, TP53 p.Arg175His (deck example):** P = 0.993, **PP3_Strong**.
  - Drivers: absent from gnomAD, 1 residue from a UniProt functional site, buried (21 Cα contacts), ESM-2 LLR −9.1.
  - This variant was in the training data, so it demonstrates the explanation, not the prediction.

## 6. Calibration and evidence strength: the honest negative result

| Model D on time-travel test | Brier | ECE |
|---|---|---|
| Random split (in-distribution) | 0.030 | 0.015 |
| Gene-disjoint CV | 0.035 | 0.004 |
| Time-travel, train-era isotonic | 0.052 | 0.084 |
| Time-travel + EM label-shift correction (ours) | **0.044** | **0.065** |

- Probabilities are well calibrated within one ClinVar era (ECE 0.004–0.015) but **over-confident on later
  variants**, especially between 0.5 and 0.85 (`reliability_label_shift.png`).
- Part of the cause is a change in class balance: 38.6% pathogenic in the 2023 labels against 24.4% in later ones.
  - The Saerens EM correction uses no labels and recovers part of the gap.
  - It estimates the prior at 0.31 against the true 0.24, so some shift remains that class balance doesn't explain.

**PP3/BP4 thresholds for Model D** were learned on gene-disjoint out-of-fold scores from the 2023 era
(`pp3_bp4_modelD_*.csv`) and validated on the time-travel test:

| Level | Threshold | Share of test variants | Realised LR | Required | OK? |
|---|---|---|---|---|---|
| PP3 Strong | P ≥ 0.951 | 22.2% (86% of all pathogenic) | 59.3 | ≥ 33.5 | ✅ |
| PP3 Moderate | 0.836–0.951 | 3.1% | 3.7 | ≥ 5.79 | ❌ |
| PP3 Supporting | 0.667–0.836 | 1.9% | 1.3 | ≥ 2.41 | ❌ |
| BP4 Supporting / Moderate / Strong | ≤ 0.170 / 0.099 / 0.011 | 59.3% | 0.043 / 0.013 / 0.005 | ≤ 0.42 / 0.17 / 0.03 | ✅ |

**Conclusion:** use Model D's BP4 (all levels) and PP3_Strong evidence. Do not use its PP3 Supporting or
Moderate levels under time shift. REVEL's published thresholds pass every level, so better
calibration for mid-range scores is the main open problem.

## 7. Limitations

1. ClinVar labels are noisy, and curators use allele frequency themselves, so frequency features are partly circular. The rare-variant results address this.
2. gnomAD and dbNSFP annotations are current (2026), not frozen at 2023. Only labels are time-split.
3. Baselines were trained on data we can't fully exclude. AlphaMissense and REVEL may have seen some time-travel test variants.
4. 7% of variants don't match the canonical UniProt isoform. They get no ESM-2 or structure features (XGBoost handles the missing values).
5. The new-gene subset has only 405 pathogenic variants, so its AUROC differences are less stable.

## 8. Next steps (Weeks 2–4 of PLAN.md)

- Error analysis of the new-gene false positives, and of the over-confident mid-range on new variants.
- Try temperature or Platt calibration on a recent hold-out, or train on 2023 + 2024 with 2025–26 as test.
- Small hyper-parameter search with gene-grouped CV. Add monotone constraints (e.g. higher AF → more benign) for robustness.
- Mid-term deck: Table §2, `auroc_by_split.png`, `circularity.csv`, the SHAP plots, and a live `predict.py` demo.
