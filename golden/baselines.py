"""Baselines, evaluated on exactly the same corpus as the model-based detector.

All of them use only arrival ticks (-1 never, -2 high before arm) and return (fault, decision_tick).

1. Fixed timeout: 'did liquid reach the end electrode before T?' (what a timed RDT read-out checks).
2. Single-sensor threshold: the end electrode's arrival must fall inside [T_lo, T_hi]. This is the
   single-flow-time check (Bezinge et al. 2024 flag wrong volume or viscosity from one flow time).
3. Fixed-K ablation (no online K): every segment ratio rho_k = dt_k / E_k must lie in [1-tol, 1+tol].
   This is the same electrodes as the model-based detector, but with absolute windows only.
"""
import numpy as np


def end_tick(ticks):
    t = ticks[-1]
    return 0 if t == -2 else (None if t == -1 else t)


def timeout(ticks, T):
    t = end_tick(ticks)
    if t is None or t > T:
        return True, T
    return False, t


def single_sensor(ticks, lo, hi):
    t = end_tick(ticks)
    if t is None or t > hi:
        return True, hi
    return t < lo, t


def fixed_k(ticks, E, tol):
    """Fault if any electrode is missing / out of order or any rho_k is outside 1 +/- tol."""
    if any(t < 1 for t in ticks):
        return True, None
    prev, t_last = 0, 0
    for k, t in enumerate(ticks):
        if t <= prev:
            return True, t
        rho = (t - prev) / E[k]
        if abs(rho - 1) > tol:
            return True, t
        prev = t_last = t
    return False, t_last


def tune_quantile(values, far):
    """Upper threshold that lets (1 - far) of the nominal calibration values through."""
    return float(np.quantile(values, 1 - far))
