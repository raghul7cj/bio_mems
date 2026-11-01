"""Build the one-page proposal PDF (BioMEMS_Project_GroupX_Proposal.pdf).

Usage:  py -3.12 proposal/make_proposal.py [--group N] [--members "A (roll), B (roll)"]
Source text: handoff section 2. Fails if the result is not exactly one page.
"""
import argparse
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (HRFlowable, ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

FONT_DIR = r"C:\Windows\Fonts"
# Calibri covers Greek (gamma, theta, mu); built-in Helvetica does not.
FACES = {"Body": "calibri.ttf", "Body-B": "calibrib.ttf", "Body-I": "calibrii.ttf", "Body-BI": "calibriz.ttf"}
for name, fname in FACES.items():
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, fname)))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-B", italic="Body-I", boldItalic="Body-BI")

ACCENT = colors.HexColor("#1F3A5F")
BASE = 9.6
body = ParagraphStyle("body", fontName="Body", fontSize=BASE, leading=BASE * 1.22, spaceAfter=1.5)
head = ParagraphStyle("head", parent=body, fontName="Body-B", fontSize=BASE + 1.2, textColor=ACCENT,
                      spaceBefore=4, spaceAfter=1.5)
title = ParagraphStyle("title", parent=body, fontName="Body-B", fontSize=14.5, leading=17.5,
                       alignment=TA_CENTER, textColor=ACCENT, spaceAfter=2)
meta = ParagraphStyle("meta", parent=body, fontSize=BASE - 0.4, alignment=TA_CENTER, textColor=colors.HexColor("#444444"))
ref = ParagraphStyle("ref", parent=body, fontSize=BASE - 1.6, leading=(BASE - 1.6) * 1.2, spaceAfter=0.5)
cell = ParagraphStyle("cell", parent=body, fontSize=BASE - 0.8, leading=(BASE - 0.8) * 1.18, spaceAfter=0)


def P(text, style=body):
    return Paragraph(text, style)


def bullets(items, numbered=False):
    return ListFlowable(
        [ListItem(P(t), leftIndent=11) for t in items],
        bulletType="1" if numbered else "bullet", start="1" if numbered else "\u2022",
        bulletFormat="%s." if numbered else None,
        bulletFontName="Body", bulletFontSize=BASE, leftIndent=11, bulletOffsetY=0,
    )


