# Leakage-Controlled ML for Predicting Pathogenic Missense Variants

B.Tech major project (IIIT Nagpur, 2026–27) by Piyush Gupta, Om Tilwar and Varun Tripathi.
Guide: Dr. Nikhil Dhengre.

- `PLAN.md` is the full execution plan.
- `papers/LITERATURE_REVIEW.md` covers the literature and what we replicate.
- `results/REPORT.md` has the findings.

## Layout
```
data/raw/         ClinVar 2023-01 & 2026-09 variant_summary, UniProt FASTA + feature TSV
data/interim/     per-step outputs (labels, annotations, AlphaFold cache, ESM-2 scores)
data/processed/   variants.parquet  (final modelling table) + feature_groups.json
papers/           downloaded papers + literature review
src/              pipeline (run in order)
results/          tables/, figures/, trained model, REPORT.md
```

## Run the web app
```bash
pip install -r requirements.txt
streamlit run app.py                 # opens http://localhost:8501
```
Windows with an NVIDIA GPU: install the CUDA build of PyTorch from pytorch.org before the line above.
The PDF report button needs the pango library (see requirements.txt); without it, HTML and Markdown reports still work.

## Reproduce
```bash
pip install -r requirements.txt   # Python 3.11; see requirements.txt for Windows/macOS/Linux notes
# raw downloads (ClinVar + UniProt) – see PLAN.md Phase 1 for URLs
python src/01_build_clinvar.py           # labels from ClinVar 2023-01 and 2026-09
python src/02_annotate_myvariant.py      # gnomAD + dbNSFP features via MyVariant.info (resumable)
python src/03_protein_features.py        # UniProt annotations + AlphaFold pLDDT / burial
python src/04_esm2_features.py           # ESM-2 650M scores + embeddings (GPU, ~6 GB VRAM OK)
python src/05_build_dataset.py           # merge + amino-acid properties + evaluation subsets
python src/06_train_eval.py              # experiments A–D, 3 split levels, ablation, SHAP
python src/06b_label_shift.py            # EM label-shift correction of calibration over time
python src/07_pp3_bp4_thresholds.py      # ClinGen PP3/BP4 calibration (Pejaver 2022 replication)
python src/08_save_models.py             # train + save all models to results/models/
python src/09_dataset_analysis.py        # dataset statistics and EDA figures
python src/10_pure_vs_mixed_genes.py     # Grimm 2015 pure-vs-mixed gene analysis
python src/predict.py "chr17:g.7675088C>T"   # score any GRCh38 missense SNV
```

## Leakage rules enforced in code
1. ClinVar is used only as the label. Its classifications are never model inputs.
2. Existing predictors (`bl_*` columns) are only comparison baselines and are never features.
3. The time-travel test contains only variants first labelled after the 2023-01 release.
4. The gene-disjoint CV never places one gene in both train and test.
5. ESM-embedding PCA and isotonic calibration are fit on training data only.
   Calibration uses a gene-disjoint hold-out.

*Research use only. This is not a clinical diagnostic or a final variant classification.*
