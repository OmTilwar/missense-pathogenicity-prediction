# From Raw Data to the 110-Number XGBoost Input

*How each data source becomes numbers, traced end to end with TP53 R175H.*
*Every value below is the real value from our pipeline, not an illustration.*

---

## 0. The big picture

```
RAW SOURCE                 RAW FORM                           EXTRACTION / ENCODING                    FEATURES
─────────────────────────  ─────────────────────────────────  ───────────────────────────────────────  ─────────────
ClinVar variant_summary    TSV text row                       text match on 6 label strings → 0/1      TARGET (y)
                                                              regex on HGVS name → gene, R, 175, H     (keys only)
gnomAD (MyVariant JSON)    nested JSON numbers                pick fields → max → log10(x + 1e-7)      8 population
dbNSFP (MyVariant JSON)    nested JSON numbers + text list    pick scores; text → "is non-empty" 0/1   9 conservation (+1 protein flag)
UniProt FASTA + TSV        sequence string + feature text     parse "TYPE start..end" → inside? 0/1    17 protein context
                                                              distances, lengths → numbers
AlphaFold PDB file         fixed-width text, 1 line per atom  read Cα x,y,z + B-factor → geometry      3 structure
ref / alt amino acid       two letters ("R", "H")             lookup tables + one-hot                  53 aa properties
ESM-2 (protein sequence)   tensor 395 × 33 and 395 × 1280     log-softmax → LLR etc.; PCA(1280 → 16)    4 + 16 ESM-2
                                                                                                         ─────
                                                                                         TOTAL INPUT =   110 floats
```

**The key rule:** XGBoost only ever receives a matrix of floating-point numbers (rows = variants, 110 columns).
- **No text, no category strings and no IDs reach the model.**
- Every textual or categorical piece of information is converted to a number first, in one of three ways:
  - a 0/1 flag;
  - a distance or count;
  - a one-hot column.
- Missing information stays as `NaN` (Not a Number). XGBoost handles `NaN` natively, as explained in §8.

| Script | What it does |
|---|---|
| `src/01_build_clinvar.py` | ClinVar → labels |
| `src/02_annotate_myvariant.py` | gnomAD + dbNSFP |
| `src/03_protein_features.py` | UniProt + AlphaFold |
| `src/04_esm2_features.py` | ESM-2 |
| `src/05_build_dataset.py` | log transforms, amino-acid features, merge |
| `src/common.py` (`VariantModel._X`) | ESM PCA + assembly of the final 110-column matrix |

---

## 1. ClinVar → target label (not a feature)

### 1.1 Fields extracted

From the 43 columns of `variant_summary.txt.gz` we read these 12:

| ClinVar column | TP53 R175H raw value | What we do with it |
|---|---|---|
| `Assembly` | `GRCh38` | Keep only GRCh38 rows |
| `Type` | `single nucleotide variant` | Keep only SNVs |
| `ClinicalSignificance` | `Pathogenic` | → **label** (see 1.2) |
| `ReviewStatus` | `reviewed by expert panel` | Keep only ≥ 1 star; store stars = 3 |
| `Name` | `NM_000546.6(TP53):c.524G>A (p.Arg175His)` | Regex → transcript, gene, ref, position, alt |
| `Chromosome` | `17` | Part of the variant key |
| `PositionVCF` | `7675088` | Part of the variant key |
| `ReferenceAlleleVCF` | `C` | Part of the variant key |
| `AlternateAlleleVCF` | `T` | Part of the variant key |
| `GeneSymbol`, `VariationID`, `LastEvaluated` | `TP53`, `12374`, `Sep 06, 2024` | Stored for reference only |

**Regex on the Name field:**

```
^(N[MC]_\d+\.\d+)\(([^)]+)\):c\.[^ ]+ \(p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)$
 └ transcript ┘     └ gene ┘                   └ ref ┘   └pos┘ └ alt ┘
   NM_000546.6        TP53                       Arg       175    His   →  R, 175, H  (3-letter → 1-letter)
```

The row is kept only if:
- ref and alt are among the 20 standard amino acids;
- ref ≠ alt (not synonymous);
- alt ≠ `Ter` (not a stop codon).

### 1.2 Text → label

`ClinicalSignificance` is a text field. We match it **exactly** against six strings:

| ClinicalSignificance text | label |
|---|---|
| `Pathogenic`, `Likely pathogenic`, `Pathogenic/Likely pathogenic` | **1** |
| `Benign`, `Likely benign`, `Benign/Likely benign` | **0** |
| anything else (VUS, `Conflicting classifications…`, `risk factor`, `Pathogenic; drug response`, …) | **row dropped** |

