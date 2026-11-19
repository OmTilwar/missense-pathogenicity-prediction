"""Local web UI for src/predict.py.

    streamlit run app.py

Scores one GRCh38 missense SNV and shows the calibrated probability, the ClinGen-style PP3/BP4
evidence level, and a SHAP explanation. Uses the same feature code as src/predict.py; the
UniProt tables and the ESM-2 model are loaded once and cached between requests.
Research use only - not a clinical classification.
"""
import contextlib
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# macOS: torch, scikit-learn and xgboost each ship their own libomp; with several OpenMP
# threads the copies deadlock. One OpenMP thread avoids it (ESM-2 still runs in ~20 s).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
# Use the local ESM-2 copy without network checks when it has been downloaded.
if (ROOT / "models/esm2_t33_650M_UR50D/model.safetensors").exists():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import shap
import streamlit as st
import streamlit.components.v1 as components
import transformers

sys.path.insert(0, str(ROOT / "src"))
import predict  # noqa: E402  (src/predict.py)
import report  # noqa: E402  (report.py, rule-based report builder)

st.set_page_config(page_title="Missense Variant Scorer", page_icon="🧬", layout="wide")

# ---------------------------------------------------------------------------- caching
# predict.features_for reloads UniProt and ESM-2 on every call; cache them for the app.
if not getattr(predict, "_app_cached", False):
    predict.prot_mod.load_uniprot = st.cache_resource(show_spinner="Loading UniProt tables…")(
        predict.prot_mod.load_uniprot)
    _esm_load = transformers.EsmForMaskedLM.from_pretrained
    _tok_load = transformers.AutoTokenizer.from_pretrained

    @st.cache_resource(show_spinner="Loading ESM-2 protein model (first run only)…")
    def _cached_esm(name):
        return _esm_load(name)

    @st.cache_resource(show_spinner=False)
    def _cached_tok(name):
        return _tok_load(name)

    transformers.EsmForMaskedLM.from_pretrained = staticmethod(lambda name, *a, **k: _cached_esm(name))
    transformers.AutoTokenizer.from_pretrained = staticmethod(lambda name, *a, **k: _cached_tok(name))
    predict._app_cached = True


@st.cache_resource(show_spinner="Loading trained model…")
def load_bundle(stem):
    b = joblib.load(ROOT / f"results/models/{stem}.joblib")
    b["clf"].set_params(device="cpu")
    return b


@st.cache_data
def load_thresholds():
    p = ROOT / "results/tables/pp3_bp4_modelD_thresholds.csv"
    return pd.read_csv(p, index_col=0) if p.exists() else None


# ---------------------------------------------------------------------------- labels
GROUP_NAMES = {"population": "Population frequency", "conservation": "Evolutionary conservation",
               "protein_context": "Protein context (UniProt)", "structure": "3D structure (AlphaFold)",
               "aa_properties": "Amino-acid chemistry", "esm2": "ESM-2 protein language model"}
