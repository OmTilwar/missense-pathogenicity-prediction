# Mid-term Presentation Script and Explainer

**Deck:** `Midterm_Presentation_FINAL_10_slides.pptx` (now 12 slides, about 15–18 minutes; consider renaming the file to `..._FINAL_12_slides.pptx`)
**Presenters:** Piyush (slides 1–6) · Om (slides 7–12). This split supersedes the presenter tags in the slide notes.

This guide assumes you know nothing about the project. Read it in order:

| Part | What it gives you |
|---|---|
| A | The 10-minute crash course: the minimum biology and ML you need |
| B | Slide by slide (12 slides): what is on the slide, what to say, and what it means underneath |
| C | Questions the panel may ask, with answers |
| D | One-page cheat sheet of every number on the slides |

Even if you present only your half, **read all of it**. Questions can come to either of you.

---

# Part A: Crash course (read this first)

## A1. The biology in five minutes

**DNA → protein.**
- DNA is a long string of 4 letters (A, C, G, T). It works like source code.
- A **gene** is a section of DNA that holds the recipe for one **protein**.
- The cell reads the gene three letters at a time. Each 3-letter group (a **codon**) means one **amino acid**. There are 20 kinds of amino acid, each written as one letter: R = Arginine, H = Histidine, and so on.
- A protein is a chain of amino acids. The chain folds into a 3-D shape, and that shape lets it do its job.

**A variant** is a spot where a person's DNA differs from the standard human reference.
A **missense variant** changes one DNA letter, so one amino acid in the protein changes.

**Our example is TP53 R175H.**
- **TP53** is a gene that protects cells from becoming cancerous.
- **R175H** means: at amino-acid position **175**, **R** (Arginine) became **H** (Histidine).
- In DNA terms, codon 175 changed from **CGC** to **CAC** (one G became an A).
- It is the most common TP53 mutation in cancer and causes Li-Fraumeni syndrome (inherited cancer risk).

**Pathogenic vs benign.** Labs classify each variant:
- **Pathogenic**: causes disease.
- **Benign**: harmless.
- **VUS** (variant of uncertain significance): not enough evidence yet. Most rare variants end up here.

Our model's job is to predict pathogenic vs benign from biological evidence, to help resolve VUS cases.

**ACMG guidelines, PP3 and BP4.** Clinical labs follow the ACMG guidelines, which have 28 kinds of evidence.
- A computer prediction counts as just one kind: **PP3** (supports pathogenic) or **BP4** (supports benign).
- Each can be "supporting", "moderate" or "strong" evidence.
- Our output maps onto exactly this scale.

## A2. The data sources (where the numbers come from)

| Source | What it is | What we take |
|---|---|---|
| **ClinVar** | Public database where labs post their classification of variants | **Only the answer (label)**: pathogenic = 1, benign = 0. Never an input |
| **gnomAD** | DNA from hundreds of thousands of people | How common the variant is. Common variants are almost never disease-causing |
| **dbNSFP** | Precomputed scores for every possible variant | **Conservation**: has this DNA position stayed the same across species? If evolution protected it, changing it is risky |
| **UniProt** | Database of proteins | Where functional parts of the protein are (binding sites, helices, domains) |
| **AlphaFold** | DeepMind's predicted 3-D shapes of proteins | Is the changed residue buried inside the protein (risky) or on a floppy surface (usually fine)? |
| **ESM-2** | A "language model" for proteins (like ChatGPT, but trained on protein sequences) | How "natural" the new amino acid looks at that position |

## A3. The ML in five minutes

- **Task:** binary classification. Input = 110 numbers describing a variant. Output = probability that it is pathogenic.
- **Models we compare:**
  - **B**: logistic regression (simple baseline).
  - **C**: XGBoost (gradient-boosted decision trees).
  - **D**: XGBoost + ESM-2 features. **This is our final model.**
- **XGBoost:** 700 small decision trees. Each tree fixes the mistakes of the previous ones. It is good at tables of numbers with missing values.
- **Calibration:** we make the probability honest. "0.8" should mean that about 80% of such variants really are pathogenic. We use **isotonic regression** fitted on held-out genes.
- **SHAP:** explains each prediction. For every feature it gives how much that feature pushed the score up (+) or down (−).
- **AUROC:** the main metric.
  - Take one random pathogenic and one random benign variant; AUROC is the chance the model scores the pathogenic one higher.
  - 0.5 = coin flip, 1.0 = perfect.
- **ECE (calibration error):** how far predicted probabilities are from reality. Lower is better.

## A4. The single most important idea of the project

Normally in ML you shuffle the data and split it 80/20 into train and test. **For this data that gives a misleadingly high score**, because the databases contain shortcuts:

