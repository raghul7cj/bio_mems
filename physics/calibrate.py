"""Calibrate the effective Washburn coefficient K of nitrocellulose FF170HP from published wicking data.

Data: Kasetsirikul et al. 2020, Fig. 7(a), digitised (data/literature/kasetsirikul2020/).
The experiment is a VERTICAL capillary rise, while the detector strip is horizontal. Darcy flow with
gravity gives

    dh/dt = (K/2) (1 - h/h_eq) / h,   h_eq = P_c / (rho g)

so the horizontal Washburn law (L^2 = K t) is recovered when h << h_eq. Integrating:

    t(h) = (2 h_eq^2 / K) [ -x - ln(1 - x) ],   x = h / h_eq

We fit K three ways:
  (1) plain Washburn L = sqrt(K t) through the origin (what the paper reports as p^2);
  (2) gravity-corrected, with h_eq from the paper's own capillary-pressure estimate (2345 Pa);
  (3) gravity-corrected with h_eq free (to see whether the data constrain it).
Fit (2) is the horizontal K used by the detector; (1) and the manufacturer rating are cross-checks.
"""
import os

import numpy as np
from scipy.optimize import brentq, least_squares

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "literature", "kasetsirikul2020", "fig7a_nc_ff170hp.csv")
RHO, G = 1000.0, 9.81          # kg/m^3 (paper Table 2), m/s^2
PC_PAPER = 2345.0              # Pa, Kasetsirikul 2020 Table 8 (nitrocellulose, model estimate)
P_PUBLISHED = 3.12             # mm s^-1/2, Kasetsirikul 2020 Table 6 (mean over widths)
P_WIDTHS = (3.08, 3.18, 3.12)  # same table, 2/4/6 mm strips
MANUF_S_PER_4CM = 170.0        # FF170HP product rating: 170 s per 4 cm (Kasetsirikul 2020 Appendix A)


def load():
    with open(DATA) as f:
        rows = [ln for ln in f if ln.strip() and not ln.startswith("#")][1:]  # drop header
    d = np.loadtxt(rows, delimiter=",")
    s, L = d[:, 0], d[:, 1]
    return s ** 2, L


def t_vertical(h, K, h_eq):
    x = np.asarray(h) / h_eq
    return (2 * h_eq ** 2 / K) * (-x - np.log1p(-x))


def h_vertical(t, K, h_eq):
    return np.array([brentq(lambda h: t_vertical(h, K, h_eq) - ti, 0.0, h_eq * (1 - 1e-12)) if ti > 0 else 0.0
                     for ti in np.atleast_1d(t)])


def fit():
    t, L = load()
    out = {"n_points": int(len(t)), "t_max_s": float(t.max()), "L_max_mm": float(L.max())}

    # (1) plain Washburn through origin: L = p sqrt(t), least squares in L
    s = np.sqrt(t)
    p = float(np.sum(L * s) / np.sum(s * s))
    out["K_plain"] = p ** 2
    out["rms_plain_mm"] = float(np.sqrt(np.mean((L - p * s) ** 2)))

    # (2) gravity-corrected, h_eq fixed from the paper's capillary pressure
    h_eq = PC_PAPER / (RHO * G) * 1e3  # mm
    r = least_squares(lambda k: h_vertical(t, k[0], h_eq) - L, x0=[p ** 2], bounds=([0.1], [100]))
    J = r.jac
    sigma2 = np.sum(r.fun ** 2) / (len(t) - 1)
    out["h_eq_mm"] = h_eq
    out["K_grav"] = float(r.x[0])
    out["K_grav_se"] = float(np.sqrt(sigma2 * np.linalg.inv(J.T @ J)[0, 0]))
    out["rms_grav_mm"] = float(np.sqrt(np.mean(r.fun ** 2)))

    # (3) both free
    r3 = least_squares(lambda q: h_vertical(t, q[0], q[1]) - L, x0=[p ** 2, h_eq], bounds=([0.1, 45], [100, 1e5]))
    out["K_free"], out["h_eq_free_mm"] = float(r3.x[0]), float(r3.x[1])
    out["rms_free_mm"] = float(np.sqrt(np.mean(r3.fun ** 2)))

    # power-law exponent L = c t^n (Washburn: n = 0.5), fitted for t >= 1 s
    m = t >= 1.0
    n, _ = np.polyfit(np.log(t[m]), np.log(L[m]), 1)
    out["exponent_n"] = float(n)

    # cross-checks
    out["K_published_p2"] = P_PUBLISHED ** 2
    Kw = np.array(P_WIDTHS) ** 2
    out["K_width_cv"] = float(Kw.std(ddof=1) / Kw.mean())
    out["K_manufacturer"] = 40.0 ** 2 / MANUF_S_PER_4CM
    return out


def plot(res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t, L = load()
    tt = np.linspace(0, t.max() * 1.05, 300)
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.8))
    ax[0].plot(t, L ** 2, "o", ms=4, mfc="none", color="#333333", label="Kasetsirikul 2020, Fig. 7a (digitised)")
    ax[0].plot(tt, res["K_plain"] * tt, "-", color="#2a6fb0", label=f"Washburn fit, K = {res['K_plain']:.2f} mm²/s")
    ax[0].plot(tt, h_vertical(tt, res["K_grav"], res["h_eq_mm"]) ** 2, "--", color="#c0392b",
               label=f"gravity-corrected, K = {res['K_grav']:.2f} mm²/s")
    ax[0].set_xlabel("t (s)"); ax[0].set_ylabel("L² (mm²)"); ax[0].legend(fontsize=7.5, frameon=False)
    ax[0].set_title("Nitrocellulose FF170HP, water", fontsize=9)

    ax[1].axhline(0, color="#999999", lw=0.8)
    ax[1].plot(t, L - np.sqrt(res["K_plain"] * t), "o", ms=4, mfc="none", color="#2a6fb0", label="Washburn")
    ax[1].plot(t, L - h_vertical(t, res["K_grav"], res["h_eq_mm"]), "s", ms=3.5, mfc="none", color="#c0392b",
               label="gravity-corrected")
    ax[1].axhspan(-0.5, 0.5, color="#dddddd", alpha=0.5, lw=0, label="±0.5 mm reading uncertainty")
    ax[1].set_xlabel("t (s)"); ax[1].set_ylabel("residual L (mm)"); ax[1].legend(fontsize=7.5, frameon=False)
    ax[1].set_title("Fit residuals", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
