// Mid-term deck: Prospective, circularity-aware prediction of pathogenic missense variants
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa6 = require("react-icons/fa6");
const gi = require("react-icons/gi");
const { applyTheme } = require("C:/Users/omtil/.claude/skills/synced/dbc5d6ad-38cd-46b6-afa9-5d59a0c1af7c_ca111fba-f5fd-4d5c-adc9-fe1ce149d3d0/pptx/scripts/apply_theme.js");

const PROJ = "C:/Users/omtil/OneDrive/Desktop/Major_project";
const SCR = __dirname;
const OUT = `${PROJ}/Midterm_Presentation_Variant_Prediction.pptx`;

const THEME = {
  name: "Variant Midterm",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "161613", lt1: "FFFFFF", dk2: "5B5A55", lt2: "F9F8F5",
    accent1: "5A4B9C", accent2: "B4473A", accent3: "2F7D74", accent4: "D3D1C9",
    accent5: "EFEDE7", accent6: "E7E3F3", hlink: "5A4B9C", folHlink: "5B5A55",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Prospective, Circularity-Aware Prediction of Pathogenic Missense Variants";
pres.author = "Piyush Gupta, Om Tilwar, Varun Tripathi";
const C = pres.SchemeColor;
const W = 13.333, M = 0.6;

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE",
  background: { color: C.background2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.35, w: 8.6, h: 1.6, fontSize: 38, bold: true, color: C.text1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.1, w: 8.6, h: 0.9, fontSize: 18, color: C.text2, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "SECTION",
  background: { color: C.accent1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 2.6, w: 9.5, h: 1.3, fontSize: 36, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: M, y: 4.05, w: 9.5, h: 1.0, fontSize: 18, color: C.accent6, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.35, w: W - 2 * M, h: 0.8, fontSize: 30, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "IIIT Nagpur · B.Tech Major Project · Mid-term review, Oct 2026", options: { x: M, y: 7.02, w: 8, h: 0.3, fontSize: 10, color: C.text2, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: 7.02, w: 0.6, h: 0.3, fontSize: 10, color: C.text2, align: "right" },
});

// ---------------------------------------------------------------- helpers
async function icon(Comp, color = "#FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
function txt(slide, text, o) {
  slide.addText(text, { isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top", ...o });
}
function card(slide, x, y, w, h, fill = C.background1, name = "card") {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: C.accent4, width: 0.75 }, objectName: name });
}
async function iconCircle(slide, Comp, x, y, d, fill = C.accent1, name = "icon") {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" }, objectName: name + " circle" });
  const pad = d * 0.24;
  slide.addImage({ data: await icon(Comp), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: name });
}
function arrow(slide, x1, y1, x2, y2, color = C.text2) {
  slide.addShape(pres.shapes.LINE, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color, width: 1.5, endArrowType: "triangle" } });
}
function stepBadge(slide, n, label) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: W - M - 3.0, y: 0.12, w: 3.0, h: 0.36, rectRadius: 0.18, fill: { color: C.accent6 }, line: { type: "none" }, objectName: "step badge" });
  txt(slide, `Step ${n} · ${label}`, { x: W - M - 3.0, y: 0.12, w: 3.0, h: 0.36, fontSize: 12, bold: true, color: C.accent1, align: "center", valign: "middle" });
}

