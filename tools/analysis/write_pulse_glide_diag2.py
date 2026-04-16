#!/usr/bin/env python3
"""Round 2 diagnostics: isolate Hold(step 1) crash.

Known:  Pulse(step 9) + notes → WORKS
Crash:  Hold(step 1)  + note(step 9) → CRASH

Three variables to isolate:
  A. Component TYPE  (Hold vs Pulse)
  B. Component STEP  (1 vs 9)
  C. Note presence/position

Usage:
    python tools/write_pulse_glide_diag2.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject
from xy.note_events import Note, STEP_TICKS
from xy.step_components import StepComponent, ComponentType
from xy.project_builder import (
    append_notes_to_track, append_notes_to_tracks, add_step_components,
)

TEMPLATE = Path("src/one-off-changes-from-default/unnamed 1.xy")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

QUARTER = STEP_TICKS * 4
KICK = 48

def n(step, note, vel=100, gate=0):
    return Note(step=step, note=note, velocity=vel, gate_ticks=gate)

baseline = XYProject.from_bytes(TEMPLATE.read_bytes())

print("=== Round 2: Isolate Hold(step 1) crash ===\n")

tests = [
    # --- Isolate: Is Hold step 1 encoding itself broken? ---
    ("pg_r2_hold_s1_only",
     StepComponent(1, ComponentType.HOLD, 0x01), None,
     "Hold(step1) only, NO notes — tests encoding alone"),

    # --- Isolate: Is step 1 slot + notes the issue? ---
    ("pg_r2_pulse_s1_note_s9",
     StepComponent(1, ComponentType.PULSE, 0x01), [n(9, KICK, 100)],
     "Pulse(step1) + note(step9) — tests step 1 slot with notes"),

    # --- Isolate: Is Hold + notes the issue at any step? ---
    ("pg_r2_hold_s9_note_s1",
     StepComponent(9, ComponentType.HOLD, 0x01), [n(1, KICK, 100)],
     "Hold(step9) + note(step1) — tests Hold at verified step 9"),

    # --- Isolate: Is it Hold's 8-byte size at step 1? ---
    ("pg_r2_rampup_s1_note_s9",
     StepComponent(1, ComponentType.RAMP_UP, 0x08), [n(9, KICK, 100)],
     "RampUp(step1) + note(step9) — another 8-byte comp at step 1"),

    # --- Isolate: Hold step 1 + note on same step 1 ---
    ("pg_r2_hold_s1_note_s1",
     StepComponent(1, ComponentType.HOLD, 0x01), [n(1, KICK, 100)],
     "Hold(step1) + note(step1) — same step combo"),
]

for name, comp, notes, desc in tests:
    if notes:
        proj = append_notes_to_track(baseline, 1, notes)
        proj = add_step_components(proj, 1, [comp])
    else:
        proj = add_step_components(baseline, 1, [comp])
    data = proj.to_bytes()
    (OUTPUT_DIR / f"{name}.xy").write_bytes(data)
    print(f"  {name + '.xy':40s} {len(data):5d}B  {desc}")

# --- Also: regenerate the musical arrangement with T1 Pulse only ---
EIGHTH = STEP_TICKS * 2
DOTTED_QTR = STEP_TICKS * 6
HALF = STEP_TICKS * 8
WHOLE = STEP_TICKS * 16
SNARE = 50
CH = 56

t1_notes = [
    n(1, KICK, 110), n(3, CH, 70), n(5, SNARE, 100), n(7, CH, 70),
    n(9, KICK, 110), n(11, CH, 70), n(13, SNARE, 100), n(15, CH, 80),
    n(16, CH, 90),
]
t3_notes = [
    n(1, 48, 100, QUARTER), n(5, 43, 90, QUARTER),
    n(9, 44, 95, QUARTER), n(13, 41, 85, QUARTER),
]
t5_notes = [
    n(1, 63, 90, EIGHTH), n(4, 62, 80, EIGHTH), n(6, 60, 85, QUARTER),
    n(9, 67, 100, DOTTED_QTR), n(15, 63, 75, EIGHTH),
]
t7_notes = [
    n(1, 60, 80, WHOLE), n(9, 67, 70, HALF),
]

# Full arrangement: all 4 tracks notes + T1 Pulse on step 9 (confirmed working)
proj = append_notes_to_tracks(baseline, {
    1: t1_notes, 3: t3_notes, 5: t5_notes, 7: t7_notes,
})
proj = add_step_components(proj, 1,
    [StepComponent(9, ComponentType.PULSE, 0x01)])
data = proj.to_bytes()
(OUTPUT_DIR / "pulse_glide_v2.xy").write_bytes(data)
print(f"\n  {'pulse_glide_v2.xy':40s} {len(data):5d}B  Full 4-track + T1 Pulse(step9)")

print(f"\nExpected results:")
print(f"  hold_s1_only       → if WORKS: Hold encoding OK, crash is notes combo")
print(f"                       if CRASH: Hold step 1 encoding is broken")
print(f"  pulse_s1_note_s9   → if WORKS: step 1 slot OK with notes")
print(f"                       if CRASH: step 1 slot + notes broken")
print(f"  hold_s9_note_s1    → if WORKS: Hold + notes OK at step 9")
print(f"                       if CRASH: Hold + notes broken everywhere")
print(f"  rampup_s1_note_s9  → if WORKS: Hold specifically is the issue")
print(f"                       if CRASH: any 8-byte comp at step 1 + notes broken")
print(f"  hold_s1_note_s1    → if WORKS: Hold + note on same step OK")
print(f"                       if CRASH: consistent with other Hold crashes")
