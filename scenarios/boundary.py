"""Directed boundary-case scenarios (Phase 5).

Each case is placed on, or one tick beside, a decision boundary of SPEC.md, built from the
detector constants so it stays on the edge if the parameters change. Every case carries an
`intent` check that the golden model's verdict must satisfy, so a case that drifts off its
boundary is reported rather than silently passing.

Glitches are w-clock pulses; the RTL glitch filter (DEB clocks, testbench value) accepts a pulse
as an arrival iff w >= DEB, so the golden input is the effective arrival tick after that rule.
"""
from math import gcd

from golden import golden_fixed as gf

TB_DEB = 4  # must match tb/tb_top.sv
NOM, U_SLOW, U_FAST, RESTR, STALL, SENSOR, ANOM = range(7)


def effective_ticks(ticks, glitches, deb=TB_DEB):
    t = list(ticks)
    for j, g, w in glitches:
        if w >= deb and t[j] != -2:
            t[j] = g if t[j] == -1 else min(t[j], g)
    return t


def _cum(dts):
    out, s = [], 0
    for d in dts:
        s += d
        out.append(s)
    return out


def cases(cfg):
    N, E = cfg["N"], cfg["E"]
    E0 = E[0]
    out = []

    def add(name, ticks, intent, glitches=()):
        out.append((name, list(ticks), list(glitches), intent))

    is_ = lambda c, l=None: (lambda r: r[0] == c and (l is None or r[1] == l))
    not_ = lambda c, l: (lambda r: not (r[0] == c and r[1] == l))
    nom = _cum(E)
    add("nominal", nom, is_(NOM, 0))

    # --- stage windows: last accepted elapsed tick, and one past it
    e0max = E0 * cfg["FIRST_Q"] // 256
    add("win0_edge_in", [e0max * (k + 1) for k in range(N)], lambda r: r != (STALL, 0))
    add("win0_edge_out", [e0max + 1] + [-1] * (N - 1), is_(STALL, 0))
    for L in range(1, N):
        emax = (E0 * E[L] * (256 + cfg["TOL_STALL_Q"])) // (E0 * 256)   # dt0 = E0
        base = nom[:L]
        add(f"win{L}_edge_in", base + [base[-1] + emax] + [-1] * (N - L - 1),
            (lambda L: lambda r: r != (STALL, L))(L) if L == N - 1 else is_(STALL, L + 1))
        add(f"win{L}_edge_out", base + [base[-1] + emax + 1] + [-1] * (N - L - 1), is_(STALL, L))

    # --- segment-consistency tolerance edges (equality reachable when E_1 = E_0)
    for tol_sign, name, cls in ((+1, "hi", RESTR), (-1, "lo", ANOM)):
        f = 256 + tol_sign * cfg["TOL_Q"]
        step = 256 // gcd(256, f)
        dt0 = max(step, round(E0 / step) * step)
        num = dt0 * E[1] * f
        dt1 = num // (E0 * 256)
        exact = dt1 * E0 * 256 == num
        if tol_sign < 0 and not exact:
            dt1 += 1                                        # smallest dt1 that is not an anomaly
        rest = [dt0 * E[k] // E0 for k in range(2, N)]
        add(f"tol_{name}_edge_in", _cum([dt0, dt1] + rest), not_(cls, 1))
        add(f"tol_{name}_edge_out", _cum([dt0, dt1 + tol_sign] + rest), is_(cls, 1))

    # --- first-segment plausibility floor
    mf = -(-E0 * cfg["MIN_FIRST_Q"] // 256)                 # smallest accepted dt0
    add("minfirst_edge_in", _cum([mf * E[k] // E0 for k in range(N)]), lambda r: r != (SENSOR, 0))
    add("minfirst_edge_out", _cum([mf - 1] + [(mf - 1) * E[k] // E0 for k in range(1, N)]), is_(SENSOR, 0))
    add("earliest_tick", [1] + nom[1:], is_(SENSOR, 0))

    # --- uniform-K band on the total fill time
    et = sum(E)
    for name, T, chk in (("uni_hi_in", (et * (256 + cfg["TOL_ABS_Q"])) // 256, NOM),
                         ("uni_hi_out", (et * (256 + cfg["TOL_ABS_Q"])) // 256 + 1, U_SLOW),
                         ("uni_lo_in", -(-et * (256 - cfg["TOL_ABS_Q"]) // 256), NOM),
                         ("uni_lo_out", -(-et * (256 - cfg["TOL_ABS_Q"]) // 256) - 1, U_FAST)):
        dts = [T * e // et for e in E]
        dts[-1] += T - sum(dts)
        add(name, _cum(dts), is_(chk, 0))

    # --- back-to-back and simultaneous arrivals
    add("b2b_consecutive", [E0 + k for k in range(N)], is_(ANOM, 1))
    add("b2b_last_pair", nom[:-1] + [nom[-2] + 1], is_(ANOM, N - 1))
    add("tie_e0_e1", [E0, E0] + nom[2:], is_(SENSOR, 1))
    add("tie_mid", nom[:1] + [nom[1], nom[1]] + nom[3:], is_(SENSOR, 2))
    add("all_same_tick", [E0] * N, is_(SENSOR, 1))
    add("out_of_order", [nom[0], nom[2], nom[1]] + nom[3:], is_(SENSOR, 1))

    # --- lines high before arm
    for j in range(N):
        add(f"prehigh_e{j}", [(-2 if k == j else t) for k, t in enumerate(nom)], is_(SENSOR, j))
    add("prehigh_e1_e3", [(-2 if k in (1, 3) else t) for k, t in enumerate(nom)], is_(SENSOR, 1))
    add("prehigh_all", [-2] * N, is_(SENSOR, 0))

    # --- every classifier location (so one boundary run reaches every coverage bin)
    for k in range(1, N):
        for name, f, cls in (("restr", 3, RESTR), ("anom", -2, ANOM)):     # x1.5 / x0.6 on segment k
            dts = [E[i] * (2 + (f > 0)) // 2 if i == k and f > 0 else (E[i] * 3 // 5 if i == k else E[i])
                   for i in range(N)]
            add(f"{name}_seg{k}", _cum(dts), is_(cls, k))

    # --- missing electrodes
    for L in range(N):                                   # nothing arrives after stage L-1: pure timeout
        add(f"missed_from_e{L}", nom[:L] + [-1] * (N - L), is_(STALL, L))
    add("missed_all", [-1] * N, is_(STALL, 0))
    add("missed_last", nom[:-1] + [-1], is_(STALL, N - 1))
    add("missed_middle", [nom[0], -1] + nom[2:], is_(SENSOR, 1))

    # --- glitches (filter length TB_DEB clocks)
    for w in (1, TB_DEB - 1):
        add(f"glitch_e0_w{w}", nom, is_(NOM, 0), [(0, 1000, w)])
        add(f"glitch_e2_stage1_w{w}", nom, is_(NOM, 0), [(2, (nom[0] + nom[1]) // 2, w)])
    add(f"glitch_e0_w{TB_DEB}", nom, is_(SENSOR, 0), [(0, 1000, TB_DEB)])
    add(f"glitch_e2_stage1_w{TB_DEB}", nom, is_(SENSOR, 1), [(2, (nom[0] + nom[1]) // 2, TB_DEB)])
    add("glitch_all_lines_w3", nom, is_(NOM, 0), [(j, 500, TB_DEB - 1) for j in range(N)])
    return out


def saturation_bound(cfg):
    """Largest tick at which any run can still be undecided: every stage at its maximal window."""
    E = cfg["E"]
    dt0_max = E[0] * cfg["FIRST_Q"] // 256
    t = dt0_max
    for L in range(1, cfg["N"]):
        t += dt0_max * E[L] * (256 + cfg["TOL_STALL_Q"]) // (E[0] * 256) + 1
    return t + 1


def build(cfg, id0=0):
    """[(id, name, ticks, glitches, expected(cls, loc), intent_ok)]"""
    rows = []
    for i, (name, ticks, gl, intent) in enumerate(cases(cfg)):
        exp = gf.classify(cfg, effective_ticks(ticks, gl))
        rows.append((id0 + i, name, ticks, gl, exp, bool(intent(exp))))
    return rows