1. **Labels are reused.** Several popular tools were *trained on ClinVar*, so testing them on ClinVar is like testing students on the exact questions they practised.
2. **Genes carry the label.** In our data **77% of genes contain only benign variants**. A model can learn "variants in gene X are benign" without understanding the variant. With a random split, other variants from the same gene sit on both sides of the split.
3. **Labels drift over time.** In 2023, 38.6% of labels were pathogenic. Among labels added later, it is only 24.4%. A model tuned on the past can be over-confident about the future.

Grimm et al. (2015) named shortcuts 1 and 2 **"circularity"**. So instead of a random split, we test like a real deployment:

- **Prospective test (main result):** freeze knowledge at **January 2023** and train only on that. Then test on the **124,139 variants experts classified after that date**. This is the honest question: *would our model have predicted what experts later decided?*
- **Gene-held-out test:** whole genes are kept out of training.
- **Mixed-gene test:** score only genes that contain both pathogenic and benign variants, so knowing the gene gives no hint.
- **Calibration check:** are the probabilities trustworthy as clinical evidence?

**Old name vs new name.** The proposal called this "leakage-controlled". We renamed it **"prospective, circularity-aware evaluation"**, because every ML project avoids leakage. Our point is that here the leakage is *inside the data*, so we changed what the test set represents.

## A5. Isotonic calibration (what "calibrated" means)

- **The problem:** XGBoost's output is a good *ranking* score, but not automatically an honest probability. Among variants it scores 0.80, perhaps only 60% are really pathogenic.
- **Calibrated** means that among variants given probability *p*, about *p* × 100% really are pathogenic.
- **How isotonic regression works:**
  1. Hold out 15% of the training data, **chosen by gene**, so these genes are never used to build the trees.
  2. Run the model on them and sort by raw score.
  3. Fit a **staircase that only goes up** ("isotonic" = monotone), mapping each raw-score range to the real fraction pathogenic in that range. Example: raw 0.5–0.9 → 55% actually pathogenic → output 0.55.
  4. Every future prediction passes through this staircase. R175H: raw 0.984 → calibrated 0.985.
- **It never changes the ranking**, so AUROC is unchanged. It only fixes the probability values.
- **Why not Platt scaling (a sigmoid)?** Isotonic assumes no curve shape, and we have plenty of calibration data.
- **Results:**
  - Calibration error (ECE) is 0.004–0.015 within one ClinVar era.
  - It rises to 0.084 on future variants, because the pathogenic share fell from 38.6% to 24.4%.
  - Our label-shift correction brings it to 0.065.

## A6. PP3 and BP4 (the clinical evidence codes)

**The ACMG/AMP guidelines** (Richards 2015) classify variants by collecting **28 types of evidence**.
- **First letter:** P = pathogenic direction, B = benign direction.
- **Strength:**
  - Pathogenic: VS very strong, S strong, M moderate, P supporting.
  - Benign: A stand-alone, S strong, P supporting.
- **Examples:**
  - PS3: a lab experiment shows damage (strong).
  - PM2: absent from population databases (moderate).
- **Combining:** fixed rules turn codes into a class. For example, one strong code plus two moderate codes can give "Likely pathogenic".

**The two codes for computer predictions:**
- **PP3:** computational evidence supports pathogenic.
- **BP4:** computational evidence supports benign.

In 2015 they were allowed only at the weakest level, supporting, with arbitrary tool cut-offs.

**Pejaver 2022 (ClinGen) made strength measurable** with the likelihood ratio (LR): how much more common a score range is among pathogenic variants than among benign ones. With a baseline (prior) of 4.41%:

| Level | PP3 needs LR ≥ | BP4 needs LR ≤ |
|---|---|---|
| Supporting | 2.41 | 0.42 |
| Moderate | 5.79 | 0.17 |
| Strong | 33.5 | 0.03 |
| Very strong | 1,124 | 0.0009 |

**What we did:**
1. Derived probability cut-offs for our model with Pejaver's method. For example, P ≥ 0.951 means PP3 Strong.
2. Checked the real LR on the 124,139 future variants:
   - PP3 Strong: 59.3, **passes**.
   - PP3 Moderate: 3.7, **fails**.
   - PP3 Supporting: 1.3, **fails**.
   - All BP4 levels **pass** (0.043 / 0.013 / 0.005).

So a lab can trust our PP3 Strong (as for R175H) and our BP4 levels, but not yet the mid-range PP3 levels.

**Our model gives one code, not a diagnosis.** A lab combines our PP3/BP4 with its other evidence.

---

# Part B: Slide by slide

Timing guide: about 1.25–1.5 minutes per slide (15–18 minutes total). Slides 5, 6, 9 and 11 can take 2 minutes; the title and Problem slides can be quick.

---

## Slide 1: Title (Piyush)

**On the slide:** title "Predicting Pathogenic Missense Variants Before the Experts Do". Subtitle "Prospective, circularity-aware evaluation with calibrated and explainable evidence". Team names, guide, IIIT Nagpur logo.

