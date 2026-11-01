"""Threshold tuning on the calibration split and metrics on the held-out test split.

Every method is tuned to the same operating point, a false-alarm rate of at most FAR_TARGET on
nominal calibration strips pooled over all noise conditions, and then evaluated on unseen seeds.
"""
from collections import Counter, defaultdict

import numpy as np

from golden import baselines, golden_fixed as gf, golden_float

FAR_TARGET = 0.05
CLS = ["NOMINAL", "UNIFORM_SLOW", "UNIFORM_FAST", "RESTRICTION", "STALL", "SENSOR", "ANOMALY"]
TRUTH_GROUPS = ["NOMINAL", "UNIFORM_SLOW", "UNIFORM_FAST", "RESTRICTION", "RESTRICTION_UPSTREAM", "STALL", "SENSOR"]
METHODS = ["model-based", "fixed timeout", "single sensor", "fixed-K windows"]


def truth_group(r):
    if r["cls"] == gf.RESTRICTION and r["loc"] == 0:
        return "RESTRICTION_UPSTREAM"
    return CLS[r["cls"]]


# ---------------------------------------------------------------- model-based tuning (vectorised)
def tune_model(cfg, rows, tol_grid=range(4, 161, 2), abs_grid=range(4, 201, 2)):
    """Grid search over (TOL_Q, TOL_ABS_Q). Constraint: nominal FAR <= target on calibration.
    Objective: exact (class, loc) accuracy on calibration fault scenarios."""
    E = np.array(cfg["E"], dtype=np.int64)
    N = cfg["N"]
    fixed_pred, done_idx, DT = {}, [], []
    for i, r in enumerate(rows):
        s = gf.stages(cfg, r["ticks"])
        if s[0] == "final":
            fixed_pred[i] = (s[1], s[2])
        else:
            done_idx.append(i); DT.append(s[1])
    DT = np.array(DT, dtype=np.int64)
    truth = [(r["cls"], r["loc"]) for r in rows]
    is_nom = np.array([r["cls"] == gf.NOMINAL for r in rows])
    n_nom, n_fault = is_nom.sum(), (~is_nom).sum()

    lhs = DT[:, 1:] * E[0] * 256                     # (n, N-1)
    base = DT[:, :1] * E[None, 1:]                   # dt0 * E_k
    a = DT.sum(axis=1) * 256
    ET = int(E.sum())
    # contributions of the 'final' (tolerance-independent) scenarios
    fin_far = sum(1 for i, p in fixed_pred.items() if is_nom[i] and p[0] != gf.NOMINAL)
    fin_ok = sum(1 for i, p in fixed_pred.items() if not is_nom[i] and p == truth[i])
    t_cls = np.array([truth[i][0] for i in done_idx]); t_loc = np.array([truth[i][1] for i in done_idx])
    d_nom = is_nom[done_idx]

    best = None
    for tol in tol_grid:
        hi, lo = lhs > base * (256 + tol), lhs < base * (256 - tol)
        flag = hi | lo
        anyf = flag.any(axis=1)
        k = np.argmax(flag, axis=1)
        seg_cls = np.where(hi[np.arange(len(k)), k], gf.RESTRICTION, gf.ANOMALY)
        for ta in abs_grid:
            u = np.where(a > ET * (256 + ta), gf.UNIFORM_SLOW, np.where(a < ET * (256 - ta), gf.UNIFORM_FAST, gf.NOMINAL))
            pc = np.where(anyf, seg_cls, u)
            pl = np.where(anyf, k + 1, 0)
            far = (fin_far + np.sum(d_nom & (pc != gf.NOMINAL))) / n_nom
            if far > FAR_TARGET:
                continue
            acc = (fin_ok + np.sum(~d_nom & (pc == t_cls) & (pl == t_loc))) / n_fault
            if best is None or acc > best[0] + 1e-12:
                best = (acc, far, tol, ta)
    return {"TOL_Q": best[2], "TOL_ABS_Q": best[3], "cal_far": float(best[1]), "cal_acc": float(best[0])}


