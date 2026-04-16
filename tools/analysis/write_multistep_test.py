#!/usr/bin/env python3
"""Multi-step step component test files — round 2.

Round 1 results: all-Hold works (incl. varied params), mixed types crash.
Hypothesis: the separator byte encodes the type of the NEXT record.
  - 0x0A = repeat of the first record's type (Hold in unnamed 118)
  - 0x0B - type_id = introduces a new type (per unnamed 119)

Round 2 tests: use CORRECT separators for mixed-type blocks.

Usage:
    python tools/write_multistep_test.py
"""

import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject, TrackBlock
from xy.note_events import Note, STEP_TICKS, build_event, event_type_for_track

TEMPLATE = Path("src/one-off-changes-from-default/unnamed 1.xy")
OUTPUT_DIR = Path("output/multistep")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Multi-step block builder ───────────────────────────────────────────

# For Drum engine (0x03) on T1:
#   Sentinel table in body07 starts at body07[0x0020]
#   Entry 45 = body07[0x00A7] = body[0x00B1] (activated)
#   Alloc byte = body07[0x00BF] = body[0x00C9] (activated)
#   Replace region: body[0x00B1:0x00CA] = 25 bytes
#   Replace with: block + 7*FF0000 + 0x06 alloc byte
MULTI_STEP_START = 0x00B1  # body offset in activated T1 body
MULTI_STEP_END = 0x00CA    # exclusive
MULTI_STEP_ALLOC = 0x06    # alloc byte value for multi-step


def _activate_body(body: bytes) -> bytearray:
    """Flip type byte 0x05->0x07 and remove 2-byte padding."""
    buf = bytearray(body)
    if buf[9] == 0x05:
        buf[9] = 0x07
        del buf[10:12]
    return buf


# ── Record builders ────────────────────────────────────────────────────
# Multi-step record format:
#   7B standard: [bitmask] [00] [00] [type_id] [param] [00] [00]
#   5B Pulse:    [0x01]    [00] [param] [00] [00]
#
# Multi-step type_ids (different from single-step!):
#   0x00=Hold, 0x01=Multiply, 0x02=Velocity, 0x03=RampUp, 0x04=RampDown,
#   0x05=Random, 0x06=Port+Bend, 0x07=Tonality+Jump, 0x08=Parameter,
#   0x09=Conditional, 0x0A=Trigger
#
# Separator before a NEW type = 0x0B - type_id (byte3 in record)
# Separator for REPEAT of already-seen type = 0x0A (hypothesis)
# Separator for Pulse (no type_id) = 0x00 (hypothesis)

def hold_record(param: int = 0x04) -> bytes:
    return bytes([0x02, 0x00, 0x00, 0x00, param & 0xFF, 0x00, 0x00])

def pulse_record(param: int = 0x04) -> bytes:
    return bytes([0x01, 0x00, param & 0xFF, 0x00, 0x00])

def random_record(param: int = 0x04) -> bytes:
    return bytes([0x40, 0x00, 0x00, 0x05, param & 0xFF, 0x00, 0x00])

def velocity_record(param: int = 0x05) -> bytes:
    return bytes([0x08, 0x00, 0x00, 0x02, param & 0xFF, 0x00, 0x00])

def multiply_record(param: int = 0x04) -> bytes:
    return bytes([0x04, 0x00, 0x00, 0x01, param & 0xFF, 0x00, 0x00])

def rampup_record(param: int = 0x04) -> bytes:
    return bytes([0x10, 0x00, 0x00, 0x03, param & 0xFF, 0x00, 0x00])

def rampdown_record(param: int = 0x04) -> bytes:
    return bytes([0x20, 0x00, 0x00, 0x04, param & 0xFF, 0x00, 0x00])

def portamento_record(param: int = 0x04) -> bytes:
    return bytes([0x80, 0x00, 0x00, 0x06, param & 0xFF, 0x00, 0x00])


# Separator lookup: type_id → new-type separator
SEP_FOR_TYPE = {
    0x00: 0x0B,  # Hold
    0x01: 0x0A,  # Multiply
    0x02: 0x09,  # Velocity
    0x03: 0x08,  # RampUp
    0x04: 0x07,  # RampDown
    0x05: 0x06,  # Random
    0x06: 0x05,  # Portamento/Bend
    0x07: 0x04,  # Tonality/Jump
    0x08: 0x03,  # Parameter (adjusted from byte3)
    0x09: 0x02,  # Conditional
    0x0A: 0x01,  # Trigger
}
SEP_PULSE = 0x00   # Pulse (5B compact, no type_id)
SEP_REPEAT = 0x0A  # Repeat of already-seen type


def sep_for_record(rec: bytes, seen_type_ids: set, first_rec_type_id: int | None) -> int:
    """Compute separator for a record given what types have been seen."""
    if len(rec) == 5:
        # Pulse compact format
        if 'pulse' in seen_type_ids:
            return SEP_REPEAT  # or 0x00?
        return SEP_PULSE

    # Standard 7B+ record: type_id at byte[3]
    type_id = rec[3]

    if type_id == first_rec_type_id:
        # Same type as step 1 (the "default" type) → always 0x0A
        return SEP_REPEAT
    elif type_id in seen_type_ids:
        # Previously introduced type → use its original separator
        return SEP_FOR_TYPE.get(type_id, SEP_REPEAT)
    else:
        # New type introduction
        return SEP_FOR_TYPE.get(type_id, SEP_REPEAT)


