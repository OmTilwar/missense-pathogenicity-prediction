"""Step 4 - ESM-2 (650M) protein language model features, run locally on GPU.

Wild-type-marginal scoring (as used by Brandes et al. 2023 for ESM1b, Meier et al. 2021):
one forward pass per protein window gives log-probabilities for all 20 AAs at every residue.
    esm_llr      = log p(alt) - log p(ref)      (zero-shot pathogenicity signal)
    esm_entropy  = entropy of the position's AA distribution (tolerance to substitution)
    esm_logp_ref = log p(ref)
The 1280-d residue embedding at the variant position is also stored (PCA is fit later on
training data only, to avoid leakage).
Long proteins (>1022 aa) are tiled with overlapping windows; each residue uses the window in
which it is most central.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoTokenizer, EsmForMaskedLM

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data/interim"
_LOCAL = ROOT / "models/esm2_t33_650M_UR50D"
MODEL = str(_LOCAL) if (_LOCAL / "model.safetensors").exists() else "facebook/esm2_t33_650M_UR50D"
MAXLEN, STRIDE = 1022, 511
AAS = "ACDEFGHIKLMNPQRSTVWY"


def windows(n):
    if n <= MAXLEN:
        return [(0, n)]
    starts = list(range(0, n - MAXLEN, STRIDE)) + [n - MAXLEN]
    return [(s, s + MAXLEN) for s in starts]


@torch.no_grad()
def score_protein(seq, positions, tok, model, aa_ids, dev):
    """Returns {pos: (logprobs[20], embedding[1280])} for requested 1-based positions."""
    wins = windows(len(seq))
    best = {}
    for p in positions:  # pick the window where p is furthest from an edge
        i = p - 1
        best[p] = max(range(len(wins)), key=lambda w: min(i - wins[w][0], wins[w][1] - 1 - i))
    out = {}
    for w, (s, e) in enumerate(wins):
        need = [p for p in positions if best[p] == w]
        if not need:
            continue
        enc = tok(seq[s:e], return_tensors="pt").to(dev)
        res = model(**enc, output_hidden_states=True)
        lp = torch.log_softmax(res.logits[0].float(), -1)[:, aa_ids]  # (L+2, 20)
        hid = res.hidden_states[-1][0].float()
        for p in need:
            j = p - 1 - s + 1  # +1 for <cls>
            out[p] = (lp[j].cpu().numpy(), hid[j].cpu().numpy().astype(np.float16))
    return out


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = EsmForMaskedLM.from_pretrained(MODEL, torch_dtype=torch.float16 if dev == "cuda" else torch.float32).to(dev).eval()
    aa_ids = [tok.convert_tokens_to_ids(a) for a in AAS]

    seqs = json.load(open(INTERIM / "uniprot_seqs.json"))
    pf = pd.read_parquet(INTERIM / "protein_features.parquet", columns=["key", "uniprot", "seq_match"])
    cv = pd.concat([pd.read_parquet(p) for p in INTERIM.glob("clinvar_*.parquet")]).drop_duplicates("key").reset_index(drop=True)
    v = cv.merge(pf, on="key")
    v = v[v.seq_match == 1].reset_index(drop=True)

    rows, embs = [], []
    groups = list(v.groupby("uniprot"))
    for n, (acc, grp) in enumerate(groups, 1):
        res = score_protein(seqs[acc], sorted(grp.aa_pos.unique()), tok, model, aa_ids, dev)
        for key, p, r, a in zip(grp.key, grp.aa_pos, grp.aa_ref, grp.aa_alt):
            lp, emb = res[p]
            prob = np.exp(lp)
            prob /= prob.sum()
            rows.append({"key": key, "esm_llr": lp[AAS.index(a)] - lp[AAS.index(r)],
                         "esm_logp_ref": lp[AAS.index(r)], "esm_logp_alt": lp[AAS.index(a)],
                         "esm_entropy": float(-(prob * np.log(prob + 1e-12)).sum())})
            embs.append(emb)
        if n % 250 == 0:
            print(f"  {n}/{len(groups)} proteins", flush=True)

    pd.DataFrame(rows).to_parquet(INTERIM / "esm2_scores.parquet", index=False)
    np.save(INTERIM / "esm2_embeddings.npy", np.stack(embs))
    pd.Series([r["key"] for r in rows]).to_frame("key").to_parquet(INTERIM / "esm2_embedding_keys.parquet", index=False)
    print(f"scored {len(rows):,} variants")


if __name__ == "__main__":
    main()
