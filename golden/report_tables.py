"""Identifiability table for the report: physics signature, verdict, and the evidence for it
(test split of the corpus + the noise-free sweep in golden/identifiability.py)."""
from collections import defaultdict

from golden import golden_fixed as gf, identifiability as idf
from physics import params as P
from scenarios import corpus

NAMES = ["NOMINAL", "UNIFORM_SLOW", "UNIFORM_FAST", "RESTRICTION", "STALL", "SENSOR", "ANOMALY"]


def family_stats():
    cfg = P.detector_config()
    st = defaultdict(lambda: {"n": 0, "fault": 0, "cls": 0, "exact": 0, "pred": defaultdict(int)})
    for r in corpus.generate():
        if r["split"] != "test":
            continue
        c, l = gf.classify(cfg, r["ticks"])
        s = st[r["family"]]
        s["n"] += 1
        s["fault"] += c != gf.NOMINAL
        s["cls"] += c == r["cls"]
        s["exact"] += (c, l) == (r["cls"], r["loc"])
        s["pred"][NAMES[c]] += 1
    return st


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def identifiability_md():
    st = family_stats()
    eq = idf.property_equivalence()
    dl, res, tol = idf.sweep()
    crit = idf.critical(dl, res, tol)
    agg = lambda fams, key: (sum(st[f][key] for f in fams), sum(st[f]["n"] for f in fams))

    def fams(prefix):
        return [f for f in st if f.startswith(prefix)]

    same = len({tuple(t) for _, _, t, _ in eq}) == 1
    u = fams("uniform_")
    u_slow = [f for f in u if not f.endswith("water37C")]
    r_strong = [f"restriction_seg{k}_strong" for k in (1, 2, 3)]
    r_mild = [f"restriction_seg{k}_mild" for k in (1, 2, 3)]
    up = fams("restriction_seg0")
    up_pred = defaultdict(int)
    for f in up:
        for c, v in st[f]["pred"].items():
            up_pred[c] += v
    n_up = sum(up_pred.values())
    stall = fams("stall_")
    sens = fams("sensor_")
    miss_last = "sensor_missed_e3"
    thr = ", ".join(f"segment {k}: {crit[k][0]:.0f} mm" for k in (1, 2, 3))

    rows = [
        ("Fluid-property change: viscosity, surface tension, contact angle",
         "All segment ratios equal, ρ_k = ρ_0 ≠ 1: Washburn with a different K",
         "**Class: yes.** **Which property: no**",
         f"Test split: slow fluids flagged UNIFORM_SLOW {pct(*agg(u_slow, 'cls'))}; warm water (K +29 %) flagged "
         f"UNIFORM_FAST {pct(*agg(['uniform_water37C'], 'cls'))}. Viscosity ×2, surface tension ×0.5 and contact angle "
         f"0→60° give {'identical' if same else 'DIFFERENT'} arrival ticks {eq[0][2]}, so no detector can separate them."),
        ("Localized restriction in segment j ≥ 1",
         "ρ_0 … ρ_{j−1} nominal; ρ_j steps up, later segments stay raised",
         "**Yes, with location**, above a severity threshold",
         f"Noise-free threshold ΔL_eq: {thr}. Strong (20 mm): detected {pct(*agg(r_strong, 'fault'))}, correct segment "
         f"{pct(*agg(r_strong, 'exact'))}. Mild (4 mm, below threshold): detected {pct(*agg(r_mild, 'fault'))}, "
         f"barely above the {pct(st['nominal']['fault'], st['nominal']['n'])} false-alarm rate on nominal strips. "
         f"Segment 3 strong is detected least, {pct(st['restriction_seg3_strong']['fault'], st['restriction_seg3_strong']['n'])}: "
         f"20 mm sits close to its 15 mm threshold."),
        ("Restriction upstream of electrode 0",
         "Adds a constant resistance: t ∝ L² + 2·ΔL·L, so ρ_k/ρ_0 decreases along the strip",
         "**Partly.** Weak: no, it looks like a fluid change. Strong: flagged as non-Washburn",
         f"Noise-free: indistinguishable from UNIFORM_SLOW below ΔL_eq ≈ {crit[0][0]:.0f} mm, ANOMALY above. "
         f"Test split: ANOMALY {pct(up_pred['ANOMALY'], n_up)}, UNIFORM_SLOW {pct(up_pred['UNIFORM_SLOW'], n_up)}, "
         f"NOMINAL {pct(up_pred['NOMINAL'], n_up)}. The deviation saturates near 35 %, so it is never as visible as a "
         f"downstream restriction."),
        ("Insufficient volume / stall",
         "Downstream electrodes never fire within the adaptive window",
         "**Yes, with the gap**",
         f"Test split: STALL with the correct gap {pct(*agg(stall, 'exact'))}."),
        ("Sensor fault: missed, spurious, stuck",
         "Impossible ordering, a line high before the sample, or an implausibly fast first segment",
         "**Usually.** Electrode index is ambiguous",
         f"Test split: flagged as a fault {pct(*agg(sens, 'fault'))}, classified SENSOR {pct(*agg(sens, 'cls'))}, "
         f"correct electrode {pct(*agg(sens, 'exact'))}. A missed upstream electrode and a spurious downstream one "
         f"give the same out-of-order pattern. A missed last electrode is physically a stall in the last gap "
         f"(STALL {pct(st[miss_last]['pred']['STALL'], st[miss_last]['n'])} of those cases)."),
        ("K change smaller than the strip-to-strip spread",
         "Flat ρ inside the nominal band",
         "**No**, by design",
         f"The ±{P.TOL_ABS_Q / 256:.1%} band absorbs the measured 3.2–10 % batch variability and the +9 % gravity "
         f"systematic on K, at the cost of fluids within that band of water."),
    ]
    lines = ["| Fault class | Signature across 4 electrodes | Identifiable? | Evidence |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    return "\n".join(lines), st, crit