FRIENDLY = {
    "af_ex": "gnomAD exome frequency (log10)", "af_ge": "gnomAD genome frequency (log10)",
    "af_ex_popmax": "Highest population frequency, exomes (log10)",
    "af_ge_popmax": "Highest population frequency, genomes (log10)",
    "hom_ex": "Homozygous carriers, exomes (log10)", "hom_ge": "Homozygous carriers, genomes (log10)",
    "in_gnomad_ex": "Seen in gnomAD exomes", "in_gnomad_ge": "Seen in gnomAD genomes",
    "phylop_17": "phyloP conservation (primates)", "phylop_100": "phyloP conservation (vertebrates)",
    "phylop_470": "phyloP conservation (mammals)", "phastcons_17": "phastCons (primates)",
    "phastcons_100": "phastCons (vertebrates)", "phastcons_470": "phastCons (mammals)",
    "gerp_91": "GERP conservation", "siphy": "SiPhy conservation", "bstatistic": "B-statistic (selection)",
    "rel_pos": "Relative position in protein", "log_prot_len": "Protein length (log10)",
    "interpro_domain": "Inside an InterPro domain", "dist_func_site": "Distance to functional site (residues)",
    "uni_domain": "Inside a UniProt domain", "uni_active_site": "Active site", "uni_binding_site": "Binding site",
    "uni_disulfide": "Disulfide bond", "uni_transmem": "Transmembrane region", "uni_signal": "Signal peptide",
    "uni_mod_res": "Modified residue", "uni_zn_finger": "Zinc finger", "uni_motif": "Motif", "uni_helix": "Helix",
    "uni_strand": "Beta strand", "uni_region": "Annotated region", "uni_compbias": "Compositional bias",
    "af_plddt": "AlphaFold confidence (pLDDT)", "af_plddt_win": "AlphaFold confidence, nearby residues",
    "af_contacts": "Burial (neighbouring residues)", "grantham": "Grantham distance (how different the AAs are)",
    "blosum62": "BLOSUM62 substitution score", "d_hydropathy": "Change in hydropathy", "d_volume": "Change in size",
    "d_polarity": "Change in polarity", "d_charge": "Change in charge", "arom_change": "Aromatic change",
    "esm_llr": "ESM-2 log-likelihood ratio", "esm_logp_ref": "ESM-2 log p(original AA)",
    "esm_logp_alt": "ESM-2 log p(new AA)", "esm_entropy": "ESM-2 position entropy",
}
BASELINES = {"bl_revel": "REVEL", "bl_alphamissense": "AlphaMissense", "bl_cadd": "CADD (phred)",
             "bl_esm1b": "ESM1b (−LLR)", "bl_primateai": "PrimateAI"}
EXAMPLES = {
    "TP53 p.R175H (known pathogenic)": ("chr17:g.7675088C>T", "TP53", "R175H"),
    "BRCA1 p.P871L (common, benign)": ("chr17:g.43093449G>A", "BRCA1", "P871L"),
}


def friendly(name):
    if name.startswith("esm_pc"):
        return f"ESM-2 embedding component {name[6:]}"
    if name[:4] in ("ref_", "alt_"):
        kind = "Original" if name.startswith("ref_") else "New"
        return f"{kind} amino acid is {name.split('_')[-1]}"
    return FRIENDLY.get(name, name)


def group_of(name, groups):
    if name.startswith("esm_pc"):
        return "esm2"
    return next((g for g, fs in groups.items() if name in fs), "other")


def evidence_level(p, th):
    level = "Indeterminate"
    if th is None:
        return level
    for k in ("Supporting", "Moderate", "Strong", "Very strong"):
        if pd.notna(th.loc[k, "PP3"]) and p >= th.loc[k, "PP3"]:
            level = f"PP3_{k}"
        if pd.notna(th.loc[k, "BP4"]) and p <= th.loc[k, "BP4"]:
            level = f"BP4_{k}"
    return level


# ---------------------------------------------------------------------------- scoring
def score(hgvs, gene, protein, stem):
    bundle = load_bundle(stem)
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        d, emb = predict.features_for(hgvs, gene or None, protein or None)
    for f in bundle["feats"]:
        if f not in d:
            d[f] = np.nan
    X = d[bundle["feats"]].astype(float).values
    pcs = (bundle["pca"].transform(emb.astype(np.float32)[None]) if emb is not None
           else np.full((1, bundle["n_pc"]), np.nan))
    X = np.hstack([X, pcs])
    raw = float(bundle["clf"].predict_proba(X)[:, 1][0])
    p = float(bundle["iso"].predict([raw])[0])
    sv = shap.TreeExplainer(bundle["clf"]).shap_values(X)[0]
    expl = pd.DataFrame({"feature": bundle["names"], "value": X[0], "shap": sv})
    expl["label"] = expl.feature.map(friendly)
    expl["group"] = expl.feature.map(lambda f: group_of(f, bundle.get("groups") or {}))
    print(f"[SCORE] model={stem} raw={raw:.4f} calibrated={p:.4f} feats_missing={int(np.isnan(X).sum())}/{X.size}",
          flush=True)
    return {"p": p, "raw": raw, "d": d, "expl": expl, "log": log.getvalue().strip()}


