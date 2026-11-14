"""Step 3 - Protein-context features: UniProt canonical sequence/annotations + AlphaFold structure.

For each (gene, protein position, ref AA) the canonical Swiss-Prot isoform is located by gene
name and the reference residue is verified (`seq_match`). Variants whose residue does not match
the canonical isoform are kept but get NaN protein/structure/ESM features.
Outputs: data/interim/protein_features.parquet, data/interim/uniprot_seqs.json
"""
import gzip
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW, INTERIM = ROOT / "data/raw", ROOT / "data/interim"
AF_DIR = INTERIM / "alphafold"
AF_DIR.mkdir(parents=True, exist_ok=True)

# UniProt feature column -> (feature name, kind). "range": residue inside start..end,
# "site": residue equals a listed position, "pair": residue is an endpoint (disulfide bonds)
FT = {
    "Domain [FT]": ("uni_domain", "range"), "Active site": ("uni_active_site", "site"),
    "Binding site": ("uni_binding_site", "site"), "Disulfide bond": ("uni_disulfide", "pair"),
    "Transmembrane": ("uni_transmem", "range"), "Signal peptide": ("uni_signal", "range"),
    "Modified residue": ("uni_mod_res", "site"), "Zinc finger": ("uni_zn_finger", "range"),
    "Motif": ("uni_motif", "range"), "Helix": ("uni_helix", "range"), "Beta strand": ("uni_strand", "range"),
    "Region": ("uni_region", "range"), "Compositional bias": ("uni_compbias", "range"),
}
SPAN = re.compile(r"^[A-Z_]+ (?:[<?]?)(\d+)(?:\.\.(?:[>?]?)(\d+))?", re.M)


def load_uniprot():
    seqs, gene2acc = {}, {}
    acc, buf, gene = None, [], None
    with gzip.open(RAW / "uniprot_human_sprot.fasta.gz", "rt") as fh:
        for line in list(fh) + [">"]:
            if line.startswith(">"):
                if acc:
                    seqs[acc] = "".join(buf)
                    if gene:
                        gene2acc.setdefault(gene, acc)
                if line.strip() == ">":
                    break
                acc = line.split("|")[1]
                m = re.search(r" GN=(\S+)", line)
                gene, buf = (m.group(1) if m else None), []
            else:
                buf.append(line.strip())
    ft = pd.read_csv(RAW / "uniprot_human_features.tsv.gz", sep="\t", dtype=str).fillna("")
    # synonyms as fallback mapping (old ClinVar gene symbols)
    for _, r in ft.iterrows():
        for syn in r["Gene Names (synonym)"].split():
            gene2acc.setdefault(syn, r.Entry)
    spans = {}
    for _, r in ft.iterrows():
        d = {}
        for col, (name, kind) in FT.items():
            items = []
            for entry in re.split(r";\s(?=[A-Z_]+ [<?]?\d)", r[col]):
                m = SPAN.match(entry.strip())
                if m:
                    s, e = int(m.group(1)), int(m.group(2) or m.group(1))
                    items.append((s, e))
            d[name] = (kind, items)
        spans[r.Entry] = d
    return seqs, gene2acc, spans


def fetch_af(acc):
    out = AF_DIR / f"{acc}.npz"
    if out.exists():
        return
    for v in (6, 4):
        r = None
        for attempt in range(6):  # retry throttling / network errors; only a 404 means "no model"
            try:
                r = requests.get(f"https://alphafold.ebi.ac.uk/files/AF-{acc}-F1-model_v{v}.pdb", timeout=120)
                if r.ok or r.status_code == 404:
                    break
            except requests.RequestException:
                pass
            time.sleep(5 * 2 ** attempt)
        if r is None or not (r.ok or r.status_code == 404):
            return  # transient failure: leave uncached so a rerun retries it
        if r.ok:
            res, pl, xyz = [], [], []
            for line in r.text.splitlines():
                if line.startswith("ATOM") and line[12:16].strip() == "CA":
                    res.append(int(line[22:26])); pl.append(float(line[60:66]))
                    xyz.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
            np.savez_compressed(out, res=np.array(res), plddt=np.array(pl), xyz=np.array(xyz, dtype=np.float32))
            return
    np.savez_compressed(out, res=np.array([]), plddt=np.array([]), xyz=np.zeros((0, 3), np.float32))


