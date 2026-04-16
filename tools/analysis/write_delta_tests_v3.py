#!/usr/bin/env python3
"""Surgical delta tests v3 — isolate which record bytes trigger crashes.

Previous findings:
  - type_id changes (byte[3] of 7B records) ALWAYS crash
  - Bitmask changes (byte[0] of records) NEVER crash
  - Separator changes alone seem safe

This script probes the remaining untested bytes (byte[1], byte[2], byte[4])
in unnamed 118, and tests type_id changes in unnamed 119's variable-size context.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))

from xy.container import XYProject, TrackBlock
from verify_sep_formula import parse_block_known

TEMPLATE_118 = Path("src/one-off-changes-from-default/unnamed 118.xy")
TEMPLATE_119 = Path("src/one-off-changes-from-default/unnamed 119.xy")
OUTPUT_DIR = Path("output/multistep")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BLOCK_START = 0x00B1


def rec_offset(step_0based):
    """Body offset of record byte[0] for given step (0-based). For unnamed 118 (uniform 7B)."""
    return BLOCK_START + 1 + step_0based * 8


def sep_offset(sep_index):
    """Body offset of separator[i] (between record[i] and record[i+1]). For unnamed 118."""
    return BLOCK_START + 8 + sep_index * 8


# ─────────────────────────────────────────────────────────────────────────────
# Load unnamed 118
# ─────────────────────────────────────────────────────────────────────────────
orig_118_data = TEMPLATE_118.read_bytes()
source_118 = XYProject.from_bytes(orig_118_data)
source_118_body = source_118.tracks[0].body


def make_delta_118(name, desc, changes):
    """Create a test file with specific byte changes to unnamed 118's Track 1 body."""
    body = bytearray(source_118_body)
    print(f"  Changes:")
    for offset, value in changes:
        old = body[offset]
        body[offset] = value
        print(f"    [{offset:#06x}] {old:#04x} -> {value:#04x}")

    tracks = list(source_118.tracks)
    tracks[0] = TrackBlock(
        index=tracks[0].index,
        preamble=tracks[0].preamble,
        body=bytes(body),
    )
    proj = XYProject(pre_track=source_118.pre_track, tracks=tracks)
    data = proj.to_bytes()
    outpath = OUTPUT_DIR / f"{name}.xy"
    outpath.write_bytes(data)
    size_match = "OK" if len(data) == len(orig_118_data) else "SIZE MISMATCH!"
    print(f"  -> {outpath.name:45s} {len(data):5d}B  ({size_match})  {desc}\n")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# Load unnamed 119
# ─────────────────────────────────────────────────────────────────────────────
orig_119_data = TEMPLATE_119.read_bytes()
source_119 = XYProject.from_bytes(orig_119_data)
source_119_body = source_119.tracks[0].body

# Parse unnamed 119's multi-step block to get exact offsets
records_119, seps_119 = parse_block_known(source_119_body)
assert records_119 is not None, "Failed to parse unnamed 119 multi-step block"

# Compute absolute body offsets for each record and separator in unnamed 119
rec_offsets_119 = []  # body offset of byte[0] of each record
sep_offsets_119 = []  # body offset of each separator
pos = 0xB2  # first record starts at body[0xB2] (after 0xE4 header at 0xB1)
for i in range(16):
    type_id, size, raw = records_119[i]
    rec_offsets_119.append(pos)
    if i < 15:
        sep_body_offset = pos + size  # separator is right after the record
        sep_offsets_119.append(sep_body_offset)
        pos = sep_body_offset + 1  # next record starts after separator
    else:
        pos += size


def make_delta_119(name, desc, changes):
    """Create a test file with specific byte changes to unnamed 119's Track 1 body."""
    body = bytearray(source_119_body)
    print(f"  Changes:")
    for offset, value in changes:
        old = body[offset]
        body[offset] = value
        print(f"    [{offset:#06x}] {old:#04x} -> {value:#04x}")

    tracks = list(source_119.tracks)
    tracks[0] = TrackBlock(
        index=tracks[0].index,
        preamble=tracks[0].preamble,
        body=bytes(body),
    )
    proj = XYProject(pre_track=source_119.pre_track, tracks=tracks)
    data = proj.to_bytes()
    outpath = OUTPUT_DIR / f"{name}.xy"
    outpath.write_bytes(data)
    size_match = "OK" if len(data) == len(orig_119_data) else "SIZE MISMATCH!"
    print(f"  -> {outpath.name:45s} {len(data):5d}B  ({size_match})  {desc}\n")
    return data


