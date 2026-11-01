"""Single entry point.  py -3.12 run.py phase1"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from golden import golden_fixed, golden_float  # noqa: E402
from physics import params  # noqa: E402
from scenarios import tracer  # noqa: E402
from tools import xsim  # noqa: E402

CLS_NAME = ["NOMINAL", "UNIFORM_SLOW", "UNIFORM_FAST", "RESTRICTION", "STALL", "SENSOR", "ANOMALY"]


def read_rows(path):
    with open(path) as f:
        return {int(p[0]): tuple(map(int, p[1:])) for p in (line.split() for line in f) if p}


def phase1():
    b = os.path.join(ROOT, "build", "phase1")
    os.makedirs(b, exist_ok=True)
    pkg, stim, truth, out = (os.path.join(b, n) for n in ("params_pkg.sv", "stim.txt", "truth.txt", "rtl_out.txt"))
    cfg = params.detector_config()
    params.write_sv_package(pkg, cfg)
    rows = tracer.write(stim, truth)
    print(f"E (ticks) = {cfg['E']}")

    gold = {sid: golden_fixed.classify(cfg, ticks) for sid, ticks in rows}
    flt = {sid: golden_float.classify(cfg, ticks) for sid, ticks in rows}
    rtl, gt = xsim.run_corpus(rows, b, pkg, shards=1), read_rows(truth)

    ok = True
    print(f"{'id':>3} {'ticks':<32} {'truth':<16} {'golden_fixed':<16} {'golden_float':<16} {'rtl':<16}")
    for sid, ticks in rows:
        name = lambda c: f"{CLS_NAME[c[0]]}/{c[1]}"
        match = rtl.get(sid) == gold[sid]
        ok &= match
        print(f"{sid:>3} {str(ticks):<32} {name(gt[sid]):<16} {name(gold[sid]):<16} {name(flt[sid]):<16} "
              f"{name(rtl[sid]) if sid in rtl else 'MISSING':<16} {'ok' if match else 'MISMATCH'}")
    correct = sum(gold[s] == gt[s] for s in gt)
    print(f"golden vs truth: {correct}/{len(gt)} correct")
    print("PHASE1 PASS: RTL bit-exact with golden_fixed" if ok else "PHASE1 FAIL")
    return ok


def phase2():
    import math

    from physics import calibrate, figures, scaling
    from physics.darcy_series import Strip, arrival_times, stall_position

    fig_dir, tab_dir = (os.path.join(ROOT, "results", d) for d in ("figures", "tables"))
    os.makedirs(fig_dir, exist_ok=True); os.makedirs(tab_dir, exist_ok=True)
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {detail}")

    print("Calibration (Kasetsirikul 2020 Fig. 7a, NC FF170HP):")
    res = calibrate.fit()
    for k in ("K_plain", "K_published_p2", "K_manufacturer", "K_grav", "K_free", "h_eq_free_mm", "exponent_n",
              "rms_plain_mm", "rms_grav_mm", "K_width_cv"):
        print(f"  {k:16s} {res[k]:.4g}")
    calibrate.plot(res, os.path.join(fig_dir, "calibration_K.png"))
    check("K_NOM in params.py equals the repo fit", abs(params.v("K_NOM") - res["K_plain"]) < 0.01,
          f"({params.v('K_NOM')} vs {res['K_plain']:.3f})")
    check("fit agrees with published p^2 and manufacturer rating within 5 %",
          max(abs(res["K_plain"] / res[k] - 1) for k in ("K_published_p2", "K_manufacturer")) < 0.05)

    print("Scaling:")
    rows, meta = scaling.write(os.path.join(tab_dir, "scaling.md"))
    for name, _, lo, hi, *_ in rows:
        print(f"  {name:26s} {lo:.2e} .. {hi:.2e}")
    params.write_param_table(os.path.join(tab_dir, "parameters.md"))
    missing = [k for k, (_, _, src) in params.PARAMS.items() if not src.strip()]
    check("every parameter has a source or 'assumed' tag", not missing, str(missing or ""))

    print("Generator sanity checks:")
    K, Ls = params.v("K_NOM"), [5.0, 20.0, 40.0]
    t = arrival_times(Ls, Strip())
    check("uniform strip reproduces Washburn L^2 = K t", max(abs(ti * K / L ** 2 - 1) for ti, L in zip(t, Ls)) < 1e-4)
    check("k_rel = 1 segment is a no-op", arrival_times(Ls, Strip(perm=[(10, 15, 1.0)])) == t)
    tb = arrival_times(Ls, Strip(K=K * params.fluid_k_factor(mu=params.v("MU_BLOOD"))))
    check("viscosity scales every arrival by the same factor", max(abs(b / a - 3.5e-3 / 8.9e-4) for a, b in zip(t, tb)) < 1e-4)
    tr = arrival_times(Ls, Strip(perm=[(10, 14, 0.25)]))
    check("restriction leaves upstream arrivals unchanged, delays downstream", tr[0] == t[0] and tr[1] > t[1] and tr[2] > t[2])
    ex = 8.0 / (params.v("C_ABS") * params.v("WIDTH"))
    sp = stall_position(Strip(v_sample=8.0))
    check("8 uL sample stalls just beyond C_abs-limited length", ex < sp < ex * 1.3, f"(exhaust {ex:.1f} mm, final {sp:.1f} mm)")
    check("12 uL sample: last electrode (40 mm) unreachable", not math.isfinite(arrival_times([40.0], Strip(v_sample=12.0))[0]))
    tw = arrival_times(Ls, Strip(width=[(10, 14, 0.5)]))
    check("narrow neck slows the downstream front", tw[1] > t[1] and tw[0] == t[0])

    figures.arrival_patterns(os.path.join(fig_dir, "arrival_patterns.png"))
    print(f"Figures: {fig_dir}\nTables:  {tab_dir}")
    print("Regression: Phase 1 with the calibrated K")
    ok &= phase1()
    print("PHASE2 PASS" if ok else "PHASE2 FAIL")
    return ok


def phase3():
    import json

    from golden import evaluate as ev, figures as gfig
    from scenarios import corpus

    b = os.path.join(ROOT, "build", "corpus")
    fig_dir, tab_dir = (os.path.join(ROOT, "results", d) for d in ("figures", "tables"))
    for d in (b, fig_dir, tab_dir):
        os.makedirs(d, exist_ok=True)
    rows = corpus.generate(os.path.join(b, "corpus.csv"))
    corpus.write_stim(rows, os.path.join(b, "stim.txt"))
    cal, test = [r for r in rows if r["split"] == "cal"], [r for r in rows if r["split"] == "test"]
    print(f"Corpus: {len(rows)} scenarios ({len(cal)} calibration / {len(test)} test), "
          f"{len(corpus.specs())} fault specs x {len(corpus.JITTERS)} jitter x {len(corpus.CVS)} CV x {corpus.REPS} seeds")

    cfg = params.detector_config()
    tuned = ev.tune_model(cfg, cal)
    bcfg = ev.tune_baselines(cfg, cal)
    print(f"Tuned model-based: {tuned}\nTuned baselines:   {bcfg}")
    ok = tuned["TOL_Q"] == cfg["TOL_Q"] and tuned["TOL_ABS_Q"] == cfg["TOL_ABS_Q"]
    print(f"  [{'ok' if ok else 'FAIL'}] params.py tolerances equal the tuned values")

    preds, agree = ev.run_methods(cfg, bcfg, test)
    m, conf, loc, acc = ev.metrics(test, preds)
    print(f"\nTest split ({len(test)} scenarios). golden_float agrees with golden_fixed on {agree:.2%}")
    print(f"{'method':18s} {'detection':>9s} {'FAR':>6s}")
    for meth in ev.METHODS:
        print(f"{meth:18s} {m[meth]['detection']:9.1%} {m[meth]['far']:6.1%}")
    print("\nDetection by true cause:")
    groups = [g for g in ev.TRUTH_GROUPS if g != "NOMINAL"]
    print(f"{'':22s}" + "".join(f"{g[:13]:>14s}" for g in groups))
    for meth in ev.METHODS:
        print(f"{meth:22s}" + "".join(f"{m[meth]['det_by_group'].get(g, 0):14.1%}" for g in groups))
    print("\nConfusion (rows = true cause, cols = predicted):")
    print(f"{'':22s}" + "".join(f"{c[:9]:>10s}" for c in ev.CLS))
    for g, row in zip(ev.TRUTH_GROUPS, conf):
        print(f"{g:22s}" + "".join(f"{v:10d}" for v in row))
    print(f"\nExact class+location accuracy (excl. upstream restriction): {acc:.1%}")
    print("Localisation:", dict(loc))
    print("Median time to decision (s):")
    for meth in ev.METHODS:
        print(f"  {meth:18s}", {g: round(v, 1) for g, v in m[meth]["median_decision_s"].items()})

    gfig.confusion(conf, os.path.join(fig_dir, "confusion_matrix.png"))
    gfig.vs_noise(m, corpus.JITTERS, corpus.CVS, os.path.join(fig_dir, "detection_vs_noise.png"))
    gfig.by_group(m, os.path.join(fig_dir, "detection_by_cause.png"))
    with open(os.path.join(tab_dir, "metrics.json"), "w") as f:
        json.dump({"tuned_model": tuned, "tuned_baselines": bcfg, "metrics": m, "confusion": conf.tolist(),
                   "confusion_rows": ev.TRUTH_GROUPS, "confusion_cols": ev.CLS,
                   "localisation": {f"{k[0]}:{k[1]}": v for k, v in loc.items()},
                   "exact_accuracy": acc, "float_fixed_agreement": agree}, f, indent=1)
    print(f"Figures: {fig_dir}")
    print("PHASE3 PASS" if ok else "PHASE3 FAIL")
    return ok


def phase4_sim():
    from collections import Counter

    from scenarios import corpus

    b = os.path.join(ROOT, "build", "rtl_regress")
    os.makedirs(b, exist_ok=True)
    pkg = os.path.join(b, "params_pkg.sv")
    cfg = params.detector_config()
    params.write_sv_package(pkg, cfg)
    rows = corpus.generate()
    gold = {r["id"]: golden_fixed.decide(cfg, r["ticks"]) for r in rows}
    ticks = sum(g[2] for g in gold.values())
    shards = xsim.SIM_JOBS
    print(f"RTL regression: {len(rows)} scenarios, {ticks / 1e9:.2f}e9 timebase ticks, {shards} shards")
    rtl = xsim.run_corpus([(r["id"], r["ticks"]) for r in rows], b, pkg, shards=shards)

    bad = [r for r in rows if rtl.get(r["id"]) != gold[r["id"]][:2]]
    by_cls = Counter(CLS_NAME[gold[r["id"]][0]] for r in rows)
    print(f"  golden output classes exercised: {dict(by_cls)}")
    for r in bad[:10]:
        print(f"  MISMATCH id={r['id']} {r['family']} ticks={r['ticks']} golden={gold[r['id']][:2]} rtl={rtl.get(r['id'])}")
    ok = not bad and len(rtl) == len(rows)
    with open(os.path.join(ROOT, "results", "tables", "rtl_regression.txt"), "w") as f:
        f.write(f"scenarios {len(rows)}\nticks {ticks}\nmatched {len(rows) - len(bad)}\nmismatched {len(bad)}\n"
                f"classes {dict(by_cls)}\n")
    print(f"  bit-exact: {len(rows) - len(bad)}/{len(rows)}")
    return ok


def phase4_syn():
    import re
    import subprocess

    b = os.path.join(ROOT, "build", "syn")
    os.makedirs(b, exist_ok=True)
    params.write_sv_package(os.path.join(b, "params_pkg.sv"))
    vivado = os.path.join(xsim.VIVADO_BIN, "vivado.bat")
    print("Vivado OOC synth + implementation (xc7z020clg400-1, 100 MHz) ...")
    with open(os.path.join(b, "vivado.out"), "w") as f:
        p = subprocess.run(["cmd", "/c", vivado, "-mode", "batch", "-notrace", "-source", "../../syn/synth.tcl"],
                           cwd=b, stdout=f, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        print(f"  Vivado failed (rc={p.returncode}); see {b}\\vivado.out")
        return False
    util = open(os.path.join(b, "utilization.rpt")).read()
    timing = open(os.path.join(b, "timing.rpt")).read()
    power = open(os.path.join(b, "power.rpt")).read()

    def cell(name):
        m = re.search(r"\|\s*" + re.escape(name) + r"\s*\|\s*([\d.]+)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*([\d.]+)\s*\|\s*([<\d.]+)", util)
        return (m.group(1), m.group(2), m.group(3)) if m else ("?", "?", "?")

    res = {n: cell(n) for n in ("Slice LUTs", "Slice Registers", "DSPs", "Block RAM Tile")}
    m = re.search(r"WNS\(ns\)\s+TNS\(ns\).*?\n\s*-+.*?\n\s*([-\d.]+)\s+([-\d.]+)", timing, re.S)
    wns = float(m.group(1)) if m else float("nan")
    pw = re.search(r"Total On-Chip Power \(W\)\s*\|\s*([\d.]+)", power)
    dyn = re.search(r"Dynamic \(W\)\s*\|\s*([\d.]+)", power)
    lines = ["| Resource | Used | Available | Util % |", "|---|---|---|---|"]
    lines += [f"| {n} | {u} | {a} | {pc} |" for n, (u, a, pc) in res.items()]
    fmax = 1000.0 / (10.0 - wns)
    lines += ["", f"Clock 100 MHz: WNS = {wns:.3f} ns -> Fmax ~ {fmax:.0f} MHz (post-route, out-of-context)",
              f"Power (vectorless estimate): total {pw.group(1) if pw else '?'} W, dynamic {dyn.group(1) if dyn else '?'} W"]
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(ROOT, "results", "tables", "synthesis.md"), "w") as f:
        f.write(text + "\n")
    return wns >= 0


def _sim_errors(dirs):
    """Assertion / $error / $fatal messages in the simulator transcripts."""
    msgs = []
    for d in dirs:
        for line in open(os.path.join(d, "xsim.out"), errors="replace"):
            if line.lstrip().startswith(("Error:", "ERROR:", "Fatal:", "FATAL")):
                msgs.append(f"{os.path.basename(d)}: {line.strip()}")
    return msgs


def _coverage(dirs, out_dir):
    """Merge the per-shard functional-coverage databases with xcrg and return the text report."""
    import glob
    import shutil
    import subprocess

    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir)
    lst = os.path.join(out_dir, "covdbs.txt")
    with open(lst, "w") as f:
        for d in dirs:   # relative: xcrg splits list-file paths at spaces
            f.write(os.path.relpath(os.path.join(d, "xsim.covdb"), out_dir).replace("\\", "/") + "\n")
    with open(os.path.join(out_dir, "xcrg.out"), "w") as f:
        subprocess.run(["cmd", "/c", os.path.join(xsim.VIVADO_BIN, "xcrg.bat"), "-file", "covdbs.txt",
                        "-merge_dir", "merged", "-merge_db_name", "all", "-report_format", "text",
                        "-report_dir", "report", "-nolog"], cwd=out_dir, stdout=f, stderr=subprocess.STDOUT)
    reps = glob.glob(os.path.join(out_dir, "report", "**", "*.txt"), recursive=True)
    return "\n".join(open(r, errors="replace").read() for r in sorted(reps)), reps


def _coverage_summary(text, n):
    """Per-covergroup scores, plus the result coverpoint judged from the codes actually hit
    (code = class*8 + loc), so the verdict does not depend on how the bins were declared."""
    import re

    groups = dict(re.findall(r"^\s*tb_top\.dut\.u_core::(cg_\w+)\s*,([\d.]+)", text, re.M))
    hit = {}
    if "cg_result_u_cg_result_cp_res" in text:
        blk = text[text.index("Table tag :, cg_result_u_cg_result_cp_res"):]
        blk = blk[:blk.find("Table tag", 10)] if "Table tag" in blk[10:] else blk
        if "Covered bins" in blk:
            for name, h in re.findall(r"^\s+(\w+)\s*,\s*(\d+)\s*,", blk[blk.index("Covered bins"):], re.M):
                m = re.match(r"[a-z_]+?_(\d+)$", name)
                code = int(m.group(1)) if m else {"nominal": 0, "u_slow": 8, "u_fast": 16}.get(name)
                if code is not None:   # max: a code listed under overlapping bins is one event
                    hit[code] = max(hit.get(code, 0), int(h))
    want = [0, 8, 16] + [8 * c + l for c in (3, 6) for l in range(1, n)] + [8 * c + l for c in (4, 5) for l in range(n)]
    lines = ["| Covergroup | xcrg score % |", "|---|---|"] + [f"| {g} | {s} |" for g, s in groups.items()]
    lines += ["", "| Result (class, location) | Hits |", "|---|---|"]
    lines += [f"| {CLS_NAME[w // 8]}, {w % 8} | {hit.get(w, 0)} |" for w in want]
    missing = [w for w in want if w not in hit]
    unexpected = sorted(set(hit) - set(want))
    lines.append(f"\nResult combinations hit: {len(want) - len(missing)}/{len(want)}; unexpected: {unexpected or 'none'}")
    others_full = all(float(s) >= 100 for g, s in groups.items() if g != "cg_result")
    return "\n".join(lines), (others_full and not missing and not unexpected and len(groups) == 4)


def phase5(with_corpus=False):
    """Default: the boundary suite in ONE simulator process (assertions + coverage). The corpus is
    already bit-exact from Phase 4 on the same RTL; `phase5-corpus` reruns it with checks enabled."""
    from scenarios import boundary, corpus

    cfg = params.detector_config()
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {detail}")

    # 1. boundary-case suite
    bdir = os.path.join(ROOT, "build", "boundary")
    os.makedirs(bdir, exist_ok=True)
    pkg = os.path.join(bdir, "params_pkg.sv")
    params.write_sv_package(pkg, cfg)
    brows = boundary.build(cfg)
    print(f"Boundary suite: {len(brows)} directed cases")
    check("every case lands on its intended side (golden)", all(r[5] for r in brows),
          str([r[1] for r in brows if not r[5]] or ""))
    rtl = xsim.run_corpus([(i, t, g) for i, _, t, g, _, _ in brows], bdir, pkg, shards=1)
    bad = [(n, e, rtl.get(i)) for i, n, t, g, e, _ in brows if rtl.get(i) != e]
    for n, e, r in bad:
        print(f"    MISMATCH {n}: golden {e} rtl {r}")
    check("RTL bit-exact on the boundary suite", not bad, f"({len(brows) - len(bad)}/{len(brows)})")
    sat = boundary.saturation_bound(cfg)
    check("timebase cannot saturate (worst-case undecided tick < 2^TS_BITS - 1)",
          sat < (1 << cfg["TS_BITS"]) - 1, f"({sat} < {(1 << cfg['TS_BITS']) - 1}, margin x{((1 << cfg['TS_BITS']) - 1) / sat:.1f})")

    sdirs = [os.path.join(bdir, "shard00")]

    # 2. optional: full corpus with assertions and coverage compiled in
    if with_corpus:
        cdir = os.path.join(ROOT, "build", "rtl_regress")
        os.makedirs(cdir, exist_ok=True)
        pkg_c = os.path.join(cdir, "params_pkg.sv")
        params.write_sv_package(pkg_c, cfg)
        rows = corpus.generate()
        gold = {r["id"]: golden_fixed.classify(cfg, r["ticks"]) for r in rows}
        shards = xsim.SIM_JOBS
        print(f"Corpus regression with SVA + coverage: {len(rows)} scenarios, {shards} shards")
        rtl = xsim.run_corpus([(r["id"], r["ticks"]) for r in rows], cdir, pkg_c, shards=shards)
        nbad = sum(rtl.get(r["id"]) != gold[r["id"]] for r in rows)
        check("RTL bit-exact on the corpus", nbad == 0 and len(rtl) == len(rows), f"({len(rows) - nbad}/{len(rows)})")
        sdirs += [os.path.join(cdir, f"shard{i:02d}") for i in range(shards)]

    # 3. assertions
    errs = _sim_errors(sdirs)
    for e in errs[:10]:
        print("    " + e)
    check("no assertion failures", not errs, f"({len(errs)} error lines)")

    # 4. functional coverage (merged over all simulator runs)
    text, reps = _coverage(sdirs, os.path.join(ROOT, "build", "coverage"))
    rpt = os.path.join(ROOT, "results", "tables", "coverage.txt")
    with open(rpt, "w") as f:
        f.write(text)
    summary, full = _coverage_summary(text, cfg["N"])
    with open(os.path.join(ROOT, "results", "tables", "coverage_summary.md"), "w") as f:
        f.write(summary + "\n")
    print(summary)
    check("coverage: every state, transition, boundary event and result combination hit", bool(reps) and full)
    print("PHASE5 PASS" if ok else "PHASE5 FAIL")
    return ok, text


def phase5_mutants():
    from tools import mutants

    res = mutants.run(os.path.join(ROOT, "build", "mutants"))
    lines = ["| Mutant | Wrong results (boundary suite) | Assertion errors | Messages |", "|---|---|---|---|"]
    for name, mism, nerr, kinds in res:
        lines.append(f"| {name} | {mism} | {nerr} | {'; '.join(k[7:] for k in kinds[:3])} |")
    caught = sum(1 for r in res if r[2] > 0)
    lines.append(f"\n{caught}/{len(res)} mutants caught by assertions")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(ROOT, "results", "tables", "mutants.md"), "w") as f:
        f.write(text + "\n")
    return caught == len(res)


def phase6():
    from realdata import bezinge_flow as bf, compare

    path = os.path.join(ROOT, "data", "bezinge2024", "raw", "data_P3.csv")
    ok, ev = bf.self_test()
    print(f"  [{'ok' if ok else 'FAIL'}] port self-test (analytic step response) {ev}")
    res = compare.analyse(path)
    print(f"data_P3: {len(res['i'])} pulse samples ({res['t'][-1]:.1f} s), {res['nswv']} SWV scans (not analysed)")
    text = compare.table(res)
    print(text)
    with open(os.path.join(ROOT, "results", "tables", "realdata.md"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    compare.figure(res, os.path.join(ROOT, "results", "figures", "bezinge_flow.png"))
    judged = [r for r in res["rows"] if r["in_iqr"] is not None]
    ok &= len(res["events"]) == 4 and all(r["in_iqr"] for r in judged)
    print(f"  [{'ok' if ok else 'FAIL'}] 4 injections detected; reproduced flow times inside the paper's IQR "
          f"({sum(r['in_iqr'] for r in judged)}/{len(judged)})")
    print("PHASE6 PASS" if ok else "PHASE6 FAIL")
    return ok


def phase8():
    """Report assets: regenerate the identifiability figure and table; check every asset the
    report draft (report/REPORT_DRAFT.md) refers to exists. No simulator runs here."""
    from golden import identifiability, report_tables

    fig_dir, tab_dir = (os.path.join(ROOT, "results", d) for d in ("figures", "tables"))
    eq, crit = identifiability.figure(os.path.join(fig_dir, "identifiability.png"))
    md, _, _ = report_tables.identifiability_md()
    with open(os.path.join(tab_dir, "identifiability.md"), "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(md)
    need = {"figures": ["calibration_K.png", "arrival_patterns.png", "identifiability.png", "confusion_matrix.png",
                        "detection_vs_noise.png", "detection_by_cause.png", "bezinge_flow.png"],
            "tables": ["parameters.md", "scaling.md", "identifiability.md", "metrics.json", "rtl_regression.txt",
                       "synthesis.md", "coverage_summary.md", "realdata.md"]}
    missing = [f"{d}/{n}" for d, names in need.items() for n in names
               if not os.path.exists(os.path.join(ROOT, "results", d, n))]
    for m in missing:
        print(f"  MISSING results/{m} (regenerate with the phase that produces it)")
    ok = not missing and len({tuple(t) for _, _, t, _ in eq}) == 1
    print("PHASE8 PASS" if ok else "PHASE8 FAIL")
    return ok


def phase4():
    ok = phase4_sim()
    ok &= phase4_syn()
    print("PHASE4 PASS" if ok else "PHASE4 FAIL")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "phase1"
    sys.exit(0 if {"phase1": phase1, "phase2": phase2, "phase3": phase3, "phase4": phase4,
                   "phase4-sim": phase4_sim, "phase4-syn": phase4_syn,
                   "phase5": lambda: phase5()[0], "phase5-corpus": lambda: phase5(True)[0],
                   "phase5-mutants": phase5_mutants, "phase6": phase6, "phase8": phase8}[cmd]() else 1)
