# Leakage-Controlled ML for Predicting Pathogenic Missense Variants — Execution Plan

Team: Piyush Gupta · Om Tilwar · Varun Tripathi — Guide: Dr. Nikhil Dhengre (ECE, IIIT Nagpur)

This plan turns the proposal deck into a reproducible pipeline. Every step is a script in `src/`
that reads from `data/` and writes to `data/` or `results/`.

---

## Phase 0 — Literature (`papers/`)

| # | Paper | What we take from it | Role in project |
|---|-------|----------------------|-----------------|
| 1 | Richards 2015 (ACMG/AMP) | PP3/BP4 = computational evidence | Framing; final output maps to PP3/BP4 |
| 2 | Grimm 2015 | Type-1 (variant overlap) & type-2 (gene-level) circularity | **Replicate**: random vs gene-disjoint gap |
| 3 | Ioannidis 2016 (REVEL) | Ensemble of 13 tools, rare missense | Baseline |
| 4 | Rentzsch 2019 (CADD) | Genome-wide deleteriousness | Baseline |
| 5 | Pejaver 2022 | Local-posterior calibration → PP3/BP4 thresholds | **Replicate** thresholds for REVEL; apply to our model |
| 6 | Cheng 2023 (AlphaMissense) | Strong modern baseline (not trained on ClinVar) | Baseline |
| 7 | Brandes 2023 (ESM1b) | PLM log-likelihood ratio ≈ pathogenicity | **Replicate** zero-shot LLR with ESM-2 |
| 8 | Lin 2023 (ESM-2) | The PLM we run locally | Feature extractor |
| 9 | Bergquist 2025 | Calibration of more tools | Extends #5 |
| 10 | Livesey & Marsh 2023 | DMS-based benchmarking avoids circularity | Discussion / future work |
| 11 | Meier 2021 (ESM-1v) | Wild-type / masked-marginal scoring | ESM scoring method |
| 12 | Lundberg 2020 (TreeSHAP) | Exact SHAP for trees | Interpretability |

## Phase 1 — Dataset

**Labels — ClinVar (GRCh38, `variant_summary`):**
- Releases: **2023-01** (train era) and **2026-09** (latest).
- Keep: single-nucleotide variants whose HGVS protein change is missense (`p.Xxx123Yyy`, Yyy ≠ Ter/=).
- Label 1 = Pathogenic / Likely pathogenic / Pathogenic/Likely pathogenic.
- Label 0 = Benign / Likely benign / Benign/Likely benign.
- Drop VUS, conflicting, and other classes.
- Review status ≥ 1 star ("criteria provided").
- ClinVar is the **target only**, never a feature.

**Features (no ClinVar-trained scores enter the model):**

| Group | Features | Source |
|-------|----------|--------|
| Population frequency | gnomAD exome/genome AF (log10), max AF across ancestries, homozygote count, absent-flag | MyVariant.info (gnomAD) |
| Conservation | phyloP (17/100/470-way), phastCons, GERP++, SiPhy, B-statistic | dbNSFP via MyVariant.info |
| Protein context | relative position, protein length, UniProt domain / active / binding site / TM / disulfide / signal / motif / helix / strand flags, InterPro domain flag | UniProt REST, dbNSFP |
| Structure (improvement) | AlphaFold pLDDT at residue, local contact density (burial proxy) | AlphaFold DB |
| Amino-acid properties | Grantham, BLOSUM62, Δhydrophobicity, Δvolume, Δcharge, polarity change, Pro/Gly/Cys flags | Computed |
| ESM-2 (advanced) | Zero-shot LLR (log p(alt) − log p(ref)), position entropy, wt-probability, PCA of residue embedding | ESM-2 650M, run locally on GPU |

**Baselines (comparison only, never features):** CADD, REVEL, AlphaMissense, ESM1b.
We also report ClinPred and MetaRNN, which were trained on ClinVar. They are flagged as
*circular* to demonstrate the leakage problem.