A variant whose two rows disagree is removed entirely.

We do this for two releases, giving two label columns:
- **`label_old`**: from 2023-01. This is the training target for the time-travel model.
- **`label_new`**: from 2026-09. This is the test target, and the training target for the final model.

TP53 R175H: `label_old = 1`, `label_new = 1`.

**Output IDs** (used to join every other source):

| ID | Value | Purpose |
|---|---|---|
| `key` | `17-7675088-C-T` | internal join key |
| `hgvs` | `chr17:g.7675088C>T` | query to MyVariant.info |
| `gene`, `aa_ref`, `aa_pos`, `aa_alt` | `TP53`, `R`, `175`, `H` | protein mapping |

> ClinVar contributes **0 features**. The label `y` is kept in a separate array and is never inside X.

---

## 2. gnomAD → 8 population features

### 2.1 Raw data returned

We POST `chr17:g.7675088C>T` to MyVariant.info and receive nested JSON. The relevant gnomAD part, trimmed:

```json
"gnomad_exome": {
  "af":  { "af": 3.97969e-06,                                   ← global exome AF
           "af_afr": 0.0, "af_amr": 0.0, "af_asj": 0.0, "af_eas": 0.0,
           "af_fin": 0.0, "af_nfe": 8.80282e-06, "af_oth": 0.0, "af_sas": 0.0,   ← per-ancestry AF
           "af_female": 0.0, "af_male": 7.36204e-06,            ← per-sex (ignored for popmax)
           "af_nfe_bgr": 0.0, "af_eas_jpn": 0.0, … (36 keys in total) },
  "hom": { "hom": 0, "hom_afr": 0, … }                          ← homozygote counts
},
"gnomad_genome": {
  "af":  { "af": 6.57013e-06,
           "af_afr": 0.0, "af_ami": 0.0, "af_amr": 0.0, "af_asj": 0.0, "af_eas": 0.0,
           "af_fin": 0.0, "af_mid": 0.0, "af_nfe": 1.46972e-05, "af_oth": 0.0, "af_sas": 0.0,
           "af_xx": 1.28442e-05, "af_xy": 0.0 },
  "hom": { "hom": 0, … }
}
```

### 2.2 Extraction (`flatten()` in `02_annotate_myvariant.py`)

| Feature | Raw field used | Extraction rule |
|---|---|---|
| `af_ex` (raw) | `gnomad_exome.af.af` | take the number |
| `af_ge` (raw) | `gnomad_genome.af.af` | take the number |
| `af_ex_popmax` (raw) | all keys `af_xxx` with exactly one underscore, except `af_female`/`af_male` | **maximum** of those values |
| `af_ge_popmax` (raw) | same, genome | maximum |
| `hom_ex` (raw) | `gnomad_exome.hom.hom` | take the number |
| `hom_ge` (raw) | `gnomad_genome.hom.hom` | take the number |
| `in_gnomad_ex` | does a `gnomad_exome` record exist? | 1 / 0 |
| `in_gnomad_ge` | does a `gnomad_genome` record exist? | 1 / 0 |

### 2.3 Transformation (`05_build_dataset.py`)

```python
for c in ["af_ex", "af_ge", "af_ex_popmax", "af_ge_popmax"]:
    df[c] = np.log10(df[c].fillna(0) + 1e-7)      # absent from gnomAD -> AF 0 -> log10(1e-7) = -7
for c in ["hom_ex", "hom_ge"]:
    df[c] = np.log10(df[c].fillna(0) + 1)         # 0 homozygotes -> 0
```

| Feature | Transformation | TP53 raw | → TP53 final |
|---|---|---|---|
| `af_ex` | log10(AF + 1e-7) | 3.97969e-06 | log10(4.07969e-06) = **−5.389** |
| `af_ge` | log10(AF + 1e-7) | 6.57013e-06 | **−5.176** |
| `af_ex_popmax` | log10(max + 1e-7) | max = af_nfe = 8.80282e-06 | **−5.050** |
| `af_ge_popmax` | log10(max + 1e-7) | max = af_nfe = 1.46972e-05 | **−4.830** |
| `hom_ex` | log10(count + 1) | 0 | **0** |
| `hom_ge` | log10(count + 1) | 0 | **0** |
| `in_gnomad_ex` | none (0/1) | record present | **1** |
| `in_gnomad_ge` | none (0/1) | record present | **1** |

