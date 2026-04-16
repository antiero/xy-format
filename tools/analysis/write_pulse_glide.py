#!/usr/bin/env python3
"""Generate "Pulse & Glide" — a 4-track step-component showcase in C minor.

Concept: each track uses a different primary step component to create
contrasting textures that interlock musically.

  T1  Drums (Boop)    — driving groove + Pulse retrigger on beat 3
  T3  Bass (Prism)    — walking Cm bass + Hold on beat 1
  T5  Lead (Dissolve) — sparse melody + RampUp on beat 3
  T7  Pad (Axis)      — sustained tones + Hold on beat 1

Outputs (6 files for progressive crash isolation):
  Individual tracks (notes + component):
    pulse_glide_t1.xy  — T1 drums + Pulse(step 9)
    pulse_glide_t3.xy  — T3 bass + Hold(step 1)
    pulse_glide_t5.xy  — T5 lead + RampUp(step 9)
    pulse_glide_t7.xy  — T7 pad + Hold(step 1)
  Combined:
    pulse_glide_notes.xy  — all 4 tracks, notes only (safe control)
    pulse_glide_full.xy   — all 4 tracks + all step components

Testing order:
  1. pulse_glide_notes.xy   (if this crashes → note/preamble issue)
  2. pulse_glide_t1.xy      (T1 component safest — corpus-verified slot)
  3. pulse_glide_t3/t5/t7   (experimental — slot table unverified on T3/T5/T7)
  4. pulse_glide_full.xy    (all together)

NOTE: Step components are only verified on Track 1 in the corpus
(unnamed 8/9/59-78). Components on T3/T5/T7 are experimental —
the slot table may be at a different offset for non-drum engines.

Usage:
    python tools/write_pulse_glide.py
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

# ── Constants ───────────────────────────────────────────────────────

TEMPLATE = Path("src/one-off-changes-from-default/unnamed 1.xy")
OUTPUT_DIR = Path("output")

# Gate lengths in ticks (STEP_TICKS=480)
EIGHTH = STEP_TICKS * 2        # 960
QUARTER = STEP_TICKS * 4       # 1920
DOTTED_QTR = STEP_TICKS * 6    # 2880
HALF = STEP_TICKS * 8          # 3840
WHOLE = STEP_TICKS * 16        # 7680

# Drum sounds (Track 1 "boop" kit)
KICK = 48
SNARE = 50
CH = 56   # closed hat

# Shorthand
def n(step, note, vel=100, gate=0):
    return Note(step=step, note=note, velocity=vel, gate_ticks=gate)


# ════════════════════════════════════════════════════════════════════
#  TRACK 1 — Drums (Boop kit, event type 0x25)
#  Kick-snare-hat groove with double hat at bar end
#
#  Step:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
#  Note:  K  .  CH .  S  .  CH .  K  .  CH .  S  .  CH CH
#  Comp:  .  .  .  .  .  .  .  .  P  .  .  .  .  .  .  .
# ════════════════════════════════════════════════════════════════════

TRACK1 = [
    n(1,  KICK,  110),
    n(3,  CH,     70),
    n(5,  SNARE, 100),
    n(7,  CH,     70),
    n(9,  KICK,  110),
    n(11, CH,     70),
    n(13, SNARE, 100),
    n(15, CH,     80),   # slight accent
    n(16, CH,     90),   # fill ending — double hat
]

COMP_T1 = StepComponent(step=9, component=ComponentType.PULSE, param=0x01)


# ════════════════════════════════════════════════════════════════════
#  TRACK 3 — Bass (Prism "shoulder", event type 0x21)
#  Walking bass in C minor with quarter-note sustains
#
#  Step:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
#  Note:  C3 .  .  .  G2 .  .  .  Ab2.  .  .  F2 .  .  .
#  Comp:  H  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
#
#  C3=48, G2=43, Ab2=44, F2=41  (i - V - bVI - IV in Cm)
# ════════════════════════════════════════════════════════════════════

TRACK3 = [
    n(1,  48, 100, QUARTER),    # C3  — root, anchored
    n(5,  43,  90, QUARTER),    # G2  — dominant
    n(9,  44,  95, QUARTER),    # Ab2 — bVI color
    n(13, 41,  85, QUARTER),    # F2  — subdominant
]

COMP_T3 = StepComponent(step=1, component=ComponentType.HOLD, param=0x01)


# ════════════════════════════════════════════════════════════════════
#  TRACK 5 — Lead (Dissolve, event type 0x21)
#  Sparse melody over the harmony — 5 notes, lots of space
#
#  Step:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
#  Note:  Eb4.  .  D4 .  C4 .  .  G4 .  .  .  .  .  Eb4.
#  Comp:  .  .  .  .  .  .  .  .  RU .  .  .  .  .  .  .
#
#  Eb4=63, D4=62, C4=60, G4=67  (minor 3rd, 2nd, root, 5th)
# ════════════════════════════════════════════════════════════════════

TRACK5 = [
    n(1,  63,  90, EIGHTH),         # Eb4 — sets the minor tonality
    n(4,  62,  80, EIGHTH),         # D4  — stepwise descent
    n(6,  60,  85, QUARTER),        # C4  — root, longer
    n(9,  67, 100, DOTTED_QTR),     # G4  — peak, RampUp blooms here
    n(15, 63,  75, EIGHTH),         # Eb4 — echo of the opening
]

COMP_T5 = StepComponent(step=9, component=ComponentType.RAMP_UP, param=0x08)


# ════════════════════════════════════════════════════════════════════
#  TRACK 7 — Pad (Axis, event type 0x20)
#  Two sustained tones — harmonic bed underneath
#
#  Step:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
#  Note:  C4 .  .  .  .  .  .  .  G4 .  .  .  .  .  .  .
#  Comp:  H  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
#
#  C4=60 (whole note), G4=67 (half note)
#  Creates open fifth — the harmony floats
# ════════════════════════════════════════════════════════════════════

TRACK7 = [
    n(1, 60, 80, WHOLE),    # C4 — sustain through entire bar
    n(9, 67, 70, HALF),     # G4 — fifth enters halfway, sustains to end
]

COMP_T7 = StepComponent(step=1, component=ComponentType.HOLD, param=0x01)


# ── File generation ─────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    template_data = TEMPLATE.read_bytes()
    template = XYProject.from_bytes(template_data)

    print(f"Template: {TEMPLATE} ({len(template_data)} bytes)")
    print(f"Arrangement: Pulse & Glide — C minor, 1 bar")
    print()

    counts = {
        "T1 Drums":  len(TRACK1),
        "T3 Bass":   len(TRACK3),
        "T5 Lead":   len(TRACK5),
        "T7 Pad":    len(TRACK7),
    }
    for name, count in counts.items():
        print(f"  {name:12s}: {count:3d} notes")
    print(f"  {'Total':12s}: {sum(counts.values()):3d} notes")
    print()

    print("Generating files:")
    print(f"  {'File':30s} {'Size':>6s}  Description")
    print(f"  {'-'*30} {'-'*6}  {'-'*40}")

    # ── Individual tracks (notes + component each) ──────────────────

    for name, ti, notes, comp, desc in [
        ("pulse_glide_t1", 1, TRACK1, COMP_T1,
         "T1 Drums + Pulse(step 9) [SAFE]"),
        ("pulse_glide_t3", 3, TRACK3, COMP_T3,
         "T3 Bass + Hold(step 1) [EXPERIMENTAL]"),
        ("pulse_glide_t5", 5, TRACK5, COMP_T5,
         "T5 Lead + RampUp(step 9) [EXPERIMENTAL]"),
        ("pulse_glide_t7", 7, TRACK7, COMP_T7,
         "T7 Pad + Hold(step 1) [EXPERIMENTAL]"),
    ]:
        proj = append_notes_to_track(template, ti, notes)
        proj = add_step_components(proj, ti, [comp])
        data = proj.to_bytes()
        (OUTPUT_DIR / f"{name}.xy").write_bytes(data)
        print(f"  {name + '.xy':30s} {len(data):6d}B  {desc}")

    # ── Combined: notes only (safe control) ─────────────────────────

    proj_notes = append_notes_to_tracks(template, {
        1: TRACK1, 3: TRACK3, 5: TRACK5, 7: TRACK7,
    })
    data = proj_notes.to_bytes()
    (OUTPUT_DIR / "pulse_glide_notes.xy").write_bytes(data)
    print(f"  {'pulse_glide_notes.xy':30s} {len(data):6d}B  "
          f"All 4 tracks, notes only [SAFE CONTROL]")

    # ── Combined: notes + all components ────────────────────────────

    proj_full = append_notes_to_tracks(template, {
        1: TRACK1, 3: TRACK3, 5: TRACK5, 7: TRACK7,
    })
    for ti, comp in [
        (1, COMP_T1), (3, COMP_T3), (5, COMP_T5), (7, COMP_T7),
    ]:
        proj_full = add_step_components(proj_full, ti, [comp])
    data = proj_full.to_bytes()
    (OUTPUT_DIR / "pulse_glide_full.xy").write_bytes(data)
    print(f"  {'pulse_glide_full.xy':30s} {len(data):6d}B  "
          f"All 4 tracks + all components [FULL]")

    print(f"\nDone. 6 files in {OUTPUT_DIR}/")
    print()
    print("Test order:")
    print("  1. pulse_glide_notes.xy   — if crash → note/preamble bug")
    print("  2. pulse_glide_t1.xy      — T1 Pulse (corpus-verified slot)")
    print("  3. pulse_glide_t3.xy      — T3 Hold (experimental)")
    print("  4. pulse_glide_t5.xy      — T5 RampUp (experimental)")
    print("  5. pulse_glide_t7.xy      — T7 Hold (experimental)")
    print("  6. pulse_glide_full.xy    — everything together")


if __name__ == "__main__":
    main()