def structure_feats(acc, positions):
    if not (AF_DIR / f"{acc}.npz").exists():
        return {p: (np.nan, np.nan, np.nan) for p in positions}
    z = np.load(AF_DIR / f"{acc}.npz")
    if len(z["res"]) == 0:
        return {p: (np.nan, np.nan, np.nan) for p in positions}
    idx = {r: i for i, r in enumerate(z["res"])}
    xyz, pl = z["xyz"], z["plddt"]
    out = {}
    for p in positions:
        i = idx.get(p)
        if i is None:
            out[p] = (np.nan, np.nan, np.nan)
            continue
        d = np.linalg.norm(xyz - xyz[i], axis=1)
        seq_far = np.abs(np.arange(len(xyz)) - i) > 2
        contacts = int(((d < 10) & seq_far).sum())  # CA contact density ~ burial
        win = pl[max(0, i - 5): i + 6].mean()
        out[p] = (pl[i], win, contacts)
    return out


def main():
    seqs, gene2acc, spans = load_uniprot()
    cv = pd.concat([pd.read_parquet(p) for p in INTERIM.glob("clinvar_*.parquet")]).drop_duplicates("key").reset_index(drop=True)
    v = cv[["key", "gene", "aa_ref", "aa_pos", "aa_alt"]].copy()
    v["uniprot"] = v.gene.map(gene2acc)
    v["prot_len"] = v.uniprot.map(lambda a: len(seqs[a]) if isinstance(a, str) and a in seqs else np.nan)
    v["seq_match"] = [int(isinstance(a, str) and a in seqs and 0 < p <= len(seqs[a]) and seqs[a][p - 1] == r)
                      for a, p, r in zip(v.uniprot, v.aa_pos, v.aa_ref)]
    print(f"variants: {len(v):,} | mapped to UniProt: {v.uniprot.notna().mean():.1%} | ref AA matches: {v.seq_match.mean():.1%}")

    ok = v.seq_match == 1
    v["rel_pos"] = np.where(ok, v.aa_pos / v.prot_len, np.nan)
    for name, _ in FT.values():
        v[name] = np.nan
    v["dist_func_site"] = np.nan
    for acc, grp in v[ok].groupby("uniprot"):
        sp = spans.get(acc, {})
        for name, (kind, items) in sp.items():
            pos = grp.aa_pos.values
            if kind == "range":
                hit = np.array([any(s <= p <= e for s, e in items) for p in pos])
            elif kind == "pair":
                ends = {x for s, e in items for x in (s, e)}
                hit = np.array([p in ends for p in pos])
            else:
                sites = {x for s, e in items for x in range(s, e + 1)}
                hit = np.array([p in sites for p in pos])
            v.loc[grp.index, name] = hit.astype(float)
        func = sorted({x for nm in ("uni_active_site", "uni_binding_site") for s, e in sp.get(nm, ("", []))[1] for x in range(s, e + 1)})
        if func:
            f = np.array(func)
            v.loc[grp.index, "dist_func_site"] = [min(np.abs(f - p).min(), 50) for p in grp.aa_pos]
        else:
            v.loc[grp.index, "dist_func_site"] = 50.0

    accs = sorted(v.loc[ok, "uniprot"].unique())
    print(f"fetching AlphaFold models for {len(accs):,} proteins ...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(fetch_af, accs))
    v["af_plddt"] = v["af_plddt_win"] = v["af_contacts"] = np.nan
    for acc, grp in v[ok].groupby("uniprot"):
        sf = structure_feats(acc, grp.aa_pos.unique())
        v.loc[grp.index, ["af_plddt", "af_plddt_win", "af_contacts"]] = [sf[p] for p in grp.aa_pos]
    print(f"AlphaFold coverage: {v.af_plddt.notna().mean():.1%}")

    v.drop(columns=["gene", "aa_ref", "aa_pos", "aa_alt"]).to_parquet(INTERIM / "protein_features.parquet", index=False)
    json.dump({a: seqs[a] for a in accs}, open(INTERIM / "uniprot_seqs.json", "w"))


if __name__ == "__main__":
    main()
