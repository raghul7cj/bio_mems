"""Fixed-point golden model, written from SPEC.md (integer arithmetic, same widths as the RTL).

Because every RTL decision is an exact integer comparison (cross-multiplication, no division,
no rounding), Python's unbounded integers reproduce it exactly as long as products fit the RTL's
64-bit comparators, which is asserted below.

Split in two so threshold tuning can reuse the first part:
  stages()           arrival sequencing, timeouts, sensor checks (independent of TOL / TOL_ABS)
  classify_segments() the segment-ratio classifier (depends on TOL / TOL_ABS only)
"""
NOMINAL, UNIFORM_SLOW, UNIFORM_FAST, RESTRICTION, STALL, SENSOR, ANOMALY = range(7)
LIMIT = 1 << 64


def _chk(*xs):
    for x in xs:
        assert 0 <= x < LIMIT, "product exceeds RTL comparator width"
    return xs


def _timeout_params(cfg, idx, dt0):
    """Timeout fires at elapsed e iff e*A > B."""
    E = cfg["E"]
    if idx == 0:
        return 256, E[0] * cfg["FIRST_Q"]
    return E[0] * 256, dt0 * E[idx] * (256 + cfg["TOL_STALL_Q"])


def stages(cfg, ticks):
    """Returns ('done', dt, t_last) or ('final', cls, loc, decision_tick)."""
    N = cfg["N"]
    pre = [k for k in range(N) if ticks[k] == -2]
    if pre:
        return "final", SENSOR, pre[0], 0
    dt, t_prev = [], 0
    for idx in range(N):
        A, B = _timeout_params(cfg, idx, dt[0] if dt else 0)
        cand = [ticks[j] for j in range(idx, N) if ticks[j] >= 1]
        te = min(cand) if cand else None
        if te is None or _chk((te - t_prev) * A, B)[0] > B:
            return "final", STALL, idx, t_prev + B // A + 1
        arrived = [j for j in range(idx, N) if ticks[j] == te]
        others = [j for j in arrived if j != idx]
        if others:
            return "final", SENSOR, (min(others) if idx in arrived else idx), te
        dt.append(te - t_prev)
        t_prev = te
        if idx == 0 and dt[0] * 256 < cfg["E"][0] * cfg["MIN_FIRST_Q"]:
            return "final", SENSOR, 0, te                  # implausibly fast first segment
    return "done", dt, t_prev


def classify_segments(cfg, dt):
    N, E, tol = cfg["N"], cfg["E"], cfg["TOL_Q"]
    for k in range(1, N):
        lhs, hi, lo = _chk(dt[k] * E[0] * 256, dt[0] * E[k] * (256 + tol), dt[0] * E[k] * (256 - tol))
        if lhs > hi:
            return RESTRICTION, k
        if lhs < lo:
            return ANOMALY, k
    et = sum(E)
    a, hi, lo = _chk(sum(dt) * 256, et * (256 + cfg["TOL_ABS_Q"]), et * (256 - cfg["TOL_ABS_Q"]))
    if a > hi:
        return UNIFORM_SLOW, 0
    if a < lo:
        return UNIFORM_FAST, 0
    return NOMINAL, 0


def decide(cfg, ticks):
    """(class, loc, decision_tick)."""
    s = stages(cfg, ticks)
    if s[0] == "final":
        return s[1], s[2], s[3]
    c, l = classify_segments(cfg, s[1])
    return c, l, s[2]


def classify(cfg, ticks):
    c, l, _ = decide(cfg, ticks)
    return c, l
