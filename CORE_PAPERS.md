# The Two Papers Our Project Is Built On

Our title has two halves, and each comes from one paper:

| Part of our title | Paper | What it gives us |
|---|---|---|
| **"Leakage-Controlled** Machine Learning…" | **Grimm et al. 2015**, *Human Mutation* | The *problem*: why most accuracy numbers for variant predictors are inflated, and how to test honestly |
| "…with **Interpretable (calibrated) Evidence**" | **Pejaver et al. 2022**, *American Journal of Human Genetics* | The *output standard*: how to turn a score into clinically meaningful PP3/BP4 evidence |

In one sentence: **Grimm tells us how to evaluate honestly; Pejaver tells us what a useful output must look like.**

A third, method-level paper, Brandes et al. 2023 (ESM1b), supports our ESM-2 features. It is covered briefly at the end.

---

# Paper 1: Grimm et al. 2015

**"The Evaluation of Tools Used to Predict the Impact of Missense Variants Is Hindered by Two Types of Circularity."**
D. G. Grimm, C.-A. Azencott, …, D. G. MacArthur, …, K. M. Borgwardt.
*Human Mutation* 36(5):513–523, 2015. doi:10.1002/humu.22768. PDF: `papers/02_Grimm2015_circularity.pdf`.

## 1.1 The question they asked

Dozens of tools predict whether a missense variant is harmful: SIFT, PolyPhen-2, MutationTaster, CADD, FatHMM, and others.
Papers kept reporting very high accuracy, and different papers crowned different winners.
Grimm and colleagues asked: **which tool really generalises to new variants?** They found that the comparisons themselves were broken.

## 1.2 What they did

- **Tools tested (10):** MutationTaster-2, LRT, PolyPhen-2, SIFT, MutationAssessor, FatHMM-weighted, FatHMM-unweighted, CADD, phyloP and GERP++. They also tested two "meta-predictors" that combine tools: Condel and Logit.
- **Benchmarks (5):** HumVar, ExoVar, VariBench, predictSNP and SwissVar.
- **De-duplication:** they built "Selected" versions by **removing every variant that overlaps with other datasets or with the tools' training data**:
  - VariBench-Selected: 10,266 variants;
  - predictSNP-Selected: 16,098;
  - SwissVar-Selected: 12,729.
- **Control:** they built a deliberately "dumb" predictor, the **protein majority vote (MV)**. It labels a variant by the majority label of *other* variants in the same protein, and knows nothing about the variant itself.

## 1.3 The two types of circularity (the core idea)

| | Type 1 circularity | Type 2 circularity |
|---|---|---|
| **What it is** | The same variants appear in a tool's training data **and** in the benchmark used to test it | **Different** variants from the same protein appear in training and testing, and databases tend to label whole proteins as all-pathogenic or all-benign |
| **Why it inflates scores** | The tool has seen the answers: memorisation | The tool can predict from *which gene* the variant is in, not from the variant itself |
| **Analogy** | Exam questions leaked to students | Learning "every question about chapter 5 has answer B" |
| **Evidence in the paper** | Tools trained on HumVar or ExoVar (MutationTaster-2, PolyPhen-2, MutationAssessor) look excellent there, but drop on the "Selected" datasets. They overfit | In VariBench-Selected, **98% of proteins (4,425 / 4,490) are "pure"** (one class only). **94.8% of variants** sit in pure proteins (57.2% neutral-only, 37.6% pathogenic-only) |

**The striking finding about FatHMM-weighted:**
- It weights predictions by how many disease variants are known in the protein, which is a built-in gene prior.
- It looked like the best tool on four of the five datasets.
- On "**mixed**" proteins (containing both pathogenic and benign variants), it **performed poorly**.
- Its apparent success was type-2 circularity, not skill.
- The protein majority vote, which knows nothing about variants, also achieved excellent accuracy on pure proteins. That proves the benchmarks rewarded gene-memorisation.

On the clean VariBench-Selected set, accuracies were modest. For example, SIFT and Condel reached an **AUC of about 0.70**.

## 1.4 Their recommendations (directly from the Discussion)

