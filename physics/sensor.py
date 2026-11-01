"""Electrode sensing model: physical arrival time (s) -> digital arrival tick seen by the detector.

Effects (all optional): constant detection lag, Gaussian jitter, and electrode faults:
  'missed'    the electrode never reports (tick -1)
  'spurious'  it reports at a random time before the front arrives (e.g. condensation, crosstalk)
  'stuck'     its line is already high when the test is armed (tick -2)
"""
import math

from physics import params as P

NEVER, PRE_HIGH = -1, -2


def to_ticks(times_s, rng=None, lag_s=0.0, jitter_s=0.0, faults=None):
    """faults: {electrode_index: 'missed' | 'spurious' | 'stuck'}"""
    faults = faults or {}
    tick = P.v("TICK_S")
    out = []
    for k, t in enumerate(times_s):
        f = faults.get(k)
        if f == "stuck":
            out.append(PRE_HIGH); continue
        if f == "missed" or not math.isfinite(t):
            out.append(NEVER); continue
        if f == "spurious":
            t = rng.uniform(0.05, 0.6) * t
        else:
            t = t + lag_s + (rng.normal(0.0, jitter_s) if (jitter_s > 0 and rng is not None) else 0.0)
        out.append(max(1, math.ceil(t / tick)))  # first tick at which the line is seen high
    return out
