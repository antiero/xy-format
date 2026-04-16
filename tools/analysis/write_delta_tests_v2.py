#!/usr/bin/env python3
"""Minimal delta tests to isolate the ms_t1 crash root cause.

ms_t1 (from write_multistep_tests.py) crashed on device despite matching
the separator formula. The diff showed 27 byte changes from unnamed 118:
  14 bitmask changes + 1 type_id change + 12 separator changes.

This script creates surgical tests to isolate which changes cause the crash.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject, TrackBlock

TEMPLATE = Path("src/one-off-changes-from-default/unnamed 118.xy")
OUTPUT_DIR = Path("output/multistep")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load unnamed 118
orig_data = TEMPLATE.read_bytes()
source = XYProject.from_bytes(orig_data)
source_body = source.tracks[0].body

BLOCK_START = 0x00B1

def rec_offset(step_0based):
    """Body offset of record byte[0] for given step (0-based)."""
    return BLOCK_START + 1 + step_0based * 8

def sep_offset(sep_index):
    """Body offset of separator[i] (between record[i] and record[i+1])."""
    return BLOCK_START + 8 + sep_index * 8


def make_delta(name, desc, changes):
    """Create a test file with specific byte changes to unnamed 118's body."""
    body = bytearray(source_body)
    for offset, value in changes:
        old = body[offset]
        body[offset] = value
        print(f"    [{offset:#06x}] {old:#04x} -> {value:#04x}")

    tracks = list(source.tracks)
    tracks[0] = TrackBlock(
        index=tracks[0].index,
        preamble=tracks[0].preamble,
        body=bytes(body),
    )
    proj = XYProject(pre_track=source.pre_track, tracks=tracks)
    data = proj.to_bytes()
    outpath = OUTPUT_DIR / f"{name}.xy"
    outpath.write_bytes(data)
    print(f"  -> {outpath.name:40s} {len(data):5d}B  {desc}\n")
    return data


print("=" * 70)
print("  Minimal Delta Tests v2 — Isolating ms_t1 Crash")
print("=" * 70)

# First verify unnamed 118 round-trips perfectly
print("\n--- Round-trip check ---")
rt_data = source.to_bytes()
if rt_data == orig_data:
    print("  unnamed 118 round-trips PERFECTLY (byte-identical)")
else:
    diffs = sum(1 for a, b in zip(rt_data, orig_data) if a != b)
    print(f"  WARNING: unnamed 118 round-trip has {diffs} byte differences!")
    if len(rt_data) != len(orig_data):
        print(f"  Length diff: {len(orig_data)} -> {len(rt_data)}")
print()

# Show unnamed 118 block structure for reference
print("--- Unnamed 118 block (steps 4-7 around step 5) ---")
for step in range(3, 7):
    off = rec_offset(step)
    rec = source_body[off:off+7]
    if step < 15:
        sep = source_body[sep_offset(step)]
        print(f"  Step {step+1:2d}: {rec.hex(' ')}  sep={sep:#04x}")
    else:
        print(f"  Step {step+1:2d}: {rec.hex(' ')}")
print()

# ═══ Test M0: Pure identity — round-trip unnamed 118 with zero changes ═══
print("=== Test M0: Identity (round-trip unnamed 118, NO changes) ===")
data_m0 = make_delta("delta_m0_identity", "Pure round-trip, no changes", [])

# ═══ Test M1: type_id + formula seps ONLY (no bitmask changes) ═══
# Formula for Hold*4 + Random + Hold*11:
#   sep[0-2] = 10 (unchanged)
#   sep[3] = 9  (Hold != Random)
#   sep[4] = 8  (Random != Hold)
#   sep[5-14] = 8 (Hold == Hold, hold at 8)
print("=== Test M1: type_id + formula seps (NO bitmask change) ===")
changes_m1 = [
    (rec_offset(4) + 3, 0x05),   # type_id of step 5: Hold -> Random
]
# Change seps 3-14 per formula
formula_seps = [10, 10, 10, 9, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8]
for i in range(15):
    if formula_seps[i] != 10:  # only change what differs
        changes_m1.append((sep_offset(i), formula_seps[i]))
make_delta("delta_m1_type_and_seps", "type_id=0x05 step 5 + formula seps (bitmask=0x02)", changes_m1)

# ═══ Test M2: ALL 14 bitmask changes (no type_id, no sep changes) ═══
# This tests whether mass bitmask changes cause crashes
# (delta_b proved ONE bitmask change works)
print("=== Test M2: All 14 bitmask changes (no type_id or sep changes) ===")
STEP_BITMASK = [1 << (i % 8) for i in range(16)]
changes_m2 = []
for step in range(16):
    new_bm = STEP_BITMASK[step]
    old_bm = 0x02  # unnamed 118 uses 0x02 for all
    if new_bm != old_bm:
        changes_m2.append((rec_offset(step) + 0, new_bm))
