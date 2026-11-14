"""Step 5 - Merge labels + features into one modelling table and define evaluation subsets.

Output: data/processed/variants.parquet (one row per variant) and data/processed/feature_groups.json
Columns of note:
    label_old / label_new  ClinVar label in 2023-01 / 2026-09 release (NaN if not confidently labelled)
    temporal_test          labelled in 2026-09 but NOT labelled in 2023-01  (time-travel test set)
    temporal_newgene       temporal_test AND gene had no labelled variant in 2023-01
    rare                   max gnomAD AF < 1e-4 (or absent)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from Bio.Align import substitution_matrices

ROOT = Path(__file__).resolve().parents[1]
INTERIM, PROC = ROOT / "data/interim", ROOT / "data/processed"
PROC.mkdir(parents=True, exist_ok=True)
OLD, NEW = "2023-01", "2026-09"

# Grantham (1974) composition, polarity, volume
GRANTHAM_CPV = {"S": (1.42, 9.2, 32), "R": (0.65, 10.5, 124), "L": (0, 4.9, 111), "P": (0.39, 8.0, 32.5),
                "T": (0.71, 8.6, 61), "A": (0, 8.1, 31), "V": (0, 5.9, 84), "G": (0.74, 9.0, 3),
                "I": (0, 5.2, 111), "F": (0, 5.2, 132), "Y": (0.20, 6.2, 136), "C": (2.75, 5.5, 55),
                "H": (0.58, 10.4, 96), "Q": (0.89, 10.5, 85), "N": (1.33, 11.6, 56), "K": (0.33, 11.3, 119),
                "D": (1.38, 13.0, 54), "E": (0.92, 12.3, 83), "M": (0, 5.7, 105), "W": (0.13, 5.4, 170)}
KD = {"A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
      "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2}
CHARGE = {"D": -1, "E": -1, "K": 1, "R": 1, "H": 0.1}
AROM = set("FWYH")
AAS = "ACDEFGHIKLMNPQRSTVWY"
BLOSUM = substitution_matrices.load("BLOSUM62")


def grantham(a, b):
    (c1, p1, v1), (c2, p2, v2) = GRANTHAM_CPV[a], GRANTHAM_CPV[b]
    return 50.723 * np.sqrt(1.833 * (c1 - c2) ** 2 + 0.1018 * (p1 - p2) ** 2 + 0.000399 * (v1 - v2) ** 2)


def aa_features(ref, alt):
    f = pd.DataFrame({
        "grantham": [grantham(r, a) for r, a in zip(ref, alt)],
        "blosum62": [BLOSUM[r][a] for r, a in zip(ref, alt)],
        "d_hydropathy": [KD[a] - KD[r] for r, a in zip(ref, alt)],
        "d_volume": [GRANTHAM_CPV[a][2] - GRANTHAM_CPV[r][2] for r, a in zip(ref, alt)],
        "d_polarity": [GRANTHAM_CPV[a][1] - GRANTHAM_CPV[r][1] for r, a in zip(ref, alt)],
        "d_charge": [CHARGE.get(a, 0) - CHARGE.get(r, 0) for r, a in zip(ref, alt)],
        "arom_change": [int((r in AROM) != (a in AROM)) for r, a in zip(ref, alt)],
    })
    for x in "PGC":
        f[f"ref_is_{x}"] = (ref == x).astype(int).values
        f[f"alt_is_{x}"] = (alt == x).astype(int).values
    for x in AAS:
        f[f"ref_{x}"] = (ref == x).astype(int).values
        f[f"alt_{x}"] = (alt == x).astype(int).values
    return f


def main():
    old = pd.read_parquet(INTERIM / f"clinvar_{OLD}.parquet")
    new = pd.read_parquet(INTERIM / f"clinvar_{NEW}.parquet")
    base = pd.concat([new, old]).drop_duplicates("key")[["key", "hgvs", "gene", "aa_ref", "aa_pos", "aa_alt"]]
    base = base.merge(old[["key", "label", "review_stars"]].rename(columns={"label": "label_old", "review_stars": "stars_old"}), on="key", how="left")
    base = base.merge(new[["key", "label", "review_stars"]].rename(columns={"label": "label_new", "review_stars": "stars_new"}), on="key", how="left")

    ann = pd.read_parquet(INTERIM / "annotations.parquet")
    prot = pd.read_parquet(INTERIM / "protein_features.parquet")
    esm = pd.read_parquet(INTERIM / "esm2_scores.parquet")
    df = base.merge(ann, on="hgvs", how="left").merge(prot, on="key", how="left").merge(esm, on="key", how="left")
    df = pd.concat([df.reset_index(drop=True), aa_features(df.aa_ref, df.aa_alt)], axis=1)

    # population-frequency transforms: absent from gnomAD -> AF 0
    for c in ["af_ex", "af_ge", "af_ex_popmax", "af_ge_popmax"]:
        df[c] = np.log10(df[c].fillna(0) + 1e-7)
    for c in ["hom_ex", "hom_ge"]:
        df[c] = np.log10(df[c].fillna(0) + 1)
    df["log_prot_len"] = np.log10(df.prot_len)
    max_af = 10 ** df[["af_ex", "af_ge", "af_ex_popmax", "af_ge_popmax"]].max(axis=1) - 1e-7

    old_genes = set(old.gene)
    df["temporal_test"] = (df.label_new.notna() & df.label_old.isna()).astype(int)
    df["temporal_newgene"] = (df.temporal_test.eq(1) & ~df.gene.isin(old_genes)).astype(int)
    df["rare"] = (max_af < 1e-4).astype(int)
    df["reclassified"] = (df.label_old.notna() & df.label_new.notna() & (df.label_old != df.label_new)).astype(int)

    groups = {
        "population": ["af_ex", "af_ge", "af_ex_popmax", "af_ge_popmax", "hom_ex", "hom_ge", "in_gnomad_ex", "in_gnomad_ge"],
        "conservation": ["phylop_17", "phylop_100", "phylop_470", "phastcons_17", "phastcons_100", "phastcons_470",
                         "gerp_91", "siphy", "bstatistic"],
        "protein_context": ["rel_pos", "log_prot_len", "interpro_domain", "dist_func_site"] + [c for c in df if c.startswith("uni_")],
        "structure": ["af_plddt", "af_plddt_win", "af_contacts"],
        "aa_properties": list(aa_features(pd.Series(["A"]), pd.Series(["C"])).columns),
        "esm2": ["esm_llr", "esm_logp_ref", "esm_logp_alt", "esm_entropy"],  # + esm_pc* added at train time
    }
    json.dump(groups, open(PROC / "feature_groups.json", "w"), indent=1)
    df.to_parquet(PROC / "variants.parquet", index=False)

    print(f"total variants: {len(df):,}")
    print(f"labelled {OLD}: {df.label_old.notna().sum():,}  | labelled {NEW}: {df.label_new.notna().sum():,}")
    t = df[df.temporal_test == 1]
    print(f"time-travel test: {len(t):,} (P/LP {int(t.label_new.sum()):,}) | in new genes: {t.temporal_newgene.sum():,} | rare: {t.rare.sum():,}")
    print(f"reclassified P<->B between releases: {df.reclassified.sum():,}")
    print(f"coverage: myvariant {df.mv_found.mean():.1%}, phyloP {df.phylop_100.notna().mean():.1%}, "
          f"AlphaFold {df.af_plddt.notna().mean():.1%}, ESM-2 {df.esm_llr.notna().mean():.1%}")


if __name__ == "__main__":
    main()