def build(out_path, group, members):
    s = []
    s.append(P("Physics-Based Fault Classification in Capillary-Driven Paper Microfluidics "
               "Using Multi-Point Electrode Sensing and Real-Time Hardware", title))
    s.append(P(f"BioMEMS Course Project Proposal &nbsp;|&nbsp; Group {group} &nbsp;|&nbsp; {members}", meta))
    s.append(P("Instructor: Prof. (Dr.) Amit Prabhakar &nbsp;|&nbsp; IIIT Allahabad, B.Tech ECE, Semester 7", meta))
    s.append(HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceBefore=3, spaceAfter=2))

    s.append(P("1. Problem statement", head))
    s.append(P(
        "Paper-based rapid diagnostic tests (RDTs) move sample and reagents by capillary wicking alone, with no pump. "
        "This makes them cheap, but failures are <i>silent</i>: too little sample, a defect in the paper or wax barrier, "
        "or a sample with abnormal viscosity can each give an invalid result that looks valid. Bezinge <i>et al.</i> [1] "
        "showed that electrodes embedded in a paper RDT can track reagent flow and flag incorrect volumes or abnormal "
        "viscosities. Practical checks, however, reduce flow to one number (\u201cdid liquid arrive before a timeout?\u201d "
        "or a single flow time). One number cannot say <i>where</i> a problem is, nor separate causes that the physics "
        "makes distinguishable."))

    s.append(P("2. Hypothesis", head))
    s.append(P(
        "Liquid-arrival times at several electrodes along a lateral paper strip, compared with a calibrated "
        "Lucas\u2013Washburn/Darcy model, can (a) <b>detect</b> filling faults with fewer missed and false alarms than a "
        "fixed timeout or a single-sensor threshold, and (b) <b>classify</b> them into physically distinguishable classes "
        "(uniform fluid-property change; localized flow restriction <i>with its location</i>; stalled front; sensor fault), "
        "in a small fixed-point hardware block."))

    s.append(P("3. Physics basis", head))
    s.append(P(
        "Washburn [2]: the wetted length obeys <i>L</i><super>2</super> = <i>K t</i>, with "
        "<i>K</i> = \u03b3 <i>r</i> cos\u03b8 / (2\u03bc). For paper, <i>K</i> is an <i>effective</i> Darcy coefficient "
        "fitted to published wicking data [3, 4]. The expected time to fill the segment between electrodes <i>i</i>\u22121 "
        "and <i>i</i> is \u0394<i>t<sub>i</sub></i> = (<i>L<sub>i</sub></i><super>2</super> \u2212 "
        "<i>L<sub>i\u22121</sub></i><super>2</super>)/<i>K</i>, so a fluid-property change scales every segment equally, "
        "while a local restriction first appears in the segment that contains it. Scaling (Bond, capillary and pore-scale "
        "Reynolds numbers all far below 1) justifies the quasi-static, inertia-free model. <b>Identifiability limit:</b> "
        "arrival times reveal only <i>K</i> and its spatial pattern, so viscosity cannot be told apart from surface "
        "tension or contact angle, and a restriction upstream of the first electrode mimics a fluid change. These limits "
        "will be stated explicitly."))

    s.append(P("4. Objectives", head))
    s.append(bullets([
        "Build a capillary-filling model of a paper strip, calibrated to <b>published</b> wicking data, with a sourced scaling analysis.",
        "Derive an <b>identifiability table</b>: which faults multi-point arrival times can and cannot distinguish.",
        "Design a model-based detector/classifier and two baselines (fixed timeout; single-sensor threshold).",
        "Implement the detector as <b>synthesizable SystemVerilog RTL</b>, verified bit-exactly against an independent Python golden model, with assertions and coverage.",
        "Quantify detection, classification and localization under noise, and the hardware cost (FPGA resources, timing).",
    ], numbered=True))

    s.append(P("5. Methodology", head))
    s.append(P(
        "<b>Python physics model</b> (Washburn + Darcy series resistance, finite sample volume, fluid-property changes, "
        "strip-to-strip variability, sensor jitter and failures; richer than the detector, so validation is not circular) "
        "\u2192 <b>seeded fault-scenario corpus</b> (each class \u00d7 location \u00d7 noise level) \u2192 <b>golden "
        "detector</b> (floating and fixed point) and baselines \u2192 <b>RTL</b>: timestamp unit, per-segment ratio test by "
        "cross-multiplication (no divider), online estimate of <i>K</i>, flow-validation FSM with model-derived adaptive "
        "timeouts, rule-based classifier \u2192 <b>verification</b> in Vivado xsim (file-driven corpus regression, SVA, "
        "functional coverage) \u2192 <b>synthesis</b> for Zynq-7020 (PYNQ-Z2). Thresholds are tuned on one seed set and "
        "evaluated on a held-out set. Real electrode traces released with [1] will be used to check the event-detection "
        "front end."))

    s.append(P("6. Expected outcomes and deliverables", head))
    outcomes = [
        ["Physics", "Calibrated <i>L</i><super>2</super>\u2013<i>t</i> fit with sourced <i>K</i>; scaling table; identifiability table"],
        ["Performance", "Detection/false-alarm rate vs. noise for all 3 methods; confusion matrix; localization accuracy; latency"],
        ["Hardware", "RTL bit-exact with the golden model on 100% of scenarios; LUT/FF/DSP and Fmax report; optional PYNQ-Z2 replay demo"],
    ]
    t = Table([[P(f"<b>{a}</b>", cell), P(b, cell)] for a, b in outcomes], colWidths=[22 * mm, None])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#BBBBBB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F7")),
    ]))
    s.append(t)

    s.append(P("7. Relevance and novelty", head))
    s.append(P(
        "Applies core course physics (capillarity, Darcy flow in porous media, dimensionless scaling) to an active "
        "research area: paper and electrochemical RDTs (course topics #3, #8, #12; sensor-data processing #44). It extends "
        "published flow monitoring [1] from single flow times to <b>multi-point fault localization with an explicit "
        "identifiability analysis</b>, implemented as real-time hardware."))

    s.append(P("8. Plan", head))
    s.append(P(
        "(i) Physics model, literature calibration and scaling analysis → (ii) scenario corpus, golden classifier "
        "and baselines with metrics → (iii) RTL, corpus regression, assertions, coverage and synthesis → "
        "(iv) real-trace check against [1] and report. Hardware demo on PYNQ-Z2 only if time permits. "
        "A revised 1–2 page plan follows the TA discussion (7 Nov)."))

    s.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#999999"), spaceBefore=4, spaceAfter=2))
    for r in [
        "[1] L. Bezinge, A. J. deMello, C.-J. Shih, D. A. Richards, \u201cQuantitative reagent monitoring in paper-based "
        "electrochemical rapid diagnostic tests,\u201d <i>Lab Chip</i>, 24(15), 3651\u20133657, 2024. doi:10.1039/D4LC00390J",
        "[2] E. W. Washburn, \u201cThe dynamics of capillary flow,\u201d <i>Phys. Rev.</i>, 17(3), 273\u2013283, 1921.",
        "[3] S. Mendez <i>et al.</i>, \u201cImbibition in porous membranes of complex shape: quasi-stationary flow in thin "
        "rectangular segments,\u201d <i>Langmuir</i>, 26(2), 1380\u20131385, 2010.",
        "[4] E. Fu, S. Ramsey, P. Kauffman, B. Lutz, P. Yager, \u201cTransport in two-dimensional paper networks,\u201d "
        "<i>Microfluid. Nanofluid.</i>, 10, 29\u201335, 2011.",
    ]:
        s.append(P(r, ref))

    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=12 * mm, bottomMargin=11 * mm,
                            title="BioMEMS Project Proposal", author=f"BioMEMS Group {group}")
    doc.build(s)
    return doc.page


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="X")
    ap.add_argument("--members", default="Members: ________________")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, f"BioMEMS_Project_Group{a.group}_Proposal.pdf")
    pages = build(out, a.group, a.members)
    print(f"{out}: {pages} page(s)")
    sys.exit(0 if pages == 1 else 1)
