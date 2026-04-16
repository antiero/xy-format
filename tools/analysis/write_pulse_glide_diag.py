#!/usr/bin/env python3
"""Diagnostic files for step component + notes combination.

Findings so far:
  - pulse_glide_t1.xy: T1 body matches corpus 59 byte-for-byte in first
    1836 bytes, with 125 bytes of note events appended. But step component
    is invisible on device.
  - T3/T5/T7 crash: slot table at 0xA2 is wrong for non-drum engines.

This script generates targeted diagnostics to isolate the T1 issue.

Usage:
    python tools/write_pulse_glide_diag.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject, TrackBlock
from xy.note_events import Note, STEP_TICKS
from xy.step_components import StepComponent, ComponentType
from xy.project_builder import (
    append_notes_to_track, append_notes_to_tracks, add_step_components,
)

TEMPLATE = Path("src/one-off-changes-from-default/unnamed 1.xy")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

EIGHTH = STEP_TICKS * 2
QUARTER = STEP_TICKS * 4
DOTTED_QTR = STEP_TICKS * 6
HALF = STEP_TICKS * 8
WHOLE = STEP_TICKS * 16
KICK = 48
SNARE = 50
CH = 56

def n(step, note, vel=100, gate=0):
    return Note(step=step, note=note, velocity=vel, gate_ticks=gate)

baseline = XYProject.from_bytes(TEMPLATE.read_bytes())

# Same note data as pulse_glide
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

comp_pulse_s9 = StepComponent(step=9, component=ComponentType.PULSE, param=0x01)
comp_hold_s1 = StepComponent(step=1, component=ComponentType.HOLD, param=0x01)

print("=== Pulse & Glide Diagnostics ===\n")

# ── Diag 1: Component ONLY on T1 (exact corpus recipe) ─────────────
# This should match unnamed 59 behavior. If this fails, encoding is broken.
proj = add_step_components(baseline, 1, [comp_pulse_s9])
data = proj.to_bytes()
(OUTPUT_DIR / "pg_diag1_comp_only.xy").write_bytes(data)
print(f"  1. pg_diag1_comp_only.xy      {len(data):6d}B  T1 Pulse(step9) only, NO notes")
print(f"     If this works: our component encoding is correct")
print(f"     If this fails: encoding is broken")

# ── Diag 2: Component first, THEN notes ────────────────────────────
# Maybe order matters — add component while body is still type 05,
# then append notes.
proj = add_step_components(baseline, 1, [comp_pulse_s9])
proj = append_notes_to_track(proj, 1, t1_notes)
data = proj.to_bytes()
(OUTPUT_DIR / "pg_diag2_comp_first.xy").write_bytes(data)
print(f"  2. pg_diag2_comp_first.xy     {len(data):6d}B  T1 comp first, then notes")
print(f"     Tests: does order of operations matter?")

# ── Diag 3: Notes first, THEN component (same as pulse_glide_t1) ───
# This is what we already tested. Included for completeness.
proj = append_notes_to_track(baseline, 1, t1_notes)
proj = add_step_components(proj, 1, [comp_pulse_s9])
data = proj.to_bytes()
(OUTPUT_DIR / "pg_diag3_notes_first.xy").write_bytes(data)
print(f"  3. pg_diag3_notes_first.xy    {len(data):6d}B  T1 notes first, then comp")
print(f"     Same as pulse_glide_t1 (expected invisible)")

# ── Diag 4: Note on step 1 only, component on step 9 ───────────────
# Tests whether the issue is note + component on the SAME step (step 9).
proj = append_notes_to_track(baseline, 1, [n(1, KICK, 100)])
proj = add_step_components(proj, 1, [comp_pulse_s9])
data = proj.to_bytes()
(OUTPUT_DIR / "pg_diag4_diff_steps.xy").write_bytes(data)
print(f"  4. pg_diag4_diff_steps.xy     {len(data):6d}B  T1 note(step1) + comp(step9)")
print(f"     Tests: is the conflict about same-step note+comp?")

# ── Diag 5: Hold on step 1, note on step 9 ─────────────────────────
# Reverse of diag 4: component on step 1, note on step 9.
proj = append_notes_to_track(baseline, 1, [n(9, KICK, 100)])
proj = add_step_components(proj, 1, [comp_hold_s1])
data = proj.to_bytes()
(OUTPUT_DIR / "pg_diag5_hold_s1_note_s9.xy").write_bytes(data)
print(f"  5. pg_diag5_hold_s1_note_s9.xy {len(data):5d}B  T1 Hold(step1) + note(step9)")
print(f"     Tests: does any note+comp combo work?")

# ── Musical arrangement (notes only, no components) ─────────────────
# Safe version with all 4 tracks, using gate lengths for expressiveness.
proj = append_notes_to_tracks(baseline, {
    1: t1_notes, 3: t3_notes, 5: t5_notes, 7: t7_notes,
})
data = proj.to_bytes()
(OUTPUT_DIR / "pulse_glide_notes.xy").write_bytes(data)
print(f"\n  N. pulse_glide_notes.xy       {len(data):6d}B  All 4 tracks, notes only [SAFE]")

print(f"\nTest order:")
print(f"  1. pg_diag1_comp_only.xy     — confirms encoding works at all")
print(f"  2. pg_diag2_comp_first.xy    — comp then notes (maybe order matters)")
print(f"  3. pg_diag3_notes_first.xy   — notes then comp (known invisible)")
print(f"  4. pg_diag4_diff_steps.xy    — note step 1, comp step 9")
print(f"  5. pg_diag5_hold_s1_note_s9  — Hold step 1, note step 9")
print(f"  N. pulse_glide_notes.xy      — safe musical arrangement")


if __name__ == "__main__":
    pass  # Script runs at import
