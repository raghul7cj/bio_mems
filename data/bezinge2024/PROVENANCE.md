# Bezinge et al. 2024: example data and analysis code

**Paper.** L. Bezinge, A. J. deMello, C.-J. Shih, D. A. Richards, "Quantitative reagent monitoring in paper-based electrochemical rapid diagnostic tests", *Lab Chip* 24(15), 3651–3657 (2024), doi:10.1039/D4LC00390J. The article is open access under CC BY-NC 3.0 (ETH Research Collection record, handle 20.500.11850/682802).

**Files (`raw/`, unmodified; see `SHA256SUMS.txt`).** Copied on 2026-10-28 from a folder the user supplied, "Quantitative reagent monitoring in electrochemical rapid diagnostic tests". The paper's data-availability statement places the design files and potentiostat code at Mendeley Data, doi:10.17632/nd9cyw62rk.1; the user confirmed these are those files. The folder contains no licence file, and the dataset licence was not checked (user decision). Use them non-commercially with attribution, consistent with the article's CC BY-NC 3.0 licence. Do not redistribute the raw data with the course submission; cite the paper and the dataset DOI instead.

| File | Content | Use here |
|---|---|---|
| `data_P3.csv` | `;`-separated. Index 0: pulsed-amperometry flow-monitoring current, one sample per 0.1 s. Indices 1–22: square-wave voltammograms | Real-trace test of event detection |
| `plotResults.m` | Authors' MATLAB analysis: flow tracking with a differential-current threshold state machine, plus SWV peak tracking | Flow-tracking part ported to `realdata/bezinge_flow.py` |
| `PulseMethod.txt`, `SWVMethod.txt` | PalmSens MethodSCRIPT. Pulse method: 100 mV pulses, 1 ms, every 100 ms, for 175.1 s | Sampling interval and record length |
| `plot_swv_bipot.py` | Potentiostat control script; needs the instrument | Reference only, not run |
| `electrofluidic_design_file.pdf` | Vertical-flow assay layers. One three-electrode cell: disk working electrode, ring counter, reference | Geometry: one sensing location, not a lateral multi-electrode strip |

**Scope limit.** This is a vertical-flow device with a single electrode cell. It validates the event-detection front end: when liquid arrives, and how long detection takes. It cannot calibrate the lateral Washburn model or test multi-point classification.