def build_multi_step_block(records: list[bytes]) -> bytes:
    """Build a multi-step block from 16 records with auto-computed separators."""
    assert len(records) == 16

    block = bytearray()
    block.append(0xE4)  # header byte

    # Step 1: no separator
    block.extend(records[0])
    first_type_id = records[0][3] if len(records[0]) >= 4 else None

    seen_type_ids = set()
    if first_type_id is not None:
        seen_type_ids.add(first_type_id)
    if len(records[0]) == 5:
        seen_type_ids.add('pulse')

    for i in range(1, 16):
        rec = records[i]
        sep = sep_for_record(rec, seen_type_ids, first_type_id)
        block.append(sep)
        block.extend(rec)

        # Track seen types
        if len(rec) == 5:
            seen_type_ids.add('pulse')
        elif len(rec) >= 4:
            seen_type_ids.add(rec[3])

    return bytes(block)


def build_multi_step_block_raw(records: list[bytes], separators: list[int]) -> bytes:
    """Build with explicit separators (for testing specific values)."""
    assert len(records) == 16
    assert len(separators) == 15
    block = bytearray([0xE4])
    block.extend(records[0])
    for i in range(15):
        block.append(separators[i])
        block.extend(records[i + 1])
    return bytes(block)


def insert_multi_step(body: bytearray, block: bytes) -> bytearray:
    """Insert a multi-step block into an activated T1 Drum body."""
    replacement = block + b'\xff\x00\x00' * 7 + bytes([MULTI_STEP_ALLOC])
    body[MULTI_STEP_START:MULTI_STEP_END] = replacement
    return body


# ── Note helpers ───────────────────────────────────────────────────────

KICK, SNARE, CH, OH = 48, 50, 56, 58

def n(step, note, vel=100, gate=0):
    return Note(step=step, note=note, velocity=vel, gate_ticks=gate)

# 16-step drum pattern
DRUM_PATTERN = [
    n(1,  KICK,  110), n(2,  CH,   60), n(3,  CH,   65), n(4,  CH,   60),
    n(5,  SNARE, 105), n(6,  CH,   60), n(7,  CH,   65), n(8,  CH,   60),
    n(9,  KICK,  108), n(10, CH,   60), n(11, CH,   65), n(12, CH,   60),
    n(13, SNARE, 100), n(14, CH,   60), n(15, CH,   65), n(16, OH,   80),
]


# ── Project builder ───────────────────────────────────────────────────

baseline = XYProject.from_bytes(TEMPLATE.read_bytes())


def _build_project(body: bytearray, notes=None):
    tracks = list(baseline.tracks)
    preamble = tracks[0].preamble
    if notes:
        etype = event_type_for_track(1)
        event_blob = build_event(notes, event_type=etype)
        body.extend(event_blob)
        bars = math.ceil(max(n.step for n in notes) / 16)
        preamble = bytearray(preamble)
        preamble[2] = bars * 16
        preamble = bytes(preamble)

    tracks[0] = TrackBlock(index=tracks[0].index, preamble=preamble, body=bytes(body))

    if notes:
        t2 = tracks[1]
        t2_pre = bytearray(t2.preamble)
        t2_pre[0] = 0x64
        tracks[1] = TrackBlock(index=t2.index, preamble=bytes(t2_pre), body=t2.body)

    return XYProject(pre_track=baseline.pre_track, tracks=tracks)


def make_body_with_block(records):
    """Activate T1 body and insert multi-step block."""
    body = _activate_body(baseline.tracks[0].body)
    block = build_multi_step_block(records)
    insert_multi_step(body, block)
    return body


# ── Build variants ────────────────────────────────────────────────────

print("=== Multi-Step Tests — Round 2 (corrected separators) ===\n")
variants = []

def emit(name, desc, build_fn):
    proj = build_fn()
    data = proj.to_bytes()
    (OUTPUT_DIR / f"{name}.xy").write_bytes(data)
    print(f"  {name + '.xy':35s} {len(data):5d}B  {desc}")
    variants.append(name)


# ── Round 1 survivors (keep for reference) ────────────────────────────

# 1. All-Hold + varied params (confirmed working)
def build_varied():
    records = []
    for step in range(16):
        param = 0x08 if (step % 4 == 0) else 0x01
        records.append(hold_record(param))
    body = _activate_body(baseline.tracks[0].body)
    block = build_multi_step_block_raw(records, [0x0A] * 15)
    insert_multi_step(body, block)
    return _build_project(body, notes=DRUM_PATTERN)

emit("ms_varied_params", "Hold varied params [CONFIRMED WORKING]", build_varied)


# ── Round 2: corrected separators for mixed types ─────────────────────