# ---------------------------------------------------------------------------- charts
def gauge(p, th):
    steps = [{"range": [0, 1], "color": "rgba(150,150,150,0.15)"}]
    if th is not None:
        bp4 = [th.loc[k, "BP4"] for k in ("Strong", "Moderate", "Supporting")]
        pp3 = [th.loc[k, "PP3"] for k in ("Supporting", "Moderate", "Strong")]
        blues = ["#1d4ed8", "#3b82f6", "#93c5fd"]
        reds = ["#fca5a5", "#ef4444", "#b91c1c"]
        lo = 0.0
        for edge, c in zip(bp4, blues):
            steps.append({"range": [lo, edge], "color": c}); lo = edge
        edges = pp3 + [1.0]
        for i, c in enumerate(reds):
            steps.append({"range": [edges[i], edges[i + 1]], "color": c})
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=p, number={"valueformat": ".3f"},
        gauge={"axis": {"range": [0, 1]}, "bar": {"color": "#111827", "thickness": 0.25}, "steps": steps}))
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=30, b=0))
    return fig


def shap_bar(expl, n):
    top = expl.reindex(expl.shap.abs().sort_values(ascending=False).index).head(n).iloc[::-1]
    colors = ["#dc2626" if v > 0 else "#2563eb" for v in top.shap]
    text = [f"value = {v:.3g}" if pd.notna(v) else "missing" for v in top.value]
    fig = go.Figure(go.Bar(x=top.shap, y=top.label, orientation="h", marker_color=colors,
                           hovertext=text, hoverinfo="text+x"))
    fig.update_layout(height=40 + 28 * len(top), margin=dict(l=10, r=10, t=10, b=30),
                      xaxis_title="SHAP (log-odds):  ← benign  |  pathogenic →")
    return fig


# ---------------------------------------------------------------------------- page
st.title("🧬 Missense Variant Scorer")
st.caption("Leakage-controlled XGBoost + ESM-2 model from this repository. "
           "**Research use only - not a clinical variant classification.**")

models = sorted(p.stem for p in (ROOT / "results/models").glob("*.joblib"))
with st.sidebar:
    st.header("Settings")
    if not models:
        st.error("No model found in results/models/. Copy results/model_D_temporal.joblib to "
                 "results/models/D_XGB_ESM_temporal.joblib.")
        st.stop()
    stem = st.selectbox("Model", models, index=models.index("D_XGB_ESM_final") if "D_XGB_ESM_final" in models else 0)
    n_feats = st.slider("Features in explanation", 5, 25, 12)
    st.header("Examples")
    for name, ex in EXAMPLES.items():
        if st.button(name, use_container_width=True):
            st.session_state.hgvs, st.session_state.gene, st.session_state.protein = ex
    st.divider()
    st.markdown("**How to read it**\n\n"
                "- Probability: calibrated chance the variant is pathogenic.\n"
                "- PP3 / BP4: ClinGen computational evidence strength (red = pathogenic side, "
                "blue = benign side, grey = indeterminate).\n"
                "- Red bars push towards pathogenic, blue bars towards benign.")

with st.form("variant"):
    c1, c2, c3 = st.columns([3, 1, 1])
    hgvs = c1.text_input("Variant (GRCh38 genomic HGVS)", key="hgvs", placeholder="chr17:g.7675088C>T")
    gene = c2.text_input("Gene (optional)", key="gene", placeholder="TP53")
    protein = c3.text_input("Protein change (optional)", key="protein", placeholder="R175H")
    go_btn = st.form_submit_button("Score variant", type="primary")

if go_btn:
    if not hgvs.strip():
        st.warning("Enter a variant first.")
        st.stop()
    try:
        with st.spinner("Fetching annotations (MyVariant, UniProt, AlphaFold) and running ESM-2…"):
            res = score(hgvs.strip(), gene.strip(), protein.strip().upper(), stem)
    except SystemExit as e:
        st.error(str(e))
        st.stop()
    except Exception as e:  # network errors, unknown variants, ...
        st.error(f"Could not score this variant: {e}")
        st.stop()
    res["time"] = report.now()
    res["run_id"] = report.new_run_id(hgvs.strip(), stem, res["time"])
    st.session_state.result = (hgvs.strip(), stem, res)