## Phase 2 — Three levels of honest testing
1. **Random 80/20** (stratified) — optimistic reference.
2. **Gene-disjoint** — 5-fold GroupKFold by gene. This is the scalable form of
   leave-one-gene-out: no test gene is ever seen in training.
3. **Time-travel (primary)** — train on the 2023-01 labels and test on variants that first
   received a P/LP/B/LB label after 2023-01 (present in 2026-09).
   - Sub-reports: test variants in genes unseen in 2023 (temporal + gene-disjoint), and
     **rare variants** (gnomAD AF < 1e-4). The rare-variant subset removes the BA1/BS1
     frequency shortcut.

## Phase 3 — Experiments (as in deck)
- **A** Existing tools (scores evaluated directly).
- **B** Logistic regression on biological features.
- **C** XGBoost on the same features.
- **D** XGBoost + ESM-2.
- **Calibration:** isotonic regression fit on a held-out slice of the training era.
- **Metrics:** AUROC, AUPRC, Brier, ECE (15 bins), 1000× bootstrap 95% CI.
- **Ablation:** drop one feature group at a time (Model D, time split).
- **SHAP:** global beeswarm + local explanation (e.g. TP53 p.Arg175His).

## Phase 4 — Improvements over the proposal ("improvise")
1. ESM-2 *zero-shot* LLR + entropy features, not just raw embeddings (from Brandes 2023 / Meier 2021).
2. AlphaFold structural context (pLDDT, burial).
3. Explicit circularity demonstration with ClinVar-trained tools (Grimm 2015 replication).
4. ClinGen-style **PP3/BP4 evidence-strength thresholds** for our model via local-posterior
   calibration (Pejaver 2022 replication, prior = 0.0441).
5. Rare-variant evaluation to neutralise the allele-frequency shortcut.

## Phase 5 — Deliverables
- `results/tables/*.csv` — all metrics with CIs.
- `results/figures/*.png` — ROC/PR, reliability, ablation, SHAP.
- `results/REPORT.md` — findings write-up for the mid-term / final presentation.
- `src/predict.py` — CLI: variant → calibrated probability + SHAP top features + PP3/BP4 strength.

## Timeline: 8 weeks (starting 5 Oct 2026, ending 29 Nov 2026)

| Week | Dates | Work | Output | Owner |
|------|-------|------|--------|-------|
| 1 | 5–11 Oct | Pipeline finished on 5 Oct ✅ · **Mid-term presentation on 7 Oct** (proposal + results slides + live demo) | Mid-term deck | All |
| 2 | 12–18 Oct | Each member reads the code and results end-to-end and reruns one step | Everyone can explain every script | Split: Piyush = data (01–03), Om = features/ESM (04–05), Varun = models/eval (06–07) |
| 3 | 19–25 Oct | Error analysis: worst genes, false positives/negatives, rare vs common, reclassified variants; small XGBoost hyper-parameter search with gene-grouped CV | Error-analysis section, tuned model | Om + Varun |
| 4 | 26 Oct–1 Nov | Fix mid-range calibration (train 2023–24, calibrate 2025, test 2026); act on mid-term feedback | Improved calibration | Varun |
| 5 | 2–8 Nov | Guide feedback. Optional extras only if weeks 1–4 are on track: simple web demo (Streamlit/Gradio) **or** ProteinGym DMS validation. The LLM evidence module (slide 10) is **dropped** for time | Demo or extra validation | Piyush |
| 6 | 9–15 Nov | Final report draft: Introduction, Literature, Data, Method | Chapters 1–4 | Split by chapter |
| 7 | 16–22 Nov | Final report: Results, Discussion, Limitations, Conclusion; final figures | Complete report | All |
| 8 | 23–29 Nov | Buffer, viva preparation, mock viva with likely questions, final submission | Submission + viva | All |

**Scope rule:** after Week 4, no new features. Only analysis, writing and fixes.
**Milestones:** mid-term 7 Oct, improvements frozen 8 Nov, report complete 22 Nov, submission 29 Nov.

*Research use only — not a clinical diagnostic.*
