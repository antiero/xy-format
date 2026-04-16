#!/usr/bin/env python3
"""Diagnostic: test step components on tonal (non-drum) tracks.

Engine-aware slot table offsets:
  Drum/Prism:                table at body07[0x0024], same as T1
  Dissolve/Hardsync/Axis/MS: table at body07[0x0025], +1 byte
  EPiano:                    table at body07[0x0021], -3 bytes

Tests step 9 Pulse component on each engine type, plus a musical
arrangement with components on T1 (drums) + T3 (Prism bass).

Usage:
    python tools/write_tonal_comp_diag.py
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
OUTPUT_DIR = Path("output/step_diag")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

QUARTER = STEP_TICKS * 4
EIGHTH = STEP_TICKS * 2
HALF = STEP_TICKS * 8
WHOLE = STEP_TICKS * 16

def n(step, note, vel=100, gate=0):
    return Note(step=step, note=note, velocity=vel, gate_ticks=gate)

baseline = XYProject.from_bytes(TEMPLATE.read_bytes())

print("=== Tonal Track Step Components ===")
print("    (engine-aware slot table offsets)\n")

# Verify engine IDs match expectations
engine_names = {0x03: 'Drum', 0x07: 'EPiano', 0x12: 'Prism', 0x13: 'Hardsync',
                0x14: 'Dissolve', 0x16: 'Axis', 0x1E: 'Multisampler'}
for i in range(8):
    t = baseline.tracks[i]
    eid = t.engine_id
    print(f"  T{i+1}: engine_id={eid:#04x} ({engine_names.get(eid, '?')})")
print()

# --- D: Component-only on each engine ---
print("--- D: Pulse(s9) on each engine (component only, no notes) ---")

tonal_tests = [
    ("r3_D01_t3_prism_pulse_s9",    3, "T3 Prism"),
    ("r3_D02_t4_epiano_pulse_s9",   4, "T4 EPiano"),
    ("r3_D03_t5_dissolve_pulse_s9", 5, "T5 Dissolve"),
    ("r3_D04_t6_hardsync_pulse_s9", 6, "T6 Hardsync"),
    ("r3_D05_t7_axis_pulse_s9",     7, "T7 Axis"),
    ("r3_D06_t8_multisamp_pulse_s9",8, "T8 Multisampler"),
]

comp = StepComponent(9, ComponentType.PULSE, 0x01)

for name, track, desc in tonal_tests:
    proj = add_step_components(baseline, track, [comp])
    data = proj.to_bytes()
    (OUTPUT_DIR / f"{name}.xy").write_bytes(data)
    print(f"  {name + '.xy':45s} {len(data):5d}B  {desc}")

# --- E: Component + notes on tonal tracks ---
print("\n--- E: Pulse(s9) + notes on tonal tracks ---")

# T3 bass notes
t3_bass = [
    n(1, 48, 100, QUARTER), n(5, 43, 90, QUARTER),
    n(9, 44, 95, QUARTER), n(13, 41, 85, QUARTER),
]

# T7 pad notes
t7_pad = [
    n(1, 60, 80, WHOLE), n(9, 67, 70, HALF),
]

comp_note_tonal = [
    ("r3_E01_t3_pulse_s9_bass",  3, t3_bass, "T3 Prism + bass notes"),
    ("r3_E02_t7_pulse_s9_pad",   7, t7_pad,  "T7 Axis + pad notes"),
]

for name, track, notes, desc in comp_note_tonal:
    proj = append_notes_to_track(baseline, track, notes)
    proj = add_step_components(proj, track, [comp])
    data = proj.to_bytes()
    (OUTPUT_DIR / f"{name}.xy").write_bytes(data)
    print(f"  {name + '.xy':45s} {len(data):5d}B  {desc}")

# --- F: Multi-track with components on drums AND tonal ---
print("\n--- F: Multi-track musical arrangement with components ---")

t1_drums = [
    n(1, 48, 110), n(3, 56, 70), n(5, 50, 100), n(7, 56, 70),
    n(9, 48, 110), n(11, 56, 70), n(13, 50, 100), n(15, 56, 80),
]

proj = append_notes_to_tracks(baseline, {
    1: t1_drums, 3: t3_bass, 7: t7_pad,
})
# Pulse on T1 drums step 9
proj = add_step_components(proj, 1, [StepComponent(9, ComponentType.PULSE, 0x01)])
# Pulse on T3 bass step 9
proj = add_step_components(proj, 3, [StepComponent(9, ComponentType.PULSE, 0x01)])
data = proj.to_bytes()
(OUTPUT_DIR / "r3_F01_multi_t1_t3_pulse.xy").write_bytes(data)
print(f"  {'r3_F01_multi_t1_t3_pulse.xy':45s} {len(data):5d}B  T1 drums + T3 bass + T7 pad, Pulse on T1+T3")

print(f"\n=== Test plan ===")
print(f"  D01: T3 Prism (SAME table offset as T1, should work)")
print(f"  D02: T4 EPiano (DIFFERENT offset 0x21, table 3B earlier)")
print(f"  D03-D06: T5-T8 (offset 0x25, table 1B later)")
print(f"  E01-E02: Tonal + notes combo")
print(f"  F01: Multi-track musical arrangement with components on drums+tonal")
print(f"\nTotal: 9 new test files")
