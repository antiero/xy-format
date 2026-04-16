#!/usr/bin/env python3
"""Generate diagnostic 9-pattern files to isolate crash cause.

Creates 3 files with increasing complexity, all using the n110
topology (8 tracks × 9 patterns):

  diag_A_minimal.xy  — 1 note/pattern, 1 bar (matches n110 structure)
  diag_B_4bar_t1.xy  — T1 has 4-bar drum patterns, others 1 note
  diag_C_full_4bar.xy — All tracks have 4-bar patterns with real notes

If A works → builder structure is correct
If A crashes → fundamental builder issue
If B works → 4-bar drum patterns are fine
If B crashes → 4-bar or body-size issue
If C works → our music content is fine (bug is elsewhere)
If C crashes → complex content problem
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject
from xy.note_events import Note, STEP_TICKS
from xy.project_builder import build_multi_pattern_project

BASELINE_PATH = "src/one-off-changes-from-default/unnamed 1.xy"


def one_note(note: int = 60, vel: int = 100) -> List[Note]:
    """Single note at step 1."""
    if note == vel:
        vel = vel + 1 if vel < 127 else vel - 1
    return [Note(step=1, note=note, velocity=vel, tick_offset=0, gate_ticks=STEP_TICKS)]


def drum_4bar() -> List[Note]:
    """Simple 4-bar kick/snare/hat pattern."""
    notes = []
    for bar in range(4):
        base_step = bar * 16 + 1
        for beat in range(4):
            step = base_step + beat * 4
            # Kick on 1,3; Snare on 2,4
            if beat % 2 == 0:
                notes.append(Note(step=step, note=48, velocity=100,
                                  tick_offset=0, gate_ticks=STEP_TICKS))
            else:
                notes.append(Note(step=step, note=50, velocity=90,
                                  tick_offset=0, gate_ticks=STEP_TICKS))
            # Closed hat on every beat
            notes.append(Note(step=step, note=56, velocity=70,
                              tick_offset=0, gate_ticks=STEP_TICKS))
    return notes


def synth_4bar(base_note: int = 60) -> List[Note]:
    """Simple 4-bar synth melody: quarter notes, ascending."""
    notes = []
    scale = [0, 2, 4, 5, 7, 9, 11, 12]  # major scale
    idx = 0
    for bar in range(4):
        base_step = bar * 16 + 1
        for beat in range(4):
            step = base_step + beat * 4
            note_num = base_note + scale[idx % len(scale)]
            vel = 80
            if note_num == vel:
                vel = 81
            notes.append(Note(step=step, note=note_num, velocity=vel,
                              tick_offset=0, gate_ticks=STEP_TICKS * 3))
            idx += 1
    return notes


def build_and_write(
    track_patterns: Dict[int, List[Optional[List[Note]]]],
    output_path: str,
    label: str,
) -> None:
    proj = XYProject.from_bytes(Path(BASELINE_PATH).read_bytes())

    result = build_multi_pattern_project(
        proj, track_patterns, descriptor_strategy="strict",
    )

    data = result.to_bytes()
    rt = XYProject.from_bytes(data)
    assert rt.to_bytes() == data, f"{label}: Round-trip FAILED!"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_bytes(data)

    # Summary
    total = 0
    for ti in range(1, 9):
        pats = track_patterns.get(ti, [])
        counts = [len(p) if p else 0 for p in pats]
        active = sum(1 for c in counts if c > 0)
        total += sum(counts)
        print(f"  T{ti}: {active}/9 pat, notes={counts}")
    print(f"  Total: {total} notes, {len(data)} bytes")
    print(f"  Round-trip: PASS")
    print()


def main():
    # ── Test A: Minimal (matches n110 structure) ──────────────────────
    print("=== diag_A_minimal.xy ===")
    print("  1 note per pattern on all 8 tracks, 1-bar patterns")

    # Drum notes for T1/T2, synth notes for T3-T8
    drum_notes = {1: 48, 2: 48}  # kick
    synth_notes = {3: 60, 4: 64, 5: 67, 6: 72, 7: 60, 8: 64}

    tp_a: Dict[int, List[Optional[List[Note]]]] = {}
    for ti in range(1, 9):
        patterns = []
        for _ in range(9):
            note = drum_notes.get(ti, synth_notes.get(ti, 60))
            patterns.append(one_note(note, 100))
        tp_a[ti] = patterns

    build_and_write(tp_a, "output/diag_A_minimal.xy", "diag_A")

    # ── Test B: 4-bar drums on T1, minimal elsewhere ─────────────────
    print("=== diag_B_4bar_t1.xy ===")
    print("  T1 has 4-bar drum patterns, others 1 note")

    tp_b: Dict[int, List[Optional[List[Note]]]] = {}
    for ti in range(1, 9):
        patterns = []
        for _ in range(9):
            if ti == 1:
                patterns.append(drum_4bar())
            else:
                note = drum_notes.get(ti, synth_notes.get(ti, 60))
                patterns.append(one_note(note, 100))
        tp_b[ti] = patterns

    build_and_write(tp_b, "output/diag_B_4bar_t1.xy", "diag_B")

    # ── Test C: 4-bar patterns on all tracks ──────────────────────────
    print("=== diag_C_full_4bar.xy ===")
    print("  All tracks have 4-bar patterns with real notes")

    tp_c: Dict[int, List[Optional[List[Note]]]] = {}
    for ti in range(1, 9):
        patterns = []
        for pat_idx in range(9):
            if ti <= 2:
                patterns.append(drum_4bar())
            else:
                # Offset base note per track and pattern for variety
                base = 48 + (ti - 3) * 2 + pat_idx
                patterns.append(synth_4bar(base))
        tp_c[ti] = patterns

    build_and_write(tp_c, "output/diag_C_full_4bar.xy", "diag_C")

    print("Done! Test files:")
    print("  output/diag_A_minimal.xy  — minimal 1-note patterns")
    print("  output/diag_B_4bar_t1.xy  — 4-bar drums, minimal synths")
    print("  output/diag_C_full_4bar.xy — all tracks 4-bar")


if __name__ == "__main__":
    main()