1. Compare tools only on benchmarks that **do not overlap** any tool's training data.
2. Tools should **publish their training data**. Otherwise type-1 circularity cannot be excluded.
3. Report accuracy **as a function of the pathogenic-to-neutral ratio of the protein**: pure vs mixed proteins.
4. Better still, **split train and test by protein**, so that no protein appears on both sides.
5. Ideally, retrain all predictors on the same data from **raw descriptors** (features), so that methods are compared, not training sets.
6. Beware a future circularity: new database labels may themselves be assigned **using prediction tools** (PP3).

## 1.5 Limitations of the paper

| Limitation | Explanation |
|---|---|
| Diagnosis, not cure | They showed the problem but did not build a predictor that avoids it |
| Small benchmarks | About 10–16k variants per clean set, from older (pre-2014) databases |
| No time-based test | De-duplication removes known overlaps, but tools whose training data is private can still overlap; it does not simulate "predicting before the label existed" |
| Tools of their era | No modern methods such as protein language models, AlphaFold or REVEL |
| Ratio reporting only | They suggested protein-stratified training but did not run it at scale |

## 1.6 How our project uses and extends Grimm

| Grimm recommendation | What we did |
|---|---|
| No overlap between training and test (type 1) | **Time-travel split**: train on ClinVar Jan 2023, test only on the 124,139 variants labelled *afterwards*. Overlap is impossible by construction, even for private training sets |
| Split by protein (type 2) | **Gene-disjoint 5-fold cross-validation**: no gene appears in both train and test |
| Retrain on raw descriptors, publish data | We train only on **raw biological features** (110 numbers), never on other tools' scores. All code and data sources are public |
| Report pure vs mixed proteins | **Done (`src/10_pure_vs_mixed_genes.py`)**, results below |
| Beware tools used to label variants | We report ClinPred, MetaRNN and VARITY separately as "circular" and never use any tool score as a feature |

**Our replication 1: circularity is visible in 2026 data.** We scored the same tools on variants already in ClinVar 2023 vs variants labelled later:

| Tool | Trained on ClinVar? | AUROC on old variants | AUROC on new variants | Change |
|---|---|---|---|---|
| ClinPred | Yes | 0.987 | 0.980 | **−0.006** |
| MetaRNN | Yes | 0.989 | 0.985 | **−0.005** |
| REVEL | No | 0.958 | 0.975 | +0.017 |
| AlphaMissense | No | 0.948 | 0.966 | +0.018 |
| CADD | No | 0.898 | 0.939 | +0.041 |

Every honest tool improves on newer variants, which are easier on average. The ClinVar-trained tools get worse. The gap is the memorisation effect Grimm described.

**Our replication 2: Grimm's pure vs mixed analysis, done on our time-travel test.** Values are AUROC.

| Gene type (by % pathogenic among its labelled variants) | Variants | **Model D (ours)** | REVEL | AlphaMissense | CADD | MetaRNN* |
|---|---|---|---|---|---|---|
| Pure genes (all one class) | 53,156 | 0.995 | 0.993 | 0.988 | 0.984 | 0.997 |
| Mixed genes (any mix) | 70,983 | **0.979** | 0.955 | 0.941 | 0.887 | 0.970 |
| Mixed genes, 20–80% pathogenic | 25,448 | **0.969** | 0.925 | 0.940 | 0.876 | 0.961 |
| Mixed genes, 40–60% pathogenic | 7,807 | **0.974** | 0.933 | 0.947 | 0.891 | 0.966 |

\* MetaRNN is trained on ClinVar, so it is circular.

**This is our strongest evidence:**
- On pure genes every tool looks great (0.98–0.997), exactly as Grimm warned.
- On mixed genes, where the gene tells you nothing and the model must understand the *variant*, our model's lead grows. It is **+0.044 over REVEL** and **+0.029 over AlphaMissense** in the 20–80% bin.
- It even beats the circular MetaRNN.

## 1.7 Two-minute explanation (presentation script)

> "Grimm and colleagues showed in 2015 that published accuracies of variant predictors are inflated by
> two kinds of circularity.
>
> Type 1 is simple overlap: the test variants were in the tool's training data.
> Type 2 is subtler. Databases label whole genes as all-pathogenic or all-benign: in their clean benchmark,
> 98% of proteins had only one class. So a tool can score well just by recognising the gene. Their
> 'majority vote' baseline, which knows nothing about the variant, did very well. The tool that looked best,
> FatHMM-weighted, collapsed on genes with mixed labels.
>
> Their recommendations were to avoid overlap, split by protein, report pure vs mixed genes, and train on raw
> features. Our project implements all four:
> - a time-travel split for type 1;
> - a gene-disjoint split for type 2;
> - only raw biological features;
> - a pure-versus-mixed analysis, where our model's advantage is largest: 0.969 vs 0.925 for REVEL
>   on genes with 20–80% pathogenic variants."