(async () => {
  // ============================================================ SECTION 1: framing
  pres.addSection({ title: "Introduction and framing" });

  // ---- 1. Title
  let s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Introduction and framing" });
  s.addImage({ path: `${SCR}/orig_unz/ppt/media/image1.png`, x: M, y: 0.55, w: 1.1, h: 1.1, objectName: "IIITN logo" });
  s.addText("Predicting Pathogenic Missense Variants Before the Experts Do", { placeholder: "title" });
  s.addText("Prospective, circularity-aware evaluation with calibrated and explainable evidence", { placeholder: "body" });
  txt(s, [
    { text: "Mid-term review · B.Tech 4th Year · 2026–27", options: { breakLine: true } },
    { text: "Piyush Gupta · Om Tilwar · Varun Tripathi", options: { bold: true, breakLine: true } },
    { text: "Guide: Dr. Nikhil Dhengre · Department of ECE · IIIT Nagpur" },
  ], { x: M, y: 5.45, w: 8.6, h: 1.0, fontSize: 14, color: C.text2, paraSpaceAfter: 4 });
  s.addImage({ path: `${SCR}/orig_unz/ppt/media/image17.png`, x: 9.75, y: 0.5, w: 2.9, h: 6.5, sizing: { type: "contain", w: 2.9, h: 6.5 }, objectName: "DNA illustration" });
  s.addNotes("Title. Our project predicts whether a single-letter change in a protein-coding gene causes disease. The key word is 'before': we test the model on variants that experts classified only after our training data was frozen. Today we will follow one real variant, TP53 R175H, through the entire pipeline, and then show results.");

  // ---- 2. One variant
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Introduction and framing" });
  s.addText("Our running example: one letter changed in TP53", { placeholder: "title" });
  txt(s, [
    { text: "TP53 is the genome's \"guardian\": a tumour-suppressor gene", options: { bullet: true, breakLine: true } },
    { text: "Chromosome 17, position 7,675,088: one DNA letter changes", options: { bullet: true, breakLine: true } },
    { text: "Codon 175: CGC → CAC, so Arginine (R) becomes Histidine (H)", options: { bullet: true, breakLine: true } },
    { text: "Written as TP53 p.Arg175His, or R175H", options: { bullet: true, breakLine: true } },
    { text: "The most frequent TP53 mutation in cancer; causes Li-Fraumeni syndrome", options: { bullet: true } },
  ], { x: M, y: 1.45, w: 5.3, h: 3.6, fontSize: 16, paraSpaceAfter: 10 });
  card(s, M, 5.35, 5.3, 1.25, C.accent6, "question card");
  txt(s, [{ text: "The question for every such change: ", options: { bold: true } }, { text: "does it break the protein (pathogenic) or is it harmless (benign)?" }],
    { x: M + 0.25, y: 5.5, w: 4.8, h: 1.0, fontSize: 15, valign: "middle" });
  // DNA codon row
  const vx = 6.5;
  txt(s, "DNA (gene strand), codon 175", { x: vx, y: 1.45, w: 6.2, h: 0.35, fontSize: 13, bold: true, color: C.text2 });
  const codon = (x, letters, hi, label) => {
    letters.split("").forEach((l, i) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + i * 0.62, y: 1.9, w: 0.55, h: 0.7, rectRadius: 0.06, fill: { color: i === 1 && hi ? C.accent2 : C.background1 }, line: { color: C.accent4, width: 0.75 }, objectName: `nucleotide ${label} ${i}` });
      txt(s, l, { x: x + i * 0.62, y: 1.9, w: 0.55, h: 0.7, fontSize: 24, bold: true, align: "center", valign: "middle", color: i === 1 && hi ? C.background1 : C.text1 });
    });
    txt(s, label, { x, y: 2.68, w: 1.85, h: 0.35, fontSize: 13, align: "center", color: C.text2 });
  };
  codon(vx, "CGC", false, "normal: Arg (R)");
  arrow(s, vx + 2.05, 2.25, vx + 2.85, 2.25, C.accent2);
  txt(s, "G → A", { x: vx + 1.95, y: 1.85, w: 1.0, h: 0.3, fontSize: 12, bold: true, color: C.accent2, align: "center" });
  codon(vx + 3.05, "CAC", true, "variant: His (H)");
  // Protein strip
  txt(s, "Protein (393 amino acids), residues 171–179", { x: vx, y: 3.35, w: 6.2, h: 0.35, fontSize: 13, bold: true, color: C.text2 });
  const strip = (y, seq, hiColor, label) => {
    seq.split("").forEach((a, i) => {
      const hi = i === 4;
      s.addShape(pres.shapes.OVAL, { x: vx + i * 0.6, y, w: 0.52, h: 0.52, fill: { color: hi ? hiColor : C.background1 }, line: { color: hi ? hiColor : C.accent4, width: 1 }, objectName: `residue ${label} ${171 + i}` });
      txt(s, a, { x: vx + i * 0.6, y, w: 0.52, h: 0.52, fontSize: 16, bold: true, align: "center", valign: "middle", color: hi ? C.background1 : C.text1 });
    });
    txt(s, label, { x: vx + 5.5, y: y + 0.08, w: 1.4, h: 0.4, fontSize: 13, color: C.text2 });
  };
  strip(3.8, "EVVRRCPHH", C.accent3, "normal");
  strip(4.55, "EVVRHCPHH", C.accent2, "variant");
  txt(s, "175", { x: vx + 2.4, y: 5.1, w: 0.52, h: 0.3, fontSize: 12, bold: true, align: "center", color: C.accent2 });
  txt(s, "One amino acid out of 393 changes, yet the protein can no longer bind DNA. Our model must recognise that from evidence alone.",
    { x: vx, y: 5.55, w: 6.2, h: 0.9, fontSize: 14, color: C.text2 });
  s.addNotes("Our guide asked us to explain the pipeline around one example, so we picked the most famous disease mutation. A single G to A change in codon 175 swaps arginine for histidine. We will carry this exact variant through every step: label, features, ESM-2, model, explanation.");

  // ---- 3. Problem
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Introduction and framing" });
  s.addText("The problem: most rare variants have no clear answer", { placeholder: "title" });
  const cls = [
    ["Pathogenic", "Evidence that it causes disease", "61,611 missense variants (P/LP) in ClinVar, Sep 2026", C.accent2, fa6.FaTriangleExclamation],
    ["VUS", "Uncertain significance: not enough evidence yet", "The model's target use case: help resolve these", C.text2, fa6.FaCircleQuestion],
    ["Benign", "Evidence that it is harmless", "140,404 missense variants (B/LB) in ClinVar, Sep 2026", C.accent3, fa6.FaCircleCheck],
  ];
  for (let i = 0; i < 3; i++) {
    const x = M + i * 4.1;
    card(s, x, 1.5, 3.8, 3.0, C.background1, `${cls[i][0]} card`);
    await iconCircle(s, cls[i][4], x + 0.3, 1.8, 0.75, cls[i][3], `${cls[i][0]} icon`);
    txt(s, cls[i][0], { x: x + 0.3, y: 2.75, w: 3.2, h: 0.5, fontSize: 22, bold: true, color: cls[i][3] });
    txt(s, cls[i][1], { x: x + 0.3, y: 3.3, w: 3.2, h: 0.55, fontSize: 15 });
    txt(s, cls[i][2], { x: x + 0.3, y: 3.85, w: 3.2, h: 0.55, fontSize: 12, color: C.text2 });
  }
  card(s, M, 4.85, W - 2 * M, 1.7, C.accent6, "output card");
  txt(s, [
    { text: "What we deliver: ", options: { bold: true } },
    { text: "a calibrated probability that a missense variant is pathogenic, the biological reasons behind it, and the matching ACMG computational-evidence level (PP3 supporting pathogenic / BP4 supporting benign). " },
    { text: "The model learns pathogenic vs. benign only; VUS is \"not yet known\", not a third class.", options: { italic: true } },
  ], { x: M + 0.3, y: 5.0, w: W - 2 * M - 0.6, h: 1.4, fontSize: 15, valign: "middle" });
  s.addNotes("Clinical labs classify variants as pathogenic, benign, or VUS. A computational prediction is one line of evidence in the ACMG guidelines, called PP3 or BP4. Our output is exactly that: a probability, its reasons, and an evidence level. We train only on pathogenic versus benign because VUS means missing evidence, not a biological class.");

  // ---- 4. Why random split is not enough (reframing)
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Introduction and framing" });
  s.addText("Why a random 80/20 split is not enough for this data", { placeholder: "title" });
  txt(s, "Variant databases contain three built-in shortcuts. A random split keeps all three on both sides of the split.",
    { x: M, y: 1.25, w: W - 2 * M, h: 0.45, fontSize: 16, color: C.text2 });
  const sc = [
    ["Labels are reused", "3 of 8", "popular predictors we compare against were trained on ClinVar itself. Testing them on ClinVar rewards memory, not skill", "Grimm 2015: type-1 circularity", fa6.FaRepeat],
    ["Genes carry the label", "77%", "of our 15,264 genes contain only benign labelled variants. A model can learn \"which gene\" instead of \"which change\"", "Grimm 2015: type-2 circularity", fa6.FaDna],
    ["Labels drift over time", "38.6% → 24.4%", "pathogenic share in 2023 labels vs. labels added afterwards. Probabilities tuned on the past mislead on the future", "Dataset shift", fa6.FaClockRotateLeft],
  ];
  for (let i = 0; i < 3; i++) {
    const x = M + i * 4.1;
    card(s, x, 1.9, 3.8, 3.75, C.background1, `shortcut ${i + 1}`);
    await iconCircle(s, sc[i][4], x + 0.3, 2.15, 0.65, C.accent1, `shortcut ${i + 1} icon`);
    txt(s, sc[i][0], { x: x + 1.1, y: 2.2, w: 2.55, h: 0.55, fontSize: 17, bold: true, valign: "middle" });
    txt(s, sc[i][1], { x: x + 0.3, y: 2.95, w: 3.3, h: 0.75, fontSize: i === 2 ? 30 : 40, bold: true, color: C.accent2, valign: "middle" });
    txt(s, sc[i][2], { x: x + 0.3, y: 3.75, w: 3.3, h: 1.3, fontSize: 13.5 });
    txt(s, sc[i][3], { x: x + 0.3, y: 5.2, w: 3.3, h: 0.3, fontSize: 11, italic: true, color: C.text2 });
  }
  card(s, M, 5.85, W - 2 * M, 0.85, C.accent6, "consequence card");
  txt(s, [{ text: "Consequence: ", options: { bold: true } }, { text: "our model scores AUROC 0.992 on a random split. That number is real, but it answers the wrong question." }],
    { x: M + 0.3, y: 5.9, w: W - 2 * M - 0.6, h: 0.75, fontSize: 16, valign: "middle" });
  s.addNotes("This is how we answer 'isn't leakage control just a proper train-test split?'. Here the leakage is in the data, not in the code. First, public labels are reused to train popular tools, so testing them on ClinVar is circular. Second, labels cluster by gene: 77% of our genes have only benign variants, so a random split lets a model memorise genes. Grimm and colleagues in 2015 named these type-1 and type-2 circularity. Third, labels drift: the pathogenic share fell from 38.6% to 24.4%. No random split removes these, so we changed what the test set represents.");

  // ---- 5. Our framing
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Introduction and framing" });
  s.addText("Our framing: test the model the way it will be used", { placeholder: "title" });
  // timeline bar
  const tx0 = M + 0.2, tx1 = W - M - 0.2, ty = 1.95;
  s.addShape(pres.shapes.LINE, { x: tx0, y: ty, w: tx1 - tx0, h: 0, line: { color: C.accent4, width: 3 } });
  s.addShape(pres.shapes.RECTANGLE, { x: tx0, y: ty - 0.09, w: 4.6, h: 0.18, fill: { color: C.accent1 }, line: { type: "none" }, objectName: "training era" });
  s.addShape(pres.shapes.RECTANGLE, { x: tx0 + 4.75, y: ty - 0.09, w: tx1 - tx0 - 4.75, h: 0.18, fill: { color: C.accent2 }, line: { type: "none" }, objectName: "test era" });
  s.addShape(pres.shapes.OVAL, { x: tx0 + 4.55, y: ty - 0.2, w: 0.4, h: 0.4, fill: { color: C.background1 }, line: { color: C.text1, width: 2 }, objectName: "freeze point" });
  txt(s, [{ text: "Knowledge frozen: ClinVar Jan 2023", options: { bold: true, breakLine: true } }, { text: "91,261 labelled variants → training" }], { x: tx0, y: 1.2, w: 4.6, h: 0.6, fontSize: 13 });
  txt(s, [{ text: "Classified later, up to Sep 2026", options: { bold: true, breakLine: true } }, { text: "124,139 new variants → prospective test" }], { x: tx0 + 5.1, y: 1.2, w: 6.5, h: 0.6, fontSize: 13 });
  const qs = [
    ["Will it work on future variants?", "Prospective (time-split) test", "Train on 2023 knowledge, test on what experts decided later", fa6.FaForward],
    ["Will it work on genes it never saw?", "Gene-held-out test", "No gene in both train and test; plus 26,268 test variants in genes new since 2023", fa6.FaDna],
    ["Does it understand the variant, not the gene?", "Mixed-gene test", "Score only genes that contain both pathogenic and benign variants", fa6.FaShuffle],
    ["Can its probability be trusted as evidence?", "Calibration + ClinGen PP3/BP4", "Validated likelihood ratios on the future variants", fa6.FaScaleBalanced],
  ];
  for (let i = 0; i < 4; i++) {
    const x = M + i * 3.07;
    card(s, x, 2.55, 2.85, 3.45, C.background1, `question ${i + 1}`);
    await iconCircle(s, qs[i][3], x + 0.25, 2.8, 0.6, C.accent1, `question ${i + 1} icon`);
    txt(s, qs[i][0], { x: x + 0.25, y: 3.5, w: 2.35, h: 0.8, fontSize: 15, bold: true });
    txt(s, qs[i][1], { x: x + 0.25, y: 4.35, w: 2.35, h: 0.55, fontSize: 14, bold: true, color: C.accent1 });
    txt(s, qs[i][2], { x: x + 0.25, y: 4.9, w: 2.35, h: 1.0, fontSize: 12.5, color: C.text2 });
  }
  txt(s, [{ text: "Why we renamed \"leakage-controlled\": ", options: { bold: true } }, { text: "every ML project avoids leakage. Our contribution is a prospective, circularity-aware evaluation: the test sets are defined by time, gene and label structure, not by random sampling." }],
    { x: M, y: 6.2, w: W - 2 * M, h: 0.65, fontSize: 13.5, color: C.text1 });
  s.addNotes("Instead of one split we ask four questions a clinician would ask. Each question defines a test set. The main one is prospective: we freeze knowledge at January 2023 and evaluate on the 124,139 variants experts classified afterwards. This is like a clinical study that enrols patients after the model is fixed. We also hold out whole genes, test on genes where gene identity gives no hint, and check whether probabilities are trustworthy enough to be clinical evidence.");

  // ---- 6. Literature
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Introduction and framing" });
  s.addText("Literature: two core papers and the gap", { placeholder: "title" });
  const hdr = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.accent1 } } });
  const core = { fill: { color: HEX.accent6 } };
  const rows = [
    [hdr("Study"), hdr("What it showed / built"), hdr("Limitation we address")],
    [{ text: "Grimm et al., 2015 · core", options: { bold: true, ...core } }, { text: "Predictor accuracy is inflated by type-1 (same variants) and type-2 (same genes) circularity", options: core }, { text: "Diagnosed, but built no predictor; no time-based test", options: core }],
    [{ text: "Pejaver et al., 2022 · core", options: { bold: true, ...core } }, { text: "Turned tool scores into ClinGen PP3/BP4 evidence via likelihood ratios", options: core }, { text: "Calibrates existing tools only; small data sets (11,834 variants)", options: core }],
    ["REVEL (Ioannidis 2016)", "Random forest over 13 other tools' scores", "Score of scores: hard to interpret; inherits circularity"],
    ["AlphaMissense (Cheng 2023)", "AlphaFold-based deep model, no ClinVar labels", "Black box; no per-feature explanation"],
    ["ESM1b (Brandes 2023)", "Protein language model, zero-shot scoring", "Ignores population and conservation data"],
    ["CADD (Rentzsch 2019)", "Genome-wide score from proxy labels", "Weaker on clinical missense labels"],
  ];
  s.addTable(rows, { x: M, y: 1.35, w: W - 2 * M, colW: [3.0, 5.0, 4.13], fontSize: 13, color: HEX.dk1, fontFace: "Calibri", border: { type: "solid", color: HEX.accent4, pt: 0.75 }, fill: { color: HEX.lt1 }, rowH: 0.62, valign: "middle", margin: 0.08 });
  card(s, M, 5.95, W - 2 * M, 0.8, C.accent6, "gap card");
  txt(s, [{ text: "Gap: ", options: { bold: true } }, { text: "no open model combines prospective, circularity-aware testing with calibrated, validated evidence levels and explanations in biological terms." }],
    { x: M + 0.3, y: 6.0, w: W - 2 * M - 0.6, h: 0.7, fontSize: 15, valign: "middle" });
  s.addNotes("Two papers define our project. Grimm 2015 showed that published accuracies are inflated by circularity: that defines how we test. Pejaver 2022 showed how to turn a score into clinical evidence with likelihood ratios: that defines our output. The other tools are our baselines; each has a limitation we address.");

  // ============================================================ SECTION 2: one variant through the pipeline
  pres.addSection({ title: "Pipeline: one variant" });
  s = pres.addSlide({ masterName: "SECTION", sectionTitle: "Pipeline: one variant" });
  s.addText("Following TP53 R175H through the pipeline", { placeholder: "title" });
  s.addText("Raw biological data → numbers → model → calibrated, explained answer", { placeholder: "body" });
  const steps = ["Label", "Rarity & conservation", "Protein & structure", "ESM-2", "Model & explanation"];
  for (let i = 0; i < 5; i++) {
    const x = M + i * 2.45;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.5, w: 2.25, h: 0.8, rectRadius: 0.1, fill: { color: C.background1, transparency: 85 }, line: { color: C.accent6, width: 1 }, objectName: `pipeline step ${i + 1}` });
    txt(s, `${i + 1}. ${steps[i]}`, { x, y: 5.5, w: 2.25, h: 0.8, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
  }
  s.addNotes("Now the example our guide asked for. We take TP53 R175H and show exactly what each data source returns and how it becomes numbers for the model.");

  // ---- 8. Step 1: label
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pipeline: one variant" });
  s.addText("ClinVar provides the answer key, never an input", { placeholder: "title" });
  stepBadge(s, 1, "Label");
  card(s, M, 1.4, 6.0, 2.6, C.background1, "raw ClinVar record");
  txt(s, "Raw ClinVar record (variant_summary, Sep 2026)", { x: M + 0.25, y: 1.55, w: 5.5, h: 0.35, fontSize: 13, bold: true, color: C.text2 });
  txt(s, [
    { text: "Name: NM_000546.6(TP53):c.524G>A (p.Arg175His)", options: { breakLine: true } },
    { text: "Assembly / position: GRCh38 · chr17:7,675,088 C>T", options: { breakLine: true } },
    { text: "ClinicalSignificance: Pathogenic", options: { breakLine: true, bold: true, color: HEX.accent2 } },
    { text: "ReviewStatus: reviewed by expert panel (3 stars)", options: { breakLine: true } },
    { text: "Submitters: 39" },
  ], { x: M + 0.25, y: 2.0, w: 5.6, h: 2.0, fontSize: 13.5, fontFace: "Consolas", paraSpaceAfter: 6 });
  arrow(s, M + 3.0, 4.1, M + 3.0, 4.5, C.accent2);
  card(s, M, 4.55, 6.0, 1.45, C.accent6, "label result");
  txt(s, [{ text: "label y = 1 (pathogenic)", options: { bold: true, fontSize: 20, color: HEX.accent2, breakLine: true } },
    { text: "\"Pathogenic\", \"Likely pathogenic\" → 1 · \"Benign\", \"Likely benign\" → 0 · VUS and conflicting → dropped", options: { fontSize: 12.5 } }],
    { x: M + 0.25, y: 4.65, w: 5.5, h: 1.25, valign: "middle" });
  // funnel
  txt(s, "Filtering 9.2 million ClinVar rows", { x: 7.1, y: 1.4, w: 5.6, h: 0.4, fontSize: 15, bold: true });
  const fun = [["All rows", "9,223,698"], ["GRCh38 genome build", "4,578,190"], ["Single-letter changes", "4,238,174"], ["Pathogenic or benign label", "1,528,802"], ["≥ 1 review star", "1,480,512"], ["Missense, de-duplicated", "202,015"]];
  for (let i = 0; i < fun.length; i++) {
    const w = 5.6 - i * 0.55, x = 7.1 + (5.6 - w) / 2, y = 1.95 + i * 0.68;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.56, rectRadius: 0.06, fill: { color: i === fun.length - 1 ? C.accent1 : C.accent6 }, line: { type: "none" }, objectName: `funnel ${i + 1}` });
    txt(s, [{ text: fun[i][1], options: { bold: true } }, { text: "  " + fun[i][0] }], { x, y, w, h: 0.56, fontSize: 13, align: "center", valign: "middle", color: i === fun.length - 1 ? C.background1 : C.text1 });
  }
  txt(s, "Same rules on the Jan 2023 release give 91,261 training variants", { x: 7.1, y: 6.1, w: 5.6, h: 0.5, fontSize: 12, italic: true, color: C.text2, align: "center" });
  s.addNotes("Step 1. From ClinVar we only read the label. TP53 R175H is Pathogenic, reviewed by an expert panel with 39 submitters, so y equals 1. The text classification maps to 1 or 0; VUS and conflicting entries are dropped. The funnel shows how 9.2 million rows become 202,015 clean missense variants. ClinVar is never a feature.");

  // ---- 9. Step 2: rarity and conservation
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pipeline: one variant" });
  s.addText("Is it rare in people? Has evolution preserved this spot?", { placeholder: "title" });
  stepBadge(s, 2, "Population & conservation");
  const row = async (y, Comp, head, raw, rule, out, sub) => {
    card(s, M, y, 6.6, 2.35, C.background1, head);
    await iconCircle(s, Comp, M + 0.25, y + 0.25, 0.6, C.accent1, head + " icon");
    txt(s, head, { x: M + 1.0, y: y + 0.25, w: 5.4, h: 0.6, fontSize: 17, bold: true, valign: "middle" });
    txt(s, [{ text: "Raw: ", options: { bold: true } }, { text: raw }], { x: M + 0.25, y: y + 0.95, w: 6.1, h: 0.45, fontSize: 13.5 });
    txt(s, [{ text: "Encoding: ", options: { bold: true } }, { text: rule }], { x: M + 0.25, y: y + 1.35, w: 6.1, h: 0.45, fontSize: 13.5 });
    txt(s, [{ text: out, options: { bold: true, color: HEX.accent1 } }, { text: "  " + sub, options: { color: HEX.dk2 } }], { x: M + 0.25, y: y + 1.8, w: 6.1, h: 0.45, fontSize: 13.5 });
  };
  await row(1.4, fa6.FaUsers, "gnomAD: how common is it?", "seen in about 4 of every 1,000,000 chromosomes (AF 0.000004)", "log10(AF + 0.0000001); never seen = −7", "af_ex = −5.39", "8 population features");
  await row(4.0, fa6.FaTree, "dbNSFP: is the position conserved?", "phyloP (100 vertebrates) = 6.16 · GERP = 5.48 · SiPhy = 17.1", "scores used as they are (already numbers)", "phylop_100 = 6.16", "9 conservation features");
  s.addChart(pres.charts.BAR, [{ name: "% pathogenic", labels: ["absent", "<1e-5", "1e-5–1e-4", "1e-4–1e-3", "1e-3–1e-2", "≥1%"], values: [72, 38, 22, 10, 2, 0.2] }], {
    x: 7.45, y: 1.4, w: 5.3, h: 4.9, barDir: "col", chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "General\"%\"", dataLabelFontSize: 12, dataLabelColor: HEX.dk1,
    showTitle: true, title: "Share pathogenic by population frequency", titleFontSize: 14, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
    catAxisLabelColor: HEX.dk2, valAxisLabelColor: HEX.dk2, catAxisLabelFontSize: 11, valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
    catAxisTitle: "max gnomAD allele frequency", showCatAxisTitle: true, catAxisTitleFontSize: 11, catAxisTitleColor: HEX.dk2, catAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
  });
  txt(s, "202,015 ClinVar 2026 variants. Common variants are almost never pathogenic, so rarity is strong evidence; we also report rare variants separately.", { x: 7.45, y: 6.35, w: 5.3, h: 0.6, fontSize: 11.5, color: C.text2 });
  s.addNotes("Step 2. gnomAD tells us how common the variant is in hundreds of thousands of people. R175H is extremely rare, about 4 in a million, which we log-transform to minus 5.39. The chart shows why: variants absent from gnomAD are 72% pathogenic, common ones almost never. Conservation scores from dbNSFP show the position is preserved across vertebrates. These become 8 plus 9 numbers.");

  // ---- 10. Step 3: protein and structure
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pipeline: one variant" });
  s.addText("Where in the protein is it, and how buried?", { placeholder: "title" });
  stepBadge(s, 3, "Protein & structure");
  txt(s, "UniProt text annotation → number", { x: M, y: 1.35, w: 6.4, h: 0.4, fontSize: 15, bold: true });
  const ann = [["HELIX 174..176", "inside a helix?", "uni_helix = 1"], ["BINDING 176 (Zn²⁺)", "residues to nearest functional site", "dist_func_site = 1"], ["InterPro: p53 DNA-binding domain", "inside a known domain?", "interpro_domain = 1"], ["393 amino acids long", "position ÷ length", "rel_pos = 0.45"]];
  for (let i = 0; i < ann.length; i++) {
    const y = 1.85 + i * 0.95;
    card(s, M, y, 2.75, 0.75, C.background1, `annotation ${i + 1}`);
    txt(s, ann[i][0], { x: M + 0.12, y, w: 2.55, h: 0.75, fontSize: 12.5, fontFace: "Consolas", valign: "middle" });
    arrow(s, M + 2.8, y + 0.375, M + 3.35, y + 0.375, C.accent1);
    txt(s, [{ text: ann[i][2], options: { bold: true, color: HEX.accent1, breakLine: true } }, { text: ann[i][1], options: { fontSize: 11.5, color: HEX.dk2 } }], { x: M + 3.45, y, w: 3.0, h: 0.75, fontSize: 14, valign: "middle" });
  }
  txt(s, "Only positions are read; names and notes are discarded, so no text and no gene identity reaches the model (17 features).", { x: M, y: 5.75, w: 6.4, h: 0.8, fontSize: 12.5, color: C.text2 });
  // AlphaFold panel
  card(s, 7.3, 1.35, 5.43, 5.25, C.background1, "AlphaFold panel");
  txt(s, "AlphaFold 3-D model, residue 175", { x: 7.55, y: 1.5, w: 5.0, h: 0.4, fontSize: 15, bold: true });
  // contact diagram: center + 21 dots
  const cx = 8.65, cy = 3.65;
  for (let k = 0; k < 21; k++) {
    const a = (2 * Math.PI * k) / 21, r = 1.05;
    s.addShape(pres.shapes.LINE, { x: Math.min(cx, cx + r * Math.cos(a)), y: Math.min(cy, cy + r * Math.sin(a)), w: Math.abs(r * Math.cos(a)), h: Math.abs(r * Math.sin(a)), flipH: (Math.cos(a) < 0) !== (Math.sin(a) < 0), line: { color: C.accent4, width: 0.75 } });
  }
  for (let k = 0; k < 21; k++) {
    const a = (2 * Math.PI * k) / 21, r = 1.05;
    s.addShape(pres.shapes.OVAL, { x: cx + r * Math.cos(a) - 0.09, y: cy + r * Math.sin(a) - 0.09, w: 0.18, h: 0.18, fill: { color: C.accent3 }, line: { type: "none" }, objectName: `contact ${k + 1}` });
  }
  s.addShape(pres.shapes.OVAL, { x: cx - 0.36, y: cy - 0.36, w: 0.72, h: 0.72, fill: { color: C.accent2 }, line: { type: "none" }, objectName: "residue 175" });
  txt(s, "R175", { x: cx - 0.36, y: cy - 0.36, w: 0.72, h: 0.72, fontSize: 12, bold: true, color: C.background1, align: "center", valign: "middle" });
  txt(s, [{ text: "96.6", options: { fontSize: 36, bold: true, color: HEX.accent1, breakLine: true } }, { text: "pLDDT: confidently folded (benign median 64)", options: { fontSize: 12.5 } }], { x: 10.15, y: 2.1, w: 2.4, h: 1.4 });
  txt(s, [{ text: "21", options: { fontSize: 36, bold: true, color: HEX.accent1, breakLine: true } }, { text: "residues within 10 Å: buried (benign median 6)", options: { fontSize: 12.5 } }], { x: 10.15, y: 3.65, w: 2.4, h: 1.4 });
  txt(s, "Contacts = other Cα atoms within 10 Å, skipping the 2 sequence neighbours on each side; residue 175 packs against loops L2 and L3 of the DNA-binding core (3 features).", { x: 7.55, y: 5.35, w: 5.0, h: 1.1, fontSize: 12, color: C.text2 });
  s.addNotes("Step 3. UniProt annotations are text like 'HELIX 174..176' or 'BINDING 176'. We read only the positions and ask simple questions: is residue 175 inside a helix, how far is the nearest functional site. Residue 175 is one residue from a zinc-binding site. From AlphaFold we read the 3-D coordinates: AlphaFold is 96.6% confident, and 21 other residues sit within 10 angstroms, so the residue is buried in the core. Benign variants have a median of only 6 contacts.");

  // ---- 11. Step 4: ESM-2
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pipeline: one variant" });
  s.addText("ESM-2 reads the protein like a language model reads text", { placeholder: "title" });
  stepBadge(s, 4, "ESM-2");
  const flow = [
    ["Input", "Protein sequence (not DNA)", "MEEPQSDPSV … VVRRCPHH … (393 letters)"],
    ["Tokens", "One ID per amino acid", "<cls> M E E P … <eos> → 395 IDs"],
    ["ESM-2 650M", "33 transformer layers, trained on ~65M proteins", "one forward pass on the GPU"],
  ];
  for (let i = 0; i < 3; i++) {
    const x = M + i * 4.1;
    card(s, x, 1.4, 3.75, 1.5, i === 2 ? C.accent6 : C.background1, `esm flow ${i + 1}`);
    txt(s, [{ text: flow[i][0], options: { bold: true, fontSize: 16, color: HEX.accent1, breakLine: true } }, { text: flow[i][1], options: { fontSize: 13, breakLine: true } }, { text: flow[i][2], options: { fontSize: 12, fontFace: "Consolas", color: HEX.dk2 } }],
      { x: x + 0.2, y: 1.5, w: 3.35, h: 1.3, valign: "middle" });
    if (i < 2) arrow(s, x + 3.78, 2.15, x + 4.07, 2.15, C.accent1);
  }
  // outputs
  card(s, M, 3.25, 7.3, 3.4, C.background1, "probabilities panel");
  txt(s, "Output 1: probability of each amino acid at position 175", { x: M + 0.25, y: 3.35, w: 6.9, h: 0.4, fontSize: 14, bold: true });
  s.addChart(pres.charts.BAR, [{ name: "probability", labels: ["R (normal)", "K", "C", "H (variant)", "Q"], values: [0.9992, 0.0003, 0.0001, 0.0001, 0.0001] }], {
    x: M + 0.15, y: 3.75, w: 4.0, h: 2.8, barDir: "bar", chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0000", dataLabelFontSize: 11, dataLabelColor: HEX.dk1,
    catAxisOrientation: "maxMin", valAxisHidden: true, valAxisMaxVal: 1.25, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
  });
  txt(s, [
    { text: "LLR = log p(H) − log p(R)", options: { bold: true, breakLine: true } },
    { text: "= −9.13", options: { fontSize: 34, bold: true, color: HEX.accent2, breakLine: true } },
    { text: "benign median −4.0 · pathogenic −10.2", options: { fontSize: 12, color: HEX.dk2, breakLine: true } },
    { text: "Entropy 0.009: only Arg fits here", options: { fontSize: 12.5 } },
  ], { x: M + 4.3, y: 3.85, w: 2.85, h: 2.6, fontSize: 14 });
  card(s, 8.25, 3.25, 4.48, 3.4, C.background1, "embedding panel");
  txt(s, [
    { text: "Output 2: embedding", options: { bold: true, breakLine: true } },
    { text: "1,280 numbers describing residue 175 in context", options: { breakLine: true } },
  ], { x: 8.5, y: 3.35, w: 4.0, h: 0.85, fontSize: 14 });
  txt(s, "[0.227, 0.078, 0.098, −0.093, −0.444, …]", { x: 8.5, y: 4.25, w: 4.0, h: 0.4, fontSize: 12, fontFace: "Consolas", color: C.text2 });
  arrow(s, 10.5, 4.7, 10.5, 5.05, C.accent1);
  txt(s, [{ text: "PCA → 16 numbers", options: { bold: true, color: HEX.accent1, breakLine: true } }, { text: "PCA fitted on training variants only. Model gets 4 scores + 16 components = 20 features", options: { fontSize: 12, color: HEX.dk2 } }],
    { x: 8.5, y: 5.1, w: 4.0, h: 1.4, fontSize: 15 });
  s.addNotes("Step 4. ESM-2 never sees DNA: its input is the protein's amino-acid sequence. Each letter becomes a token. One forward pass gives, at every position, a probability for each of the 20 amino acids. At position 175 the model is 99.9% sure arginine belongs there; histidine gets 0.0001. The log-likelihood ratio is minus 9.13, strongly damaging. The second output is a 1,280-number embedding, which we compress to 16 numbers with PCA fitted only on training data.");

  // ---- 12. Step 5: model and explanation
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pipeline: one variant" });
  s.addText("110 numbers in, one calibrated and explained answer out", { placeholder: "title" });
  stepBadge(s, 5, "Model & explanation");
  const grp = [["Population", 8], ["Conservation", 9], ["Protein context", 17], ["Structure", 3], ["Amino-acid properties", 53], ["ESM-2", 20]];
  txt(s, "Feature vector for TP53 R175H", { x: M, y: 1.35, w: 3.2, h: 0.4, fontSize: 14, bold: true });
  for (let i = 0; i < grp.length; i++) {
    const y = 1.85 + i * 0.6;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y, w: 3.2, h: 0.5, rectRadius: 0.06, fill: { color: C.accent6 }, line: { type: "none" }, objectName: `feature group ${i + 1}` });
    txt(s, [{ text: grp[i][0] }, { text: `  ${grp[i][1]}`, options: { bold: true, color: HEX.accent1 } }], { x: M + 0.15, y, w: 2.9, h: 0.5, fontSize: 13.5, valign: "middle" });
  }
  txt(s, [{ text: "= 110 numbers", options: { bold: true } }, { text: "  (no text, no gene name)", options: { color: HEX.dk2 } }], { x: M, y: 5.5, w: 3.4, h: 0.4, fontSize: 13.5 });
  const pipe = [["XGBoost", "700 decision trees"], ["Raw score", "0.984"], ["Isotonic calibration", "fitted on held-out genes"], ["P(pathogenic)", "0.985"]];
  for (let i = 0; i < pipe.length; i++) {
    const y = 1.85 + i * 1.0;
    card(s, 4.25, y, 2.6, 0.78, i === 3 ? C.accent6 : C.background1, `model step ${i + 1}`);
    txt(s, [{ text: pipe[i][0], options: { bold: true, breakLine: true } }, { text: pipe[i][1], options: { fontSize: i === 3 ? 18 : 12.5, bold: i === 3, color: i === 3 ? HEX.accent2 : HEX.dk2 } }], { x: 4.4, y, w: 2.35, h: 0.78, fontSize: 13.5, valign: "middle" });
    if (i < 3) arrow(s, 5.55, y + 0.8, 5.55, y + 0.98, C.accent1);
  }
  arrow(s, 3.9, 3.5, 4.2, 3.5, C.accent1);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.25, y: 5.95, w: 2.6, h: 0.6, rectRadius: 0.3, fill: { color: C.accent2 }, line: { type: "none" }, objectName: "evidence badge" });
  txt(s, "ACMG: PP3 Strong", { x: 4.25, y: 5.95, w: 2.6, h: 0.6, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle" });
  s.addImage({ path: `${PROJ}/results/figures/shap_waterfall_TP53_R175H_final.png`, x: 7.15, y: 1.3, w: 5.58, h: 3.98, objectName: "SHAP explanation" });
  txt(s, [{ text: "Why (SHAP): ", options: { bold: true } }, { text: "ESM-2 LLR −9.1 is the strongest push, then burial (21 contacts), rarity in gnomAD, the nearby zinc-binding site and conservation. Same model and output as the live demo." }],
    { x: 7.15, y: 5.65, w: 5.58, h: 0.95, fontSize: 13 });
  s.addNotes("Step 5. All groups together give 110 numbers; no text and no gene name. This is our final model, the same one the live demo uses. XGBoost with 700 trees outputs 0.984; isotonic calibration, fitted on genes held out from training, gives 0.985. That maps to PP3 Strong on the ClinGen scale. SHAP shows what pushed the prediction up: the ESM-2 score most, then burial, rarity, the nearby zinc site and conservation. Protein length also appears, which is the gene-proxy effect we disclose on the last slide. The test-set results come from the 2023-trained version of the same model, which gives 0.993 for this variant. Note: R175H was in training, so this demonstrates the pipeline, not test accuracy.");

  // ============================================================ SECTION 3: results
  pres.addSection({ title: "Evaluation and results" });
  s = pres.addSlide({ masterName: "SECTION", sectionTitle: "Evaluation and results" });
  s.addText("Does it hold up on variants it has never seen?", { placeholder: "title" });
  s.addText("Prospective test · held-out genes · mixed genes · paper replications · honest limits", { placeholder: "body" });
  s.addNotes("Now the results, evaluated the way we framed earlier.");

  // ---- 14. Data at a glance
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation and results" });
  s.addText("Data at a glance", { placeholder: "title" });
  const stats = [["215,400", "missense variants with a confident ClinVar label"], ["91,261", "training variants (ClinVar Jan 2023)"], ["124,139", "prospective test variants (labelled later)"], ["15,264", "genes; 77% contain only benign variants"]];
  for (let i = 0; i < 4; i++) {
    const x = M + i * 3.07;
    card(s, x, 1.45, 2.85, 1.95, C.background1, `stat ${i + 1}`);
    txt(s, stats[i][0], { x: x + 0.2, y: 1.6, w: 2.45, h: 0.9, fontSize: 38, bold: true, color: C.accent1, valign: "middle" });
    txt(s, stats[i][1], { x: x + 0.2, y: 2.55, w: 2.45, h: 0.95, fontSize: 13.5 });
  }
  const src = [["ClinVar", "labels only", fa6.FaClipboardCheck], ["gnomAD", "population frequency", fa6.FaUsers], ["dbNSFP", "conservation", fa6.FaTree], ["UniProt", "protein annotation", fa6.FaBookOpen], ["AlphaFold", "3-D structure", fa6.FaCube], ["ESM-2", "language model", fa6.FaBrain]];
  txt(s, "Six public sources, all processed on one laptop GPU (RTX 4050)", { x: M, y: 4.0, w: W - 2 * M, h: 0.4, fontSize: 15, bold: true });
  for (let i = 0; i < 6; i++) {
    const x = M + i * 2.04;
    await iconCircle(s, src[i][2], x + 0.6, 4.6, 0.7, i === 0 ? C.accent2 : C.accent1, `${src[i][0]} icon`);
    txt(s, [{ text: src[i][0], options: { bold: true, breakLine: true } }, { text: src[i][1], options: { fontSize: 12, color: HEX.dk2 } }], { x, y: 5.4, w: 1.9, h: 0.8, fontSize: 14, align: "center" });
  }
  s.addNotes("215,400 variants across 15,264 genes. We train on what was known in January 2023 and test prospectively on 124,139 variants classified later. All features come from six public sources; ClinVar provides labels only.");

  // ---- 15. Main result
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation and results" });
  s.addText("Prospective test: our model leads every independent tool", { placeholder: "title" });
  const res = [["Ours: XGBoost + ESM-2 (D)", 0.987], ["Ours: XGBoost (C)", 0.984], ["REVEL", 0.975], ["Ours: logistic regression (B)", 0.974], ["AlphaMissense", 0.966], ["ESM1b", 0.940], ["CADD", 0.939], ["Ours: ESM-2 zero-shot", 0.916], ["PrimateAI", 0.890]];
  s.addChart(pres.charts.BAR, [{ name: "AUROC", labels: res.map((r) => r[0]), values: res.map((r) => r[1]) }], {
    x: M, y: 1.35, w: 7.9, h: 5.3, barDir: "bar", catAxisOrientation: "maxMin", valAxisMinVal: 0.85, valAxisMaxVal: 1.0, valAxisMajorUnit: 0.05, valAxisLabelFormatCode: "0.00",
    chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000", dataLabelFontSize: 12, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
    showTitle: true, title: "AUROC on 124,139 variants labelled after Jan 2023", titleFontSize: 14, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
    catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelColor: HEX.dk2, valAxisLabelFontSize: 11, valAxisLabelFontFace: "+mn-lt", valGridLine: { color: HEX.accent4, size: 0.5 }, catGridLine: { style: "none" }, showLegend: false,
  });
  card(s, 8.85, 1.35, 3.88, 1.6, C.background1, "callout lead");
  txt(s, [{ text: "0.987 vs 0.975", options: { fontSize: 28, bold: true, color: HEX.accent1, breakLine: true } }, { text: "vs REVEL, best independent tool; 95% CIs do not overlap (0.986–0.987 vs 0.974–0.976)", options: { fontSize: 12.5 } }], { x: 9.05, y: 1.45, w: 3.5, h: 1.4 });
  card(s, 8.85, 3.15, 3.88, 1.45, C.background1, "callout rare");
  txt(s, [{ text: "0.983", options: { fontSize: 28, bold: true, color: HEX.accent1, breakLine: true } }, { text: "on 71,570 rare variants: the lead holds without the frequency shortcut", options: { fontSize: 12.5 } }], { x: 9.05, y: 3.25, w: 3.5, h: 1.3 });
  card(s, 8.85, 4.8, 3.88, 1.85, C.accent6, "callout circular");
  txt(s, [{ text: "Not shown: ", options: { bold: true } }, { text: "ClinPred (0.980) and MetaRNN (0.985) were trained on ClinVar labels, so their scores are circular and not a fair comparison." }], { x: 9.05, y: 4.9, w: 3.5, h: 1.65, fontSize: 12.5, valign: "middle" });
  s.addNotes("Main result. On the prospective test, our model D reaches AUROC 0.987, ahead of REVEL at 0.975 and AlphaMissense at 0.966, with non-overlapping bootstrap confidence intervals. On rare variants, where the frequency shortcut is unavailable, it still reaches 0.983. ClinPred and MetaRNN are excluded because they were trained on ClinVar itself.");

  // ---- 16. Robustness
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation and results" });
  s.addText("The harder the test, the bigger our lead", { placeholder: "title" });
  txt(s, "Model D across the three test designs (AUROC)", { x: M, y: 1.35, w: 5.2, h: 0.4, fontSize: 14, bold: true });
  const tr = [["Random 80/20", "0.992", "optimistic"], ["Gene-held-out (5-fold)", "0.988", "no gene memorisation"], ["Prospective (time split)", "0.987", "primary result"]];
  for (let i = 0; i < 3; i++) {
    const y = 1.9 + i * 1.05;
    card(s, M, y, 5.2, 0.85, i === 2 ? C.accent6 : C.background1, `test design ${i + 1}`);
    txt(s, [{ text: tr[i][0], options: { bold: true, breakLine: true } }, { text: tr[i][2], options: { fontSize: 12, color: HEX.dk2 } }], { x: M + 0.2, y, w: 3.4, h: 0.85, fontSize: 14, valign: "middle" });
    txt(s, tr[i][1], { x: M + 3.6, y, w: 1.4, h: 0.85, fontSize: 26, bold: true, color: C.accent1, align: "right", valign: "middle" });
  }
  txt(s, "Only 0.005 lost from random to prospective: the features describe the variant, not the gene.", { x: M, y: 5.15, w: 5.2, h: 0.8, fontSize: 13.5, color: C.text2 });
  s.addChart(pres.charts.BAR, [
    { name: "Ours (D)", labels: ["Pure genes", "Mixed genes", "Mixed, 20–80% P"], values: [0.995, 0.979, 0.969] },
    { name: "REVEL", labels: ["Pure genes", "Mixed genes", "Mixed, 20–80% P"], values: [0.993, 0.955, 0.925] },
    { name: "AlphaMissense", labels: ["Pure genes", "Mixed genes", "Mixed, 20–80% P"], values: [0.988, 0.941, 0.940] },
  ], {
    x: 6.3, y: 1.35, w: 6.43, h: 4.6, barDir: "col", barGrouping: "clustered", valAxisMinVal: 0.9, valAxisMaxVal: 1.0, valAxisMajorUnit: 0.025, valAxisLabelFormatCode: "0.000",
    chartColors: [HEX.accent1, HEX.accent4, HEX.dk2], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000", dataLabelFontSize: 10, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
    showTitle: true, title: "Prospective test, split by gene label mix (AUROC)", titleFontSize: 14, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: "+mn-lt", legendColor: HEX.dk1, catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt",
    valAxisLabelColor: HEX.dk2, valAxisLabelFontSize: 10, valAxisLabelFontFace: "+mn-lt", valGridLine: { color: HEX.accent4, size: 0.5 }, catGridLine: { style: "none" },
  });
  txt(s, "Mixed genes contain both pathogenic and benign variants, so knowing the gene gives no hint (Grimm 2015's recommended check). Here our lead over REVEL grows to +0.044.",
    { x: 6.3, y: 6.0, w: 6.43, h: 0.75, fontSize: 12.5, color: C.text2 });
  s.addNotes("Robustness. From random to prospective we lose only 0.005, so the model is not relying on gene memorisation. The right chart is the check Grimm recommended: in pure genes every tool looks perfect, but in mixed genes, where the gene gives no hint, our lead grows. In genes with 20 to 80% pathogenic variants: 0.969 for us versus 0.925 for REVEL and 0.940 for AlphaMissense.");

  // ---- 17. Replications
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation and results" });
  s.addText("Replicating three published results", { placeholder: "title" });
  const rep = [
    ["Brandes et al. 2023", "Protein language model predicts disease variants without labels", "ESM-2 zero-shot LLR on all ClinVar 2026 missense variants (ESM1b in dbNSFP: 0.933)", "Reproduced", C.accent3, "0.906", "AUROC with no training labels"],
    ["Grimm et al. 2015", "Circularity inflates tools trained on database labels", "On variants added after 2023, ClinVar-trained tools get worse while every independent tool gets better", "Reproduced", C.accent3, "−0.006 vs +0.041", "AUROC change: MetaRNN/ClinPred vs CADD"],
    ["Pejaver et al. 2022", "ClinGen thresholds turn REVEL scores into PP3/BP4 evidence", "Our recomputed thresholds have the same structure but are stricter", "Partly reproduced", C.accent1, "6 / 6", "published REVEL levels still pass on 2023→2026 data"],
  ];
  for (let i = 0; i < 3; i++) {
    const x = M + i * 4.1;
    card(s, x, 1.4, 3.8, 5.2, C.background1, `replication ${i + 1}`);
    txt(s, rep[i][0], { x: x + 0.25, y: 1.6, w: 3.3, h: 0.45, fontSize: 18, bold: true });
    txt(s, [{ text: "Claim: ", options: { bold: true } }, { text: rep[i][1] }], { x: x + 0.25, y: 2.15, w: 3.3, h: 0.9, fontSize: 14 });
    txt(s, [{ text: rep[i][5], options: { bold: true, fontSize: 30, color: HEX.accent1, breakLine: true } }, { text: rep[i][6], options: { fontSize: 12, color: HEX.dk2 } }], { x: x + 0.25, y: 3.1, w: 3.3, h: 1.05 });
    txt(s, [{ text: "Our result: ", options: { bold: true } }, { text: rep[i][2] }], { x: x + 0.25, y: 4.25, w: 3.3, h: 1.4, fontSize: 13.5 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.25, y: 5.75, w: 2.4, h: 0.5, rectRadius: 0.25, fill: { color: rep[i][4] }, line: { type: "none" }, objectName: `verdict ${i + 1}` });
    txt(s, rep[i][3], { x: x + 0.25, y: 5.75, w: 2.4, h: 0.5, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
  }
  s.addNotes("We replicated three papers. Brandes: the protein language model alone gives AUROC 0.906. Grimm: tools trained on ClinVar get worse on newer variants while independent tools get better, which is circularity in action. Pejaver: our REVEL thresholds have the same structure but are stricter, and their published thresholds still hold on our newer data.");

  // ---- 18. Honest limits
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation and results" });
  s.addText("What does not work yet", { placeholder: "title" });
  card(s, M, 1.4, 5.9, 2.4, C.background1, "calibration card");
  txt(s, "Probabilities drift on future variants (ECE)", { x: M + 0.25, y: 1.55, w: 5.4, h: 0.45, fontSize: 16, bold: true });
  [["0.004–0.015", "same ClinVar era", C.accent3], ["0.084", "future variants", C.accent2], ["0.065", "+ label-shift correction", C.accent1]].forEach(([v, l, col], k) => {
    txt(s, [{ text: v, options: { bold: true, fontSize: k === 0 ? 20 : 26, color: col, breakLine: true } }, { text: l, options: { fontSize: 12, color: HEX.dk2 } }],
      { x: M + 0.25 + k * 1.85, y: 2.2, w: 1.75, h: 1.0, valign: "middle" });
  });
  txt(s, "Partly caused by label shift: pathogenic share fell from 38.6% to 24.4%.", { x: M + 0.25, y: 3.3, w: 5.4, h: 0.4, fontSize: 12.5, color: C.text2 });
  card(s, M, 4.0, 5.9, 1.25, C.background1, "new genes card");
  txt(s, [{ text: "Genes never labelled before: ", options: { bold: true } }, { text: "AUROC 0.973 vs AlphaMissense 0.986 (only 405 pathogenic variants)" }], { x: M + 0.25, y: 4.1, w: 5.4, h: 1.05, fontSize: 14, valign: "middle" });
  card(s, M, 5.45, 5.9, 1.2, C.background1, "proxy card");
  txt(s, [{ text: "Gene proxy: ", options: { bold: true } }, { text: "protein length partly acts as gene identity (SHAP); we disclose it as a known bias" }], { x: M + 0.25, y: 5.55, w: 5.4, h: 1.0, fontSize: 14, valign: "middle" });
  txt(s, "ClinGen evidence levels validated on future variants", { x: 6.95, y: 1.4, w: 5.8, h: 0.4, fontSize: 15, bold: true });
  const ev = [["PP3 Strong (P ≥ 0.951)", "LR 59.3 ≥ 33.5", true], ["PP3 Moderate", "LR 3.7 < 5.79", false], ["PP3 Supporting", "LR 1.3 < 2.41", false], ["BP4 Supporting", "LR 0.043 ≤ 0.42", true], ["BP4 Moderate", "LR 0.013 ≤ 0.17", true], ["BP4 Strong", "LR 0.005 ≤ 0.03", true]];
  for (let i = 0; i < ev.length; i++) {
    const y = 1.95 + i * 0.75;
    card(s, 6.95, y, 5.78, 0.62, C.background1, `evidence ${i + 1}`);
    await iconCircle(s, ev[i][2] ? fa6.FaCheck : fa6.FaXmark, 7.07, y + 0.1, 0.42, ev[i][2] ? C.accent3 : C.accent2, `evidence ${i + 1} mark`);
    txt(s, ev[i][0], { x: 7.65, y, w: 2.8, h: 0.62, fontSize: 14, bold: true, valign: "middle" });
    txt(s, ev[i][1], { x: 10.4, y, w: 2.2, h: 0.62, fontSize: 13, color: C.text2, valign: "middle", align: "right" });
  }
  txt(s, "4 of 6 levels pass. Fixing mid-range calibration is the main task before the final review.", { x: 6.95, y: 6.5, w: 5.8, h: 0.4, fontSize: 12.5, italic: true, color: C.text2 });
  s.addNotes("We report what fails too. On future variants our probabilities are over-confident; part of the cause is that ClinVar's pathogenic share fell, and our label-shift correction recovers about a quarter of the gap. On genes never labelled before, AlphaMissense still ranks better by AUROC. Of the ClinGen evidence levels, strong pathogenic and all benign levels pass on future variants; moderate and supporting pathogenic do not yet.");

  // ---- 19. Next steps (no dates)
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation and results" });
  s.addText("Next steps", { placeholder: "title" });
  const nxt = [["Recalibrate on recent data", "so the mid-range PP3 levels pass on future variants"], ["Error analysis on unseen genes", "where AlphaMissense still ranks better"], ["Refine the population feature", "exclude sex groups from popmax, then retrain"], ["Optional: lab-measured data", "test on deep mutational scanning (DMS) effects"]];
  const nicons = [fa6.FaScaleBalanced, fa6.FaMagnifyingGlass, fa6.FaUsers, fa6.FaFlask];
  for (let i = 0; i < nxt.length; i++) {
    const x = M + (i % 2) * 6.15, y = 1.9 + Math.floor(i / 2) * 1.85;
    card(s, x, y, 5.95, 1.45, C.background1, `next step ${i + 1}`);
    await iconCircle(s, nicons[i], x + 0.3, y + 0.3, 0.75, C.accent1, `next step ${i + 1} icon`);
    txt(s, [{ text: nxt[i][0], options: { bold: true, fontSize: 19, breakLine: true } }, { text: nxt[i][1], options: { fontSize: 14, color: HEX.dk2 } }], { x: x + 1.3, y: y + 0.25, w: 4.4, h: 0.95, valign: "middle" });
  }
  s.addNotes("Next we will recalibrate on recent data so the mid-range evidence levels pass, study the errors on genes the model has never seen, refine the population-frequency feature and retrain, and optionally validate on lab-measured deep mutational scanning data.");

  // ---- 20. Thank you
  pres.addSection({ title: "Close" });
  s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Close" });
  s.addText("Thank you", { placeholder: "title" });
  s.addText("Questions? Live demo: python src/predict.py \"chr17:g.7675088C>T\"", { placeholder: "body" });
  txt(s, "Research use only: the model gives computational evidence, not a clinical diagnosis.", { x: M, y: 5.6, w: 8.6, h: 0.4, fontSize: 13, italic: true, color: C.text2 });
  s.addImage({ path: `${SCR}/orig_unz/ppt/media/image17.png`, x: 9.75, y: 0.5, w: 2.9, h: 6.5, sizing: { type: "contain", w: 2.9, h: 6.5 }, objectName: "DNA illustration" });
  s.addNotes("Thank you. If time allows, we can run the live demo: the tool fetches every feature for a variant and prints the calibrated probability, the evidence level, and the top reasons.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("written", OUT);
})();