**Say:**
> "Good morning. We are Piyush Gupta, Om Tilwar and Varun Tripathi, guided by Dr. Nikhil Dhengre.
>
> Our project predicts whether a single-letter change in a human gene causes disease. The key word in our title is *before*: we test our model on variants that experts classified only *after* our training data was frozen, so we measure whether it can genuinely predict the future.
>
> Today we will follow one real mutation, TP53 R175H, through the whole pipeline, and then show our results."

**Understand:**
- "Calibrated": the probabilities are honest.
- "Explainable": every prediction comes with the reasons behind it (SHAP).

---

## Slide 2: The problem, most rare variants have no clear answer (Piyush)

**On the slide:**
- Three cards:
  - **Pathogenic**: 61,611 missense variants (P/LP) in ClinVar.
  - **VUS**: uncertain significance; helping resolve these is the model's purpose.
  - **Benign**: 140,404 missense variants (B/LB).
- Bottom box: what we deliver.

**Say:**
> "When a patient's DNA is sequenced, labs find thousands of variants and must classify each one. Pathogenic means there is evidence it causes disease; benign means evidence it is harmless. Many rare variants end up as VUS, variants of uncertain significance, because there isn't enough evidence yet.
>
> Computer predictions are one accepted line of evidence. In the clinical guidelines they are called PP3 when they support pathogenic and BP4 when they support benign.
>
> What we deliver for each missense variant is three things: a calibrated probability that it is pathogenic, the biological reasons behind it, and the matching PP3 or BP4 evidence level. We train only on pathogenic versus benign, because VUS means 'not known yet', not a third biological class."

**Understand:** see A5 and A6 in Part A for calibration and PP3/BP4.

---

## Slide 3: Our running example, TP53 R175H (Piyush)

**On the slide:**
- Left: bullet facts about TP53.
- Right top: DNA codon **C G C → C A C** (the changed letter is highlighted).
- Right middle: protein chain residues 171–179, **R → H** at position 175.
- Bottom left: the key question box.

**Say:**
> "Our guide asked us to explain the pipeline around one example, so we chose the most famous disease mutation, TP53 R175H.
>
> TP53 is called the guardian of the genome: it stops damaged cells from becoming cancer. On chromosome 17, one DNA letter changes, G to A in codon 175. CGC codes for arginine, CAC codes for histidine. So in the protein, position 175 changes from R to H. One amino acid out of 393, yet the protein can no longer bind DNA. This is the most frequent TP53 mutation in cancer.
>
> For every such change the question is the same: does it break the protein, pathogenic, or is it harmless, benign? Our model has to answer that from evidence alone. We will carry this exact variant through every step."

**Understand:**
- Notation: `p.Arg175His` = protein change; `c.524G>A` = DNA change; `chr17:7,675,088` = genome position.
- Why the slide shows **C→T** at the genome position but **G→A** in the codon: TP53 is read from the opposite DNA strand. G on one strand pairs with C on the other.

---

## Slide 4: Literature, two core papers and the gap (Piyush)

**On the slide:**
- A table of six studies with columns: Study / What it showed or built / Limitation we address.
- The two core papers are highlighted in purple.
- A "Gap" box at the bottom.

**Say:**
> "Two papers define our project.
>
> Grimm and colleagues in 2015 tested popular predictors and showed their accuracy was inflated by circularity: the same variants, or variants from the same genes, in both training and testing. But they only diagnosed the problem; they did not build a predictor or test over time. That is our evaluation design.
>
> Pejaver and colleagues in 2022, for ClinGen, showed how to turn a tool's score into clinical evidence strength using likelihood ratios. They produced the official REVEL thresholds. But they only calibrated existing tools, on about 12,000 variants. We apply their method to our own model and validate it on 124,000 future variants.
>
> The other four are our baselines.
> - REVEL combines 13 other tools' scores, so it is hard to interpret and inherits their circularity.
> - AlphaMissense from DeepMind is strong but a black box.
> - ESM1b is a protein language model that ignores population and conservation data.
> - CADD is trained on proxy labels, not clinical ones.
>
> The gap: no open model combines prospective, circularity-aware testing with calibrated, validated evidence levels and biological explanations."

**Understand (row by row):**

| Paper | Key fact | Limitation | Our answer |
|---|---|---|---|
| Grimm 2015 | 10 tools, 5 benchmarks; in a clean benchmark 98% of proteins had one label class; FatHMM-W looked best only because of gene-level labels | No predictor, no time-based test | Prospective + gene-held-out + mixed-gene tests |
| Pejaver 2022 | Prior 4.41%; LR thresholds 2.41 / 5.79 / 33.5 / 1,124; REVEL PP3 ≥ 0.644 / 0.773 / 0.932 | Only existing tools; 11,834 calibration + 9,114 validation variants | Same method on our model, validated on 124,139 future variants |
| REVEL 2016 | Random forest over 13 tools' scores | Score of scores; inherits circularity | Raw biological features only (our AUROC 0.987 vs REVEL 0.975) |
| AlphaMissense 2023 | AlphaFold-based, trained without ClinVar labels | No per-feature explanation | SHAP reasons for every prediction (0.987 vs 0.966) |
| ESM1b 2023 | Zero-shot protein language model | Sequence only | Combined with population, conservation, structure (0.916 → 0.987) |
| CADD 2019 | Trained on simulated vs. naturally surviving variants | Weaker on clinical labels | Clinical labels + honest testing (0.987 vs 0.939) |

