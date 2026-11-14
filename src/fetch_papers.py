"""Resolve and download open-access PDFs for the literature survey via Europe PMC."""
import json, pathlib, re, requests

OUT = pathlib.Path(__file__).resolve().parents[1] / "papers"
OUT.mkdir(exist_ok=True)
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

PAPERS = {
    "01_Richards2015_ACMG": 'TITLE:"Standards and guidelines for the interpretation of sequence variants" AND PUB_YEAR:2015',
    "02_Grimm2015_circularity": 'TITLE:"hindered by two types of circularity"',
    "03_Ioannidis2016_REVEL": 'TITLE:"REVEL: An Ensemble Method for Predicting the Pathogenicity of Rare Missense Variants"',
    "04_Rentzsch2019_CADD": 'TITLE:"CADD: predicting the deleteriousness of variants throughout the human genome" AND PUB_YEAR:2019',
    "05_Pejaver2022_calibration": 'TITLE:"Calibration of computational tools for missense variant pathogenicity classification"',
    "06_Cheng2023_AlphaMissense": 'TITLE:"Accurate proteome-wide missense variant effect prediction with AlphaMissense"',
    "07_Brandes2023_ESM1b": 'TITLE:"Genome-wide prediction of disease variant effects with a deep protein language model"',
    "08_Lin2023_ESM2": 'TITLE:"Evolutionary-scale prediction of atomic-level protein structure with a language model"',
    "09_Bergquist2025_calibration": 'TITLE:"Calibration of additional computational tools expands ClinGen recommendation options"',
    "10_Livesey2023_DMS_benchmark": 'TITLE:"Updated benchmarking of variant effect predictors using deep mutational scanning"',
    "11_Meier2021_ESM1v": 'TITLE:"Language models enable zero-shot prediction of the effects of mutations on protein function"',
    "12_Lundberg2020_TreeSHAP": 'TITLE:"From local explanations to global understanding with explainable AI for trees"',
}

index = []
for key, q in PAPERS.items():
    r = requests.get(API, params={"query": q, "format": "json", "resultType": "core", "pageSize": 5}, timeout=60).json()
    hits = r.get("resultList", {}).get("result", [])
    # prefer an open-access hit with a PMCID, then any OA (preprint), then first hit
    hits.sort(key=lambda h: (h.get("pmcid") is None, h.get("isOpenAccess") != "Y"))
    if not hits:
        print(f"[miss] {key}"); index.append({"key": key, "status": "not found"}); continue
    h = hits[0]
    rec = {"key": key, "title": h.get("title"), "journal": h.get("journalTitle") or h.get("bookOrReportDetails", {}).get("publisher"),
           "year": h.get("pubYear"), "doi": h.get("doi"), "pmid": h.get("pmid"), "pmcid": h.get("pmcid"), "source": h.get("source")}
    pdf_urls = [u["url"] for u in h.get("fullTextUrlList", {}).get("fullTextUrl", []) if u.get("documentStyle") == "pdf" and u.get("availabilityCode") in ("OA", "F")]
    if rec["pmcid"]:
        pdf_urls.insert(0, f"https://europepmc.org/articles/{rec['pmcid']}?pdf=render")
    rec["status"] = "metadata only (not open access - get via institute library)"
    for url in pdf_urls:
        try:
            resp = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
            if resp.ok and resp.content[:4] == b"%PDF":
                (OUT / f"{key}.pdf").write_bytes(resp.content)
                rec["status"], rec["pdf_url"] = "downloaded", url
                break
        except requests.RequestException:
            pass
    print(f"[{rec['status'][:10]}] {key}: {rec['title']} ({rec['year']}) doi:{rec['doi']}")
    index.append(rec)

json.dump(index, open(OUT / "index.json", "w"), indent=2)


# ---- Fallback: PMC Open Access S3 mirror (Europe PMC "render" is bot-blocked) ----
S3 = "https://pmc-oa-opendata.s3.amazonaws.com"
for rec in index:
    if rec.get("status") == "downloaded" or not rec.get("pmcid"):
        continue
    for v in range(1, 8):
        url = f"{S3}/{rec['pmcid']}.{v}/{rec['pmcid']}.{v}.pdf"
        resp = requests.get(url, timeout=120)
        if resp.ok and resp.content[:4] == b"%PDF":
            (OUT / f"{rec['key']}.pdf").write_bytes(resp.content)
            rec["status"], rec["pdf_url"] = "downloaded", url
            print(f"[downloaded via S3] {rec['key']}")
            break
json.dump(index, open(OUT / "index.json", "w"), indent=2)
