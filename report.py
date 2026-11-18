"""Rule-based variant report for one scoring run (no LLM).

build_report(run) returns (html, markdown). Every sentence comes from a fixed template filled
with the run's own numbers, so the same run always produces the same report.
"""
import datetime as dt
import hashlib
import html
import importlib.metadata as md
import math
import platform
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PKGS = ["xgboost", "scikit-learn", "torch", "transformers", "shap"]
DISCLAIMER = ("Research use only. This report gives one line of computational evidence (ACMG/AMP PP3/BP4). "
              "It is not a clinical variant classification and must not be used for diagnosis or treatment.")
LIMITATIONS = [
    "Population frequency is the strongest input. ClinVar curators also use frequency to call variants benign "
    "(BA1/BS1), so part of the model's accuracy reflects how the labels were made. If you combine this score with "
    "BA1/BS1/PM2, be careful not to count the same frequency evidence twice.",
    "Probabilities are well calibrated within one ClinVar release but are over-confident on later variants "
    "(the repository's REPORT.md, section 6).",
    "Performance is lower for genes with no labelled variants in the training data.",
    "Protein length acts partly as a gene-level proxy, so long genes with many benign variants push scores lower.",
    "Variants that were already in the training set will look over-confident; check ClinVar before interpreting.",
]


