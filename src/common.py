"""Shared pieces: data loading, metrics, and the calibrated VariantModel."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[1]
PROC, INTERIM = ROOT / "data/processed", ROOT / "data/interim"
TAB, FIG = ROOT / "results/tables", ROOT / "results/figures"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
SEED, N_PC = 42, 16
RNG = np.random.default_rng(SEED)

GROUPS = json.load(open(PROC / "feature_groups.json"))
BIO = [f for g in ("population", "conservation", "protein_context", "structure", "aa_properties") for f in GROUPS[g]]
ESM = GROUPS["esm2"]


def load_data():
    df = pd.read_parquet(PROC / "variants.parquet")
    emb = np.load(INTERIM / "esm2_embeddings.npy").astype(np.float32)
    keys = pd.read_parquet(INTERIM / "esm2_embedding_keys.parquet").key
    df["emb_row"] = df.key.map(pd.Series(np.arange(len(keys)), index=keys.values))
    return df, emb


# ----------------------------------------------------------------------------- metrics
def auroc(y, s):
    r = pd.Series(s).rank().values
    n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def auprc(y, s):
    o = np.argsort(-s, kind="mergesort"); y = y[o]
    prec = np.cumsum(y) / np.arange(1, len(y) + 1)
    return (prec * y).sum() / max(y.sum(), 1)


def ece(y, p, bins=15):
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return sum((idx == b).mean() * abs(y[idx == b].mean() - p[idx == b].mean()) for b in range(bins) if (idx == b).any())


def evaluate(y, s, prob=False, n_boot=1000):
    """AUROC/AUPRC with bootstrap 95% CI (+ Brier/ECE for probabilities). NaN scores are skipped."""
    m = ~np.isnan(s)
    y, s = y[m].astype(int), s[m]
    out = {"n": int(m.sum()), "coverage": float(m.mean()), "n_path": int(y.sum())}
    if len(y) == 0 or y.min() == y.max():
        return out
    out["auroc"], out["auprc"] = auroc(y, s), auprc(y, s)
    boots = []
    for _ in range(n_boot):
        i = RNG.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(i):
            boots.append((auroc(y[i], s[i]), auprc(y[i], s[i])))
    if boots:
        b = np.array(boots)
        out["auroc_lo"], out["auroc_hi"] = np.percentile(b[:, 0], [2.5, 97.5])
        out["auprc_lo"], out["auprc_hi"] = np.percentile(b[:, 1], [2.5, 97.5])
    if prob:
        out["brier"], out["ece"] = float(np.mean((s - y) ** 2)), ece(y, s)
    return out


# ----------------------------------------------------------------------------- model
class VariantModel:
    """LR or XGBoost + isotonic calibration on a gene-disjoint 15% slice of the training data.
    With use_pcs, a PCA of ESM-2 residue embeddings is fit on the training rows only."""

    def __init__(self, kind, feats, use_pcs=False, emb=None):
        self.kind, self.feats, self.use_pcs, self.emb = kind, list(feats), use_pcs, emb

    def _X(self, d):
        X = d[self.feats].astype(float).values
        if self.use_pcs:
            pcs = np.full((len(d), N_PC), np.nan, np.float32)
            ok = d.emb_row.notna().values
            if ok.any():
                pcs[ok] = self.pca.transform(self.emb[d.emb_row[ok].astype(int).values])
            X = np.hstack([X, pcs])
        return X

    @property
    def names(self):
        return self.feats + ([f"esm_pc{i + 1}" for i in range(N_PC)] if self.use_pcs else [])

    def fit(self, d, y):
        fit_i, cal_i = next(GroupShuffleSplit(1, test_size=0.15, random_state=SEED).split(d, y, d.gene))
        dfit = d.iloc[fit_i]
        if self.use_pcs:
            self.pca = PCA(N_PC, random_state=SEED).fit(self.emb[dfit.emb_row.dropna().astype(int).values])
        if self.kind == "lr":
            self.clf = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                                     LogisticRegression(C=0.5, max_iter=3000))
        else:
            self.clf = XGBClassifier(n_estimators=700, learning_rate=0.04, max_depth=6, subsample=0.8,
                                     colsample_bytree=0.7, min_child_weight=5, reg_lambda=2.0,
                                     tree_method="hist", device="cuda", random_state=SEED, n_jobs=8)
        self.clf.fit(self._X(dfit), y[fit_i])
        raw_cal = self.clf.predict_proba(self._X(d.iloc[cal_i]))[:, 1]
        self.iso = IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=1 - 1e-4).fit(raw_cal, y[cal_i])
        return self

    def predict(self, d, calibrated=True):
        raw = self.clf.predict_proba(self._X(d))[:, 1]
        return self.iso.predict(raw) if calibrated else raw
