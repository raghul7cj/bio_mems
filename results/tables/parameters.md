| Parameter | Value | Unit | Provenance |
|---|---|---|---|
| K_NOM | 9.42 | mm^2/s | repo: physics/calibrate.py Washburn fit to KAS20 Fig. 7a (digitised); cross-checks KAS20 Table 6 p^2 = 9.73, FF170HP rating 40^2/170 = 9.41; gravity-corrected fit +9 % (systematic) |
| K_CV | 0.032 | - | repo: CV of K = p^2 over the 2/4/6 mm strips, KAS20 Table 6 |
| K_CV_HIGH | 0.1 | - | PAT20: max deviation < 10 % across five runs (Whatman 4), used as upper bound |
| P_C | 2345.0 | Pa | KAS20 Table 8 (nitrocellulose, model-derived estimate) |
| C_ABS | 0.101 | uL/mm^2 | KAS20 Sec. 4.3: 10.1 uL/cm^2, direct weighing, non-laminated NC |
| EXPONENT | 0.546 | - | repo: power-law fit L ~ t^n to KAS20 Fig. 7a (t >= 1 s); MIR26 reports 0.39-0.46 for radial imbibition in filter paper over 60 min |
| GAMMA | 0.072 | N/m | PAT20 Table (water) |
| MU | 0.00089 | Pa s | PAT20 / MIR26 (water); KAS20 uses 8.94e-4 |
| RHO | 1000.0 | kg/m^3 | KAS20 Table 2 |
| THETA | 0.0 | deg | assumed: fully wetting (PAT20 makes the same assumption); enters only via K |
| L_MAX | 40.0 | mm | assumed: equals the 4 cm FF170HP rating length and the KAS20 strip |
| WIDTH | 4.0 | mm | assumed: middle KAS20 width (wicking speed independent of width, KAS20 Sec. 4.4) |
| N_ELEC | 4 | - | assumed: handoff default; electrodes spaced uniformly in L^2 |
| V_SAMPLE | 25.0 | uL | assumed: typical RDT sample volume; strip needs C_ABS*WIDTH*L_MAX = 16.2 uL |
| CREEP_TAU | 20.0 | s | assumed: decay time of front creep after the source empties (KAS20 Fig. 2 shows the front keeps moving after reservoir removal; magnitude not reported) |
| TICK_S | 0.001 | s | design choice: fill takes ~10^2 s, so 1 ms is ample |
| LAG_S | 1.8 | s | BEZ24 SI Fig. S4 (as reported in the handoff, not yet verified): mean offset of electrode flow times vs reference; used as a constant detection lag |
| JITTER_S | (0.0, 0.1, 0.5, 1.0, 2.0) | s | assumed: sweep of arrival-detection jitter (1 sigma) |
| MU_PLASMA | 0.0013 | Pa s | assumed: typical plasma/serum viscosity 1.1-1.3 mPa s (textbook value, verify) |
| MU_BLOOD | 0.0035 | Pa s | assumed: whole blood at high shear 3-4 mPa s (textbook value, verify) |
| MU_WATER37 | 0.00069 | Pa s | assumed: water at 37 C (standard tables) |

**References**

- KAS20: S. Kasetsirikul, M. J. A. Shiddiky, N.-T. Nguyen, Chemosensors 8(3), 65 (2020), doi:10.3390/chemosensors8030065 (CC BY)
- PAT20: S. Patari, P. Sinha Mahapatra, ACS Omega 5(36), 22931-22939 (2020), doi:10.1021/acsomega.0c02407
- MIR26: J. J. Miranda-Blancas et al., Fluids 11(5), 127 (2026), doi:10.3390/fluids11050127
- BEZ24: L. Bezinge et al., Lab Chip 24(15), 3651-3657 (2024), doi:10.1039/D4LC00390J
- MEN10: S. Mendez et al., Langmuir 26(2), 1380-1385 (2010) (quasi-stationary flow in segments; not yet read)
