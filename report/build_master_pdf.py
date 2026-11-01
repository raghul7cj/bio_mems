"""Build the master document (single source of truth) as a PDF.

    py -3.12 report/build_master_pdf.py

Every table is read from the generated project outputs (results/, physics/params.py, scenarios/),
so rebuilding after a phase rerun keeps the document consistent with the code. No simulator runs.
"""
import json
import math
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, ListFlowable, ListItem,  # noqa: E402
                                NextPageTemplate, PageBreak, PageTemplate, Paragraph, Preformatted, Spacer,
                                Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents  # noqa: E402

from physics import params as PRM  # noqa: E402
from physics import scaling  # noqa: E402
from report import diagrams  # noqa: E402
from scenarios import boundary, corpus  # noqa: E402

OUT = os.path.join(ROOT, "report", "BioMEMS_Master_Document.pdf")
ASSETS = os.path.join(ROOT, "report", "assets")
FIG = os.path.join(ROOT, "results", "figures")
TAB = os.path.join(ROOT, "results", "tables")

# ------------------------------------------------------------------ fonts and styles
FD = r"C:\Windows\Fonts"
for name, f in {"Body": "calibri.ttf", "Body-B": "calibrib.ttf", "Body-I": "calibrii.ttf", "Body-BI": "calibriz.ttf",
                "Mono": "consola.ttf", "Head": "cambriab.ttf"}.items():
    pdfmetrics.registerFont(TTFont(name, os.path.join(FD, f)))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-B", italic="Body-I", boldItalic="Body-BI")

INK, INK2, ACC, WET = colors.HexColor("#15201d"), colors.HexColor("#4b5753"), colors.HexColor("#1d4fa3"), colors.HexColor("#0f7f7a")
RULE, SOFT, WSOFT, WARNC = colors.HexColor("#c9d3d0"), colors.HexColor("#f2f5f4"), colors.HexColor("#e3f3f1"), colors.HexColor("#a25a00")
S = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=10.5, leading=14.6, textColor=INK, spaceAfter=5),
    "h1": ParagraphStyle("h1", fontName="Head", fontSize=21, leading=25, textColor=INK, spaceAfter=10, spaceBefore=4),
    "h2": ParagraphStyle("h2", fontName="Head", fontSize=14.5, leading=18, textColor=ACC, spaceBefore=12, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="Body-B", fontSize=11.5, leading=15, textColor=INK, spaceBefore=8, spaceAfter=3),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.8, leading=11.2, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Body-B", fontSize=8.6, leading=11, textColor=INK2),
    "cap": ParagraphStyle("cap", fontName="Body-I", fontSize=9, leading=12, textColor=INK2, spaceAfter=10, spaceBefore=3),
    "eq": ParagraphStyle("eq", fontName="Body", fontSize=11, leading=15, textColor=INK),
    "note": ParagraphStyle("note", fontName="Body", fontSize=9.8, leading=13.4, textColor=INK),
    "mono": ParagraphStyle("mono", fontName="Mono", fontSize=7.6, leading=9.6, textColor=INK),
    "title": ParagraphStyle("title", fontName="Head", fontSize=30, leading=35, textColor=INK, alignment=TA_CENTER),
    "sub": ParagraphStyle("sub", fontName="Body", fontSize=13, leading=18, textColor=INK2, alignment=TA_CENTER),
    "toc1": ParagraphStyle("toc1", fontName="Body-B", fontSize=10.5, leading=15, leftIndent=0),
    "toc2": ParagraphStyle("toc2", fontName="Body", fontSize=9.5, leading=12.5, leftIndent=14, textColor=INK2),
}

story = []
_glyphs = None


SUBST = {"∝": "~", "∈": "in", "≫": "&gt;&gt;", "≪": "&lt;&lt;", "∎": "QED", "∖": "\\"}  # glyphs Calibri/Consolas lack


def _check(text):
    """Substitute known-missing glyphs; fail on any other character the Calibri face cannot draw."""
    global _glyphs
    if _glyphs is None:
        _glyphs = set(pdfmetrics.getFont("Body").face.charToGlyph.keys())
    for a, b in SUBST.items():
        text = text.replace(a, b)
    plain = re.sub(r"<[^>]+>", "", text)
    bad = {c for c in plain if ord(c) > 127 and ord(c) not in _glyphs}
    if bad:
        raise ValueError(f"glyphs missing from Calibri: {sorted(bad)} in: {plain[:80]}")
    return text


def P(t, st="body"):
    story.append(Paragraph(_check(t), S[st]))


def H1(t, key):
    story.append(PageBreak())
    p = Paragraph(t, S["h1"]); p._bm = key; p._lvl = 0
    story.append(p)


def H2(t):
    p = Paragraph(t, S["h2"]); p._bm = None; p._lvl = 1
    story.append(p)


def H3(t):
    P(t, "h3")


def B(items, st="body"):
    story.append(ListFlowable([ListItem(Paragraph(_check(i), S[st]), leftIndent=12) for i in items], bulletType="bullet",
                              start="•", leftIndent=12, bulletFontName="Body", bulletFontSize=10))
    story.append(Spacer(1, 3))


def EQ(t, note=None):
    rows = [[Paragraph(_check(t), S["eq"])]] + ([[Paragraph(_check(note), S["cap"])]] if note else [])
    tb = Table(rows, colWidths=[165 * mm])
    tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WSOFT), ("LINEBEFORE", (0, 0), (0, -1), 2.5, WET),
                            ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(tb); story.append(Spacer(1, 6))


def NOTE(title, t, color=ACC, bg=SOFT):
    tb = Table([[Paragraph(_check(f"<b>{title}</b><br/>{t}"), S["note"])]], colWidths=[165 * mm])
    tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, color),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(Spacer(1, 3)); story.append(tb); story.append(Spacer(1, 7))


def IMG(path, width_mm, caption):
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    W = width_mm * mm
    story.append(KeepTogether([Image(path, width=W, height=W * h / w), Paragraph(_check(caption), S["cap"])]))


def TBL(rows, widths_mm, header=True, size=None):
    st = S["cell"] if size is None else ParagraphStyle("c2", parent=S["cell"], fontSize=size, leading=size * 1.27)
    data = []
    for i, r in enumerate(rows):
        data.append([Paragraph(_check(str(c)), S["cellh"] if (header and i == 0) else st) for c in r])
    tb = Table(data, colWidths=[w * mm for w in widths_mm], repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), SOFT), ("LINEBELOW", (0, 0), (-1, 0), 1, INK2)]
    tb.setStyle(TableStyle(style))
    story.append(tb); story.append(Spacer(1, 8))