make_delta("delta_m2_all_bitmasks", "All bitmasks positional (no type_id/sep changes)", changes_m2)

# ═══ Test M3: type_id change on step 16 + formula seps ═══
# Step 16 is the LAST record — no trailing separator.
# Under my formula: changing step 16 to Random affects sep[14]:
#   sep[14] compares records[14] (Hold) vs records[15] (Random) -> diff -> DEC
#   sep[14] = sep[13] - 1 = 10 - 1 = 9
# All other seps stay at 10 (all Hold before step 16).
print("=== Test M3: type_id step 16 + formula sep[14] (NO bitmask change) ===")
formula_seps_m3 = [10] * 14 + [9]  # only sep[14] changes
changes_m3 = [
    (rec_offset(15) + 3, 0x05),  # type_id of step 16: Hold -> Random
    (sep_offset(14), 9),          # sep[14]: 10 -> 9
]
make_delta("delta_m3_s16_type_and_sep", "type_id=0x05 step 16 + sep[14]=9 (bitmask=0x02)", changes_m3)

# ═══ Test M4: type_id step 16 ONLY (no sep change) — EXPECTED CRASH ═══
# This is equivalent to delta_h from v1, which crashed.
# Including it as a control — if M3 works and M4 crashes, it confirms
# the formula is needed but works.
print("=== Test M4: type_id step 16 ONLY (no sep, no bitmask) — control ===")
make_delta("delta_m4_s16_type_only", "type_id=0x05 step 16 (no sep change) — expect crash", [
    (rec_offset(15) + 3, 0x05),
])

# ═══ Test M5: type_id step 5 + bitmask + formula seps ═══
# Same as ms_t1 but using delta approach (only changing the 3 fields)
# instead of rebuilding the whole block
print("=== Test M5: type_id + bitmask + formula seps (matches ms_t1) ===")
changes_m5 = [
    (rec_offset(4) + 0, 0x10),   # bitmask = positional for step 5
    (rec_offset(4) + 3, 0x05),   # type_id = Random
]
for i in range(15):
    if formula_seps[i] != 10:
        changes_m5.append((sep_offset(i), formula_seps[i]))
make_delta("delta_m5_full_formula", "type_id=0x05 + bitmask=0x10 + formula seps", changes_m5)

# ═══ Test M6: type_id + bitmask of step 5 + seps ALL to 0x09 (delta_j variant) ═══
# This is close to the delta_j "backward formula" test.
# Only seps AFTER the changed step decrement.
print("=== Test M6: type_id + bitmask step 5 + seps after -> 0x09 ===")
changes_m6 = [
    (rec_offset(4) + 0, 0x10),   # bitmask
    (rec_offset(4) + 3, 0x05),   # type_id
]
for i in range(4, 15):
    changes_m6.append((sep_offset(i), 0x09))
make_delta("delta_m6_seps_after_only", "type_id + bitmask step 5 + seps[4-14]=0x09", changes_m6)

# ═══ Test M7: type_id + ALL seps from both sides of changed step ═══
# Alternative: sep decrements only at the transition, both sides
# seps[3]=9 (before Random), sep[4]=9 (after Random), rest stays at 10
print("=== Test M7: type_id + only flanking seps (no bitmask) ===")
make_delta("delta_m7_flanking_seps", "type_id=0x05 step 5 + sep[3]=9 + sep[4]=9", [
    (rec_offset(4) + 3, 0x05),
    (sep_offset(3), 0x09),
    (sep_offset(4), 0x09),
])

# ═══ Summary ═══
print("=" * 70)
print("  TEST PRIORITY")
print("=" * 70)
print("""
  CRITICAL (test first):
    delta_m0_identity       — pure round-trip, should work (validates tooling)
    delta_m1_type_and_seps  — formula with NO bitmask change (isolates formula)

  IMPORTANT (test next):
    delta_m3_s16_type_and_sep — type_id + sep on last step
    delta_m4_s16_type_only    — control: type_id only (expected crash)
    delta_m2_all_bitmasks     — mass bitmask changes only

  EXPLORATORY:
    delta_m5_full_formula     — same as ms_t1 but delta approach
    delta_m6_seps_after_only  — alternative: seps only AFTER changed step
    delta_m7_flanking_seps    — alternative: only 2 flanking seps change
""")