---

## Slide 5: Why a random 80/20 split is not enough (Piyush)

**This is the slide that answers "isn't leakage control just a normal train/test split?". Know it well.**

**On the slide:** three cards with big numbers, plus a bottom line.
1. **Labels are reused: "3 of 8"** popular predictors we compare against were trained on ClinVar itself.
2. **Genes carry the label: "77%"** of our 15,264 genes contain only benign variants.
3. **Labels drift over time: "38.6% → 24.4%"** pathogenic share in 2023 labels vs labels added later.

Bottom: our model scores AUROC 0.992 on a random split, "real, but it answers the wrong question."

**Say:**
> "A natural question from an ML point of view: why not just split randomly 80/20? Because variant databases have three built-in shortcuts, and a random split keeps all of them.
>
> First, labels are reused. Three of the eight popular tools we compare against, ClinPred, MetaRNN and VARITY, were trained on ClinVar itself, so testing them on ClinVar rewards memory, not skill.
>
> Second, genes carry the label. 77% of our genes have only benign variants. A model can learn *which gene* instead of *which change*. A random split puts other variants of the same gene on both sides.
>
> Third, labels drift. In 2023, 38.6% of labels were pathogenic; among labels added later, only 24.4%.
>
> Grimm and colleagues in 2015 called the first two 'circularity'. So our model gets 0.992 on a random split. The number is real, but it answers the wrong question."

**Understand:**
- **Type-1 circularity:** the same variants are in training and test.
- **Type-2 circularity:** the same *genes* are in training and test, and databases label genes almost uniformly.
- Grimm found that **98% of proteins** in a clean benchmark had only one class of label.

---

## Slide 6: Our framing, testing the model the way it will be used (Piyush)

**On the slide:**
- Top: a timeline. Purple = "Knowledge frozen: ClinVar Jan 2023, 91,261 variants → training". Red = "Classified later, up to Sep 2026, 124,139 variants → prospective test".
- Four question cards, each with the test that answers it.
- Bottom: why we renamed "leakage-controlled".

**Say:**
> "So instead of one random split, we ask four questions a clinician would ask, and each question defines a test.
>
> One: will it work on future variants? We freeze knowledge at January 2023, train on those 91,261 variants, and test on the 124,139 variants experts classified afterwards. This is our primary result, like a clinical study that enrols patients after the model is fixed.
>
> Two: will it work on genes it never saw? We hold out entire genes.
>
> Three: does it understand the variant, not the gene? We test only on genes containing both pathogenic and benign variants.
>
> Four: can its probability be trusted as clinical evidence? We check calibration and the ClinGen evidence levels.
>
> That's why we no longer say 'leakage-controlled'. Every project avoids leakage. Our contribution is that the test sets are defined by time, gene and label structure, not by random sampling."

**Understand:**
- "Prospective" is borrowed from clinical trials: data is collected *after* the method is fixed.
- The two ClinVar releases we downloaded are **2023-01** and **2026-09**.

*(Handover:)* "Om will now take you through the pipeline, step by step, and the results."

---

## Slide 7: Steps 1–2, label, rarity, conservation (Om)

**On the slide:** three columns.
1. **ClinVar → label only.** The raw record for R175H: "Pathogenic", reviewed by expert panel (3 stars), 39 submitters → **label y = 1**. Below: 9.2 million rows filtered to 202,015 variants.
2. **gnomAD → 8 features.** AF 0.000004 → log10(AF + 1e-7) → **af_ex = −5.39**. Chart: % pathogenic by allele frequency (72% when absent, 0.2% when ≥1%).
3. **dbNSFP → 9 features.** phyloP 6.16, GERP 5.48, SiPhy 17.1, each with its benign median for comparison.

**Say:**
> "Now the pipeline, step by step, for R175H.
>
> Step one, the label. From ClinVar we only read the answer. R175H is 'Pathogenic', reviewed by an expert panel with 39 submitting labs, so its label is 1. Pathogenic and likely pathogenic become 1, benign and likely benign become 0, and uncertain or conflicting entries are dropped. From 9.2 million ClinVar rows we keep 202,015 clean missense variants. ClinVar is never an input to the model.
>
> Step two, the first features. From gnomAD: how common is this variant in people? R175H appears about 4 times per million chromosomes. We take log10, giving minus 5.39; a variant never seen gets minus 7. The chart shows why this matters: variants absent from gnomAD are 72% pathogenic, common ones almost never. That gives eight population features.
>
> From dbNSFP: conservation. phyloP 6.16 means this DNA position has barely changed across 100 vertebrate species; a typical benign variant scores 0.85. If evolution protected a spot for hundreds of millions of years, changing it is risky. That gives nine conservation features."

