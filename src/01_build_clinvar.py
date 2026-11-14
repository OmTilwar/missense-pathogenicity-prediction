"""Step 1 - Build missense label sets from two ClinVar releases.

Output: data/interim/clinvar_<release>.parquet with one row per GRCh38 missense SNV:
    key (chr-pos-ref-alt), hgvs (myvariant id), gene, protein ref/pos/alt, label, review status.
ClinVar is used ONLY to create the target label.
"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, INTERIM = ROOT / "data/raw", ROOT / "data/interim"
INTERIM.mkdir(parents=True, exist_ok=True)

POS_LABELS = {"Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic"}
NEG_LABELS = {"Benign", "Likely benign", "Benign/Likely benign"}
# >= 1 star; "conflicting" statuses are deliberately excluded
GOOD_REVIEW = {
    "criteria provided, single submitter": 1,
    "criteria provided, multiple submitters, no conflicts": 2,
    "reviewed by expert panel": 3,
    "practice guideline": 4,
}
AA3 = {"Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C", "Gln": "Q", "Glu": "E", "Gly": "G",
       "His": "H", "Ile": "I", "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P", "Ser": "S",
       "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V"}
MISSENSE = re.compile(r"^(N[MC]_\d+\.\d+)\(([^)]+)\):c\.[^ ]+ \(p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)$")
CHROMS = {str(c) for c in range(1, 23)} | {"X", "Y"}


def build(release: str) -> pd.DataFrame:
    path = RAW / f"variant_summary_{release}.txt.gz"
    sig_col = "ClinicalSignificance"
    header = pd.read_csv(path, sep="\t", nrows=0).columns
    if sig_col not in header:  # newer releases renamed it
        sig_col = next(c for c in header if c.startswith("GermlineClassification") or c == "ClinicalSignificance")
    cols = ["Type", "Name", "GeneSymbol", sig_col, "ReviewStatus", "Assembly", "Chromosome",
            "PositionVCF", "ReferenceAlleleVCF", "AlternateAlleleVCF", "VariationID", "LastEvaluated"]
    keep = []
    for chunk in pd.read_csv(path, sep="\t", usecols=cols, dtype=str, chunksize=500_000, low_memory=False):
        c = chunk[(chunk.Assembly == "GRCh38") & (chunk.Type == "single nucleotide variant")]
        c = c[c[sig_col].isin(POS_LABELS | NEG_LABELS) & c.ReviewStatus.isin(GOOD_REVIEW)]
        keep.append(c)
    df = pd.concat(keep).rename(columns={sig_col: "clinsig"})

    m = df.Name.str.extract(MISSENSE)
    m.columns = ["transcript", "gene", "ref3", "prot_pos", "alt3"]
    df = pd.concat([df, m], axis=1).dropna(subset=["ref3"])
    df = df[df.ref3.isin(AA3) & df.alt3.isin(AA3) & (df.ref3 != df.alt3)]
    df = df[df.Chromosome.isin(CHROMS) & df.ReferenceAlleleVCF.str.fullmatch("[ACGT]")
            & df.AlternateAlleleVCF.str.fullmatch("[ACGT]")]

    out = pd.DataFrame({
        "key": df.Chromosome + "-" + df.PositionVCF + "-" + df.ReferenceAlleleVCF + "-" + df.AlternateAlleleVCF,
        "hgvs": "chr" + df.Chromosome + ":g." + df.PositionVCF + df.ReferenceAlleleVCF + ">" + df.AlternateAlleleVCF,
        "gene": df.gene.values,
        "transcript": df.transcript.values,
        "aa_ref": df.ref3.map(AA3).values,
        "aa_pos": df.prot_pos.astype(int).values,
        "aa_alt": df.alt3.map(AA3).values,
        "clinsig": df.clinsig.values,
        "label": df.clinsig.isin(POS_LABELS).astype(int).values,
        "review_stars": df.ReviewStatus.map(GOOD_REVIEW).values,
        "variation_id": df.VariationID.values,
        "last_evaluated": df.LastEvaluated.values,
    })
    # a variant listed with contradicting labels (rare) is dropped entirely
    n_lab = out.groupby("key").label.transform("nunique")
    out = out[n_lab == 1].drop_duplicates("key").reset_index(drop=True)
    out.to_parquet(INTERIM / f"clinvar_{release}.parquet", index=False)
    print(f"{release}: {len(out):,} missense variants | P/LP={out.label.sum():,} "
          f"B/LB={(1 - out.label).sum():,} | genes={out.gene.nunique():,}")
    return out


if __name__ == "__main__":
    for rel in sys.argv[1:] or ["2023-01", "2026-09"]:
        build(rel)