# 2. Random on step 5, auto-computed separators
def build_random_s5_v2():
    records = [hold_record()] * 16
    records[4] = random_record(0x03)  # step 5
    body = make_body_with_block(records)
    return _build_project(body, notes=DRUM_PATTERN)

emit("ms_random_s5_v2", "Random(s5) auto-sep [KEY TEST]", build_random_s5_v2)


# 3. Random on step 5, explicit seps: 0x06 for Random, 0x0B for return-to-Hold
def build_random_s5_v3():
    records = [hold_record()] * 16
    records[4] = random_record(0x03)
    seps = [0x0A] * 15
    seps[3] = 0x06  # before step 5 (Random)
    seps[4] = 0x0B  # before step 6 (Hold, reintroduced)
    body = _activate_body(baseline.tracks[0].body)
    block = build_multi_step_block_raw(records, seps)
    insert_multi_step(body, block)
    return _build_project(body, notes=DRUM_PATTERN)

emit("ms_random_s5_v3", "Random(s5) sep=06, retHold sep=0B", build_random_s5_v3)


# 4. Random on step 5, explicit: 0x06 for Random, 0x0A for return-to-Hold
def build_random_s5_v4():
    records = [hold_record()] * 16
    records[4] = random_record(0x03)
    seps = [0x0A] * 15
    seps[3] = 0x06  # before step 5 (Random)
    # seps[4] stays 0x0A for return to Hold
    body = _activate_body(baseline.tracks[0].body)
    block = build_multi_step_block_raw(records, seps)
    insert_multi_step(body, block)
    return _build_project(body, notes=DRUM_PATTERN)

emit("ms_random_s5_v4", "Random(s5) sep=06, retHold sep=0A", build_random_s5_v4)


# 5. Random on step 13 with auto separators
def build_random_s13_v2():
    records = [hold_record()] * 16
    records[12] = random_record(0x03)  # step 13
    body = make_body_with_block(records)
    return _build_project(body, notes=DRUM_PATTERN)

emit("ms_random_s13_v2", "Random(s13) auto-sep", build_random_s13_v2)


# 6. TWO Randoms: steps 5 and 13
def build_random_dual():
    records = [hold_record()] * 16
    records[4] = random_record(0x03)   # step 5
    records[12] = random_record(0x03)  # step 13
    body = make_body_with_block(records)
    return _build_project(body, notes=DRUM_PATTERN)

emit("ms_random_dual", "Random(s5+s13) auto-sep", build_random_dual)


# 7. Velocity on step 5 (different type than Random, still 7B)
def build_velocity_s5():
    records = [hold_record()] * 16
    records[4] = velocity_record(0x05)  # step 5
    body = make_body_with_block(records)
    return _build_project(body, notes=DRUM_PATTERN)

emit("ms_velocity_s5", "Velocity(s5) auto-sep", build_velocity_s5)


# 8. Multiple different types: Hold(1-4), Random(5-8), Hold(9-16)
def build_random_block():
    records = [hold_record()] * 16
    for i in range(4, 8):
        records[i] = random_record(0x03)
    body = make_body_with_block(records)
    return _build_project(body, notes=DRUM_PATTERN)

emit("ms_random_block", "Random(s5-s8) + Hold(rest) auto-sep", build_random_block)


# ── Print debug: show block separators for each variant ────────────────

print("\n--- Separator debug ---")
for name in ["ms_random_s5_v2", "ms_random_s5_v3", "ms_random_s5_v4"]:
    data = (OUTPUT_DIR / f"{name}.xy").read_bytes()
    proj = XYProject.from_bytes(data)
    body = proj.tracks[0].body
    body07 = body[0x0A:]
    block_start = 0x00A7
    # Find block extent
    pos = block_start + 1
    # Read 16 records, print separators
    seps_found = []
    rec_pos = block_start + 1  # skip E4
    # For a quick peek, just show the first 30 bytes
    snippet = body07[block_start:block_start+40]
    print(f"  {name}: {snippet.hex(' ')}")


# ── Test plan ──────────────────────────────────────────────────────────

print(f"""
=== Test plan (round 2) ===

  Phase 1: Confirmed working
    1. ms_varied_params   — all-Hold varied params [CONFIRMED]

  Phase 2: Corrected separators for Random
    2. ms_random_s5_v2    — Random(s5) auto-computed sep (0x06 before Random, 0x0A after)
    3. ms_random_s5_v3    — Random(s5) sep=0x06, return-to-Hold sep=0x0B
    4. ms_random_s5_v4    — Random(s5) sep=0x06, return-to-Hold sep=0x0A
       → Test 2-4 to find which separator pattern works for mixed types

  Phase 3: More types and positions (only if phase 2 works)
    5. ms_random_s13_v2   — Random on step 13 (second half of bar)
    6. ms_random_dual     — Random on steps 5+13 (both halves)
    7. ms_velocity_s5     — Velocity on step 5 (different type_id)
    8. ms_random_block    — Random on steps 5-8 (contiguous block)

Total: {len(variants)} files in output/multistep/""")
