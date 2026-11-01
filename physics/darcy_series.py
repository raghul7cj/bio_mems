"""Generator-side capillary filling model: quasi-steady Darcy flow through a strip with piecewise
permeability and width, a finite sample volume, and fluid-property scaling.

Physics. In a thin strip of thickness h, relative width w(x) and relative permeability k(x), the
volumetric flux Q is uniform along the wetted length at any instant (quasi-steady, incompressible):

    Q = (k0 h W0 / mu) * P_c / R(L),      R(L) = integral_0^L dx / (k(x) w(x))

and the front advances by filling pores at the front: phi h W0 w(L) dL/dt = Q, so

    dL/dt = (K/2) / ( w(L) R(L) ),        K = 2 k0 P_c / (mu phi)

For k = w = 1 this is Washburn, L dL/dt = K/2. Integrating dt = (2/K) w(L) R(L) dL gives t(L).
A low-permeability or narrowed segment raises R for every later position, so its signature grows
downstream (the localisation lag seen in Phase 1). Mendez et al. 2010 treat the same quasi-stationary
segment problem. Gravity and inertia are dropped (see physics/scaling.py).

Finite sample volume. The wetted volume is V(L) = C_abs W0 integral_0^L w dx. When V reaches the
sample volume at t_ex, the source is empty. The front then creeps on by redistribution with speed
decaying as exp(-(t - t_ex)/tau). Because the decay only rescales time, the front follows the
fully-supplied trajectory in the pseudo-time s = tau (1 - exp(-(t - t_ex)/tau)): it reaches x iff
t_full(x) - t_ex < tau, at t = t_ex - tau ln(1 - (t_full(x) - t_ex)/tau). Otherwise it stalls.
"""
from dataclasses import dataclass, field

import numpy as np

from physics import params as P

DX = 1e-3  # mm


@dataclass
class Strip:
    K: float = field(default_factory=lambda: P.v("K_NOM"))            # mm^2/s, includes fluid factor
    perm: list = field(default_factory=list)                           # [(a_mm, b_mm, k_rel)]
    width: list = field(default_factory=list)                          # [(a_mm, b_mm, w_rel)]
    v_sample: float = float("inf")                                     # uL
    c_abs: float = field(default_factory=lambda: P.v("C_ABS"))         # uL/mm^2
    width_mm: float = field(default_factory=lambda: P.v("WIDTH"))
    creep_tau: float = field(default_factory=lambda: P.v("CREEP_TAU"))  # s


def _profile(x, segs):
    y = np.ones_like(x)
    for a, b, val in segs:
        y[(x >= a) & (x < b)] = val
    return y


def _cumtrapz(y, dx):
    return np.concatenate([[0.0], np.cumsum(0.5 * (y[1:] + y[:-1]) * dx)])


def trajectory(strip, lmax):
    """Grid x (mm), fully-supplied arrival time t(x) (s), wetted volume V(x) (uL)."""
    x = np.arange(0.0, lmax + 2 * DX, DX)
    k, w = _profile(x, strip.perm), _profile(x, strip.width)
    R = _cumtrapz(1.0 / (k * w), DX)
    t = (2.0 / strip.K) * _cumtrapz(w * R, DX)
    V = strip.c_abs * strip.width_mm * _cumtrapz(w, DX)
    return x, t, V


def arrival_times(positions, strip):
    """Arrival time (s) at each position; math.inf if the front never gets there."""
    x, t, V = trajectory(strip, max(positions))
    t_at = np.interp(positions, x, t)
    if not np.isfinite(strip.v_sample) or V[-1] <= strip.v_sample:
        return [float(v) for v in t_at]
    t_ex = float(np.interp(strip.v_sample, V, t))
    out = []
    for tf in t_at:
        if tf <= t_ex:
            out.append(float(tf))
        elif tf - t_ex < strip.creep_tau:
            out.append(float(t_ex - strip.creep_tau * np.log(1 - (tf - t_ex) / strip.creep_tau)))
        else:
            out.append(float("inf"))
    return out


def stall_position(strip, lmax=None):
    """Final front position (mm) for a finite sample, including creep."""
    lmax = lmax or 3 * P.v("L_MAX")
    x, t, V = trajectory(strip, lmax)
    if not np.isfinite(strip.v_sample) or V[-1] <= strip.v_sample:
        return float("inf")
    t_ex = float(np.interp(strip.v_sample, V, t))
    return float(np.interp(t_ex + strip.creep_tau, t, x))