**Why log10 and why + 1e-7?**
- AF spans from 0.000001 to 0.9. The log puts rare and common variants on an even scale.
- `+ 1e-7` makes "never observed" (AF = 0) a finite value of −7 instead of −∞.
- `+ 1` does the same for counts.

> **Known limitation we found while writing this guide.** Genome records also contain `af_xx` / `af_xy`
> (sex groups), and our "one underscore" rule includes them in the popmax.
> - This changes `af_ge_popmax` for 1,462 of 126,571 variants (1.2%), and by more than 2× for only 3.
> - Our popmax also includes small groups (Amish, Ashkenazi, Finnish, "other") that gnomAD's official popmax excludes.
> - Fix scheduled for Week 3: exclude `af_xx`/`af_xy`. The effect on results is expected to be negligible.

---

## 3. dbNSFP → 9 conservation features (+ 1 protein flag)

### 3.1 Raw data returned (same MyVariant JSON, `dbnsfp` part)

```json
"phylop":     { "17way_primate":     {"score": 0.599, "rankscore": 0.4025},
                "100way_vertebrate": {"score": 6.163, "rankscore": 0.71702},
                "470way_mammalian":  {"score": 7.693, "rankscore": 0.65888} },
"phastcons":  { "17way_primate": {"score": 0.919}, "100way_vertebrate": {"score": 1.0},
                "470way_mammalian": {"score": 1.0} },
"gerp":       { "91_mammals": {"score": 5.48, "rankscore": 0.94213} },
"siphy_29way":{ "logodds_score": 17.0767 },
"bstatistic": { "score": 434.0 },
"interpro":   { "domain": ["p53, DNA-binding domain|p53, DNA-binding domain", … 13 items] },   ← TEXT
"genename":   ["TP53", "TP53", … 21 items],                                                  ← TEXT (not a feature)
"aa":         { "ref": "R", "alt": "H" }                                                       ← TEXT (not a feature)
```

### 3.2 Extraction

| Feature | Raw field | TP53 value |
|---|---|---|
| `phylop_17` | `phylop.17way_primate.score` | 0.599 |
| `phylop_100` | `phylop.100way_vertebrate.score` | 6.163 |
| `phylop_470` | `phylop.470way_mammalian.score` | 7.693 |
| `phastcons_17` | `phastcons.17way_primate.score` | 0.919 |
| `phastcons_100` | `phastcons.100way_vertebrate.score` | 1.0 |
| `phastcons_470` | `phastcons.470way_mammalian.score` | 1.0 |
| `gerp_91` | `gerp.91_mammals.score` (GERP++ "rejected substitutions") | 5.48 |
| `siphy` | `siphy_29way.logodds_score` | 17.0767 |
| `bstatistic` | `bstatistic.score` | 434.0 |

All 9 are **already numbers** and pass through unchanged. There is no scaling and no log.
- We use the raw `score`, not the `rankscore`.
- dbNSFP sometimes gives a list (one value per transcript). Our `_num()` helper then takes the **maximum** numeric value and ignores `"."` and `None`.
- Conservation is a property of the DNA position, so these are single numbers in practice.

**Are any text or categorical dbNSFP fields used?** One, converted to a binary flag:

| Feature | Raw text | Rule | TP53 |
|---|---|---|---|
| `interpro_domain` (counted in the protein-context group) | list of domain-name strings | **1** if any string is non-empty after stripping `. \|`, else **0**. The domain *name* is thrown away | `"p53, DNA-binding domain…"` → **1** |

`genename` and `aa` are text used only for checking. They are never features.

**Baseline scores** in the same JSON (`alphamissense`, `revel`, `cadd`, `esm1b`, `clinpred`, `metarnn`, `varity`, `primateai`):
- they are stored as `bl_*` columns for comparison only;
- they are **never** in X;
- TP53 values: REVEL 0.922, AlphaMissense up to 0.986, CADD 25.9.

(We also requested `gerp++.rs`, but the `+` characters were lost in the form-encoded request, so the column came back empty and was dropped. `gerp_91` covers GERP.)

---

## 4. UniProt → 17 protein-context features (the main question)

**UniProt contains text and categories (domain names, ligand names, notes). Our code converts all of
it into numbers *before* the model. No UniProt text is passed to XGBoost.** Here is exactly how.

### 4.1 Raw UniProt inputs

**(a) FASTA file:** one sequence per protein. The header gives the accession and gene name.