**Understand:**
- **Allele frequency (AF):** the fraction of chromosomes in the population that carry the variant.
- **Why log10:** AF ranges from 0.000001 to 0.9. The log puts those values on an even scale. The +1e-7 avoids log(0).
- **The 8 population features:** exome AF, genome AF, highest AF in any ancestry group ("popmax") for exome and genome, homozygote counts, and present/absent flags.
- **The 9 conservation features:** phyloP (17 primates / 100 vertebrates / 470 mammals), phastCons (same three), GERP, SiPhy, B-statistic.
- **Caveat to know:** ClinVar curators themselves call very common variants benign. Part of the AF signal is therefore the curators' rule, which is why we also report results on rare variants only.


---

## Slide 8: Step 3, protein and structure (Om)

**On the slide:**
- Left: four rows showing UniProt text → number:
  - `HELIX 174..176` → uni_helix = 1
  - `BINDING 176 (Zn²⁺)` → dist_func_site = 1
  - `InterPro: p53 DNA-binding domain` → interpro_domain = 1
  - `393 amino acids long` → rel_pos = 0.45
- Right: AlphaFold panel. A diagram of residue 175 with **21** neighbours; **pLDDT 96.6** (benign median 64); **21 contacts** (benign median 6).

**Say:**
> "Step three: where in the protein is the change, and how buried is it?
>
> UniProt describes proteins in text, such as 'HELIX from 174 to 176' or 'zinc binding at 176'. We don't feed text to the model. We read only the positions and ask simple yes/no or distance questions. Is residue 175 in a helix? Yes, so 1. How far is the nearest functional site? One residue: 176 binds zinc. Is it in a known domain? Yes, the p53 DNA-binding domain. Names are discarded, so no text and no gene identity reach the model. That gives 17 protein-context features.
>
> From AlphaFold's 3-D model we read two things. AlphaFold is 96.6% confident about this region, so it's a well-folded part of the protein. And 21 other residues sit within 10 ångström of residue 175, so it is buried in the core. A typical benign variant has only 6 neighbours. Changing a buried residue usually breaks the fold. That gives 3 structure features."

**Understand:**
- **pLDDT:** AlphaFold's confidence per residue, 0–100. Above 90 = ordered and folded; below 50 = floppy and disordered.
- **Contacts:** count other residues' central (Cα) atoms within 10 Å. The 2 neighbours on each side in the chain are skipped, because they are always close.
- **Text → number:** domain names are thrown away on purpose. Thousands of names would let the model memorise genes, which is circularity again.

---

## Slide 9: Step 4, ESM-2 (Om)

**On the slide:**
- Top flow: **Input** (protein sequence, not DNA, 393 letters) → **Tokens** (`<cls> M E E P … <eos>`, 395 IDs) → **ESM-2 650M** (33 transformer layers, trained on ~65 million proteins).
- Bottom left: bar chart of probabilities at position 175: **R 0.9992**, K 0.0003, C/H/Q 0.0001. Then **LLR = log p(H) − log p(R) = −9.13**.
- Bottom right: embedding of 1,280 numbers → PCA → **16 numbers**.

**Say:**
> "Step four, the most interesting part: ESM-2, a protein language model from Meta. Just as ChatGPT learned English by predicting missing words, ESM-2 learned proteins by predicting missing amino acids in 65 million natural protein sequences.
>
> The input is the protein sequence, not DNA: 393 letters for TP53. Each letter becomes a token ID, plus start and end tokens, so 395 tokens. One forward pass on our laptop GPU gives, at every position, a probability for each of the 20 amino acids.
>
> At position 175 the model is 99.9% sure that arginine belongs there. Histidine gets 0.0001. The log-likelihood ratio, log p(histidine) minus log p(arginine), is minus 9.13. Strongly negative means very unnatural. For comparison, benign variants average around minus 4 and pathogenic around minus 10.
>
> The second output is a 1,280-number embedding describing residue 175 in context. That's too many for our model, so we compress it with PCA to 16 numbers, fitted only on training data. In total ESM-2 gives 20 features."

**Understand:**
- **Why "zero-shot" works:** ESM-2 never saw disease labels. It learned which amino acids fit where purely from evolution's record in natural sequences.
- **LLR alone** reaches AUROC 0.906. That replicates Brandes et al. 2023, who did the same with the older ESM1b.
- **ESM-2 650M:** 650 million parameters, 33 layers, 1,280-dimensional embeddings. It fits in a 6 GB GPU at half precision. Scoring all 14,808 proteins took about 40 minutes.
- **Long proteins (over 1,022 residues):** cut into overlapping windows, and each residue uses the window where it sits most centrally.
- **Why PCA is fit on training data only:** fitting it on test data would leak test information.

---

## Slide 10: Step 5, the model and its explanation (Om)

