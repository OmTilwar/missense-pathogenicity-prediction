# Literature review: what we take from each paper, and what we replicate

PDFs/full text are in this folder (`index.json` lists DOI/PMID). AlphaMissense (Science 2023) and
REVEL (AJHG 2016) are not open access, so get them through the IIIT Nagpur library using the DOIs below.

| File | Paper | DOI |
|---|---|---|
| 01 | Richards et al. 2015, *Genet Med*: ACMG/AMP standards | 10.1038/gim.2015.30 |
| 02 | Grimm et al. 2015, *Hum Mutat*: two types of circularity | 10.1002/humu.22768 |
| — | Ioannidis et al. 2016, *AJHG*: REVEL | 10.1016/j.ajhg.2016.08.016 |
| 04 | Rentzsch et al. 2019, *NAR*: CADD v1.4 | 10.1093/nar/gky1016 |
| 05 | Pejaver et al. 2022, *AJHG*: calibration → PP3/BP4 | 10.1016/j.ajhg.2022.10.013 |
| — | Cheng et al. 2023, *Science*: AlphaMissense | 10.1126/science.adg7492 |
| 07 | Brandes et al. 2023, *Nat Genet*: ESM1b genome-wide | 10.1038/s41588-023-01465-0 |
| 08 | Lin et al. 2023, *Science*: ESM-2 / ESMFold (bioRxiv preprint) | 10.1126/science.ade2574 |
| 09 | Bergquist et al. 2025, *Genet Med*: more calibrated tools (text) | 10.1016/j.gim.2025.101402 |
| 10 | Livesey & Marsh 2023, *Mol Syst Biol*: DMS benchmark | 10.15252/msb.202211474 |
| 11 | Meier et al. 2021, *NeurIPS*: ESM-1v zero-shot (bioRxiv) | 10.1101/2021.07.09.450648 |
| 12 | Lundberg et al. 2020, *Nat Mach Intell*: TreeSHAP (text) | 10.1038/s42256-019-0138-9 |

## Key ideas and how the project uses them

**Richards 2015 (ACMG/AMP).** Variant classification combines 28 evidence criteria. Computational
predictions enter only as **PP3** (supporting pathogenic) and **BP4** (supporting benign).
→ Our tool reports a PP3/BP4 strength. It never reports a final classification.

**Grimm 2015 (circularity).** Benchmarks overstate performance in two ways:
- **Type 1:** the same or overlapping variants appear in a tool's training data and in the test set.
- **Type 2:** whole genes are mostly pathogenic or mostly benign, so a tool can score well by
  "recognising the gene" rather than the variant.

→ We handle type 1 with the time-travel split and type 2 with the gene-disjoint split.
→ **Replication (`results/tables/circularity.csv`):** tools trained on ClinVar (ClinPred, MetaRNN,
VARITY) should lose more AUROC than tools not trained on ClinVar when moving from variants already
in ClinVar to variants added later.

**REVEL (2016) and CADD (2019).** These are established meta-predictors. REVEL combines 13 tools
with a random forest. CADD trains on simulated versus evolutionarily fixed variants, so it is not
trained on clinical labels. → Baselines only.

**Pejaver 2022 and Bergquist 2025.** Calibration converts a score into evidence strength:
- The local posterior probability is computed in a sliding score window and rescaled to a prior of
  **0.0441**.
- Each threshold must meet an OddsPath of 2.406^k (Supporting, Moderate, Strong, Very strong).
- The published REVEL thresholds are:
  - PP3: ≥0.644 Supporting, ≥0.773 Moderate, ≥0.932 Strong.
  - BP4: ≤0.290 Supporting, ≤0.183 Moderate, ≤0.016 Strong.
- Bergquist 2025 extends this to AlphaMissense, ESM1b, VARITY and others.

→ **Replication (`07_pp3_bp4_thresholds.py`):** we recompute the REVEL thresholds on our data,
then derive thresholds for our own model and validate them on the time-travel test.

**AlphaMissense (2023).** It fine-tunes an AlphaFold-derived model using population frequency as a
weak label and does not train on ClinVar. It is the strongest modern baseline.
→ It is a baseline only, never a feature. Its scores are precomputed for all human missense variants.

**ESM1b (Brandes 2023), ESM-1v (Meier 2021) and ESM-2 (Lin 2023).** A protein language model's
log-likelihood ratio, log p(alt) − log p(ref), is a strong *zero-shot* pathogenicity signal.
- Brandes scored every possible missense variant with ESM1b.
- Long proteins were handled with sliding windows.

→ **Replication:** we compute the same wild-type-marginal LLR with **ESM-2 650M** on a local GPU
(`04_esm2_features.py`) and report it as the `ESM2_LLR` zero-shot method.
→ **Improvement:** we feed the LLR, the position entropy and embedding PCs into XGBoost (Model D).

**Livesey & Marsh 2023.** Deep mutational scanning data avoids circularity entirely. In their
benchmark, unsupervised methods such as EVE and ESM-1v rank near the top.
→ Future work: validate Model D on DMS data, for example from ProteinGym.

**Lundberg 2020 (TreeSHAP).** Gives exact Shapley values for tree ensembles in polynomial time.
→ Used for the global and per-variant explanations of Model D.

## Research gap restated (for the report)

None of the existing tools reports all of the following together:
1. A strict time-travel evaluation.
2. A gene-disjoint evaluation.
3. Calibrated probabilities.
4. Validated PP3/BP4 thresholds.
5. Per-variant explanations from *interpretable biological features*.

Our project covers all five in one open pipeline built from public data.
