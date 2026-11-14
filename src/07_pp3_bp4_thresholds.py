"""Step 7 - ClinGen PP3/BP4 evidence-strength thresholds (replication of Pejaver et al. 2022).

Local posterior probability of pathogenicity is estimated in a sliding score window, with class
weights that rescale the data to the population prior (0.0441). A threshold is the score beyond
which the one-sided 95% bootstrap bound of the local posterior stays above (PP3) or below (BP4)
the posterior implied by the Bayesian ACMG/AMP framework (OddsPath 2.406^k).

1. Replication: REVEL thresholds computed on our ClinVar 2023 rare-variant set, compared with the
   published values.
2. Our model D: thresholds learned from gene-disjoint out-of-fold scores on the 2023 era, then
   VALIDATED on the time-travel test (realised likelihood ratio per evidence level).
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from common import BIO, ESM, SEED, TAB, VariantModel, load_data

PRIOR = 0.0441
ODDS = {"Supporting": 2.406, "Moderate": 2.406 ** 2, "Strong": 2.406 ** 4, "Very strong": 2.406 ** 8}
prior_odds = PRIOR / (1 - PRIOR)
POST_P = {k: prior_odds * o / (1 + prior_odds * o) for k, o in ODDS.items()}
POST_B = {k: (prior_odds / o) / (1 + prior_odds / o) for k, o in ODDS.items()}
PUBLISHED_REVEL = {"PP3": {"Supporting": 0.644, "Moderate": 0.773, "Strong": 0.932},
                   "BP4": {"Supporting": 0.290, "Moderate": 0.183, "Strong": 0.016}}
rng = np.random.default_rng(SEED)


def local_posterior(s, y, grid, frac=0.03):
    """Posterior at each grid point using the `frac` share of variants nearest in score."""
    o = np.argsort(s); s, y = s[o], y[o]
    k = max(int(frac * len(s)), 100)
    w_p = PRIOR / y.mean(); w_b = (1 - PRIOR) / (1 - y.mean())
    post = []
    for g in grid:
        c = np.searchsorted(s, g)
        lo, hi = max(0, c - k // 2), min(len(s), c + k // 2)
        yy = y[lo:hi]
        p, b = yy.sum() * w_p, (len(yy) - yy.sum()) * w_b
        post.append(p / (p + b) if p + b else np.nan)
    return np.array(post)


def thresholds(s, y, n_boot=200):
    m = ~np.isnan(s); s, y = s[m], y[m].astype(int)
    grid = np.quantile(s, np.linspace(0.001, 0.999, 400))
    boots = np.array([local_posterior(s[i], y[i], grid) for i in (rng.integers(0, len(s), len(s)) for _ in range(n_boot))])
    lower, upper = np.nanpercentile(boots, 5, axis=0), np.nanpercentile(boots, 95, axis=0)
    out = {"PP3": {}, "BP4": {}}
    for lvl in ("Supporting", "Moderate", "Strong", "Very strong"):
        ok = lower >= POST_P[lvl]  # pathogenic: lowest t such that all grid points >= t pass
        idx = np.where(~ok)[0]
        first = idx.max() + 1 if len(idx) else 0
        out["PP3"][lvl] = grid[first] if first < len(grid) else np.nan
        okb = upper <= POST_B[lvl]  # benign: highest t such that all grid points <= t pass
        idxb = np.where(~okb)[0]
        last = idxb.min() - 1 if len(idxb) else len(grid) - 1
        out["BP4"][lvl] = grid[last] if last >= 0 else np.nan
    return out


def assign(s, th):
    lvl = np.array([""] * len(s), dtype=object)
    for k in ("Supporting", "Moderate", "Strong", "Very strong"):
        if not np.isnan(th["PP3"][k]):
            lvl[s >= th["PP3"][k]] = f"PP3_{k}"
        if not np.isnan(th["BP4"][k]):
            lvl[s <= th["BP4"][k]] = f"BP4_{k}"
    return lvl


def realised_lr(levels, y):
    rows = []
    for lv in sorted(set(levels) - {""}):
        m = levels == lv
        tpr = (m & (y == 1)).sum() / (y == 1).sum(); fpr = (m & (y == 0)).sum() / (y == 0).sum()
        lr = tpr / fpr if fpr else np.inf
        strength = lv.split("_")[1]
        target = ODDS[strength]
        lr_ok = lr >= target if lv.startswith("PP3") else (1 / lr if lr else np.inf) >= target
        rows.append({"level": lv, "n": int(m.sum()), "frac_variants": m.mean(), "frac_of_P": tpr, "frac_of_B": fpr,
                     "realised_LR": lr, "required_LR": target if lv.startswith("PP3") else 1 / target, "meets_target": bool(lr_ok)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df, emb = load_data()
    old = df[df.label_old.notna()].reset_index(drop=True)
    y_old = old.label_old.values.astype(int)

    # 1) REVEL replication on rare variants of the 2023 set
    rare = old.rare.values == 1
    th_revel = thresholds(old.bl_revel.values[rare], y_old[rare])
    rep = pd.DataFrame([{"criterion": c, "strength": k, "published": PUBLISHED_REVEL[c].get(k), "ours": th_revel[c][k]}
                        for c in ("PP3", "BP4") for k in ("Supporting", "Moderate", "Strong", "Very strong")])
    rep.to_csv(TAB / "pp3_bp4_revel_replication.csv", index=False)
    print("REVEL threshold replication (Pejaver 2022):\n", rep.round(3).to_string(index=False))

    # 2) Model D: gene-disjoint OOF scores on 2023 era -> thresholds
    oof = np.full(len(old), np.nan)
    for tr, te in GroupKFold(5).split(old, y_old, old.gene):
        oof[te] = VariantModel("xgb", BIO + ESM, True, emb).fit(old.iloc[tr], y_old[tr]).predict(old.iloc[te])
    th_d = thresholds(oof, y_old)
    pd.DataFrame(th_d).to_csv(TAB / "pp3_bp4_modelD_thresholds.csv")
    print("Model D thresholds:\n", pd.DataFrame(th_d).round(4))

    # validate on time-travel test
    pred = pd.read_parquet(TAB / "temporal_test_predictions.parquet")
    lv = assign(pred.D_XGB_ESM.values, th_d)
    val = realised_lr(lv, pred.label.values)
    val.to_csv(TAB / "pp3_bp4_modelD_validation.csv", index=False)
    print("Validation on time-travel test:\n", val.round(3).to_string(index=False))
    # same for REVEL with published thresholds (for comparison)
    tst = df[df.temporal_test == 1].reset_index(drop=True)
    th_pub = {c: {**{k: np.nan for k in ODDS}, **v} for c, v in PUBLISHED_REVEL.items()}
    m = tst.bl_revel.notna().values
    val_r = realised_lr(assign(tst.bl_revel.values[m], th_pub), tst.label_new.values[m].astype(int))
    val_r.to_csv(TAB / "pp3_bp4_revel_published_validation.csv", index=False)
    print("REVEL (published thresholds) on time-travel test:\n", val_r.round(3).to_string(index=False))
    cov = pd.DataFrame({"model": ["Model D (ours)", "REVEL (published)"],
                        "frac_with_any_evidence": [(lv != "").mean(), (assign(tst.bl_revel.values[m], th_pub) != "").mean()]})
    cov.to_csv(TAB / "pp3_bp4_coverage.csv", index=False)
    print(cov)