**On the slide:**
- Left: the 110 features by group. Population 8, Conservation 9, Protein context 17, Structure 3, Amino-acid properties 53, ESM-2 20.
- Middle: XGBoost (700 trees) → raw score **0.984** → isotonic calibration → **P(pathogenic) = 0.985** → **ACMG: PP3 Strong**.
- Right: the SHAP waterfall chart of the reasons.

**Say:**
> "Step five. All groups together give 110 numbers, with no text and no gene name. Fifty-three of them are simple amino-acid properties, such as how different arginine and histidine are in size and charge.
>
> XGBoost, 700 decision trees, outputs 0.984. Calibration, fitted on genes the model never trained on, makes it an honest probability: 0.985. On the ClinGen scale that is PP3 Strong, strong computational evidence for pathogenic.
>
> And we can say why. This chart is SHAP: each bar is how much a feature pushed the score up. The biggest push is the ESM-2 score, then burial with 21 contacts, rarity in gnomAD, the nearby zinc-binding site, and conservation. This is the same model and the same output as our live demo."

**Understand:**
- **The 53 amino-acid features:**
  - Grantham distance (how chemically different the two amino acids are);
  - BLOSUM62 (how often evolution allows this swap);
  - changes in hydropathy, volume, polarity and charge;
  - an aromatic-change flag;
  - Pro/Gly/Cys flags (6);
  - which amino acid it was (20 columns) and which it became (20 columns), as one-hot columns.
- **Protein length (+0.65 on the chart)** is a known weakness. Long proteins tend to have benign variants in the database, so length partly acts as a gene identity. We disclose this on slide 10.
- **Two saved versions of Model D:**
  - The **final model**, trained on all 2026 labels, gives **0.985**. It is used for the demo and this slide.
  - The **evaluation model**, trained only on 2023 labels, gives **0.993**. It produced all the test results.
  - Both say PP3 Strong.
- **R175H was in the training data**, so this slide demonstrates the *pipeline and explanation*, not test accuracy. Test accuracy is on the next slide.
- **Isotonic calibration** learns a monotone mapping from raw score to observed frequency.

---

## Slide 11: Results (Om)

**On the slide:**
- Left: horizontal bar chart, AUROC on 124,139 variants labelled after Jan 2023:

| Method | AUROC |
|---|---|
| Ours D | **0.987** |
| Ours C | 0.984 |
| REVEL | 0.975 |
| Ours B | 0.974 |
| AlphaMissense | 0.966 |
| ESM1b | 0.940 |
| CADD | 0.939 |
| ESM-2 zero-shot | 0.916 |

- Right top: "0.987 vs 0.975 (REVEL)"; confidence intervals do not overlap; rare variants only: 0.983.
- Right middle: chart "When the gene gives no hint, our lead grows":

| Genes | Ours | REVEL | AlphaMissense |
|---|---|---|---|
| Pure genes | 0.995 | 0.993 | 0.988 |
| Mixed genes (20–80% pathogenic) | **0.969** | 0.925 | 0.940 |

- Right bottom: the three replications.

**Say:**
> "Now the results, on the honest test: 124,139 variants classified after our training data was frozen.
>
> Our model D reaches AUROC 0.987. The best independent published tool, REVEL, reaches 0.975, and AlphaMissense from DeepMind 0.966. The 95% confidence intervals do not overlap, so the difference is real. On rare variants only, where the 'common means benign' shortcut doesn't help, we still reach 0.983.
>
> Two tools are deliberately not shown: ClinPred and MetaRNN were trained on ClinVar labels, so comparing against them would be circular.
>
> The small chart is the strongest evidence for our approach. In 'pure' genes, where all variants share one label, every tool looks almost perfect, exactly the circularity Grimm warned about. In mixed genes, where the gene gives no hint and the model must understand the variant, our lead grows: 0.969 versus 0.925 for REVEL.
>
> We also replicated three published results: the protein language model result of Brandes 2023, the circularity effect of Grimm 2015, and the ClinGen calibration of Pejaver 2022."

**Understand:**
- **AUROC 0.987:** in 98.7% of random pathogenic/benign pairs, our model ranks the pathogenic one higher.
- **The three test designs for model D:**

| Test | AUROC |
|---|---|
| Random | 0.992 |
| Gene-held-out | 0.988 |
| Prospective | 0.987 |

  The tiny drop shows the model isn't relying on gene memorisation.
- **Replication details:**
  - **Brandes 2023:** ESM-2 alone gives 0.906; dbNSFP's ESM1b gives 0.933.
  - **Grimm 2015:** on variants added after 2023, ClinVar-trained tools *lose* AUROC (MetaRNN −0.005, ClinPred −0.006), while independent tools *gain* (REVEL +0.017, CADD +0.041). The gap is the memorisation effect.
  - **Pejaver 2022:** our recomputed REVEL thresholds have the same structure but are stricter. Their published thresholds still pass every evidence level on our newer data.