## 1.8 Likely viva questions

- **What is the difference between type 1 and type 2 circularity?**
  - Type 1: the same variants appear in train and test.
  - Type 2: same-gene variants appear in train and test, and genes are label-homogeneous.
- **Why can't you just remove duplicate variants?** That fixes type 1 only. Type 2 needs gene-level separation (our gene-disjoint split) or reporting on mixed genes.
- **Does our dataset have the same problem?**
  - Yes. 77% of our 15,264 genes contain only benign variants, and 35% of variants sit in single-class genes.
  - That is why we never use the gene name as a feature and why we report mixed-gene results.
- **Is any of our features a gene proxy?**
  - Protein length partly is: SHAP shows long proteins pushed toward benign.
  - We disclose this. Our mixed-gene results show the model still works when the gene is uninformative.

---

# Paper 2: Pejaver et al. 2022

**"Calibration of computational tools for missense variant pathogenicity classification and ClinGen recommendations for PP3/BP4 criteria."**
V. Pejaver, …, S. V. Tavtigian, M. S. Greenblatt, L. G. Biesecker, P. Radivojac, S. E. Brenner, and the ClinGen Sequence Variant Interpretation Working Group.
*American Journal of Human Genetics* 109:2163–2177, 2022. doi:10.1016/j.ajhg.2022.10.013. PDF: `papers/05_Pejaver2022_calibration.pdf`.

## 2.1 The question they asked

The ACMG/AMP guidelines (Richards 2015) allow computational predictions only as "**supporting**" evidence (PP3 for pathogenic, BP4 for benign).
- The thresholds were whatever each tool's developers suggested, for example "CADD > 20 means damaging".
- Labs often required several tools to agree.
- **Neither practice had any quantitative justification.**

Pejaver and colleagues asked:
1. What score from a given tool actually provides supporting, moderate, strong or very strong evidence?
2. Can a computational tool ever deserve more than "supporting"?

## 2.2 Background: the Bayesian ACMG framework (Tavtigian 2018)

ACMG evidence levels can be expressed as **likelihood ratios (LR)**: how much more likely the evidence is in pathogenic than in benign variants.

With a prior probability of pathogenicity of **4.41%**, the levels need:

| Evidence strength | Required LR (PP3) | Posterior probability |
|---|---|---|
| Supporting | 2.406 | 0.100 |
| Moderate | 5.790 (= 2.406²) | 0.211 |
| Strong | 33.53 (= 2.406⁴) | 0.607 |
| Very strong | 1,124 (= 2.406⁸) | 0.981 |

For BP4 the same values apply in reverse (LR ≤ 1/2.406, and so on).

## 2.3 What they did

**Data (built carefully to avoid circularity):**

| Data set | Contents |
|---|---|
| **ClinVar 2019 set** (calibration) | Missense variants: P/LP vs B/LB, ≥ 1 star, gnomAD AF < 1%, in genes with at least one pathogenic variant. Variants in the training sets of the tools were removed. **11,834 variants, 1,914 genes** |
| **ClinVar 2020 set** (validation) | Variants **new in ClinVar after Dec 2019**, same filters. **9,114 variants, 2,197 genes** |
| **gnomAD set** | Rare gnomAD variants, used to estimate the prior. **Prior = 4.41%** |

**Tools calibrated (13):** BayesDel, CADD, EA, FATHMM, GERP++, MPC, MutPred2, phyloP, PolyPhen-2, PrimateAI, REVEL, SIFT, VEST4.

**Method: local posterior probability.**
- For each score value *s*, take the variants whose scores fall in a narrow window around *s*.
- In that window, estimate the local likelihood ratio lr⁺(s) = p(s | pathogenic) / p(s | benign), adjusted to the 4.41% prior.
- **Bootstrap 10,000 times.** Use the one-sided 95% lower bound, so the estimate is conservative.
- **The threshold for "supporting"** is the smallest score *t* such that every score ≥ *t* has a lower-bound LR ≥ 2.406. The other levels work the same way, and benign thresholds mirror it.
- Each tool's score range is cut into up to 9 intervals: 4 pathogenic, 4 benign, and "indeterminate" in the middle.

