"""Step 8 - Train and save every model to results/models/.

    {B_LR, C_XGB, D_XGB_ESM}_temporal.joblib  trained on ClinVar 2023-01 labels (the evaluated models)
    D_XGB_ESM_final.joblib                     trained on all ClinVar 2026-09 labels (for real use / demo)
Each file is a dict: feats, names, pca (or None), clf (sklearn pipeline or XGBoost), iso (isotonic
calibrator), n_pc, trained_on, n_train. XGBoost boosters are also exported as portable JSON.
"""
import json

import joblib

from common import BIO, ESM, N_PC, ROOT, VariantModel, load_data

OUT = ROOT / "results/models"
OUT.mkdir(parents=True, exist_ok=True)
SPECS = {"B_LR": ("lr", BIO, False), "C_XGB": ("xgb", BIO, False), "D_XGB_ESM": ("xgb", BIO + ESM, True)}

df, emb = load_data()
sets = {"temporal": (df[df.label_old.notna()].reset_index(drop=True), "label_old", "ClinVar 2023-01"),
        "final": (df[df.label_new.notna()].reset_index(drop=True), "label_new", "ClinVar 2026-09")}
manifest = []
for tag, (data, col, src) in sets.items():
    for name, (kind, feats, pcs) in SPECS.items():
        if tag == "final" and name != "D_XGB_ESM":
            continue
        y = data[col].values.astype(int)
        m = VariantModel(kind, feats, pcs, emb).fit(data, y)
        bundle = {"feats": m.feats, "names": m.names, "pca": getattr(m, "pca", None), "clf": m.clf, "iso": m.iso,
                  "n_pc": N_PC, "trained_on": src, "n_train": len(data)}
        path = OUT / f"{name}_{tag}.joblib"
        joblib.dump(bundle, path)
        if kind == "xgb":
            m.clf.get_booster().save_model(OUT / f"{name}_{tag}_booster.json")
        manifest.append({"file": path.name, "model": name, "trained_on": src, "n_train": len(data),
                         "n_features": len(m.names), "size_mb": round(path.stat().st_size / 1e6, 2)})
        print(manifest[-1], flush=True)
json.dump(manifest, open(OUT / "manifest.json", "w"), indent=1)