```
>sp|P04637|P53_HUMAN Cellular tumor antigen p53 OS=Homo sapiens OX=9606 GN=TP53 PE=1 SV=4
MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGP
DEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYQGSYGFRLGFLHSGTAK …   (393 letters)
```

**(b) Feature table (TSV):** one row per protein, one text column per annotation type. The real P04637 row (shortened):

| Column | Raw text (excerpt) |
|---|---|
| Entry / Gene / Length | `P04637` / `TP53` / `393` |
| Active site | *(empty)* |
| Binding site | `BINDING 176; /ligand="Zn(2+)"; … BINDING 179; /ligand="Zn(2+)"; … BINDING 238; … BINDING 242; …` |
| Disulfide bond | *(empty)* |
| Transmembrane | *(empty)* |
| Domain [FT] | *(empty: TP53's DNA-binding domain is not a UniProt "Domain" entry)* |
| Signal peptide | *(empty)* |
| Modified residue | `MOD_RES 9; /note="Phosphoserine; by HIPK4"; MOD_RES 15; … MOD_RES 18; …` |
| Zinc finger | *(empty)* |
| Motif | `MOTIF 17..25; /note="TADI"; MOTIF 48..56; …; MOTIF 305..321; …` |
| Helix | `HELIX 3..6; … HELIX 166..168; … HELIX 174..176; … HELIX 177..180; …` |
| Beta strand | `STRAND 33..35; … STRAND 156..165; … STRAND 181..183; …` |
| Region | `REGION 1..320; /note="Interaction with CCAR2"; REGION 1..83; … REGION 100..370; …` |
| Compositional bias | `COMPBIAS 69..90; /note="Pro residues"; COMPBIAS 282..299; …` |

### 4.2 Step 1: map the variant to the protein and verify it

```
gene "TP53"  --(FASTA header GN=TP53)-->  accession P04637  -->  sequence (393 aa)
check: sequence[175 - 1] == "R" ?   →  yes  →  seq_match = 1
```

- If the residue does not match, `seq_match = 0`. That happens for 7% of variants, whose ClinVar numbering is on another isoform.
- For those variants, **all UniProt, AlphaFold and ESM-2 features are left as `NaN`**.
- `seq_match` is a filter flag, not a model feature.

### 4.3 Step 2: parse the text into position intervals

Each column is a list of entries such as `BINDING 176; /ligand=…` or `HELIX 174..176; /evidence=…`.
- The code splits the column into entries wherever `"; "` is followed by a keyword and a number.
- It then reads only the **numbers** with the regex `^[A-Z_]+ [<?]?(\d+)(?:\.\.[>?]?(\d+))?`.
- **Everything after the numbers is discarded**: ligand names, notes, evidence codes, domain names.

```
"HELIX 174..176; /evidence=…"            →  (174, 176)
"BINDING 176; /ligand=\"Zn(2+)\"; …"      →  (176, 176)
"REGION 1..320; /note=\"Interaction…\""   →  (1, 320)
```

### 4.4 Step 3: turn intervals into numbers at the variant's position (p = 175)

Three encoding rules are used, depending on the annotation type:

| Rule | Applied to | Number produced |
|---|---|---|
| **range**: is p inside any `start..end`? | Domain, Transmembrane, Signal peptide, Zinc finger, Motif, Helix, Beta strand, Region, Compositional bias | 1 / 0 |
| **site**: is p exactly one of the listed positions? | Active site, Binding site, Modified residue | 1 / 0 |
| **pair**: is p one of the *two endpoints*? (`DISULFID 22..58` = residue 22 bonded to 58, not the range) | Disulfide bond | 1 / 0 |

Three further numeric features are computed:

| Feature | Computation | Type |
|---|---|---|
| `rel_pos` | p ÷ protein length | continuous 0–1 |
| `log_prot_len` | log10(protein length) | continuous |
| `dist_func_site` | distance (in residues) from p to the nearest active **or** binding site position, capped at 50; 50 if the protein has none | integer 0–50 |

### 4.5 Result for TP53 R175H: all 17 protein-context features

| # | Feature | Source | Encoding | Why this value for p = 175 | Value |
|---|---|---|---|---|---|
| 1 | `rel_pos` | FASTA length | numeric | 175 / 393 | **0.4453** |
| 2 | `log_prot_len` | FASTA length | numeric | log10(393) | **2.594** |
| 3 | `interpro_domain` | dbNSFP InterPro text | binary | "p53, DNA-binding domain" present | **1** |
| 4 | `dist_func_site` | Binding sites 176, 179, 238, 242 (Zn) | distance | \|176 − 175\| = 1 | **1** |
| 5 | `uni_domain` | Domain [FT] | range | column empty | **0** |
| 6 | `uni_active_site` | Active site | site | column empty | **0** |
| 7 | `uni_binding_site` | Binding site | site | 175 not in {176, 179, 238, 242, …} | **0** |
| 8 | `uni_disulfide` | Disulfide bond | pair | column empty | **0** |
| 9 | `uni_transmem` | Transmembrane | range | empty | **0** |
| 10 | `uni_signal` | Signal peptide | range | empty | **0** |
| 11 | `uni_mod_res` | Modified residue | site | 175 not listed | **0** |
| 12 | `uni_zn_finger` | Zinc finger | range | empty | **0** |
| 13 | `uni_motif` | Motif | range | 175 not in 17–25, 48–56, 305–321, … | **0** |
| 14 | `uni_helix` | Helix | range | **174..176 contains 175** | **1** |
| 15 | `uni_strand` | Beta strand | range | between 156–165 and 181–183 | **0** |
| 16 | `uni_region` | Region | range | **1..320 contains 175** | **1** |
| 17 | `uni_compbias` | Compositional bias | range | 69–90, 282–299 do not contain it | **0** |

### 4.6 Direct answers to the questions

| Question | Answer |
|---|---|
| Which raw UniProt fields are used? | The FASTA sequence (length, residue check, ESM input) and 13 TSV columns: Active site, Binding site, Disulfide bond, Transmembrane, Domain [FT], Signal peptide, Modified residue, Zinc finger, Motif, Helix, Beta strand, Region, Compositional bias |
| Which become binary 0/1? | The 13 `uni_*` flags (plus `interpro_domain` from dbNSFP) |
| Which become distances, counts or numbers? | `dist_func_site` (residues to nearest active/binding site), `rel_pos`, `log_prot_len` |
| Are any categorical fields one-hot encoded? | No. Each annotation type is already its own 0/1 column. Domain names, ligand names and notes are **discarded**, not encoded. (The only one-hot features in the project are the amino-acid identities, §6) |
| Is any UniProt text passed to XGBoost? | **No.** Every value in X is a float |

> **Design note.** We keep only "is the residue in an annotated element of type T". We drop *which*
> element, such as the domain name. With about 15,000 genes, domain names would be thousands of rare
> categories, and they would let the model memorise gene identity: the type-2 circularity we are trying to avoid.

---

## 5. AlphaFold → 3 structure features

### 5.1 Raw data

We download `https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v6.pdb`. It is a fixed-width text file with one line per atom.
Here are the real lines for residue 175 (Arg), which has 11 atoms:

```
ATOM   1327  N   ARG A 175       2.937  -7.932  -4.545  1.00 96.62           N
ATOM   1328  CA  ARG A 175       4.335  -7.532  -4.313  1.00 96.62           C   ← we keep ONLY the CA atom
ATOM   1329  C   ARG A 175       5.231  -8.169  -5.377  1.00 96.62           C
ATOM   1330  CB  ARG A 175       4.781  -7.914  -2.894  1.00 96.62           C
 …                (side-chain atoms CG, CD, NE, CZ, NH1, NH2, O)
         columns:  atom  res  chain resnum     x       y       z     occ  B-factor
                                                                         └── AlphaFold puts pLDDT here
```

### 5.2 Extraction (`fetch_af` in `03_protein_features.py`)

1. For each line where `line[0:4] == "ATOM"` and `line[12:16] == " CA "`, read:
   - the residue number `line[22:26]`;
   - x, y, z `line[30:54]`;
   - pLDDT `line[60:66]`.
2. Save three arrays per protein in `alphafold/P04637.npz`:
   - `res`: 393 residue numbers;
   - `xyz`: 393 × 3 coordinates;
   - `plddt`: 393 values.

### 5.3 The 3 features (`structure_feats`)

```python
i        = index of residue 175
d        = distance from Cα(175) to every other Cα           # Euclidean, in Å
seq_far  = |j - i| > 2                                       # ignore itself and the 2 neighbours each side
contacts = count( d < 10 Å  AND  seq_far )
plddt    = plddt[i]
window   = mean( plddt[i-5 : i+6] )                          # residues 170–180
```

**Why skip neighbours within 2 residues?** Residues 173–177 are always close (about 3.8 Å per peptide bond),
because they are chained together. Counting them would say nothing about burial. Real contacts are
residues far away in the *sequence* but close in *space*, which happens when the protein folds.

**TP53 residue 175:**

| Feature | Calculation | Value |
|---|---|---|
| `af_plddt` | pLDDT of residue 175 | **96.62** |
| `af_plddt_win` | mean of [95.2, 95.7, 96.3, 97.1, 95.1, **96.6**, 96.5, 95.2, 94.9, 94.2, 93.3] | **95.48** |
| `af_contacts` | 21 residues within 10 Å (listed below) | **21** |

The 21 contacts (residue, distance in Å):

| Group | Residues |
|---|---|
| Same strand/helix | 172 (10.0), 178 (8.1), 179 (6.3), 180 (5.8), 181 (9.5) |
| Loop L2 | 191 (8.1), 192 (5.8), 193 (6.6), 194 (5.5), 195 (9.3) |
| Loop L3 | 236 (9.3), 237 (7.0), 238 (5.6), 239 (8.6), 240 (9.5), 242 (8.1), 243 (9.4), 244 (7.9), 245 (5.0), 246 (7.2), 247 (9.9) |

Excluded as sequence neighbours: 173 (7.2 Å), 174 (3.8), 176 (3.8), 177 (6.5).

Residue 175 is packed against loops L2 and L3, which are far apart in the sequence. This is TP53's zinc-binding core, so the residue is deeply buried.

For proteins with no AlphaFold model (very long proteins) or isoform mismatches, all 3 features are `NaN`.

---

## 6. Reference/alternate amino acids → 53 features

The only inputs are two letters, ref = `R` and alt = `H`. Everything is a table lookup (`aa_features()` in `05_build_dataset.py`).

### 6.1 The lookup tables

| Table | Values |
|---|---|
| **Grantham (c, p, v)**: composition, polarity, volume | R = (0.65, 10.5, 124); H = (0.58, 10.4, 96); … all 20 |
| **Kyte-Doolittle hydropathy** | R = −4.5; H = −3.2; I = 4.5 (most hydrophobic); … |
| **Charge** | D, E = −1; K, R = +1; H = +0.1; others 0 |
| **Aromatic set** | {F, W, Y, H} |
| **BLOSUM62** | 20 × 20 matrix of substitution scores (from Biopython) |

### 6.2 The 53 features

| Features | Count | Formula | TP53 R→H |
|---|---|---|---|
| `grantham` | 1 | 50.723 × √(1.833·Δc² + 0.1018·Δp² + 0.000399·Δv²) | √(1.833·0.07² + 0.1018·0.1² + 0.000399·28²) × 50.723 = **28.82** |
| `blosum62` | 1 | BLOSUM62[ref][alt] | BLOSUM62[R][H] = **0** |
| `d_hydropathy` | 1 | KD[alt] − KD[ref] | −3.2 − (−4.5) = **+1.3** |
| `d_volume` | 1 | v[alt] − v[ref] | 96 − 124 = **−28** |
| `d_polarity` | 1 | p[alt] − p[ref] | 10.4 − 10.5 = **−0.1** |
| `d_charge` | 1 | charge[alt] − charge[ref] | 0.1 − 1 = **−0.9** |
| `arom_change` | 1 | 1 if exactly one of ref/alt is aromatic | R no, H yes → **1** |
| `ref_is_P`, `ref_is_G`, `ref_is_C`, `alt_is_P`, `alt_is_G`, `alt_is_C` | 6 | 1 if the amino acid is Pro/Gly/Cys | all **0** |
| `ref_A` … `ref_Y` (one-hot) | 20 | 1 in the column of the original amino acid | `ref_R` = **1**, other 19 = 0 |
| `alt_A` … `alt_Y` (one-hot) | 20 | 1 in the column of the new amino acid | `alt_H` = **1**, other 19 = 0 |
| **Total** | **53** | | |

**One-hot encoding** is the standard way to give a category (which of 20 amino acids) to a model:
20 columns per letter, exactly one of them set to 1. A single number such as R = 15, H = 7 would invent a false
ordering ("R > H"), which one-hot avoids.

---

## 7. ESM-2 → 4 scalar features + 16 PCA components

### 7.1 Input: the protein sequence, tokenised

```
sequence:  M  E  E  P  Q  S  D  P  S  V  E …  (393 letters, UniProt P04637)
tokens:  <cls> M  E  E  P  Q  S  D  P  S  V  E … <eos>
IDs:       0  20  9  9 14 16  8 13 14  8  7  9 …   2           → tensor of shape (1, 395)
```

Token index *i* = residue *i*, because index 0 is `<cls>`.
Proteins longer than 1,022 residues are cut into overlapping windows (§6.4 of `STUDY_GUIDE.md`).

### 7.2 One forward pass → two outputs

| Output | Shape for TP53 | Content |
|---|---|---|
| `logits` | (1, 395, 33) | At each position, a score for each of the 33 vocabulary tokens |
| `hidden_states[-1]` | (1, 395, 1280) | At each position, the 1,280-number **embedding** from the last layer (layer 33) |

### 7.3 The 4 scalar features (position 175, ref R, alt H)

```python
lp = log_softmax(logits[0, 175, :])[ids_of_the_20_amino_acids]   # 20 log-probabilities
esm_logp_ref = lp["R"]                      = -0.000839
esm_logp_alt = lp["H"]                      = -9.129745
esm_llr      = lp["H"] - lp["R"]            = -9.128906     # log-likelihood ratio
p            = exp(lp) / sum(exp(lp))       # probabilities over 20 AAs: R 0.9992, K 0.0003, …, H 0.0001
esm_entropy  = -Σ p · log p                 = 0.008587      # near 0: only R fits here
```

### 7.4 The 16 PCA components

1. **Store:** the 1,280-number embedding at position 175 is saved (fp16) in `esm2_embeddings.npy`. TP53 R175H starts `[0.227, 0.078, 0.098, −0.093, −0.444, 0.218, −0.224, 0.091, …]`.
2. **Fit PCA at training time** (`VariantModel.fit` in `common.py`). PCA is fitted on the embeddings of **training variants only** (the 85% fit part of ClinVar 2023), finding the 16 directions of greatest variation. These 16 directions explain 42.1% of the embedding's variance.
3. **Transform** every variant, train or test:

```
esm_pc_k = (embedding − training_mean) · component_k        for k = 1 … 16
```

For TP53 R175H this gives:

```
esm_pc1..16 = [1.390, 1.212, 0.163, 3.708, −2.000, 0.684, 0.179, −0.415,
               −0.116, 0.435, −0.906, 0.501, 0.215, 0.234, −0.245, −0.636]
```

**Why PCA and not all 1,280 numbers?**
- 1,280 extra columns would swamp the 94 biological features.
- They would slow training and invite overfitting.
- 16 compact components keep the main structure.

**Why fit only on training data?** Fitting PCA on test embeddings would leak test information into the features.

**Why the PCs are not in `variants.parquet`:** they depend on which rows were used for training, so they are computed inside the model at train and predict time, not stored once.

---

## 8. Assembling the final row and feeding XGBoost

`VariantModel._X()` builds the input matrix by placing **94 stored columns** (8 + 9 + 17 + 3 + 53 + 4) side by side with **16 PCA columns** computed on the fly. That gives **110 columns**, always in the same order.

### 8.1 The complete 110-feature row for TP53 R175H

**Population (8):**

| Feature | Value |
|---|---|
| af_ex | −5.389 |
| af_ge | −5.176 |
| af_ex_popmax | −5.050 |
| af_ge_popmax | −4.830 |
| hom_ex | 0 |
| hom_ge | 0 |
| in_gnomad_ex | 1 |
| in_gnomad_ge | 1 |

**Conservation (9):**

| Feature | Value |
|---|---|
| phylop_17 | 0.599 |
| phylop_100 | 6.163 |
| phylop_470 | 7.693 |
| phastcons_17 | 0.919 |
| phastcons_100 | 1.000 |
| phastcons_470 | 1.000 |
| gerp_91 | 5.480 |
| siphy | 17.077 |
| bstatistic | 434 |

**Protein context (17):**

| Feature | Value |
|---|---|
| rel_pos | 0.445 |
| log_prot_len | 2.594 |
| interpro_domain | 1 |
| dist_func_site | 1 |
| uni_domain | 0 |
| uni_active_site | 0 |
| uni_binding_site | 0 |
| uni_disulfide | 0 |
| uni_transmem | 0 |
| uni_signal | 0 |
| uni_mod_res | 0 |
| uni_zn_finger | 0 |
| uni_motif | 0 |
| uni_helix | 1 |
| uni_strand | 0 |
| uni_region | 1 |
| uni_compbias | 0 |

**Structure (3):**

| Feature | Value |
|---|---|
| af_plddt | 96.62 |
| af_plddt_win | 95.48 |
| af_contacts | 21 |

**Amino-acid properties (53):**

| Feature | Value |
|---|---|
| grantham | 28.82 |
| blosum62 | 0 |
| d_hydropathy | 1.3 |
| d_volume | −28 |
| d_polarity | −0.1 |
| d_charge | −0.9 |
| arom_change | 1 |
| ref_is_P, alt_is_P, ref_is_G, alt_is_G, ref_is_C, alt_is_C | all 0 |
| ref_A … ref_Y (20 columns) | `ref_R` = 1, the other 19 = 0 |
| alt_A … alt_Y (20 columns) | `alt_H` = 1, the other 19 = 0 |

**ESM-2 (4 scalars + 16 PCs):**

| Feature | Value |
|---|---|
| esm_llr | −9.129 |
| esm_logp_ref | −0.0008 |
| esm_logp_alt | −9.130 |
| esm_entropy | 0.0086 |
| esm_pc1 – esm_pc4 | 1.390, 1.212, 0.163, 3.708 |
| esm_pc5 – esm_pc8 | −2.000, 0.684, 0.179, −0.415 |
| esm_pc9 – esm_pc12 | −0.116, 0.435, −0.906, 0.501 |
| esm_pc13 – esm_pc16 | 0.215, 0.234, −0.245, −0.636 |

As a single vector:

```
X[TP53 R175H] = [ -5.389, -5.176, -5.050, -4.830, 0, 0, 1, 1,                  ← population (8)
                   0.599, 6.163, 7.693, 0.919, 1, 1, 5.48, 17.077, 434,        ← conservation (9)
                   0.445, 2.594, 1, 1, 0,0,0,0,0,0,0,0,0, 1, 0, 1, 0,           ← protein context (17)
                   96.62, 95.48, 21,                                            ← structure (3)
                   28.82, 0, 1.3, -28, -0.1, -0.9, 1, 0,0,0,0,0,0,              ← aa properties (13)
                   0,0, 0,0, 0,0, 0,0, 0,0, 0,0, 0,1, 0,0, 0,0, 0,0,            ← one-hot (ref,alt) pairs for A C D E F G H I K L
                   0,0, 0,0, 0,0, 0,0, 1,0, 0,0, 0,0, 0,0, 0,0, 0,0,            ← one-hot (ref,alt) pairs for M N P Q R S T V W Y  (= 40)
                  -9.129, -0.0008, -9.130, 0.0086,                              ← ESM scalars (4)
                   1.390, 1.212, 0.163, 3.708, -2.000, 0.684, 0.179, -0.415,    ← ESM PCs (16)
                  -0.116, 0.435, -0.906, 0.501, 0.215, 0.234, -0.245, -0.636 ]
                                                                    length = 110 floats
y[TP53 R175H] = 1   (Pathogenic, kept separately; never inside X)
```

(The one-hot columns are interleaved in the code as ref_A, alt_A, ref_C, alt_C, …: `alt_H` is column 63 and `ref_R` is column 78.)

### 8.2 What XGBoost does with it

```
X (1 × 110 floats) ──► 700 decision trees ──► sum of leaf values ──► sigmoid
                                                   raw probability = 0.99663
                    ──► isotonic calibrator (fitted on held-out genes)
                                                   calibrated P(pathogenic) = 0.99260  → PP3_Strong
```

**Handling `NaN`:** at every split, XGBoost learns a *default direction* for missing values during training.
- For example, a variant whose AlphaFold value is missing is sent left or right, whichever reduced the error most on training data.
- This is why we never need to fill in fake structure or ESM values.
- Logistic regression (Model B) cannot do this, so it uses median imputation plus "was-missing" indicator columns.

---

## 9. One-page summary

| Source | Raw form | Turned into numbers by | # features | Any text reaches XGBoost? |
|---|---|---|---|---|
| ClinVar | TSV text | exact string match → 0/1 label; regex → IDs | 0 (target only) | — |
| gnomAD | JSON numbers | pick + max + log10(x + 1e-7), log10(n + 1), presence flag | 8 | No |
| dbNSFP | JSON numbers + text | numbers pass through; InterPro text → present? 0/1 | 9 (+1) | No |
| UniProt | FASTA string + annotation text | parse "start..end" → in-range / at-site / bond-endpoint 0/1; distance; length | 17 (incl. InterPro flag) | No |
| AlphaFold | PDB fixed-width text | Cα coordinates → contact count; B-factor → pLDDT, window mean | 3 | No |
| ref/alt AA | 2 letters | lookup tables + 40-column one-hot | 53 | No |
| ESM-2 | sequence → tensors | log-softmax → 4 scalars; embedding → PCA(16, train-only) | 20 | No |
| **Total** | | | **110** | **Everything is numeric** |
