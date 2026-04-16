#!/usr/bin/env python3
"""Build Bring Me To Life v2: 9 patterns (bars 4-39), 7 active tracks.

Track mapping chosen for OP-XY default engine sounds:
  T1 (Drum/boop)       ← MIDI Trk 16 ch9   drums
  T2 (Drum/phase)      ← blank
  T3 (Prism/bass)      ← MIDI Trk 15 ch15  electric bass (finger)
  T4 (EPiano/piano)    ← MIDI Trk  5 ch4   acoustic grand piano
  T5 (Dissolve/lead)   ← MIDI Trk 14 ch14  overdriven guitar riff
  T6 (Hardsync/melody) ← MIDI Trk  1 ch0   melodic lead (tenor sax GM)
  T7 (Axis/pad)        ← MIDI Trk  6 ch5   string ensemble
  T8 (Multisampler)    ← MIDI Trk  9 ch8   warm pad

Song structure covered (bars 4-39 = 9 patterns × 4 bars):
  P1 (bars  4-7):  piano intro, timpani rumble
  P2 (bars  8-11): piano continues, building
  P3 (bars 12-15): guitar + bass + drums ENTER — the iconic moment
  P4 (bars 16-19): verse 1 full band
  P5 (bars 20-23): verse continues
  P6 (bars 24-27): pre-chorus build
  P7 (bars 28-31): pre-chorus peak
  P8 (bars 32-35): CHORUS — full energy
  P9 (bars 36-39): chorus continues
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mido

from xy.container import XYProject
from xy.note_events import Note, STEP_TICKS
from xy.project_builder import build_multi_pattern_project

# ── Config ────────────────────────────────────────────────────────────

MIDI_PATH = "/Users/kevinmorrill/Desktop/cover wavs/millionsongs/Evanescence - Bring Me To Life (4).mid"
BASELINE_PATH = "src/one-off-changes-from-default/unnamed 1.xy"
OUTPUT_PATH = "output/bring_me_to_life_v2.xy"

START_BAR = 4
NUM_PATTERNS = 9
BARS_PER_PATTERN = 4
MAX_NOTES_PER_PATTERN = 120

# MIDI track index → (OP-XY track 1-based, is_drum)
TRACK_MAP = {
    16: (1, True),   # drums
    15: (3, False),  # bass
     5: (4, False),  # piano
    14: (5, False),  # guitar riff → lead synth
     1: (6, False),  # melody → hardsync
     6: (7, False),  # strings → pad
     9: (8, False),  # warm pad
}

# ── GM Drum → OP-XY mapping ──────────────────────────────────────────

GM_TO_OPXY_DRUM = {
    35: 48, 36: 48,  # Bass Drum → Kick 1
    37: 52,          # Side Stick → Rim
    38: 50, 40: 51,  # Snare → Snare 1/2
    39: 53,          # Clap
    41: 60, 43: 61, 45: 62, 47: 63, 48: 64, 50: 65,  # Toms
    42: 56,          # Closed HH → CH Hat 1
    44: 57,          # Pedal HH → CH Hat 2
    46: 58,          # Open HH → OH Hat
    49: 54, 57: 54,  # Crash
    51: 55,          # Ride
    52: 66, 53: 67, 54: 57, 55: 68, 56: 69,  # Misc percussion
}


def extract_notes(mid: mido.MidiFile) -> Dict[int, list]:
    """Extract notes from all MIDI tracks."""
    track_notes = {}
    for i, track in enumerate(mid.tracks):
        abs_tick = 0
        pending = {}
        notes = []
        for msg in track:
            abs_tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                pending[(msg.channel, msg.note)] = (abs_tick, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in pending:
                    onset, vel = pending.pop(key)
                    gate = abs_tick - onset
                    notes.append((onset, msg.note, vel, max(gate, 1), msg.channel))
        if notes:
            track_notes[i] = sorted(notes, key=lambda n: n[0])
    return track_notes


def convert_window(
    notes: list,
    tpb: int,
    start_bar: int,
    is_drum: bool,
) -> List[Note]:
    """Convert MIDI notes in a 4-bar window to OP-XY Note objects."""
    tpbar = tpb * 4
    lo = start_bar * tpbar
    hi = (start_bar + BARS_PER_PATTERN) * tpbar
    scale = 1920.0 / tpb

    xy_notes = []
    for onset, note, vel, gate, _ch in notes:
        if onset < lo or onset >= hi:
            continue

        midi_tick = onset - lo
        xy_tick = round(midi_tick * scale)
        xy_tick = round(xy_tick / STEP_TICKS) * STEP_TICKS  # quantize

        step = xy_tick // STEP_TICKS + 1
        if step < 1 or step > 64:
            continue

        xy_gate = max(STEP_TICKS, round(gate * scale / STEP_TICKS) * STEP_TICKS)

        if is_drum:
            note_num = GM_TO_OPXY_DRUM.get(note, max(48, min(71, note)))
        else:
            note_num = note

        v = max(1, min(127, vel))

        xy_notes.append(Note(
            step=step,
            note=note_num,
            velocity=v,
            tick_offset=0,
            gate_ticks=xy_gate,
        ))

    if not xy_notes:
        return []

    xy_notes.sort(key=lambda n: (n.step - 1) * STEP_TICKS + n.tick_offset)

    # Ensure first note is at step 1, tick 0 (OP-XY format requirement)
    first = xy_notes[0]
    if first.step != 1 or first.tick_offset != 0:
        placeholder_note = first.note
        placeholder_vel = 1
        if placeholder_note == placeholder_vel:
            placeholder_vel = 2
        xy_notes.insert(0, Note(
            step=1, note=placeholder_note, velocity=placeholder_vel,
            tick_offset=0, gate_ticks=STEP_TICKS,
        ))

    return xy_notes[:MAX_NOTES_PER_PATTERN]


def main():
    mid = mido.MidiFile(MIDI_PATH)
    tpb = mid.ticks_per_beat

    # Get tempo
    bpm = 120.0
    for msg in mid.tracks[0]:
        if msg.type == "set_tempo":
            bpm = mido.tempo2bpm(msg.tempo)
            break

    print(f"MIDI: {Path(MIDI_PATH).name}")
    print(f"Tempo: {bpm:.1f} BPM, tpb: {tpb}")
    print(f"Window: bars {START_BAR}-{START_BAR + NUM_PATTERNS * BARS_PER_PATTERN - 1} "
          f"({NUM_PATTERNS} patterns)")
    print()

    # Extract all MIDI notes
    all_notes = extract_notes(mid)

    # Build per-track, per-pattern note lists
    track_patterns: Dict[int, List[Optional[List[Note]]]] = {}
    total_notes = 0

    for opxy_trk in range(1, 9):
        patterns: List[Optional[List[Note]]] = []

        # Find MIDI track for this OP-XY track
        midi_trk = None
        is_drum = False
        for mt, (ot, dr) in TRACK_MAP.items():
            if ot == opxy_trk:
                midi_trk = mt
                is_drum = dr
                break

        for pat_idx in range(NUM_PATTERNS):
            pat_start = START_BAR + pat_idx * BARS_PER_PATTERN
            if midi_trk is not None and midi_trk in all_notes:
                xy_notes = convert_window(
                    all_notes[midi_trk], tpb, pat_start, is_drum,
                )
                if xy_notes:
                    patterns.append(xy_notes)
                    total_notes += len(xy_notes)
                    continue
            patterns.append(None)

        track_patterns[opxy_trk] = patterns

    # Fill blank patterns with placeholder notes so all entries are
    # activated (type 0x07).  n110 shows the firmware activates ALL
    # track bodies during multi-pattern setup — blank type-0x05 entries
    # break the preamble 0x64 cascade and crash the device.
    for opxy_trk in range(1, 9):
        pats = track_patterns[opxy_trk]
        is_drum = opxy_trk <= 2
        for i, p in enumerate(pats):
            if p is None:
                note_num = 48 if is_drum else 60
                vel = 2 if note_num == 1 else 1  # avoid note==vel
                pats[i] = [Note(
                    step=1, note=note_num, velocity=vel,
                    tick_offset=0, gate_ticks=STEP_TICKS,
                )]
                total_notes += 1

    # Print summary
    track_names = {1: "Drum", 2: "Drum(blank)", 3: "Bass", 4: "Piano",
                   5: "GuitarRiff", 6: "Melody", 7: "Strings", 8: "Pad"}
    for opxy_trk in range(1, 9):
        pats = track_patterns[opxy_trk]
        active = sum(1 for p in pats if p)
        if active:
            counts = [len(p) if p else 0 for p in pats]
            print(f"  T{opxy_trk} {track_names[opxy_trk]:>12}: "
                  f"{active}/{NUM_PATTERNS} patterns, notes/pat: {counts}")
        else:
            print(f"  T{opxy_trk} {track_names[opxy_trk]:>12}: (blank)")

    print(f"\nTotal notes: {total_notes}")

    # Load baseline
    proj = XYProject.from_bytes(Path(BASELINE_PATH).read_bytes())

    # Set tempo
    tempo_tenths = round(bpm * 10)
    pre_track = bytearray(proj.pre_track)
    pre_track[0x08:0x0A] = struct.pack("<H", tempo_tenths)
    proj = XYProject(pre_track=bytes(pre_track), tracks=proj.tracks)

    # Build multi-pattern project
    result = build_multi_pattern_project(
        proj, track_patterns, descriptor_strategy="strict",
    )

    # Verify round-trip
    data = result.to_bytes()
    rt = XYProject.from_bytes(data)
    assert rt.to_bytes() == data, "Round-trip FAILED!"

    # Write output
    Path(OUTPUT_PATH).write_bytes(data)
    print(f"\nWrote {len(data)} bytes → {OUTPUT_PATH}")
    print("Round-trip: PASS")


if __name__ == "__main__":
    main()
