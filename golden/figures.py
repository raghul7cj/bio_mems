"""Phase 3 figures. Colours: reference palette (dataviz skill), categorical slots 1-4 in fixed order,
one-hue blue ramp for magnitude. Text stays in ink tokens, never in series colours."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from golden.evaluate import CLS, METHODS, TRUTH_GROUPS  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
MARKERS = ["o", "s", "^", "D"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
BLUES = LinearSegmentedColormap.from_list("blue", ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])

plt.rcParams.update({"axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.facecolor": SURF, "figure.facecolor": SURF, "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False})


def confusion(conf, path):
    rowsum = conf.sum(axis=1, keepdims=True)
    frac = np.divide(conf, rowsum, out=np.zeros_like(conf, dtype=float), where=rowsum > 0)
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.imshow(frac, cmap=BLUES, vmin=0, vmax=1, aspect="auto")
    for i in range(conf.shape[0]):
        for j in range(conf.shape[1]):
            if conf[i, j]:
                ax.text(j, i, f"{frac[i, j]:.0%}\n({conf[i, j]})", ha="center", va="center", fontsize=7,
                        color="#fcfcfb" if frac[i, j] > 0.55 else INK)
    ax.set_xticks(range(len(CLS)), [c.replace("_", "\n") for c in CLS], fontsize=7.5)
    ax.set_yticks(range(len(TRUTH_GROUPS)), [g.replace("_", " ").lower() for g in TRUTH_GROUPS], fontsize=8)
    ax.set_xlabel("predicted class (model-based detector)"); ax.set_ylabel("true cause")
    ax.set_title("Confusion matrix, held-out test split (row-normalised; counts in brackets)", fontsize=9, color=INK)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=170); plt.close(fig)


def vs_noise(m, jitters, cvs, path):
    fig, ax = plt.subplots(1, 3, figsize=(11, 3.6))
    panels = [("det_jitter", jitters, "jitter σ (s)", "detection rate (all faults)"),
              ("far_jitter", jitters, "jitter σ (s)", "false-alarm rate (nominal strips)"),
              ("det_cv", cvs, "strip-to-strip CV of K", "detection rate (all faults)")]
    for a, (key, xs, xl, yl) in zip(ax, panels):
        for i, meth in enumerate(METHODS):
            ys = [m[meth][f"{key}_{x}"] for x in xs]
            a.plot(xs, ys, marker=MARKERS[i], color=SERIES[i], lw=2, ms=8, mec=SURF, mew=1.5, label=meth)
        a.set_xlabel(xl); a.set_ylabel(yl); a.grid(color=GRID, lw=0.8); a.set_axisbelow(True)
        a.set_ylim(0, 1.02 if key.startswith("det") else max(0.15, a.get_ylim()[1]))
    ax[1].axhline(0.05, color=INK2, lw=1, ls=":"); ax[1].text(jitters[0], 0.056, "5 % tuning target", color=INK2, fontsize=7.5)
    ax[0].legend(frameon=False, fontsize=7.5, loc="lower left")
    fig.suptitle("Fault detection vs measurement noise (test split; every method tuned to ≤5 % FAR on calibration seeds)",
                 fontsize=9, color=INK)
    fig.tight_layout(); fig.savefig(path, dpi=170); plt.close(fig)


def by_group(m, path):
    groups = [g for g in TRUTH_GROUPS if g != "NOMINAL"]
    x = np.arange(len(groups)); w = 0.2
    fig, ax = plt.subplots(figsize=(9, 3.4))
    for i, meth in enumerate(METHODS):
        ax.bar(x + (i - 1.5) * w, [m[meth]["det_by_group"].get(g, 0) for g in groups], w - 0.02,
               color=SERIES[i], label=meth, edgecolor=SURF, linewidth=1)
    ax.set_xticks(x, [g.replace("_", " ").lower() for g in groups], fontsize=8)
    ax.set_ylabel("detection rate"); ax.set_ylim(0, 1.05); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=7.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.15))
    fig.tight_layout(); fig.savefig(path, dpi=170); plt.close(fig)
