"""Variant -> calibrated P(pathogenic) + SHAP explanation + PP3/BP4 evidence level.

Usage:
    python src/predict.py "chr17:g.7675088C>T"
    python src/predict.py "chr17:g.7675088C>T" --gene TP53 --protein R175H
Any GRCh38 missense SNV can be scored: features are computed live (MyVariant.info, UniProt,
AlphaFold, ESM-2). Research use only - not a clinical classification.
"""
import argparse
import importlib
import json
import re
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests
import shap

sys.path.insert(0, str(Path(__file__).parent))
ann_mod = importlib.import_module("02_annotate_myvariant")
prot_mod = importlib.import_module("03_protein_features")
ds_mod = importlib.import_module("05_build_dataset")
ROOT = Path(__file__).resolve().parents[1]


def features_for(hgvs, gene=None, protein=None):
    hit = requests.get(f"{ann_mod.URL}/{hgvs}", params={"fields": ann_mod.FIELDS + ",dbnsfp.hgvsp,dbnsfp.genename",
                                                         "assembly": "hg38"}, timeout=60).json()
    hit["query"] = hgvs
    row = ann_mod.flatten(hit)
    db = hit.get("dbnsfp", {}) or {}
    gene = gene or row.get("mv_gene")
    if protein is None:  # take the first 1-letter HGVS.p from dbNSFP
        hp = db.get("hgvsp"); hp = hp if isinstance(hp, list) else [hp]
        protein = next((h[2:] for h in hp if isinstance(h, str) and re.fullmatch(r"p\.[A-Z]\d+[A-Z]", h)), None)
    m = re.fullmatch(r"([A-Z])(\d+)([A-Z])", protein or "")
    if not (gene and m):
        sys.exit("Could not resolve gene / protein change; pass --gene and --protein (e.g. R175H).")
    ref, pos, alt = m.group(1), int(m.group(2)), m.group(3)

    seqs, gene2acc, spans = prot_mod.load_uniprot()
    acc = gene2acc.get(gene)
    seq = seqs.get(acc, "")
    if not (acc and 0 < pos <= len(seq) and seq[pos - 1] == ref):
        print(f"warning: {gene} {protein} does not match the canonical UniProt isoform; protein features left empty")
        acc = None
    d = pd.DataFrame([{**row, "gene": gene, "aa_ref": ref, "aa_pos": pos, "aa_alt": alt}])

    if acc:
        L = len(seq)
        d["rel_pos"], d["log_prot_len"] = pos / L, np.log10(L)
        for name, (kind, items) in spans.get(acc, {}).items():
            if kind == "range":
                d[name] = float(any(s <= pos <= e for s, e in items))
            elif kind == "pair":
                d[name] = float(pos in {x for s, e in items for x in (s, e)})
            else:
                d[name] = float(pos in {x for s, e in items for x in range(s, e + 1)})
        func = [x for nm in ("uni_active_site", "uni_binding_site") for s, e in spans.get(acc, {}).get(nm, ("", []))[1] for x in range(s, e + 1)]
        d["dist_func_site"] = min(min(abs(f - pos) for f in func), 50) if func else 50.0
        prot_mod.fetch_af(acc)
        d[["af_plddt", "af_plddt_win", "af_contacts"]] = prot_mod.structure_feats(acc, [pos])[pos]

        import torch
        from transformers import AutoTokenizer, EsmForMaskedLM
        esm_mod = importlib.import_module("04_esm2_features")
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        tok = AutoTokenizer.from_pretrained(esm_mod.MODEL)
        model = EsmForMaskedLM.from_pretrained(esm_mod.MODEL).to(dev).eval()
        aa_ids = [tok.convert_tokens_to_ids(a) for a in esm_mod.AAS]
        lp, emb = esm_mod.score_protein(seq, [pos], tok, model, aa_ids, dev)[pos]
        A = esm_mod.AAS
        prob = np.exp(lp); prob /= prob.sum()
        d["esm_llr"], d["esm_logp_ref"], d["esm_logp_alt"] = lp[A.index(alt)] - lp[A.index(ref)], lp[A.index(ref)], lp[A.index(alt)]
        d["esm_entropy"] = float(-(prob * np.log(prob + 1e-12)).sum())
    else:
        emb = None
    d = pd.concat([d, ds_mod.aa_features(d.aa_ref, d.aa_alt)], axis=1)
    for c in ["af_ex", "af_ge", "af_ex_popmax", "af_ge_popmax"]:
        d[c] = np.log10(d[c].fillna(0) + 1e-7)
    for c in ["hom_ex", "hom_ge"]:
        d[c] = np.log10(d[c].fillna(0) + 1)
    return d, emb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hgvs", help='GRCh38 genomic HGVS, e.g. "chr17:g.7675088C>T"')
    ap.add_argument("--gene"); ap.add_argument("--protein", help="1-letter change, e.g. R175H")
    ap.add_argument("--model", default="D_XGB_ESM_final", help="file stem in results/models/ (e.g. D_XGB_ESM_temporal)")
    a = ap.parse_args()

    bundle = joblib.load(ROOT / f"results/models/{a.model}.joblib")
    bundle["clf"].set_params(device="cpu")  # single-variant input is on the CPU; avoids a device-mismatch warning
    d, emb = features_for(a.hgvs, a.gene, a.protein)
    for f in bundle["feats"]:
        if f not in d:
            d[f] = np.nan
    X = d[bundle["feats"]].astype(float).values
    pcs = bundle["pca"].transform(emb.astype(np.float32)[None]) if emb is not None else np.full((1, bundle["n_pc"]), np.nan)
    X = np.hstack([X, pcs])
    raw = bundle["clf"].predict_proba(X)[:, 1]
    p = float(bundle["iso"].predict(raw)[0])

    level = "none (indeterminate)"
    th_path = ROOT / "results/tables/pp3_bp4_modelD_thresholds.csv"
    if th_path.exists():
        th = pd.read_csv(th_path, index_col=0)
        for k in ("Supporting", "Moderate", "Strong", "Very strong"):
            if pd.notna(th.loc[k, "PP3"]) and p >= th.loc[k, "PP3"]:
                level = f"PP3_{k}"
            if pd.notna(th.loc[k, "BP4"]) and p <= th.loc[k, "BP4"]:
                level = f"BP4_{k}"

    sv = shap.TreeExplainer(bundle["clf"]).shap_values(X)[0]
    top = pd.Series(sv, index=bundle["names"]).sort_values(key=np.abs, ascending=False).head(8)
    vals = pd.Series(X[0], index=bundle["names"])
    print(f"\nVariant: {a.hgvs}  {d.gene[0]} p.{d.aa_ref[0]}{d.aa_pos[0]}{d.aa_alt[0]}")
    print(f"Calibrated P(pathogenic): {p:.3f}")
    print(f"ClinGen-style computational evidence: {level}")
    print("Top contributing features (SHAP, log-odds):")
    for f, v in top.items():
        print(f"  {'+' if v > 0 else '-'} {f:<18} value={vals[f]:9.3f}  shap={v:+.3f}")
    print("\nResearch use only - not a clinical variant classification.")


if __name__ == "__main__":
    main()
