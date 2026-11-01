"""Model and detector parameters. Every entry carries a source, a repo computation, or an 'assumed' tag.

Reference keys (full citations in REFS): KAS20, PAT20, MIR26, BEZ24, MEN10.
"""
import math

REFS = {
    "KAS20": "S. Kasetsirikul, M. J. A. Shiddiky, N.-T. Nguyen, Chemosensors 8(3), 65 (2020), doi:10.3390/chemosensors8030065 (CC BY)",
    "PAT20": "S. Patari, P. Sinha Mahapatra, ACS Omega 5(36), 22931-22939 (2020), doi:10.1021/acsomega.0c02407",
    "MIR26": "J. J. Miranda-Blancas et al., Fluids 11(5), 127 (2026), doi:10.3390/fluids11050127",
    "BEZ24": "L. Bezinge et al., Lab Chip 24(15), 3651-3657 (2024), doi:10.1039/D4LC00390J",
    "MEN10": "S. Mendez et al., Langmuir 26(2), 1380-1385 (2010) (quasi-stationary flow in segments; not yet read)",
}

# name: (value, unit, provenance)
PARAMS = {
    # --- paper: nitrocellulose membrane Whatman FF170HP (the lateral-flow membrane class used in RDTs)
    "K_NOM":    (9.42, "mm^2/s", "repo: physics/calibrate.py Washburn fit to KAS20 Fig. 7a (digitised); "
                                 "cross-checks KAS20 Table 6 p^2 = 9.73, FF170HP rating 40^2/170 = 9.41; "
                                 "gravity-corrected fit +9 % (systematic)"),
    "K_CV":     (0.032, "-",     "repo: CV of K = p^2 over the 2/4/6 mm strips, KAS20 Table 6"),
    "K_CV_HIGH": (0.10, "-",     "PAT20: max deviation < 10 % across five runs (Whatman 4), used as upper bound"),
    "P_C":      (2345.0, "Pa",   "KAS20 Table 8 (nitrocellulose, model-derived estimate)"),
    "C_ABS":    (0.101, "uL/mm^2", "KAS20 Sec. 4.3: 10.1 uL/cm^2, direct weighing, non-laminated NC"),
    "EXPONENT": (0.546, "-",     "repo: power-law fit L ~ t^n to KAS20 Fig. 7a (t >= 1 s); MIR26 reports "
                                 "0.39-0.46 for radial imbibition in filter paper over 60 min"),
    # --- liquid: water at room temperature
    "GAMMA":    (0.072, "N/m",   "PAT20 Table (water)"),
    "MU":       (8.9e-4, "Pa s", "PAT20 / MIR26 (water); KAS20 uses 8.94e-4"),
    "RHO":      (1000.0, "kg/m^3", "KAS20 Table 2"),
    "THETA":    (0.0, "deg",     "assumed: fully wetting (PAT20 makes the same assumption); enters only via K"),
    # --- strip geometry and electrodes
    "L_MAX":    (40.0, "mm",     "assumed: equals the 4 cm FF170HP rating length and the KAS20 strip"),
    "WIDTH":    (4.0, "mm",      "assumed: middle KAS20 width (wicking speed independent of width, KAS20 Sec. 4.4)"),
    "N_ELEC":   (4, "-",         "assumed: handoff default; electrodes spaced uniformly in L^2"),
    "V_SAMPLE": (25.0, "uL",     "assumed: typical RDT sample volume; strip needs C_ABS*WIDTH*L_MAX = 16.2 uL"),
    "CREEP_TAU": (20.0, "s",     "assumed: decay time of front creep after the source empties (KAS20 Fig. 2 "
                                 "shows the front keeps moving after reservoir removal; magnitude not reported)"),
    # --- sensing
    "TICK_S":   (1e-3, "s",      "design choice: fill takes ~10^2 s, so 1 ms is ample"),
    "LAG_S":    (1.8, "s",       "BEZ24 main text (verified in Phase 6): electrode flow times average 1.8 s longer "
                                 "than visual absorption (IQR -0.1 to 2.5 s, Fig. S4); applied here as a constant "
                                 "arrival-detection lag (an interpretation: the paper's figure is a duration bias)"),
    "JITTER_S": ((0.0, 0.1, 0.5, 1.0, 2.0), "s", "sweep of arrival-detection jitter (1 sigma); BEZ24's IQR implies "
                                 "~1.4 s per detected event (realdata/compare.py), inside the swept range"),
    # --- sample fluids (scale K by (gamma cos(theta)/mu) relative to water)
    "MU_PLASMA": (1.3e-3, "Pa s", "assumed: typical plasma/serum viscosity 1.1-1.3 mPa s (textbook value, verify)"),
    "MU_BLOOD":  (3.5e-3, "Pa s", "assumed: whole blood at high shear 3-4 mPa s (textbook value, verify)"),
    "MU_WATER37": (6.9e-4, "Pa s", "assumed: water at 37 C (standard tables)"),
}

