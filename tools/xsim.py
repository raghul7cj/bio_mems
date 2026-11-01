"""Headless Vivado xsim driver: compile, elaborate and run the corpus testbench, sharded in parallel.

cmd.exe splits batch arguments on '=' and the project path has spaces, so no plusargs are used:
each shard runs in its own directory with a fixed stim.txt -> rtl_out.txt.
"""
import os
import subprocess
import time

VIVADO_BIN = os.environ.get("VIVADO_BIN", r"C:\Xilinx\Vivado\2022.2\bin")
# parallel simulator processes; 12 with assertions + coverage exhausted a 16 GB machine
SIM_JOBS = int(os.environ.get("SIM_JOBS", "4"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTL = ["rtl/sync2.sv", "rtl/capture_unit.sv", "rtl/mul_u.sv", "rtl/detector_core.sv", "rtl/detector_top.sv"]
TB = ["tb/tb_top.sv"]


def _cmd(tool, args):
    return ["cmd", "/c", os.path.join(VIVADO_BIN, tool + ".bat"), *args]


def _run(tool, args, cwd, log):
    with open(os.path.join(cwd, log), "w") as f:
        p = subprocess.run(_cmd(tool, args), cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        raise RuntimeError(f"{tool} failed (rc={p.returncode}); see {os.path.join(cwd, log)}")


def _shard_script(srcs):
    """One batch file per shard: compile, elaborate, simulate."""
    q = " ".join(f'"{s}"' for s in srcs)
    b = VIVADO_BIN
    inc = os.path.join(ROOT, "tb")
    # the tools write xvlog.log / elaborate.log / xsim.log themselves; console output goes to *.out
    return (f'@echo off\ncall "{b}\\xvlog.bat" -sv -i "{inc}" {q} > xvlog.out 2>&1 || exit /b 1\n'
            f'call "{b}\\xelab.bat" tb_top -s tb_sim -timescale 1ns/1ps > xelab.out 2>&1 || exit /b 2\n'
            f'call "{b}\\xsim.bat" tb_sim -R > xsim.out 2>&1 || exit /b 3\n')


def run_corpus(rows, build_dir, pkg_path, shards=1):
    """rows: list of (id, ticks) or (id, ticks, glitches[(j, g, w)]). Returns {id: (cls, loc)}.
    Each shard leaves its functional-coverage database in <shard>/xsim.covdb."""
    os.makedirs(build_dir, exist_ok=True)
    srcs = [pkg_path] + [os.path.join(ROOT, s) for s in RTL + TB]
    shards = max(1, min(shards, len(rows)))
    # round-robin keeps the expensive scenario families spread over the shards
    parts = [rows[i::shards] for i in range(shards)]
    procs = []
    for i, part in enumerate(parts):
        d = os.path.join(build_dir, f"shard{i:02d}")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "stim.txt"), "w") as f:
            for row in part:
                sid, ticks, gl = row[0], row[1], (row[2] if len(row) > 2 else [])
                f.write(f"{sid} " + " ".join(map(str, ticks)) + f" {len(gl)}"
                        + "".join(f" {j} {g} {w}" for j, g, w in gl) + "\n")
        with open(os.path.join(d, "run.bat"), "w") as f:
            f.write(_shard_script(srcs))
        procs.append((d, len(part), subprocess.Popen(["cmd", "/c", os.path.join(d, "run.bat")], cwd=d)))
    t0 = time.time()
    out, failed = {}, []
    for d, n, p in procs:
        rc = p.wait()
        log = os.path.join(d, "xsim.out")
        if rc != 0 or not os.path.exists(log) or "TB_DONE" not in open(log).read():
            failed.append(f"{d} (rc={rc})")
            continue
        with open(os.path.join(d, "rtl_out.txt")) as f:
            for line in f:
                a = line.split()
                if a:
                    out[int(a[0])] = (int(a[1]), int(a[2]))
    if failed:
        raise RuntimeError("xsim shard(s) failed: " + ", ".join(failed))
    print(f"  xsim: {len(rows)} scenarios on {shards} shard(s) in {time.time() - t0:.0f} s")
    return out