# ----------------------------------------------------------------------------- helpers
def _v(d, col):
    if col not in d:
        return math.nan
    x = d[col].iloc[0]
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def _ok(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def _af(log_val):
    """Undo the log10(AF + 1e-7) transform used in predict.features_for."""
    return max(10 ** log_val - 1e-7, 0.0) if _ok(log_val) else math.nan


def _fmt_af(a):
    if not _ok(a):
        return "not available"
    if a == 0:
        return "0"
    return f"{a:.2e}" if a < 0.001 else f"{a:.4f}"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------- rule-based findings
def findings(d):
    """List of (category, direction, sentence). direction: 'path', 'benign' or 'neutral'."""
    out = []
    in_ex, in_ge = _v(d, "in_gnomad_ex"), _v(d, "in_gnomad_ge")
    popmax = max([_af(_v(d, c)) for c in ("af_ex_popmax", "af_ge_popmax") if _ok(_v(d, c))] or [math.nan])
    af_all = max([_af(_v(d, c)) for c in ("af_ex", "af_ge") if _ok(_v(d, c))] or [math.nan])
    hom = max([10 ** _v(d, c) - 1 for c in ("hom_ex", "hom_ge") if _ok(_v(d, c))] or [0])
    if (in_ex == 0 and in_ge == 0) or (_ok(popmax) and popmax == 0 and (not _ok(af_all) or af_all == 0)):
        out.append(("Population", "path", "Not observed in gnomAD. Absence from healthy populations is "
                    "consistent with a damaging variant (compare ACMG PM2)."))
    elif _ok(popmax) and popmax >= 0.05:
        out.append(("Population", "benign", f"Very common: highest population frequency {_fmt_af(popmax)} (≥5%). "
                    "This alone is usually treated as stand-alone benign evidence (ACMG BA1)."))
    elif _ok(popmax) and popmax >= 0.01:
        out.append(("Population", "benign", f"Common: highest population frequency {_fmt_af(popmax)} (≥1%), "
                    "which is too frequent for most rare Mendelian disorders (compare ACMG BS1)."))
    elif _ok(popmax) and popmax < 1e-4:
        out.append(("Population", "path", f"Very rare in gnomAD (highest population frequency {_fmt_af(popmax)})."))
    elif _ok(popmax):
        out.append(("Population", "neutral", f"Rare in gnomAD (highest population frequency {_fmt_af(popmax)})."))
    if hom >= 1:
        out.append(("Population", "benign", f"Seen in about {hom:.0f} homozygous individual(s) in gnomAD."))

    p100, p470 = _v(d, "phylop_100"), _v(d, "phylop_470")
    if _ok(p100):
        if p100 >= 4:
            out.append(("Conservation", "path", f"Strongly conserved across vertebrates (phyloP-100 = {p100:.2f})."))
        elif p100 >= 2:
            out.append(("Conservation", "path", f"Conserved across vertebrates (phyloP-100 = {p100:.2f})."))
        elif p100 < 0:
            out.append(("Conservation", "benign", f"Not conserved; the position appears to evolve freely "
                        f"(phyloP-100 = {p100:.2f})."))
        else:
            out.append(("Conservation", "neutral", f"Weakly conserved (phyloP-100 = {p100:.2f})."))
    elif _ok(p470):
        out.append(("Conservation", "neutral", f"phyloP-470 (mammals) = {p470:.2f}."))

    llr = _v(d, "esm_llr")
    if _ok(llr):
        if llr <= -7:
            out.append(("Protein language model", "path", f"ESM-2 finds the new amino acid highly unlikely at this "
                        f"position (log-likelihood ratio {llr:.2f}; ≤ −7 is typical of damaging changes)."))
        elif llr <= -3:
            out.append(("Protein language model", "path", f"ESM-2 finds the change moderately unlikely "
                        f"(log-likelihood ratio {llr:.2f})."))
        else:
            out.append(("Protein language model", "benign", f"ESM-2 finds the change plausible "
                        f"(log-likelihood ratio {llr:.2f})."))
    else:
        out.append(("Protein language model", "neutral", "ESM-2 features unavailable (protein change did not match "
                    "the canonical UniProt isoform)."))

    plddt, cont = _v(d, "af_plddt"), _v(d, "af_contacts")
    if _ok(plddt):
        if plddt < 50:
            out.append(("Structure", "benign", f"Located in a likely disordered region (AlphaFold pLDDT {plddt:.0f})."))
        elif _ok(cont) and cont >= 15:
            out.append(("Structure", "path", f"Buried inside a well-folded region (AlphaFold pLDDT {plddt:.0f}, "
                        f"{cont:.0f} neighbouring residues)."))
        else:
            out.append(("Structure", "neutral", f"Folded region, mostly exposed (pLDDT {plddt:.0f}, "
                        f"{cont:.0f} neighbouring residues)."))

    dist = _v(d, "dist_func_site")
    if _ok(dist) and dist <= 3:
        out.append(("Protein context", "path", f"{dist:.0f} residue(s) from a UniProt active or binding site."))
    flags = [n for c, n in (("uni_active_site", "active site"), ("uni_binding_site", "binding site"),
                            ("uni_zn_finger", "zinc finger"), ("uni_transmem", "transmembrane segment"),
                            ("uni_disulfide", "disulfide bond"), ("uni_domain", "annotated domain"))
             if _v(d, c) == 1]
    if _v(d, "interpro_domain") == 1 and "annotated domain" not in flags:
        flags.append("InterPro domain")
    if flags:
        out.append(("Protein context", "path", "Falls in: " + ", ".join(flags) + "."))

    g, b = _v(d, "grantham"), _v(d, "blosum62")
    if _ok(g):
        kind = ("radical" if g > 100 else "moderately radical" if g > 50 else "conservative")
        direction = "path" if g > 100 else "neutral"
        out.append(("Amino-acid chemistry", direction, f"{kind.capitalize()} substitution "
                    f"(Grantham {g:.0f}, BLOSUM62 {b:+.0f})." if _ok(b) else f"{kind.capitalize()} substitution "
                    f"(Grantham {g:.0f})."))
    return out


# ----------------------------------------------------------------------------- assembly
def _summary(p, level, gene, change):
    side = ("supports a pathogenic effect" if level.startswith("PP3") else
            "supports a benign effect" if level.startswith("BP4") else
            "falls in the indeterminate range and should not be used as evidence either way")
    strength = level.split("_", 1)[1].lower() if "_" in level else ""
    s = f"The model gives {gene} p.{change} a calibrated pathogenicity probability of {p:.3f}. "
    if strength:
        s += f"This {side} at **{strength}** strength ({level.replace('_', ' ')})."
    else:
        s += f"The score {side}."
    return s


def _meta(run):
    model_path = ROOT / f"results/models/{run['model']}.joblib"
    vers = {}
    for p in PKGS:
        try:
            vers[p] = md.version(p)
        except md.PackageNotFoundError:
            pass
    return {
        "Generated": run["time"].strftime("%Y-%m-%d %H:%M:%S %Z").strip(),
        "Run ID": run["run_id"],
        "Model file": f"results/models/{run['model']}.joblib",
        "Model SHA-256": _sha256(model_path)[:16] + "…" if model_path.exists() else "n/a",
        "Model trained on": run.get("trained_on") or ("ClinVar 2023-01" if "temporal" in run["model"] else "see manifest"),
        "Python / platform": f"{platform.python_version()} / {platform.platform(terse=True)}",
        "Packages": ", ".join(f"{k} {v}" for k, v in vers.items()),
        "Data sources (live)": "MyVariant.info (gnomAD, dbNSFP), UniProt Swiss-Prot, AlphaFold DB, ESM-2 650M",
        "Reproduce (CLI)": f'python src/predict.py "{run["hgvs"]}" --model {run["model"]}',
    }


def build_report(run):
    """run: dict with hgvs, model, p, level, d, expl, thresholds, time, run_id, baselines, group_names, log."""
    d, expl, p, level = run["d"], run["expl"], run["p"], run["level"]
    gene, change = d.gene.iloc[0], f"{d.aa_ref.iloc[0]}{d.aa_pos.iloc[0]}{d.aa_alt.iloc[0]}"
    facts = findings(d)
    top = expl.reindex(expl.shap.abs().sort_values(ascending=False).index).head(10)
    groups = (expl.assign(g=expl.group.map(lambda g: run["group_names"].get(g, g)))
              .groupby("g").shap.sum().sort_values(key=np.abs, ascending=False))
    meta = _meta(run)
    summary = _summary(p, level, gene, change)
    th = run["thresholds"]
    bl = run["baselines"]
    md_text = _markdown(run, gene, change, summary, facts, top, groups, meta, th, bl)
    html_text = _html(run, gene, change, summary, facts, top, groups, meta, th, bl)
    return html_text, md_text


ARROW = {"path": "▲ towards pathogenic", "benign": "▼ towards benign", "neutral": "• neutral"}


def _markdown(run, gene, change, summary, facts, top, groups, meta, th, bl):
    L = [f"# Variant report: {gene} p.{change}", "",
         f"`{run['hgvs']}` · run `{run['run_id']}` · {meta['Generated']}", "",
         f"> {DISCLAIMER}", "", "## Result", "",
         f"| Calibrated P(pathogenic) | Computational evidence | Model |", "|---|---|---|",
         f"| **{run['p']:.3f}** | **{run['level'].replace('_', ' ')}** | `{run['model']}` |", "",
         summary.replace("**", "**"), ""]
    if run.get("log"):
        L += [f"**Warning during scoring:** {run['log']}", ""]
    L += ["## Key evidence", ""]
    for cat, direction, s in facts:
        L.append(f"- **{cat}** ({ARROW[direction]}): {s}")
    L += ["", "## Top model drivers (SHAP)", "",
          "Positive values push towards pathogenic, negative towards benign (log-odds).", "",
          "| Feature | Value | SHAP |", "|---|---|---|"]
    for _, r in top.iterrows():
        val = f"{r.value:.3g}" if pd.notna(r.value) else "missing"
        L.append(f"| {r.label} | {val} | {r.shap:+.3f} |")
    L += ["", "## Contribution by evidence type", "", "| Evidence type | Summed SHAP |", "|---|---|"]
    L += [f"| {g} | {v:+.3f} |" for g, v in groups.items()]
    if th is not None:
        L += ["", "## Evidence thresholds used (model D, ClinGen local-posterior method)", "",
              "| Strength | PP3 if P ≥ | BP4 if P ≤ |", "|---|---|---|"]
        for k in th.index:
            a, b = th.loc[k, "PP3"], th.loc[k, "BP4"]
            L.append(f"| {k} | {a:.3f} |" if pd.notna(a) else f"| {k} | n/a |")
            L[-1] += f" {b:.3f} |" if pd.notna(b) else " n/a |"
    if bl:
        L += ["", "## Other predictors (comparison only, not model inputs)", "", "| Tool | Score |", "|---|---|"]
        L += [f"| {k} | {v:.3f} |" for k, v in bl.items()]
    L += ["", "## Limitations", ""] + [f"- {x}" for x in LIMITATIONS]
    L += ["", "## Run details", "", "| | |", "|---|---|"] + [f"| {k} | `{v}` |" if k.startswith(("Reproduce", "Model file"))
                                                              else f"| {k} | {v} |" for k, v in meta.items()]
    return "\n".join(L) + "\n"


def _bar_rows(items, scale):
    rows = []
    for label, val, extra in items:
        w = 0 if scale == 0 else min(abs(val) / scale * 50, 50)
        side = "pos" if val > 0 else "neg"
        style = f"left:50%;width:{w:.1f}%" if val > 0 else f"left:{50 - w:.1f}%;width:{w:.1f}%"
        rows.append(f'<tr><td class="lbl">{html.escape(label)}</td><td class="val">{html.escape(extra)}</td>'
                    f'<td class="barcell"><div class="axis"></div><div class="bar {side}" style="{style}"></div></td>'
                    f'<td class="num">{val:+.3f}</td></tr>')
    return "\n".join(rows)


def _html(run, gene, change, summary, facts, top, groups, meta, th, bl):
    e = html.escape
    p, level = run["p"], run["level"]
    tone = "path" if level.startswith("PP3") else "benign" if level.startswith("BP4") else "neutral"
    scale = max(top.shap.abs().max(), 1e-9)
    drivers = _bar_rows([(r.label, r.shap, f"{r.value:.3g}" if pd.notna(r.value) else "missing")
                         for _, r in top.iterrows()], scale)
    gscale = max(groups.abs().max(), 1e-9)
    grows = _bar_rows([(g, v, "") for g, v in groups.items()], gscale)
    facts_html = "\n".join(f'<li class="{d}"><span class="tag">{e(c)}</span> {e(s)}</li>' for c, d, s in facts)
    marker = f"{min(max(p, 0), 1) * 100:.1f}%"
    band = ""
    if th is not None:
        segs, lo = [], 0.0
        for k, c in (("Strong", "#1d4ed8"), ("Moderate", "#3b82f6"), ("Supporting", "#93c5fd")):
            hi = th.loc[k, "BP4"]
            segs.append((lo, hi, c)); lo = hi
        segs.append((lo, th.loc["Supporting", "PP3"], "#d1d5db"))
        for k, nxt, c in (("Supporting", "Moderate", "#fca5a5"), ("Moderate", "Strong", "#ef4444"), ("Strong", None, "#b91c1c")):
            a = th.loc[k, "PP3"]; b = th.loc[nxt, "PP3"] if nxt else 1.0
            segs.append((a, b, c))
        band = "".join(f'<div style="left:{a * 100:.2f}%;width:{(b - a) * 100:.2f}%;background:{c}"></div>'
                       for a, b, c in segs)
    th_rows = ""
    if th is not None:
        th_rows = "".join(f"<tr><td>{e(k)}</td><td>{th.loc[k, 'PP3']:.3f}</td><td>{th.loc[k, 'BP4']:.3f}</td></tr>"
                          if pd.notna(th.loc[k, "PP3"]) else f"<tr><td>{e(k)}</td><td>n/a</td><td>n/a</td></tr>"
                          for k in th.index)
    bl_rows = "".join(f"<tr><td>{e(k)}</td><td>{v:.3f}</td></tr>" for k, v in bl.items())
    meta_rows = "".join(f"<tr><th>{e(k)}</th><td>{'<code>' + e(str(v)) + '</code>' if k.startswith(('Reproduce', 'Model file', 'Run ID')) else e(str(v))}</td></tr>"
                        for k, v in meta.items())
    warn = f'<p class="warn">Warning during scoring: {e(run["log"])}</p>' if run.get("log") else ""
    summary_html = e(summary).replace("**", "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Variant report {e(gene)} p.{e(change)}</title>
<style>
:root {{ --fg:#111827; --muted:#6b7280; --line:#e5e7eb; --path:#b91c1c; --benign:#1d4ed8; --bg:#ffffff; --soft:#f9fafb; }}
* {{ box-sizing:border-box; }}
body {{ font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:var(--fg); background:var(--bg);
       max-width:880px; margin:0 auto; padding:32px 20px; }}
h1 {{ font-size:24px; margin:0 0 4px; }} h2 {{ font-size:16px; margin:28px 0 10px; border-bottom:1px solid var(--line); padding-bottom:4px; }}
.sub {{ color:var(--muted); }} code {{ background:var(--soft); padding:1px 5px; border-radius:4px; font-size:12px; }}
.disc {{ background:#fff7ed; border:1px solid #fed7aa; padding:10px 12px; border-radius:8px; font-size:13px; margin:14px 0; }}
.warn {{ background:#fef2f2; border:1px solid #fecaca; padding:8px 12px; border-radius:8px; }}
.cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:8px 0 12px; }}
.card {{ border:1px solid var(--line); border-radius:10px; padding:12px; background:var(--soft); }}
.card .k {{ color:var(--muted); font-size:12px; }} .card .v {{ font-size:22px; font-weight:700; }}
.v.path {{ color:var(--path); }} .v.benign {{ color:var(--benign); }} .v.neutral {{ color:var(--muted); }}
.scale {{ position:relative; height:14px; border-radius:7px; overflow:hidden; margin:18px 0 4px; background:#eee; }}
.scale div {{ position:absolute; top:0; bottom:0; }}
.mk {{ position:relative; height:0; }} .mk span {{ position:absolute; top:-26px; transform:translateX(-50%); font-size:18px; }}
.ticks {{ display:flex; justify-content:space-between; color:var(--muted); font-size:11px; }}
ul.facts {{ list-style:none; padding:0; margin:0; }} ul.facts li {{ padding:6px 10px; border-left:4px solid var(--line); margin:6px 0; background:var(--soft); }}
ul.facts li.path {{ border-color:var(--path); }} ul.facts li.benign {{ border-color:var(--benign); }}
.tag {{ font-weight:600; margin-right:4px; }}
table {{ border-collapse:collapse; width:100%; }} th,td {{ text-align:left; padding:5px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--muted); font-weight:500; width:190px; }}
table.bars td.lbl {{ width:38%; }} table.bars td.val {{ width:12%; color:var(--muted); font-variant-numeric:tabular-nums; }}
table.bars td.num {{ width:10%; text-align:right; font-variant-numeric:tabular-nums; }}
td.barcell {{ position:relative; width:40%; }} .axis {{ position:absolute; left:50%; top:4px; bottom:4px; border-left:1px solid #9ca3af; }}
.bar {{ position:absolute; top:8px; height:12px; border-radius:2px; }} .bar.pos {{ background:var(--path); }} .bar.neg {{ background:var(--benign); }}
.small {{ font-size:12px; color:var(--muted); }}
@media (max-width:640px) {{ .cards {{ grid-template-columns:1fr; }} th {{ width:auto; }} }}
@media print {{ body {{ padding:0; }} h2 {{ break-after:avoid; }} table, ul.facts li {{ break-inside:avoid; }} }}
</style></head><body>
<h1>Variant report: {e(gene)} p.{e(change)}</h1>
<div class="sub"><code>{e(run['hgvs'])}</code> · run <code>{e(run['run_id'])}</code> · {e(meta['Generated'])}</div>
<div class="disc">{e(DISCLAIMER)}</div>
{warn}
<h2>Result</h2>
<div class="cards">
  <div class="card"><div class="k">Calibrated P(pathogenic)</div><div class="v {tone}">{p:.3f}</div></div>
  <div class="card"><div class="k">Computational evidence</div><div class="v {tone}">{e(level.replace('_', ' '))}</div></div>
  <div class="card"><div class="k">Model</div><div style="font-weight:600;margin-top:6px">{e(run['model'])}</div></div>
</div>
<div class="scale">{band}</div>
<div class="mk"><span style="left:{marker}">▼</span></div>
<div class="ticks"><span>0 · benign (BP4)</span><span>indeterminate</span><span>pathogenic (PP3) · 1</span></div>
<p>{summary_html}</p>
<h2>Key evidence</h2>
<ul class="facts">{facts_html}</ul>
<p class="small">Red = points towards pathogenic, blue = towards benign. Sentences come from fixed rules applied to this run's feature values.</p>
<h2>Top model drivers (SHAP)</h2>
<table class="bars"><tr><th>Feature</th><th>Value</th><th style="text-align:center">← benign · pathogenic →</th><th style="text-align:right">SHAP</th></tr>
{drivers}</table>
<h2>Contribution by evidence type</h2>
<table class="bars"><tr><th>Evidence type</th><th></th><th></th><th style="text-align:right">Sum</th></tr>{grows}</table>
{'<h2>Evidence thresholds used</h2><table><tr><th>Strength</th><th>PP3 if P ≥</th><th>BP4 if P ≤</th></tr>' + th_rows + '</table><p class="small">Model D thresholds from the repository (ClinGen local-posterior method, Pejaver et al. 2022).</p>' if th_rows else ''}
{'<h2>Other predictors</h2><table><tr><th>Tool</th><th>Score</th></tr>' + bl_rows + '</table><p class="small">Shown for comparison only; they are never model inputs.</p>' if bl_rows else ''}
<h2>Limitations</h2>
<ul>{''.join(f'<li>{e(x)}</li>' for x in LIMITATIONS)}</ul>
<h2>Run details</h2>
<table>{meta_rows}</table>
</body></html>
"""


def new_run_id(hgvs, model, t):
    return hashlib.sha1(f"{hgvs}|{model}|{t.isoformat()}".encode()).hexdigest()[:10]


def now():
    return dt.datetime.now().astimezone()
