#!/usr/bin/env python3
"""Glitch Groove — drum ratchets + tonal step components on T4 Pluck.

T1 (Drums, boop kit): kick/snare/hat groove + PULSE ratchets on step 1 or 9
T4 (Pluck/EPiano):    C minor pluck melody   + tonal shift components on step 9

Single-step component mode only supports steps 1 and 9 (device-verified:
steps 5 and 13 crash with num_patterns > 0).  Components fire on the
target step, modifying how the note there plays.

Variants (test in order, stop at first crash):
  1. gg_control          — T1+T4 notes, no components (must work)
  2. gg_t1_pulse_s9      — T1 drums + PULSE on step 9 [device-verified]
  3. gg_t1_pulse_s1      — T1 drums + PULSE on step 1 [corpus-verified]
  4. gg_t4_notes         — T4 melody only (tests T4 note authoring)
  5. gg_t4_random_s9     — T4 + RANDOM on step 9 [device-verified]
  6. gg_t4_tonality_s9   — T4 + TONALITY on step 9 [bank 2]
  7. gg_t4_cond_s9       — T4 + CONDITIONAL on step 9 [bank 2, skip]
  8. gg_full_s1_s9       — T1 PULSE(s1) + T4 RANDOM(s9)
  9. gg_full_dual        — T1 PULSE(s1)+HOLD(s9), T4 TONALITY(s1)+RANDOM(s9)

Usage:
    python tools/write_glitch_groove.py
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
OUTPUT_DIR = Path("output/glitch_groove")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Timing
QUARTER = STEP_TICKS * 4     # 1920 ticks
EIGHTH = STEP_TICKS * 2      # 960
DOTTED_QTR = STEP_TICKS * 6  # 2880
HALF = STEP_TICKS * 8        # 3840

# Drum kit (boop)
KICK, SNARE, RIM, CH, OH = 48, 50, 52, 56, 58


def n(step, note, vel=100, gate=0):
    return Note(step=step, note=note, velocity=vel, gate_ticks=gate)


baseline = XYProject.from_bytes(TEMPLATE.read_bytes())

# ── T1 Drum groove ───────────────────────────────────────────────────
# Punchy kick/snare pattern with hat texture.
# Step 1 kick = downbeat ratchet target, step 9 snare = midbar ratchet.
t1_drums = [
    n(1,  KICK,  112),          # downbeat kick — RATCHET TARGET (step 1)
    n(3,  CH,    75),           # hat
    n(5,  SNARE, 105),          # backbeat
    n(7,  CH,    70),           # hat
    n(9,  SNARE, 100),          # midbar snare — RATCHET TARGET (step 9)
    n(10, KICK,  90),           # off-grid kick (push)
    n(11, CH,    72),           # hat
    n(13, SNARE, 108),          # backbeat
    n(15, CH,    78),           # hat
    n(16, OH,    85),           # open hat pickup into next bar
]

# ── T4 Pluck melody (C minor) ────────────────────────────────────────
# Descending minor line.  Step 1 = opening note, step 9 = held 7th.
t4_melody = [
    n(1,  63, 95,  QUARTER),     # Eb4 — minor 3rd, TONALITY TARGET (step 1)
    n(3,  60, 88,  EIGHTH),      # C4  — root, passing tone
    n(5,  67, 100, QUARTER),     # G4  — 5th, held through backbeat
    n(9,  58, 92,  DOTTED_QTR),  # Bb3 — 7th, RANDOM TARGET (step 9)
    n(13, 56, 85,  QUARTER),     # Ab3 — b6
    n(16, 60, 78,  EIGHTH),      # C4  — root pickup, loops back
]

# ── Build variants ───────────────────────────────────────────────────

print("=== Glitch Groove: Drum Ratchets + Tonal Components ===\n")

variants = []


def emit(name, desc, build_fn):
    proj = build_fn()
    data = proj.to_bytes()
    (OUTPUT_DIR / f"{name}.xy").write_bytes(data)
    print(f"  {name + '.xy':35s} {len(data):5d}B  {desc}")
    variants.append((name, desc))


# 1. Control: notes only
emit("gg_control", "T1+T4 notes, no components (control)",
     lambda: append_notes_to_tracks(baseline, {1: t1_drums, 4: t4_melody}))

# 2. T1 + PULSE on step 9 (device-verified)
def build_t1_pulse_s9():
    proj = append_notes_to_track(baseline, 1, t1_drums)
    return add_step_components(proj, 1, [StepComponent(9, ComponentType.PULSE, 0x03)])
emit("gg_t1_pulse_s9", "T1 drums + PULSE(s9) ratchet [verified]", build_t1_pulse_s9)

# 3. T1 + PULSE on step 1 (corpus-verified via unnamed 8)
def build_t1_pulse_s1():
    proj = append_notes_to_track(baseline, 1, t1_drums)
    return add_step_components(proj, 1, [StepComponent(1, ComponentType.PULSE, 0x03)])
emit("gg_t1_pulse_s1", "T1 drums + PULSE(s1) ratchet [corpus]", build_t1_pulse_s1)

# 4. T4 notes only (tests T4 Pluck insert-before-tail)
emit("gg_t4_notes", "T4 pluck melody only",
     lambda: append_notes_to_track(baseline, 4, t4_melody))

# 5. T4 + RANDOM on step 9 (bank 1, device-verified)
def build_t4_random_s9():
    proj = append_notes_to_track(baseline, 4, t4_melody)
    return add_step_components(proj, 4, [StepComponent(9, ComponentType.RANDOM, 0x03)])
emit("gg_t4_random_s9", "T4 + RANDOM(s9) [bank 1, verified]", build_t4_random_s9)

# 6. T4 + TONALITY on step 9 (bank 2, experimental)
def build_t4_tonality_s9():
    proj = append_notes_to_track(baseline, 4, t4_melody)
    return add_step_components(proj, 4, [StepComponent(9, ComponentType.TONALITY, 0x04)])
emit("gg_t4_tonality_s9", "T4 + TONALITY(s9) [bank 2]", build_t4_tonality_s9)

# 7. T4 + CONDITIONAL on step 9 (bank 2, skip cycles)
def build_t4_cond_s9():
    proj = append_notes_to_track(baseline, 4, t4_melody)
    return add_step_components(proj, 4, [StepComponent(9, ComponentType.CONDITIONAL, 0x02)])
emit("gg_t4_cond_s9", "T4 + CONDITIONAL(s9) [bank 2, skip]", build_t4_cond_s9)

# 8. Full: T1 PULSE on step 1 + T4 RANDOM on step 9
def build_full_s1_s9():
    proj = append_notes_to_tracks(baseline, {1: t1_drums, 4: t4_melody})
    proj = add_step_components(proj, 1, [StepComponent(1, ComponentType.PULSE, 0x03)])
    return add_step_components(proj, 4, [StepComponent(9, ComponentType.RANDOM, 0x03)])
emit("gg_full_s1_s9", "T1 PULSE(s1) + T4 RANDOM(s9)", build_full_s1_s9)

# 9. Dual: components on BOTH steps 1 and 9 per track
def build_full_dual():
    proj = append_notes_to_tracks(baseline, {1: t1_drums, 4: t4_melody})
    # T1: PULSE(s1) ratchet on downbeat + HOLD(s9) on midbar snare
    proj = add_step_components(proj, 1, [
        StepComponent(1, ComponentType.PULSE, 0x03),
        StepComponent(9, ComponentType.HOLD, 0x01),
    ])
    # T4: TONALITY(s1) on opening Eb + RANDOM(s9) on the Bb3
    proj = add_step_components(proj, 4, [
        StepComponent(1, ComponentType.TONALITY, 0x04),
        StepComponent(9, ComponentType.RANDOM, 0x03),
    ])
    return proj
emit("gg_full_dual", "T1 PULSE(s1)+HOLD(s9), T4 TONAL(s1)+RANDOM(s9)", build_full_dual)


print(f"""
=== Test plan (test in order, stop at first crash) ===

  Phase 1: Known-good
    1. gg_control          — notes only (must work)
    2. gg_t1_pulse_s9      — PULSE on step 9 (device-verified last session)
    3. gg_t1_pulse_s1      — PULSE on step 1 (corpus-verified, first code test)

  Phase 2: Tonal step components on T4
    4. gg_t4_notes         — T4 pluck melody (device-verified last session)
    5. gg_t4_random_s9     — RANDOM on step 9 (device-verified last session)
    6. gg_t4_tonality_s9   — TONALITY on step 9 [bank 2, first test]
    7. gg_t4_cond_s9       — CONDITIONAL on step 9 [bank 2, first test]

  Phase 3: Cross-track + dual components
    8. gg_full_s1_s9       — T1 PULSE(s1) + T4 RANDOM(s9) [cross-track]
    9. gg_full_dual        — 2 components per track, both steps

Musical content:
  T1 (boop drums): K...H.S.H.S.KH.S.H.O  (K@1, S@9 = component targets)
  T4 (pluck Cm):   Eb..C.G...Bb....Ab..C  (Eb@1, Bb@9 = component targets)

Already verified (don't need to re-test): 1, 2, 4, 5
New tests: 3, 6, 7, 8, 9

Total: 9 files in output/glitch_groove/""")
