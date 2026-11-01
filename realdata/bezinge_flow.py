"""Python port of the flow-tracking part of Bezinge et al. 2024, plotResults.m.

Kept line-for-line with the MATLAB, including its quirks, so the reproduction is of the authors'
algorithm and not an improved one:
  * di(n) = |mean_{k=n-9..n} (i(k) - i(k-10))|, a 1 s difference averaged over 1 s, so a sample
    near the start whose window reaches back past sample 10 is NaN, and NaN compares false;
  * waiting for flow: 10 consecutive samples with di > threshold -> flow (status 0), and the next
    threshold in the list is selected;
  * flowing: 100 consecutive samples with di < threshold -> stopped, status = next injection
    number; count_stop is NOT reset after a stop (MATLAB behaviour, kept);
  * the threshold in force while flowing is already the NEXT entry of threshold_v.
The SWV peak analysis (needs the third-party `backcor` and `findpeaks`) is serology, out of scope.
"""
import math

import numpy as np

DT = 0.1                                   # s, plotResults.m (PulseMethod: one pulse per 100 ms)
TINJ = np.cumsum([10, 45, 45, 60])         # s, injection times in plotResults.m
THRESHOLD_V = [1.5, 1.5, 1.5, 0.4, 0.4, 0.4]  # uA, plotResults.m


def load(path):
    """Flow-monitoring current (uA) and time base (s) from data_P3.csv (index-0 rows, column 4)."""
    idx, cur = [], []
    with open(path) as f:
        next(f)
        for line in f:
            a = line.strip().split(";")
            if len(a) >= 4:
                idx.append(int(a[0]))
                cur.append(float(a[3]))
    idx, cur = np.array(idx), np.array(cur)
    i_flow = cur[idx == 0] * 1e6
    return i_flow, np.arange(len(i_flow)) * DT, int(idx.max())


def track_flow(i_flow, threshold_v=THRESHOLD_V):
    """Literal translation of the %% Flow tracking loop (0-based arrays, m = 1-based index)."""
    Nt = len(i_flow)
    di_raw = np.full(Nt, np.nan)
    di = np.full(Nt, np.nan)
    TH = np.full(Nt, np.nan)
    status = np.zeros(Nt, dtype=int)
    count_flow = count_stop = 0
    count_inj = 1
    idx_threshold = 1                                  # 1-based, as in MATLAB
    for n in range(Nt):
        m = n + 1
        TH[n] = threshold_v[idx_threshold - 1]
        if m > 10:
            di_raw[n] = i_flow[n] - i_flow[n - 10]
            w = di_raw[n - 9:n + 1]
            di[n] = abs(w.mean()) if not np.isnan(w).any() else math.nan
        if m == 1 or status[n - 1] > 0:                # waiting for flow
            count_flow = count_flow + 1 if di[n] > TH[n] else 0
            if count_flow >= 10:
                status[n] = 0
                count_flow = 0
                idx_threshold += 1
            else:
                status[n] = count_inj
        else:                                          # ongoing flow
            status[n] = status[n - 1]
            count_stop = count_stop + 1 if di[n] < TH[n] else 0
            if count_stop >= 100:
                count_inj += 1
                status[n] = count_inj
    return {"di": di, "threshold": TH, "status": status}


def flow_events(status, dt=DT):
    """[(injection k, t_flow_detected, t_flow_stopped or None)] from the status trace."""
    ev = []
    for n in range(1, len(status)):
        if status[n - 1] > 0 and status[n] == 0:
            ev.append([int(status[n - 1]), n * dt, None])
        elif status[n - 1] == 0 and status[n] > 0 and ev:
            ev[-1][2] = n * dt
    return [tuple(e) for e in ev]


def self_test():
    """Analytic check: a step of height h >> threshold at sample s makes di a triangle that is
    above threshold on samples s..s+18, so flow is confirmed at s+9 (10th consecutive sample)
    and declared stopped at s+118 (100th consecutive sample below threshold, from s+19)."""
    s, h = 200, 100.0
    i = np.zeros(600)
    i[s:] = h
    st = track_flow(i)["status"]
    ev = flow_events(st, 1.0)
    return ev == [(1, float(s + 9), float(s + 118))], ev
