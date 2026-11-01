"""Identifiability analysis (handoff section 3.4), computed rather than asserted.

1. Property equivalence. Arrival times depend on fluid and paper only through
   K = gamma * r * cos(theta) / (2 mu), so any two changes with the same K factor give the
   same arrivals. We show it end to end: generator -> sensor ticks -> fixed-point detector.
2. Restriction detectability. A segment of relative permeability k over width w adds hydraulic
   resistance equal to dL_eq = (1/k - 1) * w of extra nominal paper. Sweeping dL_eq for a
   restriction centred in each segment, noise-free, gives the classifier's deviation statistic
   against the tolerance, and the class the detector actually returns.
"""
import math

import numpy as np

from golden import golden_fixed as gf
from physics import params as P
from physics.darcy_series import Strip, arrival_times
from physics.sensor import to_ticks

W_RESTR = 4.0  # mm, width of the swept restriction (fits inside every segment)


def property_equivalence():
    cfg, pos, K = P.detector_config(), P.electrode_positions(), P.v("K_NOM")
    th60 = math.degrees(math.acos(0.5))
    cases = [("viscosity x2", P.fluid_k_factor(mu=2 * P.v("MU"))),
             ("surface tension x0.5", P.fluid_k_factor(gamma=0.5 * P.v("GAMMA"))),
             (f"contact angle 0 -> {th60:.0f} deg", P.fluid_k_factor(theta_deg=th60))]
    out = []
    for name, f in cases:
        ticks = to_ticks(arrival_times(pos, Strip(K=K * f)))
        out.append((name, f, ticks, gf.classify(cfg, ticks)))
    return out


def deviation(times, E_s):
    """Classifier's view: segment ratios rho_k and their consistency with rho_0."""
    dt = np.diff(np.concatenate([[0.0], times]))
    rho = dt / E_s
    q = rho[1:] / rho[0]
    return rho, q


def sweep(dl_eq=np.linspace(0, 60, 61)):
    cfg, pos, K = P.detector_config(), P.electrode_positions(), P.v("K_NOM")
    edges = [0.0] + list(pos)
    E_s = np.diff(np.concatenate([[0.0], np.array(pos) ** 2])) / K
    res = {}
    for seg in range(len(pos)):
        mid = 0.5 * (edges[seg] + edges[seg + 1])
        dev, cls = [], []
        for d in dl_eq:
            k = 1.0 / (1.0 + d / W_RESTR)
            t = arrival_times(pos, Strip(perm=[(mid - W_RESTR / 2, mid + W_RESTR / 2, k)]))
            rho, q = deviation(np.array(t), E_s)
            # seg 0: restriction hides inside rho_0, visible only as non-constant q (decreasing);
            # seg j: first deviating ratio is q_{j} (rho_0 untouched)
            dev.append(float(np.max(np.abs(q - 1))) if seg == 0 else float(q[seg - 1] - 1))
            cls.append(gf.classify(cfg, to_ticks(t)))
        res[seg] = (np.array(dev), cls)
    return dl_eq, res, cfg["TOL_Q"] / 256


def critical(dl_eq, res, tol):
    """Smallest swept dL_eq at which the noise-free detector reports a fault of the right kind."""
    out = {}
    for seg, (dev, cls) in res.items():
        want = (lambda c: c[0] == gf.ANOMALY) if seg == 0 else (lambda c, s=seg: c == (gf.RESTRICTION, s))
        hit = [d for d, c in zip(dl_eq, cls) if want(c)]
        thr = [d for d, v in zip(dl_eq, dev) if abs(v) > tol]
        out[seg] = (hit[0] if hit else None, thr[0] if thr else None)
    return out


def figure(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
    MARK = ["o", "s", "^", "D"]
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    dl, res, tol = sweep()
    eq = property_equivalence()
    pos = P.electrode_positions()
    E_s = np.diff(np.concatenate([[0.0], np.array(pos) ** 2])) / P.v("K_NOM")
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.9), facecolor=SURF, gridspec_kw={"width_ratios": [1, 1.4]})
    for a in ax:
        a.set_facecolor(SURF); a.grid(color=GRID, lw=0.8); a.set_axisbelow(True)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    # (a) three different property changes, one arrival pattern
    for i, (name, f, ticks, c) in enumerate(eq):
        t = np.array(ticks) * P.v("TICK_S")
        rho, _ = deviation(t, E_s)
        ax[0].plot(range(len(pos)), rho, marker=MARK[i], ms=11 - 3 * i, lw=2, color=SERIES[i],
                   mec=SURF, mew=1.2, label=f"{name}  (K x{f:.2f})")
    ax[0].axhline(1, color=INK2, lw=1, ls=":")
    ax[0].set_xticks(range(len(pos))); ax[0].set_ylim(0, 2.6)
    ax[0].set_xlabel("segment k"); ax[0].set_ylabel("segment ratio ρ_k = Δt_k / E_k")
    ax[0].set_title("(a) Different causes, identical signature", fontsize=9, color=INK)
    ax[0].legend(frameon=False, fontsize=7.5, loc="lower right")
    # (b) detectability vs restriction severity
    for seg, (dev, cls) in res.items():
        lab = "upstream of e0 (seg 0): max|ρ_k/ρ_0 − 1|" if seg == 0 else f"segment {seg}: ρ_{seg}/ρ_0 − 1"
        ax[1].plot(dl, np.abs(dev) * 100, marker=MARK[seg], markevery=6, ms=7, lw=2, color=SERIES[seg],
                   mec=SURF, mew=1.2, label=lab)
    ax[1].axhline(tol * 100, color=INK, lw=1.2, ls="--")
    ax[1].text(dl[-1], tol * 100 + 1.5, f"tolerance {tol:.1%}", ha="right", fontsize=7.5, color=INK)
    for x, lab in ((2 * (3 - 1), "corpus 'mild'"), (4 * (6 - 1), "corpus 'strong'")):
        ax[1].axvline(x, color=INK2, lw=1, ls=":")
        ax[1].text(x + 0.6, 92, lab, fontsize=7.5, color=INK2, rotation=90, va="top")
    ax[1].set_xlabel("restriction severity ΔL_eq = (1/k − 1)·w  (mm of equivalent extra paper)")
    ax[1].set_ylabel("deviation seen by the classifier (%)"); ax[1].set_ylim(0, 100)
    ax[1].set_title("(b) A restriction is visible once its signature exceeds the tolerance", fontsize=9, color=INK)
    ax[1].legend(frameon=False, fontsize=7.5, loc="upper left", bbox_to_anchor=(0.08, 1.0))
    fig.tight_layout(); fig.savefig(path, dpi=170); plt.close(fig)
    return eq, critical(dl, res, tol)