## 2.4 Key findings

1. **Most tools reached "supporting" for both PP3 and BP4.** Several reached **moderate**, some reached **strong**, and one reached very strong for benign. Computational evidence can be worth more than ACMG allowed.
2. **Recommended tools:** BayesDel, MutPred2, REVEL and VEST4. Each reached strong for pathogenic and moderate for benign.
3. **REVEL thresholds**, now widely used in clinics:
   - PP3: supporting ≥ 0.644, moderate ≥ 0.773, strong ≥ 0.932.
   - BP4: supporting ≤ 0.290, moderate ≤ 0.183, strong ≤ 0.016, very strong ≤ 0.003.
4. **Developer thresholds were wrong.**
   - SIFT, PolyPhen-2 and CADD at their default cut-offs did *not* reach supporting evidence.
   - CADD's popular "> 20 = damaging" threshold actually fell in the **benign moderate** interval.
   - At default thresholds the tools called 50% (SIFT), 29% (PolyPhen-2) and 65% (CADD) of rare population variants "damaging", far above the 4.41% expected.
5. **Validation:** on the newer ClinVar 2020 set, the intervals held. Tools reaching strong exceeded the required LR, and all benign intervals passed. (phyloP at moderate was marginally below.)
6. **Practice rule:** labs should pick **one** tool *before* seeing results, not scan several tools for the strongest answer.

## 2.5 Limitations of the paper

| Limitation | Explanation |
|---|---|
| Calibrates tools, does not build one | Every tool keeps its own biases (training data, circularity); calibration only translates scores |
| Small data sets | 11,834 calibration and 9,114 validation variants, so the upper evidence levels rest on few variants |
| Data filtering shapes the result | They kept only genes with ≥ 1 pathogenic variant and AF < 1%. Thresholds may shift on other gene sets |
| One prior for all genes | 4.41% applies genome-wide, but the real prior varies a lot between genes |
| Tools' training data not always public | Overlap removal was only possible where training sets were published (Grimm's problem again) |
| Score-only | Thresholds say nothing about *why* a variant scores high (no interpretability) |
| Short validation horizon | Validation used one year of new ClinVar data (2019 → 2020) |

## 2.6 How our project uses and extends Pejaver

| Pejaver element | What we did |
|---|---|
| Bayesian evidence scale (prior 0.0441, LR 2.406^k) | Same scale, implemented in `src/07_pp3_bp4_thresholds.py` |
| Local posterior + bootstrap thresholds | Same approach (simplified window, 200 bootstraps, one-sided 95% bounds) |
| Calibrate existing tools | **Replication:** we recomputed REVEL's thresholds on our data |
| Validate on newer variants | Validated on **124,139** variants labelled after Jan 2023 (14× their 9,114), across *all* genes |
| (not in paper) build a new tool | We built our own model, calibrated it with isotonic regression, derived **its own PP3/BP4 thresholds** from gene-disjoint out-of-fold scores, and validated them on future variants |
| (not in paper) explanation | Each prediction carries a SHAP explanation alongside its evidence level |

**Our replication: REVEL thresholds**

| Level | Published (Pejaver) | Ours (ClinVar 2023, rare variants) |
|---|---|---|
| PP3 supporting / moderate / strong | 0.644 / 0.773 / 0.932 | 0.732 / 0.854 / 0.982 |
| BP4 supporting / moderate / strong | 0.290 / 0.183 / 0.016 | 0.406 / 0.271 / 0.081 |