# ═════════════════════════════════════════════════════════════════════════════
print("=" * 72)
print("  Surgical Delta Tests v3 — Isolating Crash-Causing Bytes")
print("=" * 72)

# ─────────────────────────────────────────────────────────────────────────────
# Round-trip checks
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Round-trip checks ---")
rt_118 = source_118.to_bytes()
if rt_118 == orig_118_data:
    print("  unnamed 118 round-trips PERFECTLY")
else:
    print(f"  WARNING: unnamed 118 round-trip differs by {sum(1 for a,b in zip(rt_118,orig_118_data) if a!=b)} bytes!")

rt_119 = source_119.to_bytes()
if rt_119 == orig_119_data:
    print("  unnamed 119 round-trips PERFECTLY")
else:
    print(f"  WARNING: unnamed 119 round-trip differs by {sum(1 for a,b in zip(rt_119,orig_119_data) if a!=b)} bytes!")

# ─────────────────────────────────────────────────────────────────────────────
# Show unnamed 118 step 5 record for reference
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Unnamed 118: Step 5 record (target for N1-N3) ---")
off = rec_offset(4)
rec = source_118_body[off:off+7]
sep = source_118_body[sep_offset(4)]
print(f"  Step 5 at body[{off:#06x}]: {rec.hex(' ')}  sep={sep}")
print(f"    byte[0]={rec[0]:#04x} (bitmask)")
print(f"    byte[1]={rec[1]:#04x}")
print(f"    byte[2]={rec[2]:#04x}")
print(f"    byte[3]={rec[3]:#04x} (type_id)")
print(f"    byte[4]={rec[4]:#04x} (data)")
print(f"    byte[5]={rec[5]:#04x}")
print(f"    byte[6]={rec[6]:#04x}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# Show unnamed 119 parsed structure for reference
# ─────────────────────────────────────────────────────────────────────────────
print("--- Unnamed 119: Parsed multi-step block ---")
print(f"  {'Step':>4s}  {'Type':>5s}  {'Size':>4s}  {'BodyOff':>7s}  {'Record Hex':<36s}  {'Sep':>3s}  {'SepOff':>7s}")
print(f"  {'─'*80}")
for i in range(16):
    type_id, size, raw = records_119[i]
    type_str = f"0x{type_id:02x}" if type_id is not None else "Pulse"
    sep_str = f"{seps_119[i]:3d}" if i < 15 else "  -"
    sep_off_str = f"{sep_offsets_119[i]:#06x}" if i < 15 else "     -"
    print(f"  {i+1:4d}  {type_str:>5s}  {size:3d}B  {rec_offsets_119[i]:#07x}  {raw.hex(' '):<36s}  {sep_str}  {sep_off_str}")
print()

# ═════════════════════════════════════════════════════════════════════════════
# Tests from unnamed 118 — probing individual bytes
# ═════════════════════════════════════════════════════════════════════════════

# ═══ N1: Change ONLY byte[4] (data byte) of step 5 ═══
print("=== N1: data_byte — Change byte[4] of step 5 from 0x04 to 0x02 ===")
make_delta_118("delta_n1_data_byte", "byte[4] only (data/parameter byte)", [
    (rec_offset(4) + 4, 0x02),
])

# ═══ N2: Change ONLY byte[1] of step 5 ═══
print("=== N2: byte1 — Change byte[1] of step 5 from 0x00 to 0x01 ===")
make_delta_118("delta_n2_byte1", "byte[1] only", [
    (rec_offset(4) + 1, 0x01),
])

# ═══ N3: Change ONLY byte[2] of step 5 ═══
print("=== N3: byte2 — Change byte[2] of step 5 from 0x00 to 0x01 ===")
make_delta_118("delta_n3_byte2", "byte[2] only", [
    (rec_offset(4) + 2, 0x01),
])

# ═════════════════════════════════════════════════════════════════════════════
# Tests from unnamed 119 — type_id changes in variable context
# ═════════════════════════════════════════════════════════════════════════════

# ═══ N4: Change step 7's type_id from 0x05 (Random) to 0x00 (Hold), no sep changes ═══
print("=== N4: 119 type_only — Step 7 type_id 0x05->0x00, NO sep changes ===")
# Verify step 7 (index 6) is what we expect
s7_type, s7_size, s7_raw = records_119[6]
print(f"  Step 7: type_id={s7_type:#04x} size={s7_size}B raw={s7_raw.hex(' ')}")
assert s7_type == 0x05, f"Expected step 7 type_id=0x05, got {s7_type:#04x}"
assert s7_size == 7, f"Expected step 7 size=7, got {s7_size}"

# type_id is byte[3] of the record
type_id_offset_s7 = rec_offsets_119[6] + 3
make_delta_119("delta_n4_119_type_only", "step 7 type_id 0x05->0x00 (no sep change)", [
    (type_id_offset_s7, 0x00),
])

# ═══ N5: Change step 9's type_id 0x06->0x00, WITH formula sep changes ═══
print("=== N5: 119 type_and_seps — Step 9 type_id 0x06->0x00, WITH sep changes ===")
s9_type, s9_size, s9_raw = records_119[8]
print(f"  Step 9: type_id={s9_type:#04x} size={s9_size}B raw={s9_raw.hex(' ')}")
assert s9_type == 0x06, f"Expected step 9 type_id=0x06, got {s9_type:#04x}"

type_id_offset_s9 = rec_offsets_119[8] + 3

# New seps after changing step 9 from Chance to Hold:
# Original seps: [11, 10, 9, 8, 7, 6, 5, 5, 4, 3, 2, 1, 0, 0, 0]
# sep[7] was HOLD at 5 (Chance=Chance at steps 8,9), now DEC to 4 (Chance!=Hold)
# sep[8] was DEC from 5->4, now DEC from 4->3
# sep[9] was DEC from 4->3, now DEC from 3->2
# sep[10] was DEC from 3->2, now DEC from 2->1
# sep[11] was DEC from 2->1, now DEC from 1->0
# sep[12-14] unchanged (already 0)
new_seps_n5 = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 0, 0, 0]

