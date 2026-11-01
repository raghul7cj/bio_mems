"""Phase 1 tracer scenarios: one nominal strip and two restrictions (strong, mild) in segment 2.

Stimulus line format (one scenario per line):  id t_0 ... t_{N-1}
t_k in ticks (>= 1); -1 = electrode never fires; -2 = line high before arm.
Ground truth is written alongside as  id class loc.
"""
from physics import params as P
from physics.darcy_series import Strip, arrival_times
from physics.sensor import to_ticks

CLS = {"NOMINAL": 0, "UNIFORM_SLOW": 1, "UNIFORM_FAST": 2, "RESTRICTION": 3, "STALL": 4, "SENSOR": 5, "ANOMALY": 6}


def tracer_scenarios():
    pos = P.electrode_positions()
    mid = 0.5 * (pos[1] + pos[2])  # segment 2 lies between electrodes 1 and 2
    return [
        (0, arrival_times(pos, Strip()), ("NOMINAL", 0)),
        (1, arrival_times(pos, Strip(perm=[(mid - 2.0, mid + 2.0, 1 / 6)])), ("RESTRICTION", 2)),
        # Mild restriction, kept on purpose: its excess resistance accumulates downstream, so with a
        # 15 % tolerance it is first flagged one segment late (localisation lag; studied in Phase 3).
        (2, arrival_times(pos, Strip(perm=[(mid - 1.0, mid + 1.0, 1 / 4)])), ("RESTRICTION", 2)),
    ]


def write(stim_path, truth_path):
    rows = []
    with open(stim_path, "w") as fs, open(truth_path, "w") as ft:
        for sid, times, (cls, loc) in tracer_scenarios():
            ticks = to_ticks(times)
            fs.write(f"{sid} " + " ".join(map(str, ticks)) + "\n")
            ft.write(f"{sid} {CLS[cls]} {loc}\n")
            rows.append((sid, ticks))
    return rows
