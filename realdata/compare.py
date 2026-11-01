"""Phase 6: reproduce Bezinge et al. 2024 flow times from data_P3.csv and compare with the paper.

Paper values are quoted from the article text (ETH Research Collection full text, CC BY-NC 3.0):
  Fig. 3d medians (IQR), clinical runs: serum 100 uL 30 s (29-39), labelling 100 uL 22 s (17-32),
  rinsing 150 uL 31 s (28-41). Flow-time agreement with visual absorption: method +1.8 s on
  average, IQR -0.1 to 2.5 s (Fig. S4). Stop confirmation: "a ten second time delay".
Flow time here = (stop declared) - (flow detected) - 10 s confirmation delay.
The mapping of injections 1-3 to serum / labelling / rinsing follows the assay order described in
the paper (sample, labelling, rinse, then substrate, after which the reader switches to SWV);
it is inferred, not stated in the data file.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from realdata import bezinge_flow as bf  # noqa: E402

STOP_DELAY_S = 10.0  # 100 samples x 0.1 s, plotResults.m / paper text
PAPER = [  # (step, median s, IQR low, IQR high)
    ("serum sample, 100 uL", 30, 29, 39),
    ("labelling solution, 100 uL", 22, 17, 32),
    ("rinsing buffer, 150 uL", 31, 28, 41),
    ("substrate (reader switches to SWV)", None, None, None),
]
BIAS_S, IQR_LO, IQR_HI = 1.8, -0.1, 2.5  # method minus visual flow time


def analyse(path):
    i, t, nswv = bf.load(path)
    r = bf.track_flow(i)
    ev = bf.flow_events(r["status"])
    rows = []
    for (k, ts, te), (name, med, lo, hi) in zip(ev, PAPER):
        ft = None if te is None else te - ts - STOP_DELAY_S
        rows.append({"k": k, "step": name, "t_inj": float(bf.TINJ[k - 1]), "t_detect": ts, "t_stop": te,
                     "flow_time": ft, "paper_median": med, "paper_iqr": (lo, hi),
                     "in_iqr": None if ft is None or lo is None else lo <= ft <= hi})
    # timing noise implied by the paper's agreement statistics (normal approximation)
    sigma_flow = (IQR_HI - IQR_LO) / 1.349
    noise = {"bias_s": BIAS_S, "sigma_flowtime_s": sigma_flow, "sigma_event_s": sigma_flow / np.sqrt(2)}
    return {"i": i, "t": t, "nswv": nswv, "track": r, "events": ev, "rows": rows, "noise": noise}


def table(res):
    lines = ["| Injection | Step (inferred) | Injected at (s) | Flow detected (s) | Stop declared (s) | "
             "Flow time, reproduced (s) | Paper median (IQR) (s) | In IQR |",
             "|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        ft = "n/a (no stop)" if r["flow_time"] is None else f"{r['flow_time']:.1f}"
        pap = "n/a" if r["paper_median"] is None else f"{r['paper_median']} ({r['paper_iqr'][0]}-{r['paper_iqr'][1]})"
        st = "-" if r["t_stop"] is None else f"{r['t_stop']:.1f}"
        iq = "-" if r["in_iqr"] is None else ("yes" if r["in_iqr"] else "no")
        lines.append(f"| {r['k']} | {r['step']} | {r['t_inj']:.0f} | {r['t_detect']:.1f} | {st} | {ft} | {pap} | {iq} |")
    n = res["noise"]
    lines += ["", f"Timing noise implied by the paper (method vs visual flow time): bias +{n['bias_s']} s, "
              f"sigma ~ {n['sigma_flowtime_s']:.1f} s per flow time, ~ {n['sigma_event_s']:.1f} s per detected event "
              f"(IQR/1.349, events independent)."]
    return "\n".join(lines)


def figure(res, path):
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    BLUE, ORANGE = "#2a78d6", "#eb6834"
    t, i, r = res["t"], res["i"], res["track"]
    fig, ax = plt.subplots(3, 1, figsize=(8.5, 6.2), sharex=True, facecolor=SURF)
    for a in ax:
        a.set_facecolor(SURF); a.grid(color=GRID, lw=0.8); a.set_axisbelow(True)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        for ti in bf.TINJ:
            a.axvline(ti, color=INK2, ls=":", lw=1)
    ax[0].plot(t, i, ".", ms=2, color=INK)
    ax[0].set_ylabel("pulse current (uA)")
    ax[0].set_title("Bezinge et al. 2024, data_P3: flow tracking reproduced in Python (dotted: injections)",
                    fontsize=9, color=INK)
    ax[1].plot(t, r["di"], color=BLUE, lw=1.2, label="|Δi| (1 s difference, 1 s mean)")
    ax[1].plot(t, r["threshold"], color=ORANGE, lw=1.2, ls="--", label="threshold")
    ax[1].set_yscale("log"); ax[1].set_ylim(0.05, 1000); ax[1].set_ylabel("|Δi| (uA)")
    ax[1].legend(frameon=False, fontsize=7.5, loc="upper right")
    ax[2].step(t, r["status"], where="post", color=BLUE, lw=1.5)
    for row in res["rows"]:
        if row["flow_time"] is not None:
            ax[2].annotate(f"{row['flow_time']:.1f} s", (row["t_detect"], 0.15), fontsize=7.5, color=INK)
    ax[2].set_ylabel("status (0 = flowing)"); ax[2].set_xlabel("time (s)")
    fig.tight_layout(); fig.savefig(path, dpi=170); plt.close(fig)
