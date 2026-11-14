"""Step 2 - Annotate every ClinVar missense variant with gnomAD + dbNSFP fields via MyVariant.info.

Raw responses are cached in data/interim/myvariant_cache.jsonl (resumable), then flattened to
data/interim/annotations.parquet. Baseline predictor scores are stored with a `bl_` prefix and
are NEVER used as model features.
"""
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data/interim"
CACHE = INTERIM / "myvariant_cache.jsonl"
URL = "https://myvariant.info/v1/variant"
FIELDS = ",".join([
    "gnomad_exome.af", "gnomad_exome.hom", "gnomad_genome.af", "gnomad_genome.hom",
    "dbnsfp.phylop", "dbnsfp.phastcons", "dbnsfp.gerp++", "dbnsfp.gerp", "dbnsfp.siphy_29way.logodds_score",
    "dbnsfp.bstatistic.score", "dbnsfp.interpro.domain", "dbnsfp.genename", "dbnsfp.aa.ref", "dbnsfp.aa.alt",
    # comparison baselines (never features)
    "dbnsfp.alphamissense.score", "dbnsfp.revel.score", "dbnsfp.esm1b.score", "dbnsfp.cadd.phred",
    "dbnsfp.clinpred.score", "dbnsfp.metarnn.score", "dbnsfp.primateai.score", "dbnsfp.varity.r.score",
])
BATCH = 1000


def fetch(ids):
    """Returns hits, or [] after repeated failures (the batch is retried on the next run)."""
    for attempt in range(8):
        try:
            r = requests.post(URL, data={"ids": ",".join(ids), "fields": FIELDS, "assembly": "hg38"}, timeout=600)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            time.sleep(min(10 * 2 ** attempt, 300))
    print("  batch failed; rerun the script to retry it", flush=True)
    return []


def download(hgvs_ids):
    done = set()
    if CACHE.exists():
        with open(CACHE) as fh:
            done = {json.loads(line)["query"] for line in fh}
    todo = [h for h in hgvs_ids if h not in done]
    print(f"{len(done):,} cached, {len(todo):,} to query")
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    with open(CACHE, "a") as out, ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(fetch, b) for b in batches]
        for n, fut in enumerate(as_completed(futs), 1):
            for hit in fut.result():
                out.write(json.dumps(hit) + "\n")
            out.flush()
            if n % 10 == 0:
                print(f"  {n}/{len(batches)} batches", flush=True)


def _num(x, agg=max):
    """dbNSFP returns scalars or per-transcript lists (with None/'.'); reduce to one float."""
    if x is None:
        return math.nan
    vals = x if isinstance(x, list) else [x]
    vals = [float(v) for v in vals if isinstance(v, (int, float))]
    return agg(vals) if vals else math.nan


def _get(d, *path):
    for p in path:
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def flatten(hit):
    db = hit.get("dbnsfp", {}) or {}
    if isinstance(db, list):  # rare multi-record hits
        db = db[0]
    row = {"hgvs": hit["query"], "mv_found": int(not hit.get("notfound", False))}
    for src in ("gnomad_exome", "gnomad_genome"):
        g = hit.get(src)
        g = g[0] if isinstance(g, list) else g
        af = _get(g, "af") or {}
        tag = "ex" if src.endswith("exome") else "ge"
        row[f"af_{tag}"] = _num(af.get("af"))
        pops = [v for k, v in af.items() if k.count("_") == 1 and k not in ("af_female", "af_male")
                and isinstance(v, (int, float))]
        row[f"af_{tag}_popmax"] = max(pops) if pops else math.nan
        hom = _get(g, "hom")
        row[f"hom_{tag}"] = _num(hom.get("hom") if isinstance(hom, dict) else hom)
        row[f"in_gnomad_{tag}"] = int(g is not None)
    for k in ("17way_primate", "100way_vertebrate", "470way_mammalian"):
        row[f"phylop_{k.split('way')[0]}"] = _num(_get(db, "phylop", k, "score"))
        row[f"phastcons_{k.split('way')[0]}"] = _num(_get(db, "phastcons", k, "score"))
    row["gerp_rs"] = _num(_get(db, "gerp++", "rs"))
    row["gerp_91"] = _num(_get(db, "gerp", "91_mammals", "score"))
    row["siphy"] = _num(_get(db, "siphy_29way", "logodds_score"))
    row["bstatistic"] = _num(_get(db, "bstatistic", "score"))
    dom = _get(db, "interpro", "domain")
    dom = dom if isinstance(dom, list) else [dom]
    row["interpro_domain"] = int(any(isinstance(d, str) and d.strip(". |") for d in dom))
    row["mv_gene"] = (db.get("genename")[0] if isinstance(db.get("genename"), list) else db.get("genename"))
    # baselines
    row["bl_alphamissense"] = _num(_get(db, "alphamissense", "score"))
    row["bl_revel"] = _num(_get(db, "revel", "score"))
    row["bl_esm1b"] = -_num(_get(db, "esm1b", "score"), agg=min)  # negate: higher = more damaging
    row["bl_cadd"] = _num(_get(db, "cadd", "phred"))
    row["bl_primateai"] = _num(_get(db, "primateai", "score"))
    row["bl_clinpred"] = _num(_get(db, "clinpred", "score"))  # trained on ClinVar -> circular
    row["bl_metarnn"] = _num(_get(db, "metarnn", "score"))  # trained on ClinVar -> circular
    row["bl_varity"] = _num(_get(db, "varity", "r", "score"))  # trained on ClinVar/HGMD -> circular
    return row


if __name__ == "__main__":
    ids = pd.concat([pd.read_parquet(p, columns=["hgvs"]) for p in INTERIM.glob("clinvar_*.parquet")]).hgvs.unique()
    download(list(ids))
    rows = {}
    with open(CACHE) as fh:
        for line in fh:
            hit = json.loads(line)
            rows[hit["query"]] = flatten(hit)
    ann = pd.DataFrame(rows.values())
    ann.to_parquet(INTERIM / "annotations.parquet", index=False)
    print(ann.describe().T[["count", "mean"]].to_string())