- **Why newer variants are easier for honest tools:** many recent submissions are clear-cut benign variants from large labs.

---

## Slide 12: What does not work yet, and next steps (Om)

**On the slide:**
- Left: ClinGen evidence levels checked on future variants:

| Level | Result |
|---|---|
| PP3 Strong (P ≥ 0.951) | ✓ (LR 59.3 ≥ 33.5) |
| PP3 Moderate | ✗ (LR 3.7 < 5.79) |
| PP3 Supporting | ✗ (LR 1.3 < 2.41) |
| BP4 Supporting / Moderate / Strong | ✓ all pass |

- Left, below the table: calibration drift (ECE 0.004–0.015 within one era → 0.084 on future variants → 0.065 after our correction); new genes (0.973 vs AlphaMissense 0.986); gene proxy (protein length).
- Right: four numbered next steps, and the thank-you box with the demo command.

**Say:**
> "We also report what doesn't work yet.
>
> We converted our probabilities into ClinGen evidence levels using the method of Pejaver 2022 and checked them on future variants. Strong pathogenic evidence passes comfortably, and all benign levels pass. But moderate and supporting pathogenic don't yet reach the required likelihood ratio.
>
> The reason is calibration drift. Within one ClinVar era our probabilities are very accurate, error about 0.01. On later variants the error is 0.084, partly because the pathogenic share fell from 38.6% to 24.4%. A label-shift correction we added brings it to 0.065.
>
> Also, on genes that had no labels before 2023, AlphaMissense still ranks slightly better than us, though that subset has only 405 pathogenic variants.
>
> Next we will recalibrate on recent data so the mid-range levels pass, study the errors on unseen genes, refine the population feature, and optionally test on laboratory-measured mutation effects.
>
> Thank you. We are happy to take questions, and we can run a live demo of the tool."

**Understand:**
- **Likelihood ratio (LR):** how much more often a score range appears in pathogenic than in benign variants. ClinGen requires 2.41 for supporting, 5.79 for moderate and 33.5 for strong.
- **BP4 uses the inverse:** a small LR means strong benign evidence.
- **The demo:** `python src/predict.py "chr17:g.7675088C>T"` prints P = 0.985, PP3_Strong, and the top SHAP reasons.
  - It takes about 30–60 seconds, because it loads ESM-2 and fetches data online.
  - Run it once before the presentation to check the internet connection.

---

# Part C: Questions you may be asked

**About the framing**

- **"Isn't this just a proper train/test split?"**
  - No. Here the leakage is inside the data: tools trained on the same labels, genes with uniform labels, and labels that drift.
  - A random split keeps all three. We defined test sets by time (prospective), gene (held-out) and label structure (mixed genes). (Slides 3–4.)
- **"Why is 0.98 not suspiciously high?"**
  - ClinVar missense is a relatively easy benchmark; REVEL already gets 0.975 on the same test.
  - What matters is that we beat independent tools under strict tests, that our lead *grows* on mixed genes (0.969 vs 0.925), and that we show where we lose (unseen genes, mid-range calibration).
- **"How do you know there's no leakage?"**
  1. ClinVar is only the label.
  2. No published tool's score is a feature.
  3. Training uses only the 2023 labels; testing uses only variants labelled afterwards.
  4. PCA and calibration are fitted only on training data.
  5. The gene-held-out split never puts one gene in both train and test.

**About the data**

- **"How many variants?"**
  - 215,400 total.
  - 91,261 for training (ClinVar Jan 2023).
  - 124,139 in the prospective test (labelled later).
  - They span 15,264 genes.
- **"Why only missense?"** Missense changes are the hardest to interpret. A stop codon usually destroys the protein, but one amino-acid swap can be harmless or lethal.
- **"Why drop VUS?"** VUS means "not enough evidence", not a biological class. We train on clear labels and can then score VUS variants.
- **"Isn't allele frequency cheating, since curators use it?"** It is real biological evidence. But because curators also use it, we report rare variants separately: 0.983, still ahead of REVEL (0.973).

**About the method**

- **"Why XGBoost and not a neural network?"**
  - The data is a table of mixed numeric features with missing values. XGBoost handles that natively, trains fast on a laptop GPU, and supports exact SHAP explanations.
  - The deep learning is in ESM-2 (650 million parameters), used as a feature extractor.
- **"What exactly goes into ESM-2?"**
  - The protein's amino-acid sequence (one-letter codes) from UniProt, not DNA, tokenised into IDs.
  - We use the probabilities at the variant position, giving the LLR, entropy and log-probabilities, plus the embedding compressed by PCA to 16 numbers.
- **"Why calibrate?"** Clinicians need probabilities they can trust. Uncalibrated scores can be systematically too high or too low. Calibration is also needed to map the probability to ACMG evidence levels.
- **"Why does protein length appear in SHAP?"**
  - Long proteins, such as the muscle protein TTN, have mostly benign variants in ClinVar, so length partly acts as gene identity.
  - We disclose it, and our mixed-gene results show the model still works where the gene gives no hint.

