"""Phase 2 illustration: what each fault class does to the arrival pattern (generator model, no noise)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from physics import params as P  # noqa: E402
from physics.darcy_series import Strip, arrival_times  # noqa: E402


def fault_cases():
    pos = P.electrode_positions()
    mid2 = 0.5 * (pos[1] + pos[2])
    return pos, [
        ("Nominal (water)", Strip(), "#333333", "o"),
        ("Fluid change: plasma viscosity", Strip(K=P.v("K_NOM") * P.fluid_k_factor(mu=P.v("MU_PLASMA"))), "#2a6fb0", "s"),
        ("Fluid change: whole-blood viscosity", Strip(K=P.v("K_NOM") * P.fluid_k_factor(mu=P.v("MU_BLOOD"))), "#6c8ebf", "D"),
        ("Restriction in segment 2 (k/6 over 4 mm)", Strip(perm=[(mid2 - 2, mid2 + 2, 1 / 6)]), "#c0392b", "^"),
        ("Restriction upstream of electrode 0", Strip(perm=[(6, 10, 1 / 6)]), "#e67e22", "v"),
        ("Insufficient sample (10 uL)", Strip(v_sample=10.0), "#27ae60", "x"),
    ]


def arrival_patterns(path):
    pos, cases = fault_cases()
    L2 = np.array(pos) ** 2
    E = np.diff(np.concatenate([[0.0], L2])) / P.v("K_NOM")
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.9))
    tt = np.linspace(0, 700, 200)
    ax[0].plot(tt, P.v("K_NOM") * tt, ":", color="#999999", lw=1, label="Washburn, nominal K")
    for name, strip, c, m in cases:
        t = np.array(arrival_times(pos, strip))
        ok = np.isfinite(t)
        t = np.where(ok, t, np.nan)
        ax[0].plot(t[ok], L2[ok], marker=m, color=c, lw=1, ms=5, label=name)
        dt = np.diff(np.concatenate([[0.0], t]))
        ax[1].plot(np.arange(len(pos))[ok], (dt / E)[ok], marker=m, color=c, lw=1, ms=5)
    ax[0].set_xlabel("arrival time t_k (s)"); ax[0].set_ylabel("L_k² (mm²)")
    ax[0].set_xlim(0, 700); ax[0].legend(fontsize=6.8, frameon=False, loc="lower right")
    ax[0].set_title("Arrivals at 4 electrodes (missing marker = never arrives)", fontsize=9)
    ax[1].axhline(1, color="#999999", lw=0.8)
    ax[1].set_xticks(range(len(pos))); ax[1].set_xlabel("segment k (ends at electrode k)")
    ax[1].set_ylabel("segment ratio ρ_k = Δt_k / E_k"); ax[1].set_yscale("log")
    ax[1].set_title("Detector's view: flat = uniform K change, step = local restriction", fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)