def tune_baselines(cfg, rows):
    nom = [r for r in rows if r["cls"] == gf.NOMINAL]
    ends = np.array([baselines.end_tick(r["ticks"]) or np.inf for r in nom], dtype=float)
    T = baselines.tune_quantile(ends, FAR_TARGET)
    lo, hi = float(np.quantile(ends, FAR_TARGET / 2)), float(np.quantile(ends, 1 - FAR_TARGET / 2))
    tol_k = None
    for tol in np.arange(0.02, 1.5, 0.005):
        far = np.mean([baselines.fixed_k(r["ticks"], cfg["E"], tol)[0] for r in nom])
        if far <= FAR_TARGET:
            tol_k = float(tol); break
    return {"T_timeout": int(np.ceil(T)), "T_lo": int(np.floor(lo)), "T_hi": int(np.ceil(hi)), "tol_fixed_k": tol_k}


# ---------------------------------------------------------------- evaluation
def run_methods(cfg, bcfg, rows):
    """Per-row predictions of every method: dict method -> list of (fault_flag, decision_tick, cls, loc)."""
    out = {m: [] for m in METHODS}
    nfix = 0
    for r in rows:
        t = r["ticks"]
        c, l, d = gf.decide(cfg, t)
        out["model-based"].append((c != gf.NOMINAL, d, c, l))
        nfix += golden_float.classify(cfg, t) == (c, l)
        f, d = baselines.timeout(t, bcfg["T_timeout"]); out["fixed timeout"].append((f, d, None, None))
        f, d = baselines.single_sensor(t, bcfg["T_lo"], bcfg["T_hi"]); out["single sensor"].append((f, d, None, None))
        f, d = baselines.fixed_k(t, cfg["E"], bcfg["tol_fixed_k"]); out["fixed-K windows"].append((f, d, None, None))
    return out, nfix / len(rows)


def metrics(rows, preds):
    m = {}
    is_fault = np.array([r["cls"] != gf.NOMINAL for r in rows])
    for meth, p in preds.items():
        flag = np.array([x[0] for x in p])
        m[meth] = {"detection": float(flag[is_fault].mean()), "far": float(flag[~is_fault].mean())}
        for key in ("jitter", "cv"):
            for val in sorted({r[key] for r in rows}):
                sel = np.array([r[key] == val for r in rows])
                m[meth][f"det_{key}_{val}"] = float(flag[sel & is_fault].mean())
                m[meth][f"far_{key}_{val}"] = float(flag[sel & ~is_fault].mean())
        by_group = defaultdict(list)
        for r, x in zip(rows, p):
            by_group[truth_group(r)].append(x)
        m[meth]["det_by_group"] = {g: float(np.mean([x[0] for x in v])) for g, v in by_group.items()}
        m[meth]["median_decision_s"] = {g: float(np.median([x[1] for x in v if x[1] is not None]) / 1000)
                                        for g, v in by_group.items() if any(x[1] is not None for x in v)}

    mb = preds["model-based"]
    conf = np.zeros((len(TRUTH_GROUPS), len(CLS)), dtype=int)
    for r, x in zip(rows, mb):
        conf[TRUTH_GROUPS.index(truth_group(r)), x[2]] += 1
    loc = Counter()
    for r, x in zip(rows, mb):
        g = truth_group(r)
        if g in ("RESTRICTION", "STALL", "SENSOR") and x[2] == r["cls"]:
            d = x[3] - r["loc"]
            loc[(g, "exact" if d == 0 else ("+1" if d == 1 else "other"))] += 1
    exact_cls = np.mean([x[2] == r["cls"] and (x[3] == r["loc"] or r["cls"] in (0, 1, 2)) for r, x in zip(rows, mb)
                         if truth_group(r) != "RESTRICTION_UPSTREAM"])
    return m, conf, loc, float(exact_cls)
