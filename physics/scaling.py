"""Dimensionless scaling analysis with sourced parameters (physics/params.py).

The pore radius of the nitrocellulose membrane is not reported in the sources, so the analysis is
bracketed by two *effective* radii computed from measured quantities:
  r_W = 2 mu K / (gamma cos(theta))   the radius an ideal capillary would need to give the fitted K
  r_P = 2 gamma cos(theta) / P_c      the radius implied by the capillary-pressure estimate
Their wide disagreement (~0.2 um vs ~60 um) is itself the reason K must be fitted, not computed
from a cylindrical-capillary model (paper is a tortuous, partially saturated fibre network).
The conclusions below hold at both extremes.
"""
import math

from physics import params as P


def table():
    g, mu, rho, K, pc = P.v("GAMMA"), P.v("MU"), P.v("RHO"), P.v("K_NOM") * 1e-6, P.v("P_C")
    cth = math.cos(math.radians(P.v("THETA")))
    r_w = 2 * mu * K / (g * cth)
    r_p = 2 * g * cth / pc
    L_fast, L_slow = 2e-3, P.v("L_MAX") * 1e-3          # front speed U = K/(2L): fastest near inlet
    U_fast, U_slow = K / (2 * L_fast), K / (2 * L_slow)
    h_eq = pc / (rho * 9.81)
    rows = []

    def add(name, expr, lo, hi, meaning, verdict):
        rows.append((name, expr, lo, hi, meaning, verdict))

    add("Bond (pore)", "rho g r^2 / gamma", rho * 9.81 * r_w ** 2 / g, rho * 9.81 * r_p ** 2 / g,
        "gravity vs capillarity at pore scale", "<< 1: meniscus shape set by capillarity")
    add("Capillary", "mu U / gamma", mu * U_slow / g, mu * U_fast / g,
        "viscous vs surface forces at the meniscus", "<< 1: quasi-static capillary pressure")
    add("Reynolds (pore)", "rho U r / mu", rho * U_slow * r_w / mu, rho * U_fast * r_p / mu,
        "inertia vs viscosity in a pore", "<< 1: Stokes/Darcy flow")
    add("Inertial time (Bosanquet)", "rho r^2 / (8 mu)  [s]", rho * r_w ** 2 / (8 * mu), rho * r_p ** 2 / (8 * mu),
        "duration of the inertial regime", "<< 1 ms tick: inertia invisible to the detector")
    add("Strip-scale gravity", "L / h_eq,  h_eq = P_c/(rho g)", L_fast / h_eq, L_slow / h_eq,
        "hydrostatic head vs capillary pressure (vertical strip only)",
        "irrelevant for a horizontal strip; up to 17 % slowdown if the strip were vertical")
    meta = {"r_W_um": r_w * 1e6, "r_P_um": r_p * 1e6, "U_mm_s": (U_slow * 1e3, U_fast * 1e3), "h_eq_mm": h_eq * 1e3}
    return rows, meta


def write(path):
    rows, meta = table()
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Effective pore radius bracket: r_W = {meta['r_W_um']:.2f} um, r_P = {meta['r_P_um']:.1f} um. "
                f"Front speed U = {meta['U_mm_s'][0]:.2f}-{meta['U_mm_s'][1]:.2f} mm/s (L = 40 mm to 2 mm). "
                f"h_eq = {meta['h_eq_mm']:.0f} mm.\n\n")
        f.write("| Number | Definition | Low | High | Compares | Conclusion |\n|---|---|---|---|---|---|\n")
        for name, expr, lo, hi, meaning, verdict in rows:
            f.write(f"| {name} | {expr} | {lo:.2e} | {hi:.2e} | {meaning} | {verdict} |\n")
    return rows, meta