- **"Could a lab double-count rarity if it uses your PP3 together with PM2?"**
  - Yes, that's a fair point. Our model uses gnomAD frequency, and PM2 is also about rarity.
  - Pejaver 2022 handled this for BayesDel by calibrating a version without allele frequency.
  - Our fix would be to release a variant of the model without the population features for clinical use.
- **"What is isotonic calibration and why does AUROC not change?"**
  - It fits an increasing staircase from raw score to the observed fraction pathogenic, on held-out genes.
  - Because it is monotone, the order of variants is unchanged, so AUROC is the same. Only the probability values become honest.

**About papers and baselines**

- **"Which papers is the project based on?"**
  - **Grimm et al. 2015** defined circularity, which drives our evaluation.
  - **Pejaver et al. 2022** turned scores into ClinGen PP3/BP4 evidence, which drives our output.
  - **Brandes et al. 2023** (protein language model scoring) is the basis of our ESM-2 features.
- **"What are the baselines?"**
  - **REVEL:** combines 13 other tools.
  - **AlphaMissense:** DeepMind's deep model.
  - **CADD:** a genome-wide score.
  - **ESM1b:** an older protein language model.
  - **PrimateAI.**
  - ClinPred, MetaRNN and VARITY were trained on ClinVar, so they are shown separately as circular.
- **"Why did ClinVar-trained tools drop on newer variants?"** They partly memorised the 2023 labels. Independent tools improved because newer submissions are easier on average.

**About limitations**

- **"What doesn't work?"**
  1. Mid-range pathogenic evidence levels (PP3 Moderate and Supporting) fail on future variants, because probabilities drift.
  2. On genes with no prior labels, AlphaMissense ranks better.
  3. Protein length acts partly as a gene proxy.
  4. gnomAD and dbNSFP features are current, not frozen at 2023; only the labels are time-split.
- **"Is this clinically usable?"** No. It is a research tool that produces one kind of computational evidence (PP3/BP4), not a diagnosis.

---

# Part D: Cheat sheet of numbers

| What | Number |
|---|---|
| ClinVar rows filtered | 9,223,698 → 202,015 missense variants (2026-09) |
| Training set (ClinVar Jan 2023) | 91,261 variants, 38.6% pathogenic |
| Prospective test (labelled after Jan 2023) | 124,139 variants, 24.4% pathogenic |
| Total variants / genes | 215,400 / 15,264 |
| Genes with only benign variants | 77% |
| Features | 110 = population 8 + conservation 9 + protein 17 + structure 3 + amino acid 53 + ESM-2 20 |
| ESM-2 model | 650M parameters, 33 layers, 1,280-dim embedding → 16 PCs |
| TP53 R175H | AF 4 in a million (−5.39), phyloP 6.16, pLDDT 96.6, 21 contacts, ESM-2 LLR −9.13, P = 0.985 (final) / 0.993 (2023 model), PP3 Strong |
| Main result AUROC | Ours 0.987 · REVEL 0.975 · AlphaMissense 0.966 · CADD 0.939 · ESM-2 zero-shot 0.916 |
| Rare variants | Ours 0.983 · REVEL 0.973 |
| Mixed genes (20–80% pathogenic) | Ours 0.969 · REVEL 0.925 · AlphaMissense 0.940 |
| Model D across tests | Random 0.992 · gene-held-out 0.988 · prospective 0.987 |
| Calibration error (ECE) | 0.004–0.015 same era · 0.084 future · 0.065 corrected |
| Evidence levels passing on future data | 4 of 6 (PP3 Strong + all BP4) |
| Unseen genes | Ours 0.973 vs AlphaMissense 0.986 (405 pathogenic) |

**Mini glossary**

| Term | Meaning |
|---|---|
| Missense | One DNA letter changed, so one amino acid changes |
| VUS | Variant of uncertain significance |
| ClinVar | Public database of variant classifications |
| gnomAD | Population frequency database |
| dbNSFP | Precomputed variant scores (conservation and tool scores) |
| phyloP | Conservation score: high means unchanged across species |
| pLDDT | AlphaFold's per-residue confidence |
| ESM-2 | Protein language model |
| LLR | log p(new amino acid) − log p(original); very negative means unnatural |
| AUROC | Ranking metric: 0.5 = random, 1 = perfect |
| ECE | Calibration error |
| SHAP | Per-feature explanation of a prediction |
| PP3 / BP4 | ACMG codes for computational evidence (pathogenic / benign) |
| Circularity | Test results inflated because training and test share variants or genes |
| Prospective test | Train on the past, test on what happened later |

**More detail if you have time:** `STUDY_GUIDE.md` (everything from scratch), `DATA_FLOW_EXPLAINED.md` (exactly how each data source becomes numbers), `CORE_PAPERS.md` (the two core papers in depth).
