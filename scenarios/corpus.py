"""Full scenario corpus: fault family x location x jitter x K variability x seed, from one call.

Every scenario passes through the rich generator (physics/darcy_series.py) and the sensor model
(physics/sensor.py) with a constant detection lag. Seeds are derived from the cell indices, so
the corpus is bit-reproducible. Replicates 0..R/2-1 form the CALIBRATION split (threshold tuning);
the rest form the TEST split (all reported metrics).

Ground truth is the physical cause. For STALL the location is the first electrode the front never
reaches (computed from the simulation, because creep can carry the front further than the
exhaustion point).
"""
import csv
import math

import numpy as np

from physics import params as P
from physics.darcy_series import Strip, arrival_times, stall_position
from physics.sensor import to_ticks

NOMINAL, UNIFORM_SLOW, UNIFORM_FAST, RESTRICTION, STALL, SENSOR, ANOMALY = range(7)
JITTERS = P.v("JITTER_S")
CVS = (0.0, P.v("K_CV"), P.v("K_CV_HIGH"))
REPS = 20
REPS_NOMINAL = 100   # false-alarm rates near 5 % need ~10^3 nominal strips per split for a tight estimate


def _volume_for_stall(target_mm):
    """Sample volume whose final front (incl. creep) stops at target_mm (bisection)."""
    lo, hi = 0.1, P.v("C_ABS") * P.v("WIDTH") * target_mm
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if stall_position(Strip(v_sample=mid)) < target_mm:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def specs(positions=None):
    """List of (family, truth_cls, truth_loc, strip_kwargs, k_factor, sensor_faults)."""
    pos = positions or P.electrode_positions()
    n = len(pos)
    edges = [0.0] + list(pos)
    out = [("nominal", NOMINAL, 0, {}, 1.0, {})]
    for name, mu in (("water37C", P.v("MU_WATER37")), ("plasma", P.v("MU_PLASMA")),
                     ("2x_viscosity", 2 * P.v("MU")), ("whole_blood", P.v("MU_BLOOD"))):
        f = P.fluid_k_factor(mu=mu)
        out.append((f"uniform_{name}", UNIFORM_FAST if f > 1 else UNIFORM_SLOW, 0, {}, f, {}))
    for k in range(n):
        mid = 0.5 * (edges[k] + edges[k + 1])
        for sev, half, krel in (("mild", 1.0, 1 / 3), ("strong", 2.0, 1 / 6)):
            out.append((f"restriction_seg{k}_{sev}", RESTRICTION, k, {"perm": [(mid - half, mid + half, krel)]}, 1.0, {}))
    for k in range(n):
        v = _volume_for_stall(0.5 * (edges[k] + edges[k + 1]))
        out.append((f"stall_seg{k}", STALL, k, {"v_sample": v}, 1.0, {}))
    for k in range(n):
        for f in ("missed", "spurious", "stuck"):
            out.append((f"sensor_{f}_e{k}", SENSOR, k, {}, 1.0, {k: f}))
    return out


def generate(path=None, positions=None, reps=REPS, reps_nominal=REPS_NOMINAL):
    pos = positions or P.electrode_positions()
    n = len(pos)
    rows = []
    sid = 0
    for si, (fam, cls, loc, kw, kf, faults) in enumerate(specs(pos)):
        nrep = reps_nominal if fam == "nominal" else reps
        for ji, jit in enumerate(JITTERS):
            for ci, cv in enumerate(CVS):
                for r in range(nrep):
                    rng = np.random.default_rng([n, si, ji, ci, r])
                    # strip-to-strip variability: lognormal multiplier with the given CV
                    s = math.sqrt(math.log1p(cv ** 2))
                    K = P.v("K_NOM") * kf * (float(rng.lognormal(-s * s / 2, s)) if cv > 0 else 1.0)
                    times = arrival_times(pos, Strip(K=K, **kw))
                    t_cls, t_loc = cls, loc
                    if cls == STALL:
                        never = [k for k, t in enumerate(times) if not math.isfinite(t)]
                        t_loc = never[0] if never else loc
                        if not never:        # a fast strip crept past every electrode: not a stall
                            t_cls, t_loc = NOMINAL, 0
                    ticks = to_ticks(times, rng=rng, lag_s=P.v("LAG_S"), jitter_s=jit, faults=faults)
                    rows.append({"id": sid, "split": "cal" if r < nrep // 2 else "test", "family": fam,
                                 "cls": t_cls, "loc": t_loc, "jitter": jit, "cv": cv, "rep": r,
                                 "ticks": ticks})
                    sid += 1
    if path:
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "split", "family", "cls", "loc", "jitter", "cv", "rep"] + [f"t{k}" for k in range(n)])
            for r_ in rows:
                w.writerow([r_[c] for c in ("id", "split", "family", "cls", "loc", "jitter", "cv", "rep")] + r_["ticks"])
    return rows


def write_stim(rows, path):
    with open(path, "w") as f:
        for r in rows:
            f.write(f"{r['id']} " + " ".join(map(str, r["ticks"])) + "\n")
