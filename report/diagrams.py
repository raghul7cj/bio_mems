"""Explanatory diagrams for the master report (drawn with Matplotlib, saved as PNG).

Coordinates: 10 units = 1 inch of figure. Schematics are labelled as such where they are not to
scale; quantitative curves are computed from physics/params.py.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle, Wedge  # noqa: E402

INK, INK2, GRID = "#15201d", "#4b5753", "#d5dcd9"
WET, WETS = "#0f7f7a", "#d6efed"
ACC, ACCS = "#1d4fa3", "#e3ebf8"
WARN, WARNS = "#a25a00", "#f6e3c8"
BAD, OK, WHITE = "#b3261e", "#157a3c", "#ffffff"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w * 10); ax.set_ylim(0, h * 10); ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, sub=None, fc=WHITE, ec=INK, tsize=9, ssize=7.4, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.0", fc=fc, ec=ec, lw=1.2))
    if sub:
        ax.text(x + w / 2, y + h * 0.63, title, ha="center", va="center", fontsize=tsize, color=INK,
                fontweight="bold" if bold else "normal")
        ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center", fontsize=ssize, color=INK2,
                family="DejaVu Sans Mono", linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=tsize, color=INK,
                fontweight="bold" if bold else "normal", linespacing=1.3)


def arrow(ax, p, q, color=INK2, ls="-", rad=0.0, lw=1.3, both=False):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=11, color=color,
                                 lw=lw, ls=ls, connectionstyle=f"arc3,rad={rad}", shrinkA=1, shrinkB=1))


def note(ax, x, y, s, color=INK2, size=7.6, ha="left", mono=True, **kw):
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va="center", family="DejaVu Sans Mono" if mono else None, **kw)


def save(fig, out, name):
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, name)
    fig.savefig(p, dpi=200, facecolor=WHITE)
    plt.close(fig)
    return p


# ------------------------------------------------------------------ 1. project pipeline
def pipeline(out):
    fig, ax = canvas(10, 4.4)
    box(ax, 2, 32, 15, 8, "Published wicking", "Kasetsirikul 2020", ACCS, ACC)
    box(ax, 21, 32, 14, 8, "Calibrate K", "9.42 mm²/s")
    box(ax, 39, 32, 19, 8, "Generator model", "Darcy series + volume\n+ sensor noise/faults", WETS, WET)
    box(ax, 62, 32, 16, 8, "Scenario corpus", "9,900 runs, seeds")
    for a, b in ((17, 21), (35, 39), (58, 62)):
        arrow(ax, (a, 36), (b, 36))
    box(ax, 44, 16, 16, 8, "Reference models", "float + fixed point")
    box(ax, 62, 16, 14, 8, "Baselines", "timeout, 1 sensor")
    box(ax, 80, 16, 17, 8, "RTL in xsim", "SystemVerilog + SVA", ACCS, ACC)
    arrow(ax, (70, 32), (52, 24), rad=0.1); arrow(ax, (70, 32), (69, 24)); arrow(ax, (72, 32), (88, 24), rad=-0.1)
    box(ax, 44, 2, 32, 8, "Metrics", "detection, false alarms, confusion, latency", WETS, WET)
    box(ax, 80, 2, 17, 8, "Bit-exact compare", "9,900 / 9,900", WETS, WET)
    arrow(ax, (52, 16), (55, 10)); arrow(ax, (69, 16), (66, 10)); arrow(ax, (88, 16), (88, 10))
    arrow(ax, (60, 16.6), (80.4, 8.4), color=ACC, ls="--")
    box(ax, 2, 16, 18, 8, "Bezinge 2024 data", "one real electrode", ACCS, ACC)
    box(ax, 2, 2, 18, 8, "Python port", "of their flow tracking")
    arrow(ax, (11, 16), (11, 10))
    arrow(ax, (20, 6), (46, 32), ls=":", rad=0.25)
    note(ax, 22, 22, "confirms sensor lag\nand jitter used by\nthe generator", size=7)
    note(ax, 71, 14.3, "expected answers", color=ACC, size=6.6)
    return save(fig, out, "d_pipeline.png")


# ------------------------------------------------------------------ 2. base-paper sensor (schematic)
def bezinge_sensor(out):
    fig, ax = canvas(10, 5.2)
    ax.text(2, 49, "Base paper device: vertical-flow assay (schematic from the published design file)", fontsize=10,
            fontweight="bold", color=INK)
    layers = [("sample pad", WETS, WET), ("nitrocellulose pad (capture)", ACCS, ACC),
              ("paper sheet with laser-engraved electrodes", "#e9e9e6", INK),
              ("wax sheet (hydrophobic, central opening)", WARNS, WARN),
              ("absorbent pad ×3 (drain)", "#efefef", INK2)]
    y = 40
    for name, fc, ec in layers:
        ax.add_patch(Rectangle((8, y), 30, 4.2, fc=fc, ec=ec, lw=1.1))
        note(ax, 40, y + 2.1, name, color=INK, size=7.6, mono=False)
        y -= 6.8
    arrow(ax, (5, 45), (5, 13), color=WET, lw=2)
    note(ax, 3.5, 29, "liquid\nflows\ndown", color=WET, size=7.2, ha="right", mono=False)
    note(ax, 8, 8, "Stacking order inferred from the design file layers and the paper text.\n"
         "Laser: 'cut' = outlines, 'engrave' = electrode pattern (graphenized carbon).", size=6.8)
    # top view of the electrode sheet
    cx, cy = 80, 30
    ax.add_patch(Rectangle((66, 15), 28, 30, fc="#f4f4f2", ec=INK2, lw=1))
    ax.add_patch(Wedge((cx, cy), 6.0, -145, 145, width=1.6, fc=INK, ec=INK))   # ring open towards the pads
    ax.add_patch(Circle((cx, cy), 2.6, fc=INK, ec=INK))
    for yy in (37, 30, 23):
        ax.add_patch(Rectangle((68, yy - 1.2), 4, 2.4, fc=INK))
    ax.plot([72, cx - 2.6], [30, 30], color=INK, lw=2.5)                       # working electrode trace
    ax.plot([72, 75.4], [37, 33.6], color=INK, lw=2.5)                         # counter electrode trace
    ax.plot([72, 75.0], [23, 25.6], color=INK, lw=2.5)                         # reference electrode
    ax.add_patch(Rectangle((74.6, 25.0), 1.6, 1.6, fc=INK))
    note(ax, 80, 47, "electrode sheet, top view", size=7.4, ha="center", mono=False)
    for (x0, y0), (x1, y1), lab in (((cx + 1.5, cy), (93, 30), "WE: disk"), ((cx + 4.4, cy + 4.0), (93, 38), "CE: ring"),
                                    ((76.2, 25.6), (93, 22), "RE")):
        ax.plot([x0, x1 - 0.5], [y0, y1], color=ACC, lw=0.7)
        note(ax, x1, y1, lab, size=7, color=ACC)
    note(ax, 68, 12, "3 contact pads → potentiostat", size=6.8)
    return save(fig, out, "d_bezinge_sensor.png")


# ------------------------------------------------------------------ 3. pulse method (schematic)
def pulse_method(out):
    fig, axs = plt.subplots(3, 1, figsize=(10, 5.8), gridspec_kw={"height_ratios": [1, 1.2, 1.2]})
    t = np.linspace(0, 400, 4000)  # ms
    v = np.where((t % 100) < 6, 100, 0)  # 1 ms pulses drawn wider for visibility
    axs[0].plot(t, v, color=ACC, lw=1.4); axs[0].set_ylabel("V (mV)"); axs[0].set_ylim(-15, 130)
    axs[0].set_title("Pulsed sensing (schematic, not to scale): 100 mV, 1 ms pulses every 100 ms", fontsize=9, loc="left")
    dry = np.where((t % 100) < 6, 1.0 * np.exp(-(t % 100) / 1.6), 0)
    wet = np.where((t % 100) < 6, 2.2 * np.exp(-(t % 100) / 2.4), 0)
    cur = np.where(t < 200, dry, wet)
    axs[1].plot(t, cur, color=INK, lw=1.2); axs[1].set_ylabel("current")
    axs[1].axvline(200, color=WET, ls="--"); axs[1].text(203, 1.9, "liquid flows over the electrode:\ncapacitive discharge changes",
                                                         fontsize=7.6, color=WET, va="top")
    axs[1].set_xlabel("time (ms)")
    ts = np.linspace(0, 60, 1200)  # s
    s = np.where(ts < 8, 0, np.where(ts < 9, ts - 8, np.where(ts < 38, 1, np.exp(-(ts - 38) / 2))))
    axs[2].plot(ts, s * 3 + 0.15 * np.sin(ts * 3), color=INK, lw=1.2); axs[2].axhline(1.5, color=WARN, ls="--")
    axs[2].set_ylabel("|Δi|"); axs[2].set_xlabel("time (s)")
    axs[2].text(0.5, 1.75, "threshold (1.5 µA; 0.4 µA after rinse)", fontsize=7.4, color=WARN)
    axs[2].axvline(9.0, color=WET, ls=":"); axs[2].text(9.6, 0.55, "10 pulses above → flow detected", fontsize=7.4, color=WET)
    axs[2].axvline(49.5, color=BAD, ls=":"); axs[2].text(50.2, 2.1, "100 pulses (10 s)\nbelow → stopped", fontsize=7.4, color=BAD)
    axs[2].set_title("Processing: |Δi| = |mean over 10 pulses of (i_n − i_{n−10})|", fontsize=8.5, loc="left")
    for a in axs:
        a.grid(color=GRID, lw=0.6); a.spines[["top", "right"]].set_visible(False); a.set_yticks([])
    fig.tight_layout()
    return save(fig, out, "d_pulse_method.png")


# ------------------------------------------------------------------ 4. base paper vs this project
def comparison(out):
    fig, ax = canvas(10, 5.4)
    ax.add_patch(Rectangle((1, 1), 46, 50, fc="#f7f7f5", ec=GRID)); ax.add_patch(Rectangle((53, 1), 46, 50, fc="#f3f8f7", ec=GRID))
    ax.text(24, 48, "Base paper: Bezinge et al. 2024", ha="center", fontsize=10, fontweight="bold", color=INK)
    ax.text(76, 48, "This project", ha="center", fontsize=10, fontweight="bold", color=WET)
    # left: vertical stack with one electrode
    for i, (fc, ec) in enumerate([(WETS, WET), (ACCS, ACC), ("#e9e9e6", INK), ("#efefef", INK2)]):
        ax.add_patch(Rectangle((12, 36 - i * 4.2), 22, 3.4, fc=fc, ec=ec))
    ax.add_patch(Circle((23, 29.3), 1.0, fc=INK))                              # electrode in the third layer
    note(ax, 35, 29.3, "electrode", size=6.8)
    arrow(ax, (9, 41), (9, 22), color=WET, lw=1.8)
    note(ax, 23, 19.5, "one sensing location, liquid passes through it", size=7.2, ha="center", mono=False)
    box(ax, 6, 7, 34, 8, "Output: one flow time per reagent", "e.g. serum 30 s, labelling 22 s", WHITE, INK)
    note(ax, 23, 3.8, "flags wrong volume / abnormal viscosity", size=7, ha="center", mono=False)
    # right: lateral strip with four electrodes
    ax.add_patch(Rectangle((58, 33), 37, 4, fc=WHITE, ec=INK)); ax.add_patch(Rectangle((58, 33), 22, 4, fc=WETS, ec="none"))
    ax.plot([80, 80], [32, 38], color=WET, lw=2.2)
    for x, lab in ((70, "e0"), (75.6, "e1"), (82.3, "e2"), (94.5, "e3")):
        ax.add_patch(Rectangle((x - 0.4, 32), 0.8, 6, fc=ACC)); note(ax, x, 30.3, lab, size=7, ha="center")
    arrow(ax, (59, 41), (76, 41), color=WET, lw=1.6)
    note(ax, 76.5, 26.8, "four arrival times along a lateral strip", size=7.2, ha="center", mono=False)
    box(ax, 58, 14, 37, 9, "Output: class + location", "NOMINAL, UNIFORM_SLOW/FAST,\nRESTRICTION k, STALL k, SENSOR, ANOMALY",
        WHITE, WET)
    note(ax, 76.5, 9.5, "+ identifiability analysis: what can/cannot be told apart", size=7, ha="center", mono=False)
    note(ax, 76.5, 5.5, "+ real-time FPGA block (535 LUT, 3 DSP)", size=7, ha="center", mono=False)
    note(ax, 76.5, 2.5, "− simulation only: no measured lateral strip", size=7, ha="center", mono=False, color=BAD)
    return save(fig, out, "d_comparison.png")


# ------------------------------------------------------------------ 5. strip layout (to scale)
def strip_layout(out):
    fig, ax = canvas(10, 2.9)
    X = lambda L: 8 + L * 2.15
    ax.add_patch(Rectangle((1, 9), 7, 12, fc=WETS, ec=WET)); note(ax, 4.5, 6.5, "sample", size=7, ha="center", mono=False)
    ax.add_patch(Rectangle((X(0), 11), X(40) - X(0), 8, fc=WHITE, ec=INK))
    ax.add_patch(Rectangle((X(0), 11), X(25) - X(0), 8, fc=WETS, ec="none"))
    ax.plot([X(25)] * 2, [10, 20], color=WET, lw=2.4); note(ax, X(25), 22.5, "front L(t)", color=WET, size=7.4, ha="center")
    for L, lab in ((20, "e0  20.0 mm"), (28.28, "e1  28.3"), (34.64, "e2  34.6"), (40, "e3  40.0")):
        ax.add_patch(Rectangle((X(L) - 0.4, 10), 0.8, 10, fc=ACC)); note(ax, X(L), 6.5, lab, size=7, ha="center")
    for L in range(0, 41, 5):
        ax.plot([X(L)] * 2, [25, 26.2], color=INK2, lw=0.8); note(ax, X(L), 27.6, f"{L}", size=6.4, ha="center")
    note(ax, X(0), 3, "L² steps of 400 mm²: every segment takes E = 42.5 s for water (K = 9.42 mm²/s)", size=7.2)
    return save(fig, out, "d_strip.png")


# ------------------------------------------------------------------ 6. electrical analogy + Washburn curve
def analogy(out, K=9.42):
    fig = plt.figure(figsize=(10, 3.4))
    ax = fig.add_axes([0, 0, 0.55, 1]); ax.set_xlim(0, 55); ax.set_ylim(0, 34); ax.axis("off")
    ax.plot([4, 4], [12, 22], color=INK, lw=2); ax.plot([6, 6], [14.5, 19.5], color=INK, lw=2)
    note(ax, 5, 8.5, "P_c\n(capillary\npressure)", size=7, ha="center", mono=False)
    xs = [6, 11]
    def resistor(x0, w, color=INK, tall=1.0):
        zz = np.linspace(x0, x0 + w, 9); yy = 17 + np.array([0, 1, -1, 1, -1, 1, -1, 1, 0]) * 1.6 * tall
        ax.plot(zz, yy, color=color, lw=1.6)
    ax.plot([6, 9], [17, 17], color=INK); resistor(9, 6); ax.plot([15, 17], [17, 17], color=INK); resistor(17, 6)
    ax.plot([23, 25], [17, 17], color=INK); resistor(25, 8, ACC, 1.5); ax.plot([33, 35], [17, 17], color=INK); resistor(35, 6)
    ax.plot([41, 45], [17, 17], color=INK); ax.plot([45, 45], [13, 21], color=WET, lw=2.5)
    note(ax, 12, 23, "seg 0", size=7, ha="center"); note(ax, 20, 23, "seg 1", size=7, ha="center")
    note(ax, 29, 24.5, "restriction:\nextra R", size=7, ha="center", color=ACC); note(ax, 38, 23, "seg 2", size=7, ha="center")
    note(ax, 45, 23, "front", size=7, ha="center", color=WET)
    note(ax, 27, 5, "flow = P_c / (sum of resistances behind the front)\nwetted paper never leaves the circuit",
         size=7.2, ha="center", mono=False)
    a2 = fig.add_axes([0.62, 0.17, 0.35, 0.72])
    t = np.linspace(0, 175, 400); a2.plot(t, np.sqrt(K * t), color=WET, lw=2)
    for L, dx, ha in ((20, 3, "left"), (40, -4, "right")):
        tt = L * L / K; a2.plot([0, tt, tt], [L, L, 0], color=INK2, ls=":", lw=1)
        a2.text(tt + dx, L - 4, f"{L} mm at {tt:.1f} s", fontsize=7.4, color=INK, ha=ha)
    a2.set_xlabel("t (s)"); a2.set_ylabel("L (mm)"); a2.set_title(f"Washburn: L = √(K t), K = {K} mm²/s", fontsize=8.5)
    a2.grid(color=GRID, lw=0.6); a2.spines[["top", "right"]].set_visible(False)
    return save(fig, out, "d_analogy.png")


# ------------------------------------------------------------------ 7. detector flow
def detector_flow(out):
    fig, ax = canvas(10, 6.4)
    box(ax, 35, 58, 30, 5, "arm: sample applied, t = 0", None, ACCS, ACC)
    box(ax, 33, 49, 34, 5, "any electrode already high?", None, bold=False)
    box(ax, 26, 37, 48, 8, "stage k: wait for earliest arrival (any j ≥ k)",
        "or window expiry: elapsed > r̂·E_k·3   (stage 0: 5·E_0)", WETS, WET)
    box(ax, 29, 27, 42, 6, "record Δt_k   (stage 0: Δt_0 ≥ 0.5·E_0 ?)", None, bold=False)
    box(ax, 22, 14, 56, 8, "segments 1..3: Δt_k·E_0·256  vs  Δt_0·E_k·(256 ± 50)",
        "first segment outside the band decides", WHITE, INK)
    box(ax, 22, 2, 56, 8, "all consistent: total Σ Δt vs Σ E · (1 ± 38/256)", "within band → NOMINAL", WHITE, INK)
    for a, b in ((58, 54), (49, 45), (37, 33), (27, 22), (14, 10)):
        arrow(ax, (50, a), (50, b))
    note(ax, 69, 51.5, "yes → SENSOR (line high before start)", color=BAD, size=7.4)
    note(ax, 76, 43, "expired first → STALL, loc k", color=BAD, size=7.4)
    note(ax, 76, 39, "tie / out of order → SENSOR", color=BAD, size=7.4)
    note(ax, 73, 30, "too fast → SENSOR", color=BAD, size=7.4)
    note(ax, 80, 19.5, "too slow → RESTRICTION, loc k", color=BAD, size=7.4)
    note(ax, 80, 16, "too fast → ANOMALY, loc k", color=BAD, size=7.4)
    note(ax, 80, 6, "slower → UNIFORM_SLOW", color=WARN, size=7.4); note(ax, 80, 2.8, "faster → UNIFORM_FAST", color=WARN, size=7.4)
    arrow(ax, (29, 30), (20, 41), rad=-0.3); note(ax, 4, 36, "next stage\nk = k + 1", size=7.2)
    note(ax, 52, 24.4, "after the last electrode", size=7)
    return save(fig, out, "d_detector_flow.png")


# ------------------------------------------------------------------ 8. RTL blocks
def rtl_blocks(out):
    fig, ax = canvas(10, 4.6)
    note(ax, 1, 36, "arrive_async\n[3:0]", size=7.4)
    box(ax, 13, 31, 14, 9, "sync2", "2 flip-flops\nper line")
    box(ax, 30, 27, 20, 17, "capture_unit ×4", "glitch filter: DEB clocks\ntimestamp = tick count\nat start of high run", WETS, WET)
    box(ax, 30, 6, 20, 9, "timebase", "1 ms tick → 24-bit now")
    box(ax, 54, 27, 18, 17, "snapshot scan", "copy all stamps,\nmin · ties · finality,\n1 electrode / clock")
    box(ax, 76, 27, 22, 17, "sequencer FSM", "16 states: windows,\nsensor checks,\nclassifier, band", ACCS, ACC)
    box(ax, 76, 4, 10, 13, "multiplier", "24×36 bit\n2 stages\n3 DSP")
    box(ax, 88, 4, 10, 13, "const ROM", "params_pkg\nE·(256±tol)")
    box(ax, 54, 4, 18, 9, "result", "valid · cls · loc", WETS, WET)
    arrow(ax, (10, 35.5), (13, 35.5)); arrow(ax, (27, 35.5), (30, 35.5)); arrow(ax, (40, 15), (40, 27))
    arrow(ax, (50, 35.5), (54, 35.5)); arrow(ax, (72, 35.5), (76, 35.5))
    arrow(ax, (81, 27), (81, 17), both=True); arrow(ax, (93, 17), (93, 27)); arrow(ax, (78, 27), (66, 13), rad=0.15)
    note(ax, 30, 1.5, "Decisions use stored timestamps only, never 'what cycle is it now'.", size=7)
    return save(fig, out, "d_rtl_blocks.png")


# ------------------------------------------------------------------ 9. FSM
def fsm(out):
    """Grid layout; arrows end on box edges; run-ending exits drawn as labelled stubs into REPORT."""
    fig, ax = canvas(10, 6.6)
    BW, BH = 12.0, 5.0
    P = {"IDLE": (9, 56), "STAGE": (29, 56), "SCAN": (49, 56), "MIN": (69, 56), "TIE": (89, 56),
         "BSET": (39, 44), "TESTM": (49, 32), "TESTN": (69, 32), "ISSUE": (89, 32),
         "CLS0": (29, 18), "CLS1": (49, 18), "CLS2": (69, 18), "CLS3": (89, 18),
         "UNI": (89, 5), "REPORT": (9, 30)}
    for name, (x, y) in P.items():
        fc = ACCS if name in ("IDLE", "REPORT") else (WETS if name.startswith(("TEST", "CLS", "UNI")) else WHITE)
        box(ax, x - BW / 2, y - BH / 2, BW, BH, name, None, fc, INK, tsize=7.8)

    def edge_pt(c, o):
        (x, y), (ox, oy) = c, o
        dx, dy = ox - x, oy - y
        s = min((BW / 2 + 0.4) / abs(dx) if dx else 9e9, (BH / 2 + 0.4) / abs(dy) if dy else 9e9)
        return x + dx * s, y + dy * s

    def e(a, b, rad=0.0, dashed=False, lab=None, at=0.5, off=(0, 1.4)):
        pa, pb = edge_pt(P[a], P[b]), edge_pt(P[b], P[a])
        arrow(ax, pa, pb, ls="--" if dashed else "-", rad=rad, color=ACC if dashed else INK2)
        if lab:
            note(ax, pa[0] + (pb[0] - pa[0]) * at + off[0], pa[1] + (pb[1] - pa[1]) * at + off[1], lab, size=6.5, ha="center")

    def stub(a, lab, dy=-1):
        x, y = P[a]
        y0 = y + dy * (BH / 2 + 0.3)
        arrow(ax, (x - 3, y0), (x - 3, y0 + dy * 3.2), color=BAD)
        note(ax, x - 2.2, y0 + dy * 2.2, "→ REPORT: " + lab, color=BAD, size=6.3)

    e("IDLE", "STAGE", lab="arm"); e("STAGE", "SCAN", lab="k = 0"); e("SCAN", "MIN", lab="snapshot")
    e("MIN", "TIE", lab="min found"); e("TIE", "ISSUE", lab="ties, final?", off=(5, 0))
    e("STAGE", "BSET", dashed=True, lab="k > 0: B = Δt0·C_k", off=(-8, 0)); e("BSET", "SCAN")
    e("ISSUE", "TESTN", dashed=True, lab="check expiry"); e("ISSUE", "TESTM", dashed=True, rad=0.25, lab="arrival final", at=0.5, off=(0, 5.6))
    e("ISSUE", "SCAN", rad=0.35, lab="filter pending", at=0.45, off=(2, 1))
    e("TESTN", "SCAN", lab="not expired", at=0.45, off=(4, 0))
    e("TESTM", "STAGE", lab="accept, k+1", at=0.3, off=(-7, 0)); e("TESTM", "CLS0", lab="last electrode", at=0.5, off=(-7, 0))
    e("CLS0", "CLS1", dashed=True); e("CLS1", "CLS2", dashed=True); e("CLS2", "CLS3", dashed=True, lab="in band")
    e("CLS3", "CLS0", rad=-0.18, lab="next k", at=0.5, off=(0, -1.8)); e("CLS3", "UNI", lab="all consistent", off=(6, 0))
    e("REPORT", "IDLE", lab="valid", off=(-3, 0)); e("IDLE", "REPORT", rad=0.4, lab="pre-high", at=0.5, off=(5, 0))
    stub("TESTN", "STALL", dy=-1); stub("TESTM", "STALL / SENSOR", dy=-1)
    stub("CLS2", "RESTRICTION", dy=-1); stub("CLS3", "ANOMALY", dy=1)
    note(ax, 83.5, 0.8, "→ REPORT: NOMINAL / UNIFORM_*", color=BAD, size=6.3)
    note(ax, 1, 64, "Dashed blue: via S_MUL (2-cycle wait for the shared multiplier; returns to the state in 'ret'). "
         "MIN loops once per electrode.", size=6.9)
    return save(fig, out, "d_fsm.png")


# ------------------------------------------------------------------ 10. timestamp argument
def timestamp_argument(out):
    fig, ax = canvas(10, 3.4)
    for i in range(9):
        x = 6 + i * 10
        ax.plot([x, x], [24, 30], color=INK2, lw=0.8); note(ax, x, 31.5, f"tick {i}", size=6.6, ha="center")
    ax.plot([6, 96], [27, 27], color=INK2, lw=0.8); note(ax, 1, 27, "now", size=7)
    ax.plot([6, 33, 33, 96], [18, 18, 21, 21], color=WET, lw=1.8); note(ax, 1, 19.5, "line", size=7)
    ax.add_patch(Rectangle((33, 15.5), 4, 1.2, fc=WARN, ec="none")); note(ax, 38, 16, "sync + filter (DEB clocks)", size=6.6, color=WARN)
    ax.plot([33, 33], [21, 27], color=ACC, ls=":", lw=1)
    note(ax, 33, 12.5, "timestamp ts = value of now at the START of the high run", size=7.2, ha="center", color=ACC)
    ax.add_patch(Rectangle((62, 7), 30, 3.2, fc=ACCS, ec=ACC)); note(ax, 77, 8.6, "decision (any later clock)", size=7, ha="center")
    note(ax, 6, 3, "The result depends only on ts values and the window predicate (monotonic in time), "
         "so clock latency cannot change it.", size=7)
    return save(fig, out, "d_timestamp.png")


# ------------------------------------------------------------------ 11. verification flow
def verification_flow(out):
    fig, ax = canvas(10, 3.9)
    box(ax, 1, 14, 12, 8, "SPEC.md", "one source", ACCS, ACC)
    box(ax, 18, 25, 20, 8, "golden_fixed.py", "written from spec")
    box(ax, 18, 3, 20, 8, "RTL", "+ SVA, covergroups")
    box(ax, 42, 14, 20, 8, "stimulus", "corpus + 52 boundary", WETS, WET)
    box(ax, 66, 25, 14, 8, "expected", "(class, loc)")
    box(ax, 66, 3, 14, 8, "xsim TB", "1 tick / clock")
    box(ax, 84, 14, 14, 8, "compare", "bit-exact", WETS, WET)
    arrow(ax, (13, 19), (18, 28)); arrow(ax, (13, 17), (18, 8)); arrow(ax, (38, 29), (66, 29)); arrow(ax, (38, 7), (66, 7))
    arrow(ax, (52, 22), (52, 27)); arrow(ax, (52, 14), (52, 9)); arrow(ax, (80, 28), (88, 22)); arrow(ax, (80, 8), (88, 14))
    note(ax, 1, 37, "also: assertions on every clock, coverage merge (xcrg), 6 seeded mutants", size=7)
    return save(fig, out, "d_verification.png")


def all_diagrams(out):
    return [f(out) for f in (pipeline, bezinge_sensor, pulse_method, comparison, strip_layout, analogy,
                             detector_flow, rtl_blocks, fsm, timestamp_argument, verification_flow)]
