"""Floating-point reference: the SPEC.md rules expressed as physical ratios.

rho_k = dt_k / E_k is the segment's slowdown relative to the nominal Washburn prediction.
Agreement with golden_fixed is reported, not required (they can differ only at exact window edges).
"""
NOMINAL, UNIFORM_SLOW, UNIFORM_FAST, RESTRICTION, STALL, SENSOR, ANOMALY = range(7)


def classify(cfg, ticks):
    N, E = cfg["N"], cfg["E"]
    tol, tol_abs = cfg["TOL_Q"] / 256, cfg["TOL_ABS_Q"] / 256
    stall, first_max = 1 + cfg["TOL_STALL_Q"] / 256, cfg["FIRST_Q"] / 256
    for k in range(N):
        if ticks[k] == -2:
            return SENSOR, k
    rho, t_prev = [], 0.0
    for idx in range(N):
        cand = [ticks[j] for j in range(idx, N) if ticks[j] >= 1]
        if not cand:
            return STALL, idx
        te = min(cand)
        limit = first_max * E[0] if idx == 0 else rho[0] * E[idx] * stall  # adaptive window
        if te - t_prev > limit:
            return STALL, idx
        arrived = [j for j in range(idx, N) if ticks[j] == te]
        if arrived != [idx]:
            others = [j for j in arrived if j != idx]
            return SENSOR, (min(others) if idx in arrived else idx)
        rho.append((te - t_prev) / E[idx])
        t_prev = te
        if idx == 0 and rho[0] < cfg["MIN_FIRST_Q"] / 256:   # faster than any plausible sample
            return SENSOR, 0
    for k in range(1, N):
        q = rho[k] / rho[0]
        if q > 1 + tol:
            return RESTRICTION, k
        if q < 1 - tol:
            return ANOMALY, k
    r_tot = t_prev / sum(E)          # whole-run K estimate: lag and jitter matter least here
    if r_tot > 1 + tol_abs:
        return UNIFORM_SLOW, 0
    if r_tot < 1 - tol_abs:
        return UNIFORM_FAST, 0
    return NOMINAL, 0