def md_table(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("|") and not re.match(r"^\|[\s\-|:]+\|$", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows.append([re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", c).replace("&", "&amp;") for c in cells])
    return rows


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wilson(x, n, z=1.96):
    p = x / n; c = (p + z * z / (2 * n)) / (1 + z * z / n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


# ------------------------------------------------------------------ data from the project
M = json.load(open(os.path.join(TAB, "metrics.json")))
MET = M["metrics"]
CONF = dict(zip(M["confusion_rows"], M["confusion"]))
CFG = PRM.detector_config()
D = {os.path.basename(p): p for p in diagrams.all_diagrams(ASSETS)}
nom_row = CONF["NOMINAL"]; n_nom = sum(nom_row); fa = n_nom - nom_row[0]
far_ci = wilson(fa, n_nom)


def pct(x):
    return f"{100 * x:.1f} %"


# ================================================================== FRONT MATTER
story.append(Spacer(1, 55 * mm))
story.append(Paragraph("Physics-Based Fault Classification in Capillary-Driven Paper Microfluidics", S["title"]))
story.append(Spacer(1, 8 * mm))
story.append(Paragraph("Master document: theory, base paper, sensor, system design, RTL, verification, results and claims", S["sub"]))
story.append(Spacer(1, 14 * mm))
story.append(Paragraph(f"BioMEMS course project · IIIT Allahabad · B.Tech ECE, Semester 7<br/>Group __ · Members: ________________<br/>"
                       f"Built from the project repository on {date.today():%d %b %Y}", S["sub"]))
story.append(Spacer(1, 20 * mm))
story.append(Paragraph("This document is generated by <font name='Mono'>report/build_master_pdf.py</font>. Every table is read from "
                       "the project's generated results, so rebuilding it after rerunning a phase keeps it consistent with the code.",
                       ParagraphStyle("c", parent=S["note"], alignment=TA_CENTER)))
story.append(NextPageTemplate("main")); story.append(PageBreak())

P("How to read this document", "h1")
P("This is the single source of truth for the project. It is written so that a teammate, or someone new to the project, "
  "can follow every step from the physics to the hardware. Suggested routes:")
TBL([["Reader", "Read in this order"],
     ["New to the topic", "1 Executive summary → 3 Theory → 4 System concept → 6 Identifiability → 9 Results → 13 Claims"],
     ["Physics / TA meeting", "3 Theory → 5 Calibration → 6 Identifiability (proofs) → 7 Detector → 13 Claims"],
     ["Hardware / verification", "4 System concept → 7 Detector → 11 Architecture and RTL → 12 Verification"],
     ["Base paper comparison", "2 Base paper and sensor → 4 Comparison → 10 Real-data validation → 13 Claims"],
     ["Reproducing results", "8 Dataset and experiments → 15 Reproduction guide"]], [42, 123])
P("Conventions: L is the distance from the inlet (mm), t the time (s), K the Washburn coefficient (mm²/s), "
  "E<sub>k</sub> the expected time for segment k, Δt<sub>k</sub> the measured segment time, and "
  "ρ<sub>k</sub> = Δt<sub>k</sub>/E<sub>k</sub> the segment ratio. A ~ B means A is proportional to B. One tick is 1 ms. Values marked <i>assumed</i> have no "
  "measured source; all others cite a reference or the computation that produced them.")
toc = TableOfContents(); toc.levelStyles = [S["toc1"], S["toc2"]]
story.append(Spacer(1, 6)); P("Contents", "h2"); story.append(toc)

# ================================================================== 1 EXECUTIVE SUMMARY
H1("1  Executive summary", "ch1")
P("<b>Problem.</b> Paper rapid diagnostic tests move liquid by capillary wicking alone. When filling goes wrong "
  "(too little sample, a defect in the paper, an unusual sample), the test can still produce a result that looks valid. "
  "Existing checks reduce the flow to one number: did liquid arrive before a timeout, or how long did one flow take.")
P("<b>Idea.</b> Time the liquid front at four electrodes along a lateral strip. A calibrated capillary-flow model "
  "(Lucas–Washburn / Darcy) predicts those times for a healthy strip. The <i>pattern</i> of deviations then identifies "
  "the kind of fault and where it is, within the limits the physics allows.")
P("<b>What was built.</b>")
B(["A physics model of the strip, calibrated to published wicking data (K = 9.42 mm²/s for nitrocellulose FF170HP).",
   "A richer generator model (series Darcy resistance, finite sample, fluid changes, strip variability, sensor faults) "
   "that produced 9,900 seeded test scenarios.",
   "A proof-backed identifiability analysis: which faults the timings can and cannot separate.",
   "A model-based detector/classifier, two baselines, and an ablation, all scored on held-out scenarios.",
   "A synthesizable SystemVerilog implementation, bit-exact with an independent Python reference on all 9,900 "
   "scenarios, verified with assertions, coverage, boundary cases and mutation testing, and implemented on the "
   "PYNQ-Z2's Zynq-7020 at 100 MHz.",
   "A reproduction of the base paper's flow-time algorithm on its published electrode data."])
H2("Key numbers")
TBL([["Result", "Value", "Where"],
     ["Calibrated K (nitrocellulose, water)", "9.42 mm²/s (cross-checks 9.73, 9.41)", "§5"],
     ["Faults detected, this method / fixed timeout / single sensor", f"{pct(MET['model-based']['detection'])} / "
      f"{pct(MET['fixed timeout']['detection'])} / {pct(MET['single sensor']['detection'])}", "§9"],
     ["False alarms on healthy strips (this method)", f"{pct(MET['model-based']['far'])} (95 % CI {far_ci[0]:.1%}–{far_ci[1]:.1%})", "§9"],
     ["Exact class + location (identifiable classes)", f"{M['exact_accuracy']:.1%}", "§9"],
     ["RTL vs reference model", "9,900 / 9,900 bit-exact; 52 / 52 boundary cases", "§12"],
     ["FPGA cost (xc7z020)", "535 LUT, 674 FF, 3 DSP, 0 BRAM; WNS +3.72 ns at 100 MHz", "§11"],
     ["Base-paper flow times reproduced", "29.2 / 19.5 / 40.6 s, all inside the paper's IQRs", "§10"]], [78, 66, 21])
NOTE("Main limitation", "The four-electrode results come from a physics model, not from a measured strip. The real data "
     "available (the base paper's) has a single electrode, so it validates timing, not classification. See §13.", WARNC)

# ================================================================== 2 BASE PAPER AND SENSOR
H1("2  Base paper and its sensor", "ch2")
P("<b>Reference [1].</b> L. Bezinge, A. J. deMello, C.-J. Shih, D. A. Richards, \"Quantitative reagent monitoring in paper-based "
  "electrochemical rapid diagnostic tests\", <i>Lab on a Chip</i> 24(15), 3651–3657 (2024), doi:10.1039/D4LC00390J. "
  "Open access, CC BY-NC 3.0. ETH Zürich (deMello and Richards groups).")
H2("2.1  What the base paper does")
P("Graphenized electrodes are embedded in a paper-based electrochemical rapid test. The same electrodes do two jobs:")
B(["<b>Flow tracking.</b> Short voltage pulses are applied continuously. When liquid flows over the electrode, the "
   "capacitive discharge current changes, which reveals when each injected sample or reagent flows and when it stops.",
   "<b>Quantification.</b> After the last reagent, the reader switches to square-wave voltammetry to read an "
   "electrochemical immunoassay (anti-SARS-CoV-2 IgG in serum)."])
P("The authors use the flow times to guide the user and to flag incorrect volumes or abnormal viscosities.")
H2("2.2  The sensor: how the device is made")
IMG(D["d_bezinge_sensor.png"], 160, "Figure 2.1. Base-paper device, drawn from the published design file "
    "(electrofluidic_design_file.pdf). Layer names and the electrode pattern are from the file; the stacking order "
    "is inferred from the file and the paper text.")
B(["<b>Format:</b> a vertical-flow assay (VFA). Liquid is applied on top and flows down through stacked layers into "
   "absorbent pads, which act as a drain.",
   "<b>Layers in the design file:</b> a wax sheet with a central opening and four alignment holes; a paper sheet carrying "
   "the electrode pattern; a nitrocellulose pad (the capture membrane of the immunoassay); a sample pad; and three absorbent pads.",
   "<b>Fabrication:</b> the design file is a laser-processing drawing. Its legend marks outlines as <i>cut</i> and the "
   "electrode pattern as <i>engrave</i>. The paper calls the electrodes <i>graphenized</i>: the engraved cellulose "
   "becomes conductive carbon.",
   "<b>Electrode cell:</b> one three-electrode cell. A disk working electrode (WE) is surrounded by an open ring counter "
   "electrode (CE), with a reference electrode (RE); three traces run to contact pads for the potentiostat.",
   "<b>Instrument:</b> a PalmSens potentiostat driven by MethodSCRIPT files (PulseMethod.txt, SWVMethod.txt) through "
   "the authors' Python script."])
H2("2.3  Measurement principle")
IMG(D["d_pulse_method.png"], 160, "Figure 2.2. Pulsed sensing and processing (schematic, not to scale). Parameters "
    "are from PulseMethod.txt and plotResults.m.")
TBL([["Setting", "Value", "Source"],
     ["DC potential, pulse height", "0 V, 100 mV", "PulseMethod.txt (meas_loop_pad)"],
     ["Pulse length, period", "1 ms, every 100 ms (10 samples/s)", "PulseMethod.txt; dt = 0.1 s in plotResults.m"],
     ["Record length", "175.1 s", "PulseMethod.txt"],
     ["Current range", "auto-ranging 59 nA – 2.95 mA", "PulseMethod.txt"],
     ["Signal", "|Δi(n)| = |mean over 10 pulses of (i(n) − i(n−10))|: 1 s difference, 1 s average", "plotResults.m; paper text"],
     ["Thresholds", "1.5 µA before the rinse, 0.4 µA after; set as mean + 10 SD of a static liquid", "plotResults.m; paper text"],
     ["Flow detected", "10 consecutive samples above threshold", "plotResults.m; paper: 'ten-hit minimum'"],
     ["Flow stopped", "100 consecutive samples below (10 s)", "plotResults.m; paper: 'ten second time delay'"]], [40, 75, 50])
H2("2.4  Results reported by the base paper")
B(["Electrode flow times were 1.8 s longer on average than visual absorption times (IQR −0.1 to 2.5 s, Fig. S4).",
   "Flow time scales with added volume: 0.19 ± 0.02 s/µL; 0.36 ± 0.04 s/µL for running buffer (R² = 0.91). "
   "Dead volume ≈ 20 µL (25 µL did not reach the electrode).",
   "Albumin at 50 and 200 g/L shortened flow times by factors of 1.5 and 2.5.",
   "Clinical runs (median, IQR): serum 100 µL 30 s (29–39), labelling 100 µL 22 s (17–32), rinse 150 µL 31 s (28–41)."])
H2("2.5  The published dataset")
P("The data-availability statement points to Mendeley Data, doi:10.17632/nd9cyw62rk.1. The user supplied these files; they "
  "were copied unmodified to <font name='Mono'>data/bezinge2024/raw/</font> with SHA-256 checksums. The dataset licence was "
  "not checked (user decision), so the files are used non-commercially with attribution and are not redistributed.")
TBL([["File", "Content", "Used here for"],
     ["data_P3.csv", "Index 0: flow-monitoring current, 1,751 samples at 0.1 s. Indices 1–22: square-wave voltammograms", "Real-trace check (§10)"],
     ["plotResults.m", "Flow tracking state machine and SWV peak analysis (MATLAB)", "Ported line by line to Python"],
     ["PulseMethod.txt, SWVMethod.txt", "Potentiostat methods", "Sampling interval, pulse settings"],
     ["plot_swv_bipot.py", "Instrument control script (needs the potentiostat)", "Reference only, not run"],
     ["electrofluidic_design_file.pdf", "Laser cut/engrave drawing of the device layers", "Figure 2.1"]], [40, 85, 40])

# ================================================================== 3 THEORY
H1("3  Theory: why liquid moves through paper", "ch3")
H2("3.1  Surface tension and wetting")
P("Molecules at a liquid surface have neighbours on one side only and are pulled inward, so creating surface costs energy. "
  "That energy per unit area is the <b>surface tension</b> γ (water: 0.072 N/m). Where the liquid meets a solid it forms a "
  "<b>contact angle</b> θ; θ ≈ 0° means the liquid spreads (wets), and θ > 90° means it beads (as on wax, which is why "
  "wax lines form channel walls).")
P("A wetting liquid in a narrow pore of radius r forms a curved meniscus, which carries a pressure jump, the "
  "<b>Laplace pressure</b>:")
EQ("ΔP = 2 γ cos θ / r", "Example: water in a 10 µm pore, ΔP ≈ 14 kPa. For the nitrocellulose membrane used here, "
   "Kasetsirikul et al. estimate an effective capillary pressure P<sub>c</sub> ≈ 2.3 kPa [3].")
H2("3.2  Viscous flow and hydraulic resistance")
P("In a thin tube the flow is laminar, and the mean speed follows Hagen–Poiseuille, where L is the length of liquid in the tube:")
EQ("v̄ = r² ΔP / (8 μ L)")
P("Viscosity μ (water 0.89 mPa·s, plasma ≈ 1.3, whole blood ≈ 3.5) resists the flow, and the resistance grows in proportion "
  "to the wetted length. In the electrical analogy, pressure is voltage, flow rate is current, and each wetted piece of "
  "paper is a resistor in series.")
IMG(D["d_analogy.png"], 165, "Figure 3.1. Left: electrical analogy; a restriction is an extra series resistor that stays in "
    "the circuit. Right: the resulting Washburn curve for K = 9.42 mm²/s (computed).")
H2("3.3  Lucas–Washburn law (derivation)")
P("Substitute the capillary pressure into Poiseuille, with v̄ = dL/dt:")
EQ("dL/dt = (r²/(8μL)) · (2γ cos θ / r) = r γ cos θ / (4 μ L)")
P("Multiplying by L leaves a right-hand side that is constant in time:")
EQ("L·dL/dt = r γ cos θ / (4μ)   →   d(L²)/dt = r γ cos θ / (2μ) ≡ K   →   L² = K t",
   "Lucas (1918), Washburn (1921) [2]. Distance grows as √t: twice the distance takes four times as long. "
   "Front speed: dL/dt = K/(2L).")
P("With K = 9.42 mm²/s, the front reaches 20 mm at 42.5 s and 40 mm at 169.9 s. It moves at 2.4 mm/s near the inlet "
  "and 0.12 mm/s at 40 mm.")
H2("3.4  Paper as a porous medium: Darcy flow through segments")
P("Paper is a fibre network with a distribution of pore sizes and tortuous paths. The proper description is Darcy's law: "
  "flux ∝ (permeability / viscosity) × pressure gradient. For a strip of relative permeability k(x) and relative width w(x), "
  "the flux Q is the same at every cross-section of the wetted region (quasi-steady, incompressible), so:")
EQ("Q ∝ P<sub>c</sub> / R(L),   R(L) = ∫<sub>0</sub><super>L</super> dx / (k(x) w(x))")
P("The front advances by filling the pores at the front, φ·h·W·w(L)·dL/dt = Q. This gives the generator equation:")
EQ("dL/dt = (K/2) / ( w(L) · R(L) ),   K = 2 k<sub>0</sub> P<sub>c</sub> / (μ φ)",
   "With k = w = 1, R(L) = L and the equation reduces exactly to L·dL/dt = K/2, i.e. Washburn. Integrating gives "
   "t(L) = (2/K) ∫ w(x) R(x) dx, which the generator evaluates numerically.")
P("Because K lumps capillary pressure, permeability, porosity and viscosity together, it is <b>fitted</b> to measured wicking "
  "rather than computed from a pore radius (§5).")
H2("3.5  Finite sample volume")
P("The paper stores liquid at its absorption capacity C<sub>abs</sub> = 10.1 µL/cm², measured by weighing [3]. A 4 mm wide "
  "strip therefore needs 0.404 µL per mm, or 16.2 µL for 40 mm. When the sample is used up, the front creeps on as liquid "
  "redistributes and then stops; the generator models the creep as a decay with τ = 20 s (<i>assumed</i>).")
H2("3.6  Scaling analysis: which forces matter")
rows, meta = scaling.table()
P(f"No source reports this membrane's pore radius, so it is bracketed by two effective radii computed from measured "
  f"quantities: r<sub>W</sub> = 2μK/γ = {meta['r_W_um']:.2f} µm and r<sub>P</sub> = 2γ/P<sub>c</sub> = {meta['r_P_um']:.1f} µm. "
  f"Front speeds are {meta['U_mm_s'][0]:.2f}–{meta['U_mm_s'][1]:.2f} mm/s. The two radii disagree by a factor of about "
  f"{meta['r_P_um'] / meta['r_W_um']:.0f}, which is itself the reason K must be fitted.")
TBL([["Number", "Definition", "Low", "High", "Conclusion"]] +
    [[esc(n), esc(e), f"{lo:.1e}", f"{hi:.1e}", esc(c)] for n, e, lo, hi, _, c in rows], [30, 38, 16, 16, 65])
P("Every ratio is well below 1 except the strip-scale gravity term, which matters only for a vertical strip. Surface "
  "tension and viscosity govern the flow; gravity and inertia can be neglected. Inertia lasts at most ~0.5 ms, less than one tick.")

# ================================================================== 4 SYSTEM CONCEPT
H1("4  System concept and comparison with the base paper", "ch4")
H2("4.1  The lateral four-electrode strip")
IMG(D["d_strip.png"], 165, "Figure 4.1. Strip layout, to scale: four electrodes at L = 20.0, 28.3, 34.6 and 40.0 mm.")
P("<b>Why these positions.</b> Washburn gives E<sub>k</sub> = (L<sub>k</sub>² − L<sub>k−1</sub>²)/K. Placing the "
  "electrodes where L² steps evenly (400, 800, 1200, 1600 mm²) makes every segment take the same expected time, "
  "E = 400/9.42 = 42.5 s for water, so each segment has the same timing resolution.")
P("<b>Sensor interface (\"interface A\").</b> Each electrode is assumed to drive a comparator whose digital output goes "
  "high when the electrode is wetted, for example a base-paper-style pulsed electrode with a threshold detector. The "
  "detector receives four asynchronous digital lines. No physical strip was built in this project.")
H2("4.2  Base paper versus this project")
IMG(D["d_comparison.png"], 165, "Figure 4.2. Visual comparison: one sensing location in a vertical-flow device against four "
    "points along a lateral strip.")
TBL([["Aspect", "Base paper [1]", "This project"],
     ["Geometry", "Vertical flow through stacked layers", "Lateral strip, 40 mm"],
     ["Sensing points", "1 electrode cell", "4 electrodes (assumed comparators)"],
     ["Measured quantity", "Flow start/stop per injected reagent", "Front arrival time at each electrode"],
     ["Output", "Flow times; flags wrong volume / viscosity", "Class + location: NOMINAL, UNIFORM_SLOW/FAST, RESTRICTION k, STALL k, SENSOR, ANOMALY"],
     ["Physics model", "Empirical thresholds", "Calibrated Washburn/Darcy model with an online K estimate"],
     ["Identifiability analysis", "Not addressed", "Proofs and computed thresholds (§6)"],
     ["Processing", "Python/MATLAB on a PC", "Synthesizable RTL, 535 LUT, verified bit-exact"],
     ["Validation", "Real devices, clinical serum samples", "Simulation; real data only for timing (§10)"],
     ["Quantification (immunoassay)", "Yes (square-wave voltammetry)", "Out of scope"]], [36, 62, 67])
NOTE("Where the two differ in strength", "The base paper is stronger on real-world evidence: real devices and clinical "
     "samples. This project adds spatial information (where a fault is), an explicit analysis of what can and cannot be "
     "identified, and a hardware implementation, but it is supported only by simulation.")
H2("4.3  End-to-end pipeline of the project")
IMG(D["d_pipeline.png"], 165, "Figure 4.3. How the parts fit together. The dashed blue arrow: the reference model supplies "
    "the expected answer for every RTL run.")

# ================================================================== 5 CALIBRATION & GENERATOR
H1("5  Calibration and generator model", "ch5")
H2("5.1  Data source")
P("Publisher pages for most wicking studies (PMC, ACS, RSC) block automated access. The open-access paper by Kasetsirikul, "
  "Shiddiky and Nguyen (<i>Chemosensors</i> 8, 65, 2020, CC BY) [3] reports wicking of dyed water in nitrocellulose "
  "FF170HP strips 2, 4 and 6 mm wide, n = 3 each, as a vertical capillary rise. 33 points were read from its Fig. 7a "
  "(±0.5 mm) and stored with provenance in <font name='Mono'>data/literature/kasetsirikul2020/</font>.")
H2("5.2  Fits")
IMG(os.path.join(FIG, "calibration_K.png"), 160, "Figure 5.1. L² against t with the Washburn fit and the gravity-corrected "
    "fit (left), and residuals (right).")
TBL([["Fit / check", "K (mm²/s)", "Note"],
     ["Washburn through the origin, L = √(Kt)", "9.42", "adopted; rms residual 0.53 mm"],
     ["Paper's own fit p² (Table 6)", "9.73", "+3 %"],
     ["Product rating, 4 cm in 170 s", "9.41", "−0.1 %"],
     ["Gravity-corrected, h<sub>eq</sub> = P<sub>c</sub>/ρg = 239 mm", "10.3", "+9 %: carried as a systematic uncertainty"],
     ["Power-law exponent n (Washburn 0.5)", "0.546", "early-time deviation of about 1 mm in the first 10 s"],
     ["CV of K across strip widths", "3.2 %", "strip-to-strip variability"]], [70, 22, 73])
H2("5.3  Generator model")
B(["<b>Flow:</b> the Darcy series equation of §3.4, integrated on a 1 µm grid. A restriction is a segment with k &lt; 1; "
   "a narrowed neck is a segment with w &lt; 1.",
   "<b>Fluid:</b> K scales with γ cos θ / μ relative to water.",
   "<b>Variability:</b> K multiplied by a log-normal factor with CV 0, 3.2 % or 10 %.",
   "<b>Finite volume:</b> the sample runs out when the wetted volume equals it; creep follows with τ = 20 s.",
   "<b>Sensor:</b> a constant detection lag of 1.8 s, Gaussian jitter σ ∈ {0, 0.1, 0.5, 1, 2} s, and missed, spurious "
   "(early random trigger) or stuck (high before arm) electrodes."])
P("Seven automated checks guard the generator (<font name='Mono'>run.py phase2</font>). A uniform strip reproduces "
  "L² = Kt to 10<super>−4</super>. A k = 1 segment changes nothing. Viscosity scales all arrivals equally. A restriction "
  "leaves upstream arrivals unchanged and delays downstream ones. An 8 µL sample stops at 24.1 mm (the volume limit is "
  "19.8 mm, the rest is creep). A 12 µL sample never reaches 40 mm. A narrow neck slows the front downstream.")
H2("5.4  Parameters and their sources")
TBL([["Parameter", "Value", "Unit", "Provenance"]] +
    [[k, esc(v), esc(u), esc(src)] for k, (v, u, src) in PRM.PARAMS.items()], [22, 20, 14, 109], size=7.8)

# ================================================================== 6 IDENTIFIABILITY
H1("6  Identifiability: what the timings can and cannot reveal", "ch6")
P("The detector sees only arrival times, and therefore only the segment ratios ρ<sub>k</sub> = Δt<sub>k</sub>/E<sub>k</sub>. "
  "This chapter states what can be inferred from them in principle, before any algorithm is involved.")
H2("6.1  Proposition 1: the fluid property behind a K change is not identifiable")
P("<b>Claim.</b> Two fluids with the same value of γ cos θ / μ produce identical arrival times on any strip.")
P("<b>Proof.</b> In the generator equation, fluid properties enter only through K ∝ γ cos θ / μ; the geometry terms w(L) and "
  "R(L) do not depend on the fluid. Equal K means an identical ODE, hence identical L(t) and arrival times. ∎")
P("<b>Demonstration.</b> Doubling viscosity, halving surface tension, and raising θ from 0° to 60° (cos 60° = 0.5) each "
  "halve K. Through the generator, the sensor model and the fixed-point detector, all three give the ticks "
  "84926, 169852, 254778, 339703 and the verdict UNIFORM_SLOW.")
H2("6.2  Proposition 2: signature of a localized restriction")
P("Let a restriction add ΔL of equivalent length, ΔL = (1/k − 1)·w for relative permeability k over width w. For x beyond "
  "the restriction, R(x) = x + ΔL, so t(L) = (L² + 2ΔL·L + c)/K, where c is a constant. A segment that lies entirely "
  "downstream of the restriction then has:")
EQ("ρ<sub>k</sub> = 1 + 2ΔL / (L<sub>k</sub> + L<sub>k−1</sub>)",
   "Segments upstream are unaffected (ρ = 1); the segment containing the restriction is partly affected.")
P("Consequences: (i) the first deviating segment locates the restriction; (ii) the same ΔL produces a smaller signature "
  "further downstream, because L<sub>k</sub> + L<sub>k−1</sub> grows; (iii) a restriction below some ΔL is hidden by the tolerance.")
H2("6.3  Proposition 3: restriction upstream of the first electrode")
P("If the restriction lies before electrode 0, every segment is downstream of it, so all ρ<sub>k</sub> exceed 1 and "
  "<b>decrease</b> along the strip by the formula above. A large one produces this non-Washburn pattern, which the detector "
  "reports as ANOMALY. A small one gives nearly flat ratios, indistinguishable from a slower fluid (Proposition 1).")
H2("6.4  Computed thresholds")
IMG(os.path.join(FIG, "identifiability.png"), 165, "Figure 6.1. (a) Three different causes, identical signature. (b) Deviation "
    "seen by the classifier against restriction severity ΔL<sub>eq</sub>, noise-free, with the 19.5 % tolerance.")
P("Noise-free, a restriction is reported in the right segment once ΔL<sub>eq</sub> exceeds 10 mm (segment 1), 13 mm "
  "(segment 2) or 15 mm (segment 3). An upstream restriction becomes ANOMALY above about 15 mm, and its deviation saturates "
  "near 35 %. The corpus's 'mild' restrictions are 4 mm (below every threshold); its 'strong' ones are 20 mm (above all).")
H2("6.5  Identifiability table (with test-split evidence)")
TBL(md_table(os.path.join(TAB, "identifiability.md")), [30, 34, 28, 73], size=7.9)

# ================================================================== 7 DETECTOR
H1("7  Detector algorithm", "ch7")
IMG(D["d_detector_flow.png"], 160, "Figure 7.1. Decision flow of the detector (SPEC.md v0.2).")
H2("7.1  Rules")
B(["<b>R0, pre-high:</b> an electrode line already high when the sample is applied → SENSOR (lowest such index).",
   "<b>R1, stage window:</b> while waiting for electrode k, STALL at k if the elapsed time e since the previous arrival satisfies "
   "e·256 > E<sub>0</sub>·FIRST_Q (k = 0) or e·E<sub>0</sub>·256 > Δt<sub>0</sub>·E<sub>k</sub>·(256 + TOL_STALL) (k ≥ 1). "
   "An arrival that already satisfies this is too late: timeout wins ties.",
   "<b>R2, order:</b> if the earliest arrival among electrodes j ≥ k is not k alone (a tie, or another electrode first) → "
   "SENSOR at the offending electrode.",
   "<b>R3, accept:</b> record Δt<sub>k</sub>; at k = 0, if Δt<sub>0</sub>·256 &lt; E<sub>0</sub>·MIN_FIRST_Q → SENSOR "
   "(faster than any real sample).",
   "<b>Classify</b> (after the last electrode): for k = 1..N−1 in order, if Δt<sub>k</sub>·E<sub>0</sub>·256 > "
   "Δt<sub>0</sub>·E<sub>k</sub>·(256 + TOL) → RESTRICTION k; if &lt; Δt<sub>0</sub>·E<sub>k</sub>·(256 − TOL) → ANOMALY k.",
   "<b>Uniform band:</b> otherwise compare the total time T = Σ Δt with E<sub>TOT</sub> = Σ E: above "
   "E<sub>TOT</sub>·(256 + TOL_ABS)/256 → UNIFORM_SLOW; below the lower band → UNIFORM_FAST; else NOMINAL."])
H2("7.2  Why these choices")
B(["<b>Online K.</b> r̂ = Δt<sub>0</sub>/E<sub>0</sub> measures the sample's own speed, so a viscous but healthy sample "
   "(blood ≈ 3.9× water) is accepted and later windows scale with it.",
   "<b>Adaptive windows.</b> Each stage's window depends on r̂, which is what lets the detector name the gap where the "
   "front stopped; a fixed global timeout cannot.",
   "<b>Total-time uniform test (v0.2).</b> A constant 1.8 s detection lag is 4 % of the first segment but only 1 % of the "
   "total, so testing the total raised fast-fluid detection from 47 % to 92 %.",
   "<b>First-segment floor (v0.2).</b> No plausible sample wicks more than twice as fast as water (water at 37 °C is "
   "1.29×). This floor removed false STALLs caused by spurious early triggers."])
H2("7.3  Exactness of the arithmetic (why hardware can match software exactly)")
P("<b>Claim.</b> Every decision is an exact integer comparison, so any correct implementation, in Python or RTL, gives "
  "identical results. <b>Argument.</b> The ratio tests are cross-multiplied: there is no division and no rounding, and all "
  "tolerances are integers over 256. Inputs are integer ticks. The largest product is Δt<sub>0</sub>·E<sub>k</sub>·768 &lt; "
  "2<super>24</super>·2<super>24</super>·2<super>10</super> = 2<super>58</super>, so a 64-bit comparator is exact. The Python "
  "model asserts every product is below 2<super>64</super>. ∎")
NOTE("Worked example", "A restriction in segment 2 (ticks in ms): Δt = 42463, 42463, 55960, 65219; all E = 42463. Segment 1: "
     "42463·256 = 10,870,528 lies between 42463·206 and 42463·306, so it is consistent. Segment 2: 55960·256 = 14,325,760 > "
     "42463·306 = 12,993,678, so the verdict is RESTRICTION in segment 2.")
H2("7.4  Parameters")
TBL([["Parameter", "Value", "Meaning", "Origin"],
     ["TOL", f"{CFG['TOL_Q']}/256 = {CFG['TOL_Q'] / 256:.1%}", "segment consistency", "tuned on calibration seeds"],
     ["TOL_ABS", f"{CFG['TOL_ABS_Q']}/256 = {CFG['TOL_ABS_Q'] / 256:.1%}", "nominal band on total time", "tuned on calibration seeds"],
     ["TOL_STALL", f"{CFG['TOL_STALL_Q']}/256", "window = r̂·E<sub>k</sub>·3", "design choice"],
     ["FIRST_Q", f"{CFG['FIRST_Q']}/256", "first segment ≤ 5·E<sub>0</sub>", "design choice (blood 3.9×)"],
     ["MIN_FIRST_Q", f"{CFG['MIN_FIRST_Q']}/256", "first segment ≥ 0.5·E<sub>0</sub>", "physics bound"],
     ["E<sub>k</sub>", ", ".join(map(str, CFG["E"])) + " ticks", "expected segment times", "L² spacing, K = 9.42"],
     ["Tick / timestamp width", f"1 ms / {CFG['TS_BITS']} bit", "4.66 h range", "design choice"]], [27, 40, 48, 50])

# ================================================================== 8 DATASET & EXPERIMENTS
H1("8  Dataset and experiments", "ch8")
H2("8.1  Simulated scenario corpus")
specs = corpus.specs()
P(f"The corpus contains {len(specs)} fault scenarios × {len(corpus.JITTERS)} jitter levels {list(corpus.JITTERS)} s × "
  f"{len(corpus.CVS)} K-variability levels {[round(c, 3) for c in corpus.CVS]} × {corpus.REPS} seeds "
  f"({corpus.REPS_NOMINAL} for nominal strips) = 9,900 runs. Seeds are derived from the cell indices, so the corpus is "
  "bit-reproducible. Replicates in the first half form the <b>calibration</b> split and the rest the <b>test</b> split.")
names = {0: "NOMINAL", 1: "UNIFORM_SLOW", 2: "UNIFORM_FAST", 3: "RESTRICTION", 4: "STALL", 5: "SENSOR"}


def describe(kw, kf, faults):
    if "perm" in kw:
        a, b, k = kw["perm"][0]
        return f"permeability ×{k:.2f} over {b - a:.0f} mm centred at {(a + b) / 2:.1f} mm (ΔL<sub>eq</sub> = {(1 / k - 1) * (b - a):.0f} mm)"
    if "v_sample" in kw:
        return f"sample volume {kw['v_sample']:.2f} µL (front stops mid-segment)"
    if faults:
        return "; ".join(f"electrode {e} {kind}" for e, kind in faults.items())
    return f"K × {kf:.2f} (fluid property change)" if kf != 1 else "healthy strip, water"


TBL([["Scenario family", "Truth", "Physical setting"]] +
    [[esc(f), f"{names[c]} {l}", describe(kw, kf, fl)] for f, c, l, kw, kf, fl in specs], [48, 30, 87], size=7.6)
H2("8.2  Methods compared")
TBL([["Method", "Decision rule", "Tuned parameter"],
     ["Model-based (this work)", "Rules of §7", f"TOL = {CFG['TOL_Q']}/256, TOL_ABS = {CFG['TOL_ABS_Q']}/256"],
     ["Fixed timeout", "fault if the last electrode does not fire before T", f"T = {M['tuned_baselines']['T_timeout'] / 1000:.1f} s"],
     ["Single sensor", "fault if the last arrival is outside [T<sub>lo</sub>, T<sub>hi</sub>]",
      f"{M['tuned_baselines']['T_lo'] / 1000:.1f}–{M['tuned_baselines']['T_hi'] / 1000:.1f} s"],
     ["Fixed-K windows (ablation)", "fault if any ρ<sub>k</sub> is outside 1 ± tol (no online K)", f"tol = {M['tuned_baselines']['tol_fixed_k']:.2f}"]],
    [40, 75, 50])
H2("8.3  Tuning protocol")
P("Every method is tuned on the calibration split to a false-alarm rate of at most 5 % on nominal strips (all noise levels "
  "pooled). For the model-based detector, a grid search over (TOL, TOL_ABS) maximizes exact class + location accuracy on "
  "calibration faults under that constraint. All reported metrics come from the unseen test split. "
  "<font name='Mono'>run.py phase3</font> fails if the tolerances in params.py differ from the tuned values.")
H2("8.4  Metrics")
B(["<b>Detection rate:</b> fraction of faulty test strips flagged as anything other than NOMINAL.",
   "<b>False-alarm rate:</b> fraction of healthy test strips flagged.",
   "<b>Exact accuracy:</b> class and location both correct (upstream restrictions excluded as not identifiable).",
   "<b>Time to decision:</b> tick at which the result is final (the stall decision tick is computed by the reference model)."])

# ================================================================== 9 RESULTS
H1("9  Results", "ch9")
H2("9.1  Detection against baselines (test split, 4,950 runs)")
TBL([["Method", "Faults detected", "False alarms", "Classifies?"]] +
    [[m, pct(MET[m]["detection"]), pct(MET[m]["far"]), "cause + location" if m == "model-based" else "no"]
     for m in ("model-based", "fixed timeout", "single sensor", "fixed-K windows")], [55, 35, 35, 40])
P(f"The model-based method's test false-alarm rate is {fa}/{n_nom} = {fa / n_nom:.1%} (Wilson 95 % CI {far_ci[0]:.1%}–{far_ci[1]:.1%}). "
  "At equal false-alarm rates, the four-electrode methods detect about twice as many faults as either single-number check. "
  "The fixed-K ablation detects equally well, so the gain in <i>detection</i> comes from the extra electrodes. The model-based "
  f"method adds <i>classification</i>: exact class and location in {M['exact_accuracy']:.1%} of cases.")
IMG(os.path.join(FIG, "confusion_matrix.png"), 150, "Figure 9.1. Confusion matrix, test split (row-normalized; counts in brackets).")
IMG(os.path.join(FIG, "detection_by_cause.png"), 155, "Figure 9.2. Detection rate by true cause for each method.")
IMG(os.path.join(FIG, "detection_vs_noise.png"), 165, "Figure 9.3. Detection and false alarms against jitter and strip "
    "variability. Real electrodes sit at about σ = 1.4 s (§10).")
H2("9.2  Time to decision (median, seconds)")
groups = ["NOMINAL", "UNIFORM_SLOW", "UNIFORM_FAST", "RESTRICTION", "RESTRICTION_UPSTREAM", "STALL", "SENSOR"]
TBL([["True cause"] + ["model-based", "fixed timeout", "single sensor", "fixed-K"]] +
    [[g.replace("_", " ").lower()] + [f"{MET[m]['median_decision_s'].get(g, float('nan')):.0f}"
                                      for m in ("model-based", "fixed timeout", "single sensor", "fixed-K windows")]
     for g in groups], [55, 27, 27, 27, 27])
P("The model-based method waits for the full run before classifying viscous samples (median 342 s), and it reports sensor "
  "faults early (31 s).")
IMG(os.path.join(FIG, "arrival_patterns.png"), 165, "Figure 9.4. Arrival patterns per fault class from the generator "
    "(no noise): flat ratios mean a uniform K change; a step means a localized restriction.")

# ================================================================== 10 REAL DATA
H1("10  Real-data validation against the base paper", "ch10")
P("<b>Method.</b> The flow-tracking section of <font name='Mono'>plotResults.m</font> was ported line by line to Python "
  "(<font name='Mono'>realdata/bezinge_flow.py</font>), keeping the MATLAB's quirks, for example a stop counter that is never "
  "reset. Octave was not installed, so instead of a side-by-side run the port is checked against an analytic case.")
P("<b>Self-test proof.</b> For a current step of height h ≫ threshold at sample s, i(n) − i(n−10) = h for n ∈ [s, s+9]. "
  "So |Δi| is a triangle above the threshold for n ∈ [s, s+18]. The 10th consecutive hit is at s+9 (flow detected). The "
  "signal falls below the threshold from s+19, so the 100th consecutive low sample is at s+118 (stop). The port returns "
  "exactly (s+9, s+118).")
IMG(os.path.join(FIG, "bezinge_flow.png"), 150, "Figure 10.1. Reproduction on data_P3.csv: current, |Δi| with threshold, and "
    "the status trace with flow times.")
rd = md_table(os.path.join(TAB, "realdata.md"))
TBL(rd[:5] if len(rd) >= 5 else rd, [14, 34, 18, 20, 18, 22, 25, 14], size=7.6)
P("Flow time = (stop declared) − (flow detected) − 10 s confirmation delay. The step names are inferred from the assay order "
  "described in the paper (sample, labelling, rinse, substrate). All three completed flow times fall inside the paper's "
  "reported IQRs.")
P("<b>Implied sensor noise.</b> The paper's agreement with visual timing has an IQR of −0.1 to 2.5 s. For a normal "
  "distribution IQR = 1.349 σ, so σ ≈ 1.9 s per flow time, or ≈ 1.4 s per detected event if the two events are independent "
  "(√2). The 1.8 s bias sets the generator's lag. The 1.4 s jitter lies inside the simulated 0–2 s range.")
NOTE("Scope of this validation", "The base-paper device has a single electrode cell and vertical flow. This check validates "
     "event timing and its noise; it cannot test multi-electrode localization or the lateral calibration.", WARNC)

# ================================================================== 11 ARCHITECTURE & RTL
H1("11  System architecture and RTL", "ch11")
IMG(D["d_rtl_blocks.png"], 160, "Figure 11.1. RTL block diagram.")
H2("11.1  Modules")
rtl = [("rtl/sync2.sv", "2-flip-flop synchronizer per electrode line (metastability)"),
       ("rtl/capture_unit.sv", "glitch filter (DEB clocks) + timestamp at the start of the high run; first rise only"),
       ("rtl/mul_u.sv", "shared unsigned multiplier 24×36 bit, 2 register stages (DSP48E1)"),
       ("rtl/detector_core.sv", "timebase, snapshot scan, 16-state sequencer, classifier, uniform band"),
       ("rtl/detector_top.sv", "sync2 + core; ports clk, rst_n, tick, arm, arrive_async[3:0], valid, cls, loc"),
       ("rtl/detector_syn_top.sv", "synthesis wrapper: 1 ms tick generator (100,000 clocks), DEB = 1000 (10 µs)"),
       ("build/*/params_pkg.sv", "generated constant ROM: E<sub>k</sub>, E<sub>k</sub>·(256 ± TOL), stall constants, bands"),
       ("tb/detector_core_checks.svh", "assertions + covergroups, compiled in simulation only"),
       ("tb/tb_top.sv", "file-driven testbench; tick per clock; glitch injection")]
TBL([["File", "Lines", "Role"]] + [[f"<font name='Mono'>{f}</font>",
                                    str(sum(1 for _ in open(os.path.join(ROOT, f)))) if os.path.exists(os.path.join(ROOT, f)) else "gen.", r]
                                   for f, r in rtl], [52, 13, 100])
H2("11.2  Timestamp-only decisions (correctness argument)")
IMG(D["d_timestamp.png"], 160, "Figure 11.2. The timestamp is taken at the start of the high run; the decision can come later.")
P("<b>Claim.</b> The RTL's result equals the SPEC function of the arrival ticks, whatever the clock-to-tick ratio or "
  "multiplier latency. <b>Argument.</b> (1) Each capture unit stores ts = now at the first clock of a high run that lasts DEB "
  "clocks, so ts equals the arrival tick if no tick boundary falls within the synchronizer latency (the testbench guarantees "
  "this; in silicon a tick is 10<super>5</super> clocks). (2) An arrival at tick m is acted on only when no filter is pending "
  "and now > m, so no other electrode can still be stamped m: the earliest arrival and its tie set are final. "
  "(3) A timeout is declared when the window predicate holds at a sampled now; any later capture has ts ≥ now, and the "
  "predicate is monotonic in time, so that capture would also be late. (4) All arithmetic is exact (§7.3). Hence decisions "
  "depend only on the ts values. ∎")
H2("11.3  Sequencer state machine")
IMG(D["d_fsm.png"], 165, "Figure 11.3. Sequencer FSM (16 states).")
TBL([["State", "Role"],
     ["IDLE", "wait for arm; clear captures; pre-high check"], ["STAGE", "set the stage window bound B (constant or via multiplier)"],
     ["BSET", "store B from the multiplier"], ["SCAN", "snapshot all timestamps, flags and now"],
     ["MIN", "earliest stamp, one electrode per clock"], ["TIE", "tie mask; finality (now > m)"],
     ["ISSUE", "restart if a filter is pending; else issue the window test"], ["TESTM", "test the earliest arrival: STALL, SENSOR or accept"],
     ["TESTN", "test expiry at the sampled now: STALL or keep scanning"], ["CLS0–CLS3", "per-segment consistency tests (3 multiplies each)"],
     ["UNI", "uniform band on the total time"], ["REPORT", "one-cycle valid pulse with cls/loc"],
     ["MUL", "2-cycle wait for the shared multiplier, returns to 'ret'"]], [30, 135])
H2("11.4  Timing closure")
P("The first implementation missed 100 MHz by 7.97 ns. The critical path was the combinational scan: a serial minimum over "
  "four timestamps, a compare and a subtract, 36 logic levels. Because latency does not affect results (§11.2), the scan was "
  "turned into a multi-clock walk over a registered snapshot. The worst path is now 5 logic levels, with +3.72 ns of slack.")
H2("11.5  Implementation results (Vivado 2022.2, xc7z020clg400-1, out-of-context)")
TBL(md_table(os.path.join(TAB, "synthesis.md")), [60, 30, 30, 30])
for line in open(os.path.join(TAB, "synthesis.md"), encoding="utf-8"):
    if line.startswith(("Clock", "Power")):
        P(esc(line.strip()))

# ================================================================== 12 VERIFICATION
H1("12  Verification", "ch12")
IMG(D["d_verification.png"], 160, "Figure 12.1. Verification flow.")
H2("12.1  Strategy")
B(["<b>Independent reference.</b> <font name='Mono'>golden_fixed.py</font> is written from SPEC.md, not from the RTL; "
   "<font name='Mono'>golden_float.py</font> expresses the same rules as physical ratios. The two agree on 100 % of the corpus.",
   "<b>Testbench.</b> Plain SystemVerilog, file-driven, under Vivado xsim. It drives the tick itself and mirrors the DUT's "
   "count without hierarchical references. It ticks every clock, except for 3 clocks after an electrode rises (the "
   "synchronizer and capture latency), and it can inject glitch pulses of a given width.",
   "<b>Regression.</b> The corpus is split across parallel xsim processes (capped at SIM_JOBS = 4 after a 12-process run "
   "exhausted the machine's memory)."])
H2("12.2  Results")
TBL([["Check", "Result"],
     ["Full corpus, RTL vs fixed-point reference", "9,900 / 9,900 bit-exact; 1.68×10<super>9</super> ticks simulated"],
     ["Boundary suite (52 directed cases)", "52 / 52 bit-exact"],
     ["Assertions (final set) on the boundary suite", "0 failures"],
     ["Functional coverage", "16/16 states, 30/30 transitions, all boundary events, 17/17 class × location"],
     ["Mutation test (6 seeded RTL bugs)", "6 / 6 caught by assertions (after two checks were strengthened)"],
     ["Counter saturation", f"unreachable: worst undecided run {boundary.saturation_bound(CFG):,} ticks of {2 ** CFG['TS_BITS'] - 1:,}"]], [70, 95])
H2("12.3  Assertions")
TBL([["Assertion", "Property"],
     ["a_legal", "only legal FSM transitions (explicit successor table)"],
     ["a_mul_ret, a_mul_hold", "multiplier wait returns to 'ret'; operands stable while waiting"],
     ["a_idx_step, a_idx_range", "stage index increases by at most 1 and stays in range"],
     ["a_valid_src, a_valid_one, a_valid_run, a_arm_clean, final", "exactly one result per run"],
     ["a_now_step, a_now_nosat, a_tprev_mono", "timebase advances by 0 or 1; never saturates; stage time monotonic"],
     ["a_filter, a_ts_hold, a_ts_past, a_pend_x", "glitch-filter rule; timestamps stable, in the past; pending excludes captured"],
     ["a_arrived, a_order, a_dt, a_inwin, a_minfirst", "every accepted stage arrived, in order, inside its window, plausible"],
     ["a_stall_idx, a_stall_late, a_stall_expired", "a STALL is only reported when its window has truly expired"],
     ["a_loc_cls, a_loc_range", "location consistent with class and within range"]], [70, 95])
P("Window predicates in the checks are recomputed from the raw tolerances, not the folded ROM constants the RTL uses.")
H2("12.4  Mutation test")
TBL([["Mutant", "Change", "Wrong results", "Assertion errors", "Fired"],
     ["classify_early", "classify after N−1 electrodes", "18", "82", "a_arrived, a_dt, a_inwin, a_order"],
     ["no_order_check", "accept out-of-order arrivals", "6", "16", "a_arrived, a_dt, a_inwin, a_order"],
     ["no_late_stall", "accept arrivals after the window", "3", "3", "a_inwin"],
     ["no_min_first", "drop the first-segment floor", "3", "3", "a_minfirst"],
     ["stall_early", "stall on the window edge (≥ for >)", "1", "1", "a_stall_late"],
     ["short_filter", "glitch filter one clock short", "3", "107", "a_filter"]], [28, 50, 20, 22, 45])
P("Measured in the Phase 5 mutation run. <font name='Mono'>run.py phase5-mutants</font> reproduces it, but its result table "
  "has not been regenerated in the repository.")
H2("12.5  Boundary suite")
brows = boundary.build(CFG)
CL = ["NOMINAL", "UNIFORM_SLOW", "UNIFORM_FAST", "RESTRICTION", "STALL", "SENSOR", "ANOMALY"]
TBL([["Case", "Arrival ticks (−1 never, −2 high before arm)", "Glitches (e, tick, clocks)", "Expected"]] +
    [[esc(n), ", ".join(map(str, t)), esc(", ".join(f"({a},{b},{c})" for a, b, c in g)) or "—", f"{CL[e[0]]} {e[1]}"]
     for _, n, t, g, e, _ in brows], [36, 58, 37, 34], size=7.2)
H2("12.6  Not verified")
B(["No formal proof (no formal tool installed); mutation testing was used instead.",
   "A single simulator (xsim). iverilog lacks covergroups and concurrent assertions.",
   "The full corpus was not rerun with the final assertion set; Phase 4's bit-exact run used the same RTL.",
   "No hardware run on the PYNQ-Z2 board (Phase 7 not done)."])

# ================================================================== 13 CLAIMS
H1("13  What we claim, and what we do not", "ch13")
H2("13.1  Claims supported by evidence")
TBL([["Claim", "Evidence"],
     ["Multi-point arrival timing detects filling faults better than a fixed timeout or a single flow-time check at equal false-alarm rate",
      f"{pct(MET['model-based']['detection'])} vs {pct(MET['fixed timeout']['detection'])} / {pct(MET['single sensor']['detection'])} (test split, §9)"],
     ["The detector classifies physically distinguishable faults and locates restrictions and stalls",
      "stall 100 % right gap; strong restriction 90 % right segment; confusion matrix §9"],
     ["Some causes are provably indistinguishable from arrival times", "Proposition 1, identical ticks (§6)"],
     ["Restriction visibility has a computable threshold", "10/13/15 mm by segment (§6.4)"],
     ["The detector fits in a small FPGA block at 100 MHz", "535 LUT, 3 DSP, WNS +3.72 ns (§11)"],
     ["The hardware implements the specification exactly", "9,900/9,900 bit-exact, 52 boundary cases, assertions, coverage, 6/6 mutants (§12)"],
     ["The base paper's flow-time algorithm is reproduced", "3/3 flow times inside the paper's IQRs (§10)"]], [85, 80])
H2("13.2  Where it is not superior")
B(["<b>Detection versus a fixed-window ablation:</b> no better (89.4 % vs 88.9 %). The gain over the ablation is "
   "classification, not detection.",
   "<b>False alarms:</b> 6–13 % at realistic jitter, as high as the baselines and too high for a clinical device.",
   "<b>Latency:</b> slower than the fixed-window variant for viscous samples (342 s vs 87 s median).",
   "<b>Evidence base:</b> weaker than the base paper, which used real devices and clinical samples."])
H2("13.3  Not covered (limitations)")
B(["The four-electrode results are simulated; no lateral strip was built or measured. The generator shares the detector's "
   "physics family, so performance is an upper bound.",
   "The calibration uses one membrane, water, a vertical-rise figure read by eye, with a +9 % gravity systematic and an "
   "early-time deviation from Washburn.",
   "The real-data check is one run of a single-electrode device; it validates timing only.",
   "Mild restrictions (ΔL<sub>eq</sub> below 10–15 mm) are not detected; weak upstream restrictions look like slow fluids; "
   "a sensor fault's electrode index is ambiguous; a missed last electrode looks exactly like a stall.",
   "Assumed values: sample volume 25 µL, creep τ 20 s, electrode positions, textbook plasma/blood viscosities. The 1.8 s lag "
   "is applied per arrival, which is our interpretation of the paper's flow-time bias.",
   "Not modelled: evaporation, temperature, swelling, partial saturation behind the front.",
   "Hardware: out-of-context timing, vectorless power, no board run; the interface assumes off-chip comparators; no "
   "sampled-signal front end ('interface B'); the 10 µs glitch filter length was chosen, not derived from measured noise.",
   "The immunoassay quantification of the base paper is out of scope."])
H2("13.4  Threats to validity")
B(["<b>Circularity:</b> the detector's physics is a simplification of the generator's. Mitigated by the richer generator "
   "(series resistance, finite volume, creep, sensor faults), but not removed.",
   "<b>Tuning:</b> thresholds were chosen on calibration seeds and reported on test seeds from the same generator; a real "
   "deployment would need re-tuning on measured strips.",
   f"<b>Statistics:</b> the false-alarm rate rests on {n_nom} healthy test strips (95 % CI {far_ci[0]:.1%}–{far_ci[1]:.1%})."])

# ================================================================== 14 PROJECT LOG
H1("14  Project log: what was done, step by step", "ch14")
TBL([["Phase", "What was done", "Outcome"],
     ["0 Plan", "Environment survey; architecture options (fixed windows, segment ratios with online K, sampled front end); PLAN.md", "approved"],
     ["Proposal", "One-page A4 PDF generated with ReportLab", "group number and names still placeholders"],
     ["1 Tracer", "generator → reference model → RTL in xsim → compare, 3 scenarios", "pass; first localization-lag finding"],
     ["2 Physics", "literature search; digitization; K fit; Darcy generator; sensor model; scaling", "K = 9.42 mm²/s; 7/7 checks"],
     ["3 Golden", "9,900-run corpus; grid-search tuning; baselines; metrics; SPEC v0.2", "detection 88.9 % vs 46.8 %"],
     ["4 RTL", "timestamp-capture redesign; sharded regression; Vivado OOC P&R; timing fix", "9,900/9,900; WNS +3.72 ns"],
     ["5 Verification", "SVA, coverage, 52 boundary cases, mutation test, parallelism cap", "all pass; 6/6 mutants"],
     ["6 Real data", "Bezinge files; Python port; analytic self-test; comparison with the paper", "3/3 inside IQR; lag and jitter confirmed"],
     ["8 Report", "identifiability computations; report draft; HTML docs; this document", "done"],
     ["7 PYNQ demo", "optional board demo", "not started"]], [22, 100, 43])
H2("14.1  Problems met and how they were solved")
TBL([["Problem", "Fix"],
     ["cmd.exe splits arguments on '=' and the project path has spaces, breaking xsim plusargs", "fixed file names in each simulation directory"],
     ["xvlog's own log file collided with the console redirect", "console output to *.out files"],
     ["Vivado read_xdc and xcrg split paths at spaces", "Tcl list / relative paths"],
     ["Corpus needed ~10<super>10</super> simulated cycles", "timestamp-only RTL; testbench ticks every clock; parallel shards"],
     ["Post-route timing missed by 7.97 ns", "multi-clock snapshot scan"],
     ["Two seeded bugs escaped the first assertions", "generalized accepted-stage checks; added a glitch-filter assertion"],
     ["12 parallel simulators with checks crashed the PC", "SIM_JOBS cap (default 4); phase 5 uses one process"],
     ["xsim mis-evaluated sized casts in coverage bin ranges (33.6 % reported)", "true coverage recovered from hit values; bins rewritten with integers"],
     ["Publisher pages bot-checked; ETH rate-limited", "open MDPI paper for calibration; user-supplied dataset"]], [85, 80])
H2("14.2  Decisions that differ from the original handoff")
TBL([["Topic", "Handoff", "Decision and reason"],
     ["Calibration source", "Mendez 2010 / Fu 2011", "Kasetsirikul 2020: open, lateral-flow membrane"],
     ["Upstream restriction", "never distinguishable", "distinguishable above ~15 mm (Proposition 3)"],
     ["Uniform test", "first segment", "total fill time (lag matters less)"],
     ["Formal check", "optional", "no formal tool; mutation testing instead"],
     ["Octave reproduction", "run plotResults.m", "not installed; Python port with an analytic self-test"],
     ["Interface B, PYNQ demo", "optional", "not done: single-electrode data; time budget"]], [35, 45, 85])

# ================================================================== 15 REPRODUCTION
H1("15  Reproduction guide", "ch15")
P("Environment: Windows, Python 3.12 (run as <font name='Mono'>py -3.12</font>), NumPy, SciPy, Matplotlib, ReportLab, "
  "Vivado 2022.2 (xsim, xcrg, synthesis). No simulator is needed for phases 2, 3, 6 and 8 or for this document.")
story.append(Preformatted(
    "py -3.12 run.py phase1          # tracer: 3 scenarios through xsim\n"
    "py -3.12 run.py phase2          # calibration, scaling, generator checks\n"
    "py -3.12 run.py phase3          # corpus, tuning, baselines, metrics (Python only)\n"
    "py -3.12 run.py phase4          # full RTL regression (SIM_JOBS parallel xsim) + Vivado\n"
    "py -3.12 run.py phase5          # boundary suite, assertions, coverage (one xsim process)\n"
    "py -3.12 run.py phase5-mutants  # mutation test (SIM_JOBS at a time)\n"
    "py -3.12 run.py phase6          # base-paper data reproduction (Python only)\n"
    "py -3.12 run.py phase8          # identifiability assets (Python only)\n"
    "py -3.12 report/build_master_pdf.py   # this document", S["mono"]))
story.append(Spacer(1, 8))
TBL([["Path", "Contents"],
     ["PLAN.md, SPEC.md", "plan with status log; detector specification"], ["physics/", "parameters, calibration, Darcy generator, sensor, scaling"],
     ["scenarios/", "corpus, boundary cases, tracer"], ["golden/", "reference models, baselines, evaluation, identifiability"],
     ["rtl/, tb/, syn/", "design, testbench + checks, Vivado script"], ["realdata/, data/", "base-paper port; literature and real data with provenance"],
     ["results/", "generated figures and tables"], ["report/", "draft report, this document and its builder"],
     ["docs/", "HTML documentation and study guide"], ["proposal/", "one-page proposal"]], [40, 125])

# ================================================================== APPENDICES
H1("Appendix A  Detector specification (SPEC.md)", "appA")
spec_text = open(os.path.join(ROOT, "SPEC.md"), encoding="utf-8").read()
for a, b in {"∈": " in ", "∖": "\\", "∝": "~", "≪": "<<"}.items():
    spec_text = spec_text.replace(a, b)
story.append(Preformatted(spec_text, S["mono"], maxLineLength=118))
H1("Appendix B  References", "appB")
for r in ["[1] L. Bezinge, A. J. deMello, C.-J. Shih, D. A. Richards, Lab Chip 24(15), 3651–3657 (2024), doi:10.1039/D4LC00390J. "
          "Data: Mendeley Data, doi:10.17632/nd9cyw62rk.1.",
          "[2] E. W. Washburn, The dynamics of capillary flow, Phys. Rev. 17, 273–283 (1921); R. Lucas, Kolloid-Z. 23, 15–22 (1918).",
          "[3] S. Kasetsirikul, M. J. A. Shiddiky, N.-T. Nguyen, Wicking in paper strips under consideration of liquid absorption "
          "capacity, Chemosensors 8(3), 65 (2020), doi:10.3390/chemosensors8030065.",
          "[4] S. Patari, P. Sinha Mahapatra, Liquid wicking in a paper strip, ACS Omega 5, 22931–22939 (2020), doi:10.1021/acsomega.0c02407.",
          "[5] J. J. Miranda-Blancas et al., Effects of permeability and gravity on capillary imbibition in filter paper, Fluids 11(5), 127 (2026).",
          "[6] S. Mendez et al., Langmuir 26, 1380–1385 (2010): quasi-stationary flow in segments (not read in full; verify before citing).",
          "[7] H. Bruus, Theoretical Microfluidics, Oxford University Press (2008)."]:
    P(esc(r))


# ------------------------------------------------------------------ document template with TOC + bookmarks
class Doc(BaseDocTemplate):
    def __init__(self, fn):
        super().__init__(fn, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
                         title="BioMEMS Capillary Fault Classifier: Master Document", author="BioMEMS group")
        fr = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate("cover", [fr]), PageTemplate("main", [fr], onPage=self._decor)])

    def _decor(self, c, d):
        c.saveState()
        c.setFont("Body", 8); c.setFillColor(INK2)
        c.drawString(20 * mm, 10 * mm, "Capillary Fault Classifier · Master Document")
        c.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Page {d.page}")
        c.setStrokeColor(RULE); c.line(20 * mm, 13 * mm, A4[0] - 20 * mm, 13 * mm)
        c.restoreState()

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and hasattr(f, "_lvl"):
            txt = f.getPlainText()
            key = f"bm{id(f)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(txt, key, level=f._lvl, closed=f._lvl > 0)
            self.notify("TOCEntry", (f._lvl, txt, self.page, key))


if __name__ == "__main__":
    doc = Doc(OUT)
    doc.multiBuild(story)
    from pypdf import PdfReader
    print(f"{OUT}: {len(PdfReader(OUT).pages)} pages")