- **Same structure, stricter pathogenic cut-offs.** The differences come from:
  - different data (we did not restrict to genes with a pathogenic variant, and we did not remove REVEL's training variants);
  - a newer ClinVar era;
  - our simplified window.
- **Importantly:** Pejaver's published REVEL thresholds **still pass every level** on our 2023→2026 time-travel data. That independently confirms their calibration four years later.

**Our model's evidence levels on future variants:**

| Level | Realised LR | Required | Passes? |
|---|---|---|---|
| PP3 Strong (P ≥ 0.951) | 59.3 | ≥ 33.5 | Yes |
| PP3 Moderate | 3.7 | ≥ 5.79 | **No** |
| PP3 Supporting | 1.3 | ≥ 2.41 | **No** |
| BP4 Supporting / Moderate / Strong | 0.043 / 0.013 / 0.005 | ≤ 0.42 / 0.17 / 0.03 | Yes |

This is honest reporting in Pejaver's spirit. Our strong and benign levels are trustworthy. Our mid-range pathogenic levels are not yet, because probabilities drift when ClinVar's class balance shifts over time. Fixing that is our next task.

## 2.7 Two-minute explanation (presentation script)

> "Clinical guidelines let computer predictions count only as 'supporting' evidence, and labs used each
> tool's own cut-offs with no proof they meant anything.
>
> Pejaver and colleagues, for ClinGen, fixed this with a Bayesian approach:
> - Each evidence level corresponds to a likelihood ratio: 2.4 for supporting, 5.8 for moderate,
>   33.5 for strong, given a 4.4% prior.
> - They estimated, in a sliding window over each tool's score, how much more common pathogenic variants
>   are than benign ones, with bootstrap confidence bounds.
> - That gives score thresholds for each level.
>
> They found good tools like REVEL reach *strong* evidence, while popular defaults such as CADD > 20 did not
> even reach supporting. Their REVEL thresholds are now standard.
>
> We use their framework in two ways:
> 1. We replicated it for REVEL. The published thresholds still hold on our 2026 data.
> 2. We applied it to our own model and validated it on 124,000 future variants. Strong pathogenic and all
>    benign levels pass. The weaker pathogenic levels do not yet, which is our main improvement target."

## 2.8 Likely viva questions

- **Why a likelihood ratio and not just accuracy?** An LR says how much a score should change a clinician's belief, and it combines with other ACMG evidence through Bayes' rule. Accuracy cannot do that.
- **Where does 4.41% come from?** Their estimate of the fraction of rare missense variants in the population that are pathogenic, from the gnomAD reference set.
- **Why a one-sided lower bound?** To be conservative: a threshold is only accepted if even the pessimistic estimate meets the required LR.
- **Why do your REVEL thresholds differ?** Different data filtering, a newer ClinVar era, and a simplified window. The structure matches, and the published thresholds validate on our data.
- **Why do your PP3 Moderate and Supporting fail?**
  - Our probabilities are over-confident on variants labelled after training.
  - Part of the cause is that ClinVar's pathogenic share fell from 38.6% to 24.4%.
  - Label-shift correction recovers part of the gap; recalibrating on recent data is planned.

---

# Supporting paper: Brandes et al. 2023 (the method behind our ESM-2 features)

**"Genome-wide prediction of disease variant effects with a deep protein language model."** *Nature Genetics* 55:1512–1522. PDF: `papers/07_Brandes2023_ESM1b.pdf`.

| Topic | Summary |
|---|---|
| **What they did** | Scored all possible missense variants in the human proteome with ESM1b. The score is the log-likelihood ratio log p(alt) − log p(ref) from one pass over the wild-type sequence, with sliding windows for long proteins. A strong predictor, without any labels |
| **Limitations** | Unsupervised: it ignores population frequency, DNA conservation and 3-D structure. It gives a threshold rather than a calibrated probability |
| **What we took** | The exact scoring recipe, applied with ESM-2 650M |
| **Our replication** | ESM-2 LLR alone reaches AUROC 0.906 on ClinVar 2026 |
| **How we extend it** | We combine it with biological features in XGBoost. ESM-2 features in a supervised model reach 0.946; the full model reaches 0.987 |

---

# Summary

| | Grimm 2015 | Pejaver 2022 |
|---|---|---|
| Problem | Accuracy claims are inflated by circularity | Computational evidence had no quantitative calibration |
| Key idea | Type 1 (overlap) and type 2 (gene-level) circularity | Bayesian LR thresholds via local posterior probability |
| Key number | 98% of proteins in a clean benchmark are single-class | Prior 4.41%; LR 2.406 / 5.79 / 33.5 / 1,124 |
| Limitation | Diagnosed but did not fix; no time-based test | Calibrates tools, builds none; small data; one prior |
| **Our use** | Time-travel + gene-disjoint tests; raw features only; pure vs mixed analysis | Same evidence scale; REVEL replication; our own thresholds validated on future data |
| **Our result** | Circularity reproduced; our lead is largest on mixed genes (0.969 vs 0.925 REVEL) | Published REVEL thresholds hold in 2026; our Strong and BP4 levels pass, Moderate and Supporting do not yet |
