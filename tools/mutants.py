"""Mutation check of the verification environment: do the SVA checkers catch deliberately broken
copies of the RTL? Each mutant runs the boundary suite; a mutant counts as caught when at least
one assertion fires, independently of the golden-model comparison."""
import os
import re
import shutil
import subprocess

from physics import params
from scenarios import boundary
from tools import xsim

ROOT = xsim.ROOT
MUTANTS = {  # name: (file, original text, mutated text)
    "classify_early": ("detector_core.sv",       # classify one electrode before the last arrival
                       "else if (idx == N-1) begin k <= 3'd1; state <= S_CLS0; end",
                       "else if (idx == N-2) begin k <= 3'd1; state <= S_CLS0; end"),
    "no_order_check": ("detector_core.sv",       # accept out-of-order / simultaneous arrivals
                       "else if (|others) begin", "else if (1'b0) begin"),
    "no_late_stall":  ("detector_core.sv",       # accept arrivals after their window closed
                       "if ((pw << 8) > B) begin cls <= STALL; loc <= idx; state <= S_REPORT; end          // arrived too late",
                       "if (1'b0) begin end"),
    "no_min_first":   ("detector_core.sv",       # drop the first-segment plausibility floor
                       "if (idx == 0 && (w_t'(m_snap) << 8) < MIN_FIRST) begin", "if (1'b0) begin"),
    "stall_early":    ("detector_core.sv",       # declare a stall on the window edge (>= for >)
                       "S_TESTN: if ((pw << 8) > B)", "S_TESTN: if ((pw << 8) >= B)"),
    "short_filter":   ("capture_unit.sv",        # glitch filter one clock short
                       "end else if (cnt == DEB-1) begin", "end else if (cnt == DEB-2) begin"),
}


def run(build_dir):
    cfg = params.detector_config()
    rows = boundary.build(cfg)
    shutil.rmtree(build_dir, ignore_errors=True)
    procs = []
    for name, (fname, old, new) in MUTANTS.items():
        src = open(os.path.join(ROOT, "rtl", fname)).read()
        assert src.count(old) == 1, f"mutant {name}: anchor text not found once in {fname}"
        d = os.path.join(build_dir, name)
        os.makedirs(d)
        open(os.path.join(d, fname), "w").write(src.replace(old, new))
        pkg = os.path.join(d, "params_pkg.sv")
        params.write_sv_package(pkg, cfg)
        srcs = [pkg] + [os.path.join(d, fname) if s.endswith(fname) else os.path.join(ROOT, s)
                        for s in xsim.RTL + xsim.TB]
        with open(os.path.join(d, "stim.txt"), "w") as f:
            for i, _, t, g, _, _ in rows:
                f.write(f"{i} " + " ".join(map(str, t)) + f" {len(g)}" + "".join(f" {a} {b} {c}" for a, b, c in g) + "\n")
        open(os.path.join(d, "run.bat"), "w").write(xsim._shard_script(srcs))
        procs.append((name, d))
    running = []
    for name, d in procs:                                  # at most SIM_JOBS simulators at a time
        if len(running) >= xsim.SIM_JOBS:
            running.pop(0).wait()
        running.append(subprocess.Popen(["cmd", "/c", os.path.join(d, "run.bat")], cwd=d))
    for p in running:
        p.wait()
    results = []
    for name, d in procs:
        out = open(os.path.join(d, "xsim.out"), errors="replace").read()
        errs = [l.strip() for l in out.splitlines() if l.lstrip().startswith("Error:")]
        rtl = {}
        if os.path.exists(os.path.join(d, "rtl_out.txt")):
            for line in open(os.path.join(d, "rtl_out.txt")):
                a = line.split()
                rtl[int(a[0])] = (int(a[1]), int(a[2]))
        mism = sum(rtl.get(i) != e for i, _, _, _, e, _ in rows)
        kinds = sorted({re.sub(r"\d+", "#", e) for e in errs})
        results.append((name, mism, len(errs), kinds))
    return results