# Detector tolerances in 1/256 units (see SPEC.md).
# TOL_Q / TOL_ABS_Q: repo, tuned by `run.py phase3` on the calibration split (nominal FAR <= 5 %,
# max exact class+location accuracy); phase3 fails if these drift from the tuned values.
TOL_Q = 50         # 19.5 % segment-to-segment consistency
TOL_ABS_Q = 38     # 14.8 % nominal band on the total fill time (covers the +9 % gravity systematic on K)
TOL_STALL_Q = 512  # stall if a segment takes > 3x its r-hat-scaled expectation
FIRST_Q = 1280     # first segment may take up to 5x nominal (whole blood ~3.9x water viscosity, +10 % CV, +lag)
MIN_FIRST_Q = 128  # first segment faster than 0.5x nominal = sensor fault (warm water is only 1.29x faster)
TS_BITS = 24      # 2^24 ms = 4.7 h, well beyond the longest run (4x nominal fill + stall margin < 1 h)


def v(name):
    return PARAMS[name][0]


def fluid_k_factor(mu=None, gamma=None, theta_deg=None):
    """K scales as gamma*cos(theta)/mu (capillary pressure over viscosity); only the product is identifiable."""
    mu = v("MU") if mu is None else mu
    gamma = v("GAMMA") if gamma is None else gamma
    th = v("THETA") if theta_deg is None else theta_deg
    return (gamma * math.cos(math.radians(th)) / mu) / (v("GAMMA") * math.cos(math.radians(v("THETA"))) / v("MU"))


def electrode_positions(n=None, lmax=None):
    """Uniform in L^2: equal expected segment times (equal timing resolution per segment)."""
    n, lmax = n or v("N_ELEC"), lmax or v("L_MAX")
    return [lmax * math.sqrt((k + 1) / n) for k in range(n)]


def expected_segment_ticks(positions=None, k_nom=None):
    pos = positions or electrode_positions()
    k_nom = k_nom or v("K_NOM")
    prev, out = 0.0, []
    for L in pos:
        out.append(round((L * L - prev * prev) / k_nom / v("TICK_S")))
        prev = L
    return out


def detector_config():
    return {"N": v("N_ELEC"), "E": expected_segment_ticks(), "TOL_Q": TOL_Q, "TOL_ABS_Q": TOL_ABS_Q,
            "TOL_STALL_Q": TOL_STALL_Q, "FIRST_Q": FIRST_Q, "MIN_FIRST_Q": MIN_FIRST_Q, "TS_BITS": TS_BITS}


def write_param_table(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("| Parameter | Value | Unit | Provenance |\n|---|---|---|---|\n")
        for k, (val, unit, src) in PARAMS.items():
            f.write(f"| {k} | {val} | {unit} | {src} |\n")
        f.write("\n**References**\n\n" + "\n".join(f"- {k}: {s}" for k, s in REFS.items()) + "\n")


def write_sv_package(path, cfg=None):
    """Expected-window unit as a constant ROM: every product of two constants is folded here,
    so the RTL multiplies only (measured time) x (constant)."""
    cfg = cfg or detector_config()
    E = cfg["E"]
    arr = lambda xs: ", ".join(str(x) for x in xs)
    et = sum(E)
    text = f"""// GENERATED by physics/params.py -- do not edit.
package params_pkg;
  localparam int N = {cfg['N']};
  localparam int TS_BITS = {cfg['TS_BITS']};
  localparam int MBW = 36;                                   // constant operand width of the multiplier
  localparam longint unsigned E [0:N-1] = '{{{arr(E)}}};
  localparam longint unsigned C_STALL [0:N-1] = '{{{arr(e * (256 + cfg['TOL_STALL_Q']) for e in E)}}};
  localparam longint unsigned C_HI [0:N-1] = '{{{arr(e * (256 + cfg['TOL_Q']) for e in E)}}};
  localparam longint unsigned C_LO [0:N-1] = '{{{arr(e * (256 - cfg['TOL_Q']) for e in E)}}};
  localparam longint unsigned B_FIRST = {E[0] * cfg['FIRST_Q']};     // stage-0 window: e*256 > B_FIRST
  localparam longint unsigned MIN_FIRST = {E[0] * cfg['MIN_FIRST_Q']}; // dt0*256 < MIN_FIRST -> sensor
  localparam longint unsigned U_HI = {et * (256 + cfg['TOL_ABS_Q'])};
  localparam longint unsigned U_LO = {et * (256 - cfg['TOL_ABS_Q'])};
  // raw tolerances: used only by the verification checkers (independent of the folded constants)
  localparam longint unsigned TOL_Q = {cfg['TOL_Q']}, TOL_ABS_Q = {cfg['TOL_ABS_Q']}, TOL_STALL_Q = {cfg['TOL_STALL_Q']};
  localparam longint unsigned FIRST_Q = {cfg['FIRST_Q']}, MIN_FIRST_Q = {cfg['MIN_FIRST_Q']};
  typedef enum logic [2:0] {{NOMINAL=0, UNIFORM_SLOW=1, UNIFORM_FAST=2, RESTRICTION=3,
                            STALL=4, SENSOR=5, ANOMALY=6}} cls_t;
endpackage
"""
    assert max(e * (256 + cfg["TOL_STALL_Q"]) for e in E) < 1 << 36 and max(E) < 1 << cfg["TS_BITS"]
    with open(path, "w") as f:
        f.write(text)
