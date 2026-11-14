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
const OUT = `${PROJ}/Midterm_Presentation_FINAL_10_slides.pptx`;

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
  s.addNotes("Presenter: Piyush. Title. Our project predicts whether a single-letter change in a protein-coding gene causes disease. The key word is 'before': we test the model on variants that experts classified only after our training data was frozen. Today we will follow one real variant, TP53 R175H, through the entire pipeline, and then show results.");

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
  s.addNotes("Presenter: Piyush. Our guide asked us to explain the pipeline around one example, so we picked the most famous disease mutation. A single G to A change in codon 175 swaps arginine for histidine. We will carry this exact variant through every step: label, features, ESM-2, model, explanation.");

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
  s.addNotes("Presenter: Piyush. This is how we answer 'isn't leakage control just a proper train-test split?'. Here the leakage is in the data, not in the code. First, public labels are reused to train popular tools, so testing them on ClinVar is circular. Second, labels cluster by gene: 77% of our genes have only benign variants, so a random split lets a model memorise genes. Grimm and colleagues in 2015 named these type-1 and type-2 circularity. Third, labels drift: the pathogenic share fell from 38.6% to 24.4%. No random split removes these, so we changed what the test set represents.");

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
  s.addNotes("Presenter: Piyush. Instead of one split we ask four questions a clinician would ask. Each question defines a test set. The main one is prospective: we freeze knowledge at January 2023 and evaluate on the 124,139 variants experts classified afterwards. This is like a clinical study that enrols patients after the model is fixed. We also hold out whole genes, test on genes where gene identity gives no hint, and check whether probabilities are trustworthy enough to be clinical evidence.");

  // ---- S5. Steps 1-2: label, rarity, conservation (merged)
  pres.addSection({ title: "Pipeline: one variant" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pipeline: one variant" });
  s.addText("Label from ClinVar; rarity and conservation as features", { placeholder: "title" });
  stepBadge(s, "1–2", "Label & rarity");
  // column 1: ClinVar label
  card(s, M, 1.4, 4.0, 5.25, C.background1, "ClinVar card");
  await iconCircle(s, fa6.FaClipboardCheck, M + 0.25, 1.6, 0.6, C.accent2, "ClinVar icon");
  txt(s, [{ text: "ClinVar → label only", options: { bold: true, breakLine: true } }, { text: "never a model input", options: { fontSize: 12, color: HEX.dk2 } }], { x: M + 1.0, y: 1.6, w: 2.85, h: 0.65, fontSize: 16, valign: "middle" });
  txt(s, [
    { text: "c.524G>A (p.Arg175His)", options: { breakLine: true } },
    { text: "ClinicalSignificance:", options: { breakLine: true } },
    { text: "  Pathogenic", options: { breakLine: true, bold: true, color: HEX.accent2 } },
    { text: "Review: expert panel (3★)", options: { breakLine: true } },
    { text: "Submitters: 39" },
  ], { x: M + 0.25, y: 2.45, w: 3.55, h: 1.65, fontSize: 12.5, fontFace: "Consolas", paraSpaceAfter: 3 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M + 0.25, y: 4.2, w: 3.5, h: 0.6, rectRadius: 0.08, fill: { color: C.accent6 }, line: { type: "none" }, objectName: "label result" });
  txt(s, "label y = 1 (pathogenic)", { x: M + 0.25, y: 4.2, w: 3.5, h: 0.6, fontSize: 17, bold: true, color: C.accent2, align: "center", valign: "middle" });
  txt(s, [{ text: "P/LP → 1 · B/LB → 0 · VUS, conflicting → dropped", options: { breakLine: true } }, { text: "9.2 million ClinVar rows → 202,015 missense variants (91,261 in the Jan 2023 release)" }],
    { x: M + 0.25, y: 4.95, w: 3.55, h: 1.55, fontSize: 12.5, color: C.text2, paraSpaceAfter: 6 });
  // column 2: gnomAD
  const c2 = M + 4.2;
  card(s, c2, 1.4, 4.0, 5.25, C.background1, "gnomAD card");
  await iconCircle(s, fa6.FaUsers, c2 + 0.25, 1.6, 0.6, C.accent1, "gnomAD icon");
  txt(s, [{ text: "gnomAD → 8 features", options: { bold: true, breakLine: true } }, { text: "how common in people?", options: { fontSize: 12, color: HEX.dk2 } }], { x: c2 + 1.0, y: 1.6, w: 2.85, h: 0.65, fontSize: 16, valign: "middle" });
  txt(s, [{ text: "Raw: ", options: { bold: true } }, { text: "AF 0.000004 (4 in a million)", options: { breakLine: true } }, { text: "Rule: ", options: { bold: true } }, { text: "log10(AF + 1e-7); absent = −7", options: { breakLine: true } }, { text: "af_ex = −5.39", options: { bold: true, color: HEX.accent1 } }],
    { x: c2 + 0.25, y: 2.45, w: 3.55, h: 1.2, fontSize: 13, paraSpaceAfter: 4 });
  s.addChart(pres.charts.BAR, [{ name: "% pathogenic", labels: ["absent", "<1e-5", "1e-5–1e-4", "1e-4–1e-3", "1e-3–1e-2", "≥1%"], values: [72, 38, 22, 10, 2, 0.2] }], {
    x: c2 + 0.1, y: 3.75, w: 3.8, h: 2.8, barDir: "col", chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "General\"%\"", dataLabelFontSize: 10, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
    showTitle: true, title: "% pathogenic by allele frequency", titleFontSize: 12, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
    catAxisLabelColor: HEX.dk2, catAxisLabelFontSize: 9, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true, valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
  });
  // column 3: conservation
  const c3 = M + 8.4;
  card(s, c3, 1.4, 3.73, 5.25, C.background1, "conservation card");
  await iconCircle(s, fa6.FaTree, c3 + 0.25, 1.6, 0.6, C.accent1, "conservation icon");
  txt(s, [{ text: "dbNSFP → 9 features", options: { bold: true, breakLine: true } }, { text: "kept by evolution?", options: { fontSize: 12, color: HEX.dk2 } }], { x: c3 + 1.0, y: 1.6, w: 2.6, h: 0.65, fontSize: 16, valign: "middle" });
  [["6.16", "phyloP, 100 vertebrates", "benign median 0.85"], ["5.48", "GERP, 91 mammals", "benign median 0.55"], ["17.1", "SiPhy, 29 mammals", "benign median 8.7"]].forEach(([v, l, b], k) => {
    txt(s, [{ text: v, options: { bold: true, fontSize: 28, color: HEX.accent1, breakLine: true } }, { text: l, options: { fontSize: 13, breakLine: true } }, { text: b, options: { fontSize: 11.5, color: HEX.dk2 } }],
      { x: c3 + 0.25, y: 2.45 + k * 1.3, w: 3.3, h: 1.2 });
  });
  txt(s, "Scores are already numbers: used as they are.", { x: c3 + 0.25, y: 6.1, w: 3.3, h: 0.4, fontSize: 12, italic: true, color: C.text2 });
  s.addNotes("Presenter: Piyush. Steps 1 and 2. ClinVar gives only the answer: R175H is Pathogenic, reviewed by an expert panel, so y = 1. Filtering 9.2 million rows leaves 202,015 clean missense variants. gnomAD tells us how common the variant is: 4 in a million, log-transformed to minus 5.39. The chart shows why this matters: variants absent from gnomAD are 72% pathogenic, common ones almost never. dbNSFP conservation scores show the position is preserved across vertebrates: phyloP 6.16 versus a benign median of 0.85.");


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
  s.addNotes("Presenter: Om. Step 3. UniProt annotations are text like 'HELIX 174..176' or 'BINDING 176'. We read only the positions and ask simple questions: is residue 175 inside a helix, how far is the nearest functional site. Residue 175 is one residue from a zinc-binding site. From AlphaFold we read the 3-D coordinates: AlphaFold is 96.6% confident, and 21 other residues sit within 10 angstroms, so the residue is buried in the core. Benign variants have a median of only 6 contacts.");

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
  s.addNotes("Presenter: Om. Step 4. ESM-2 never sees DNA: its input is the protein's amino-acid sequence. Each letter becomes a token. One forward pass gives, at every position, a probability for each of the 20 amino acids. At position 175 the model is 99.9% sure arginine belongs there; histidine gets 0.0001. The log-likelihood ratio is minus 9.13, strongly damaging. The second output is a 1,280-number embedding, which we compress to 16 numbers with PCA fitted only on training data.");

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
  s.addNotes("Presenter: Om. Step 5. All groups together give 110 numbers; no text and no gene name. This is our final model, the same one the live demo uses. XGBoost with 700 trees outputs 0.984; isotonic calibration, fitted on genes held out from training, gives 0.985. That maps to PP3 Strong on the ClinGen scale. SHAP shows what pushed the prediction up: the ESM-2 score most, then burial, rarity, the nearby zinc site and conservation. Protein length also appears, which is the gene-proxy effect we disclose on the last slide. The test-set results come from the 2023-trained version of the same model, which gives 0.993 for this variant. Note: R175H was in training, so this demonstrates the pipeline, not test accuracy.");

  // ---- S9. Results (merged: main result, mixed genes, replications)
  pres.addSection({ title: "Evaluation and results" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation and results" });
  s.addText("Prospective test: our model leads every independent tool", { placeholder: "title" });
  const res = [["Ours: XGBoost + ESM-2 (D)", 0.987], ["Ours: XGBoost (C)", 0.984], ["REVEL", 0.975], ["Ours: logistic regression (B)", 0.974], ["AlphaMissense", 0.966], ["ESM1b", 0.940], ["CADD", 0.939], ["Ours: ESM-2 zero-shot", 0.916]];
  s.addChart(pres.charts.BAR, [{ name: "AUROC", labels: res.map((r) => r[0]), values: res.map((r) => r[1]) }], {
    x: M, y: 1.35, w: 6.7, h: 5.3, barDir: "bar", catAxisOrientation: "maxMin", valAxisMinVal: 0.85, valAxisMaxVal: 1.0, valAxisMajorUnit: 0.05, valAxisLabelFormatCode: "0.00",
    chartColors: [HEX.accent1], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000", dataLabelFontSize: 12, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
    showTitle: true, title: "AUROC on 124,139 variants labelled after Jan 2023", titleFontSize: 13, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
    catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelColor: HEX.dk2, valAxisLabelFontSize: 11, valAxisLabelFontFace: "+mn-lt", valGridLine: { color: HEX.accent4, size: 0.5 }, catGridLine: { style: "none" }, showLegend: false,
  });
  const rx = 7.55, rw = W - M - rx;
  card(s, rx, 1.35, rw, 1.2, C.background1, "lead callout");
  txt(s, [{ text: "0.987 vs 0.975 (REVEL)", options: { fontSize: 22, bold: true, color: HEX.accent1, breakLine: true } }, { text: "95% CIs do not overlap · rare variants only: 0.983", options: { fontSize: 12.5 } }], { x: rx + 0.2, y: 1.42, w: rw - 0.4, h: 1.05, valign: "middle" });
  s.addChart(pres.charts.BAR, [
    { name: "Ours (D)", labels: ["Pure genes", "Mixed genes (20–80% P)"], values: [0.995, 0.969] },
    { name: "REVEL", labels: ["Pure genes", "Mixed genes (20–80% P)"], values: [0.993, 0.925] },
    { name: "AlphaMissense", labels: ["Pure genes", "Mixed genes (20–80% P)"], values: [0.988, 0.940] },
  ], {
    x: rx, y: 2.7, w: rw, h: 2.75, barDir: "col", barGrouping: "clustered", valAxisMinVal: 0.9, valAxisMaxVal: 1.0, valAxisMajorUnit: 0.05, valAxisLabelFormatCode: "0.00",
    chartColors: [HEX.accent1, HEX.accent4, HEX.dk2], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000", dataLabelFontSize: 9, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt",
    showTitle: true, title: "When the gene gives no hint, our lead grows", titleFontSize: 12, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 10, legendFontFace: "+mn-lt", legendColor: HEX.dk1, catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt",
    valAxisLabelColor: HEX.dk2, valAxisLabelFontSize: 9, valAxisLabelFontFace: "+mn-lt", valGridLine: { color: HEX.accent4, size: 0.5 }, catGridLine: { style: "none" },
  });
  card(s, rx, 5.55, rw, 1.1, C.accent6, "replications");
  txt(s, [{ text: "Replicated: ", options: { bold: true } }, { text: "Brandes 2023 (ESM-2 zero-shot 0.906) · Grimm 2015 (ClinVar-trained tools drop on new variants, independent ones gain) · Pejaver 2022 (published REVEL thresholds still hold)" }],
    { x: rx + 0.2, y: 5.6, w: rw - 0.4, h: 1.0, fontSize: 12, valign: "middle" });
  s.addNotes("Presenter: Om. Results. On the prospective test our model D reaches AUROC 0.987, ahead of REVEL at 0.975 and AlphaMissense at 0.966, with non-overlapping confidence intervals; on rare variants it still reaches 0.983. ClinPred and MetaRNN are not shown because they were trained on ClinVar itself. The small chart is Grimm's recommended check: in genes with both pathogenic and benign variants, where the gene gives no hint, our lead over REVEL grows to 0.044. We also replicated three papers: the protein language model result, the circularity effect, and the ClinGen REVEL thresholds.");

  // ---- S10. Limits, next steps, thank you (merged)
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evaluation and results" });
  s.addText("What does not work yet, and what comes next", { placeholder: "title" });
  txt(s, "ClinGen evidence levels on future variants", { x: M, y: 1.35, w: 6.0, h: 0.4, fontSize: 15, bold: true });
  const ev = [["PP3 Strong (P ≥ 0.951)", "LR 59.3 ≥ 33.5", true], ["PP3 Moderate", "LR 3.7 < 5.79", false], ["PP3 Supporting", "LR 1.3 < 2.41", false], ["BP4 Supporting / Moderate / Strong", "all pass", true]];
  for (let i = 0; i < ev.length; i++) {
    const y = 1.85 + i * 0.62;
    card(s, M, y, 6.0, 0.52, C.background1, `evidence ${i + 1}`);
    await iconCircle(s, ev[i][2] ? fa6.FaCheck : fa6.FaXmark, M + 0.1, y + 0.08, 0.36, ev[i][2] ? C.accent3 : C.accent2, `evidence ${i + 1} mark`);
    txt(s, ev[i][0], { x: M + 0.6, y, w: 3.6, h: 0.52, fontSize: 13.5, bold: true, valign: "middle" });
    txt(s, ev[i][1], { x: M + 4.2, y, w: 1.65, h: 0.52, fontSize: 12.5, color: C.text2, valign: "middle", align: "right" });
  }
  txt(s, [
    { text: "Calibration drifts: ", options: { bold: true } }, { text: "ECE 0.004–0.015 within one era, 0.084 on future variants (0.065 after our label-shift correction)", options: { breakLine: true } },
    { text: "New genes: ", options: { bold: true } }, { text: "AUROC 0.973 vs AlphaMissense 0.986 (only 405 pathogenic)", options: { breakLine: true } },
    { text: "Gene proxy: ", options: { bold: true } }, { text: "protein length partly encodes gene identity (disclosed)" },
  ], { x: M, y: 4.45, w: 6.0, h: 2.2, fontSize: 13, paraSpaceAfter: 8 });
  const nx = 7.15, nw = W - M - nx;
  txt(s, "Next steps", { x: nx, y: 1.35, w: nw, h: 0.4, fontSize: 15, bold: true });
  const plan = [["Recalibrate on recent data", "so the mid-range PP3 levels pass on future variants"], ["Error analysis on unseen genes", "where AlphaMissense still ranks better"], ["Refine the population feature", "exclude sex groups from popmax, then retrain"], ["Optional: lab-measured data", "test on deep mutational scanning (DMS) effects"]];
  plan.forEach(([t, d], i) => {
    const y = 1.85 + i * 0.78;
    s.addShape(pres.shapes.OVAL, { x: nx, y: y + 0.08, w: 0.42, h: 0.42, fill: { color: C.accent1 }, line: { type: "none" }, objectName: `step ${i + 1}` });
    txt(s, String(i + 1), { x: nx, y: y + 0.08, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
    txt(s, [{ text: t, options: { bold: true, breakLine: true } }, { text: d, options: { fontSize: 12, color: HEX.dk2 } }], { x: nx + 0.6, y, w: nw - 0.6, h: 0.65, fontSize: 14, valign: "middle" });
  });
  card(s, nx, 5.15, nw, 1.5, C.accent1, "thank you card");
  txt(s, [{ text: "Thank you. Questions?", options: { bold: true, fontSize: 22, breakLine: true } }, { text: "Live demo: python src/predict.py \"chr17:g.7675088C>T\"", options: { fontSize: 12, fontFace: "Consolas" } }],
    { x: nx + 0.3, y: 5.2, w: nw - 0.6, h: 1.4, color: C.background1, valign: "middle" });
  s.addNotes("Presenter: Om. We are honest about what fails. Strong pathogenic and all benign evidence levels pass on future variants; moderate and supporting pathogenic do not yet, because probabilities drift when ClinVar's class balance shifts. On genes never labelled before, AlphaMissense still ranks better. Next we will recalibrate on recent data so the mid-range levels pass, study the unseen-gene errors, and refine the population-frequency feature. Thank you; we can run the live demo if time allows.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("written", OUT);
})();
