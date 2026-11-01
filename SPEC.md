# Detector specification (v0.2, Phase 3)

Changes from v0.1, both driven by Phase 3 corpus results:
- **First-segment plausibility floor.** No plausible sample wicks more than 2× faster than nominal: water at 37 °C is 1.29×. A first segment faster than MIN_FIRST_Q/256 of E_0 is therefore a sensor fault, not a fluid. Under v0.1 a spurious early trigger on electrode 0 shrank r̂ and caused false STALLs.
- **Uniform-K test on the total fill time.** The test now uses t_{N−1} = ΣΔt against E_TOT = ΣE instead of Δt_0. The constant detection lag and the jitter are then a small fraction of the measured interval. Under v0.1, faster fluids hid inside the band.

This is the single source the golden models and the RTL are written from. Neither is translated from the other.

## Inputs and timebase
- N electrodes at distances L_0 < … < L_{N-1} from the inlet. The inlet is at L = 0.
- Tick = 1 ms. `arm` marks sample application (t = 0). The timestamp counter `now` (24 bit) counts ticks from arm.
- The arrival of electrode k is the tick t_k ≥ 1 at which its line is first seen high. A line already high at arm is *pre-high*.

## Constants (generated from `physics/params.py`, integer)
- E_k = round((L_k² − L_{k−1}²)/K_nom · 1000), with L_{−1} = 0. This is the expected segment time in ticks.
- E_TOT = ΣE_k, the expected total fill time.
- Tolerances are in units of 1/256: TOL (segment consistency), TOL_ABS (nominal band), TOL_STALL (stall margin), FIRST_Q (maximum first-segment time, as a multiple of E_0) and MIN_FIRST_Q (minimum first-segment time).

## Stage logic (stage idx = waiting for electrode idx; t_prev = t_{idx−1}, with t_{−1} = 0)
Segment times: Δt_k = t_k − t_{k−1}.

The **timeout predicate** at elapsed e = now − t_prev is:
- idx = 0: e·256 > E_0·FIRST_Q
- idx ≥ 1: e·E_0·256 > Δt_0·E_idx·(256 + TOL_STALL)

This is the adaptive window: the expected segment time is scaled by the measured first-segment ratio r̂ = Δt_0/E_0.

Rules, in priority order:
0. At arm, any pre-high line → **SENSOR**, loc = lowest pre-high index.
1. If the timeout predicate becomes true before any not-yet-captured electrode j ≥ idx arrives, the result is **STALL** with loc = idx. An arrival whose own elapsed time already satisfies the predicate is too late, so the timeout wins ties.
2. Otherwise let te be the earliest arrival tick among the electrodes j ≥ idx, and A the set of electrodes arriving at te. If A contains any j ≠ idx, the result is **SENSOR** with loc = (min of A∖{idx}) if idx ∈ A, else idx.
3. Otherwise capture Δt_idx = te − t_prev. If idx = 0 and Δt_0·256 < E_0·MIN_FIRST_Q, the result is **SENSOR** with loc = 0 (implausibly fast first segment). Otherwise move to the next stage. After the last electrode, classify.

## Classification (all comparisons are exact integer arithmetic; no division and no rounding)
For k = 1 … N−1, in order, the first k satisfying either test gives the result:
- Δt_k·E_0·256 > Δt_0·E_k·(256 + TOL) → **RESTRICTION**, loc = k (extra resistance first appears in segment k)
- Δt_k·E_0·256 < Δt_0·E_k·(256 − TOL) → **ANOMALY**, loc = k (a downstream segment is faster than the physics predicts)

If no k triggers, all segments are consistent with one K. Test it on the total fill time T = t_{N−1}:
- T·256 > E_TOT·(256 + TOL_ABS) → **UNIFORM_SLOW**
- T·256 < E_TOT·(256 − TOL_ABS) → **UNIFORM_FAST**
- otherwise → **NOMINAL**

For these three classes loc = 0.

## Hardware realisation (rtl/, Phase 4)
- **Arrival tick.** t_k is the value of `now` in the clock where electrode k's synchronized line starts a high run that lasts DEB clocks (the glitch filter). Filtering adds latency, never timestamp error.
- **Order-independence.** The sequencer acts only on captured timestamps. It treats an arrival as final when no filter is pending and `now` > t; it treats a timeout as final when the window predicate holds at a sampled `now`, because the predicate is monotonic. So the outcome is the SPEC function of the ticks and does not depend on the clock-to-tick ratio or the multiplier latency. The regression exploits this: it runs one tick per clock.
- **Arithmetic.** One shared 24 × 36-bit multiplier computes (measured time) × (ROM constant). params_pkg folds every constant × constant product. There is no divider.

## Class codes (3 bit)
NOMINAL 0 · UNIFORM_SLOW 1 · UNIFORM_FAST 2 · RESTRICTION 3 · STALL 4 · SENSOR 5 · ANOMALY 6

## Identifiability notes
- UNIFORM_* cannot say which fluid property changed.
- A restriction in segment 0 (upstream of electrode 0) adds a constant resistance R0, so t ∝ L² + 2·R0·L. Its segment ratios *decrease* downstream (Phase 2 generator: ρ = 2.2, 1.8, 1.6, 1.5 for k/6 over 4 mm), and it is flagged as ANOMALY. Only a weak upstream restriction (2·R0·L ≪ L², i.e. deviation within TOL) is indistinguishable from UNIFORM_SLOW. This refines the handoff's limitation; Phase 3 quantifies the boundary.