if "result" in st.session_state:
    hgvs_done, stem_done, res = st.session_state.result
    d, expl, p = res["d"], res["expl"], res["p"]
    th = load_thresholds()
    level = evidence_level(p, th)
    if res["log"]:
        st.warning(res["log"])

    st.subheader(f"{d.gene[0]} p.{d.aa_ref[0]}{d.aa_pos[0]}{d.aa_alt[0]}  ·  `{hgvs_done}`")
    left, right = st.columns([1, 1])
    with left:
        st.plotly_chart(gauge(p, th), use_container_width=True)
    with right:
        st.metric("Calibrated P(pathogenic)", "<0.1%" if p < 0.001 else ">99.9%" if p > 0.999 else f"{p:.1%}")
        color = "red" if level.startswith("PP3") else "blue" if level.startswith("BP4") else "gray"
        st.markdown(f"**Computational evidence:** :{color}[**{level.replace('_', ' ')}**]")
        st.caption(f"Model: `{stem_done}`")
        bl = {v: d[k][0] for k, v in BASELINES.items() if k in d and pd.notna(d[k][0])}
        if bl:
            st.markdown("**Other tools** (comparison only, never model inputs)")
            st.dataframe(pd.DataFrame({"Tool": bl.keys(), "Score": [f"{x:.3f}" for x in bl.values()]}),
                         hide_index=True, use_container_width=True)

    st.subheader("Why? Top contributing features")
    st.plotly_chart(shap_bar(expl, n_feats), use_container_width=True)

    by_group = (expl.assign(group=expl.group.map(lambda g: GROUP_NAMES.get(g, g)))
                .groupby("group").shap.sum().sort_values())
    st.subheader("Contribution by evidence type")
    fig = go.Figure(go.Bar(x=by_group.values, y=by_group.index, orientation="h",
                           marker_color=["#dc2626" if v > 0 else "#2563eb" for v in by_group.values]))
    fig.update_layout(height=60 + 34 * len(by_group), margin=dict(l=10, r=10, t=10, b=30),
                      xaxis_title="Summed SHAP (log-odds)")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("All feature values"):
        st.dataframe(expl[["group", "label", "feature", "value", "shap"]]
                     .sort_values("shap", key=np.abs, ascending=False),
                     hide_index=True, use_container_width=True)

    # ------------------------------------------------------------------------ report
    st.subheader("📄 Report for this run")
    st.caption("Built from fixed rules and this run's numbers only (no AI text generation), "
               "so the same run always gives the same report.")
    run = {"hgvs": hgvs_done, "model": stem_done, "p": p, "level": level, "d": d, "expl": expl,
           "thresholds": th, "time": res["time"], "run_id": res["run_id"], "log": res["log"],
           "baselines": {v: float(d[k][0]) for k, v in BASELINES.items() if k in d and pd.notna(d[k][0])},
           "group_names": GROUP_NAMES}
    html_report, md_report = report.build_report(run)
    fname = f"variant_report_{d.gene[0]}_{d.aa_ref[0]}{d.aa_pos[0]}{d.aa_alt[0]}_{res['run_id']}"
    pdf_key = f"pdf_{res['run_id']}"
    if pdf_key not in st.session_state:
        with st.spinner("Rendering PDF…"):
            st.session_state[pdf_key] = report.html_to_pdf(html_report)
    pdf_report = st.session_state[pdf_key]
    b0, b1, b2 = st.columns(3)
    if pdf_report:
        b0.download_button("⬇️ Download PDF", pdf_report, f"{fname}.pdf", "application/pdf",
                           type="primary", use_container_width=True)
    else:
        b0.button("⬇️ Download PDF", disabled=True, use_container_width=True, help=report.PDF_HINT)
    b1.download_button("⬇️ Download HTML", html_report, f"{fname}.html", "text/html",
                       use_container_width=True)
    b2.download_button("⬇️ Download Markdown", md_report, f"{fname}.md", "text/markdown",
                       use_container_width=True)
    if not pdf_report:
        st.caption(report.PDF_HINT)
    with st.expander("Preview report", expanded=True):
        components.html(html_report, height=900, scrolling=True)