# Build changes: type_id + changed seps
changes_n5 = [(type_id_offset_s9, 0x00)]
for i in range(15):
    if new_seps_n5[i] != seps_119[i]:
        changes_n5.append((sep_offsets_119[i], new_seps_n5[i]))

print(f"  Original seps: {seps_119}")
print(f"  New seps:      {new_seps_n5}")
make_delta_119("delta_n5_119_type_and_seps", "step 9 type_id 0x06->0x00 + formula seps", changes_n5)

# ═══ N6: Change ONLY seps to match N5 formula, WITHOUT changing type_id ═══
print("=== N6: 119 seps_only — Same sep changes as N5, NO type_id change ===")
changes_n6 = []
for i in range(15):
    if new_seps_n5[i] != seps_119[i]:
        changes_n6.append((sep_offsets_119[i], new_seps_n5[i]))

print(f"  Original seps: {seps_119}")
print(f"  New seps:      {new_seps_n5}")
make_delta_119("delta_n6_119_seps_only", "sep changes only (no type_id change)", changes_n6)

# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════
print("=" * 72)
print("  TEST SUMMARY")
print("=" * 72)
print("""
  FROM UNNAMED 118 (uniform Hold steps, all 7B records, all seps=10):
    delta_n1_data_byte    — byte[4] change only (0x04->0x02)
    delta_n2_byte1        — byte[1] change only (0x00->0x01)
    delta_n3_byte2        — byte[2] change only (0x00->0x01)

  FROM UNNAMED 119 (16 different step types, variable records):
    delta_n4_119_type_only     — step 7 type_id 0x05->0x00, NO sep changes
    delta_n5_119_type_and_seps — step 9 type_id 0x06->0x00 + formula seps
    delta_n6_119_seps_only     — sep changes matching N5 formula, NO type_id

  HYPOTHESES:
    If N1-N3 all WORK: only type_id (byte[3]) triggers crashes
    If N1 crashes: data byte is also protected
    If N2/N3 crash: padding bytes are also protected
    If N4 crashes but N5 works: formula is required
    If N4+N5 both crash: type_id changes are fundamentally blocked
    If N6 works: sep-only changes are safe in unnamed 119 too
""")
