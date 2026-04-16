#!/usr/bin/env python3
"""Multi-step DELTA tests — minimal single-byte changes from known-working block.

Starting from byte-perfect unnamed 118 (all-Hold, all sep=0x0A), we change
ONE field at a time to isolate what causes firmware crashes.

Tests:
  A. Change ONLY type_id of step 5 record (0x00 → 0x05)
  B. Change ONLY bitmask of step 5 record (0x02 → 0x40)
  C. Change both type_id AND bitmask of step 5
  D. Change type_id, bitmask, AND separator before step 5
  E. Change ONLY the separator before step 5 (0x0A → 0x06)
  F. Change ONLY type_id of step 2 record (position right after step 1)
  G. Change ONLY bitmask of step 2 record
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject, TrackBlock
from xy.note_events import Note, STEP_TICKS, build_event, event_type_for_track

TEMPLATE = Path("src/one-off-changes-from-default/unnamed 118.xy")
OUTPUT_DIR = Path("output/multistep")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load unnamed 118 — the known-working all-Hold multi-step project
source = XYProject.from_bytes(TEMPLATE.read_bytes())
source_body = source.tracks[0].body  # already type-07, already activated

# Multi-step block location in the body
BLOCK_START = 0x00B1

# Parse the block structure:
# E4 [rec1(7B)] sep [rec2(7B)] sep ... [rec16(7B)]
# = 1 + 16*7 + 15 = 128 bytes
# Record offsets (from BLOCK_START):
#   rec[0] at +1, rec[1] at +9, rec[2] at +17, ... rec[n] at +1 + n*8
# Separator offsets:
#   sep[0] at +8, sep[1] at +16, ... sep[n] at +8 + n*8

def rec_offset(step_0based):
    """Body offset of start of record for given step (0-based)."""
    return BLOCK_START + 1 + step_0based * 8

def sep_offset(sep_index):
    """Body offset of separator BEFORE record[sep_index+1].
    sep[0] is between rec[0] and rec[1], etc."""
    return BLOCK_START + 8 + sep_index * 8


def make_delta(name, desc, changes):
    """Create a test file from unnamed 118 with specific byte changes.

    changes: list of (body_offset, new_value) tuples
    """
    body = bytearray(source_body)
    for offset, value in changes:
        old = body[offset]
        body[offset] = value
        print(f"    [{offset:#06x}] {old:#04x} → {value:#04x}")

    # Rebuild project with modified body
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
    print(f"  → {outpath.name:35s} {len(data):5d}B  {desc}\n")


print("=== Multi-Step DELTA Tests (single-byte changes from unnamed 118) ===\n")

# Verify baseline structure
print("Baseline (unnamed 118):")
for step in range(16):
    off = rec_offset(step)
    rec = source_body[off:off+7]
    if step < 15:
        sep = source_body[sep_offset(step)]
        print(f"  Step {step+1:2d}: {rec.hex(' ')}  sep={sep:#04x}")
    else:
        print(f"  Step {step+1:2d}: {rec.hex(' ')}")
print()

# ── Test A: Change ONLY type_id of step 5 (byte[3] of record) ──────
# Record layout: [bitmask][00][00][type_id][param][00][00]
# Hold type_id = 0x00, Random type_id = 0x05
print("Test A: Change ONLY type_id of step 5 (0x00 → 0x05)")
make_delta("delta_a_typeid_only", "type_id=0x05 on step 5 (bitmask stays Hold=0x02)", [
    (rec_offset(4) + 3, 0x05),  # type_id byte of step 5 record
])

# ── Test B: Change ONLY bitmask of step 5 ──────────────────────────
print("Test B: Change ONLY bitmask of step 5 (0x02 → 0x40)")
make_delta("delta_b_bitmask_only", "bitmask=0x40 on step 5 (type_id stays Hold=0x00)", [
    (rec_offset(4) + 0, 0x40),  # bitmask byte of step 5 record
])

# ── Test C: Change both type_id AND bitmask of step 5 ──────────────
print("Test C: Change type_id AND bitmask of step 5")
make_delta("delta_c_type_and_mask", "type_id=0x05 + bitmask=0x40 on step 5 (full Random record)", [
    (rec_offset(4) + 0, 0x40),  # bitmask
    (rec_offset(4) + 3, 0x05),  # type_id
])

# ── Test D: Change type_id, bitmask, AND separator ─────────────────
print("Test D: Change type_id, bitmask, AND separator before step 5")
make_delta("delta_d_full_change", "full Random: type+mask+sep=0x06 on step 5", [
    (sep_offset(3), 0x06),      # separator before step 5
    (rec_offset(4) + 0, 0x40),  # bitmask
    (rec_offset(4) + 3, 0x05),  # type_id
])

# ── Test E: Change ONLY separator before step 5 ───────────────────
print("Test E: Change ONLY separator before step 5 (0x0A → 0x06)")
make_delta("delta_e_sep_only", "sep=0x06 before step 5 (record stays Hold)", [
    (sep_offset(3), 0x06),  # separator only
])

# ── Test F: Change ONLY type_id of step 2 (earliest non-first) ─────
print("Test F: Change ONLY type_id of step 2 (0x00 → 0x05)")
make_delta("delta_f_s2_typeid", "type_id=0x05 on step 2 (bitmask stays Hold=0x02)", [
    (rec_offset(1) + 3, 0x05),
])

# ── Test G: Change ONLY bitmask of step 2 ──────────────────────────
print("Test G: Change ONLY bitmask of step 2 (0x02 → 0x40)")
make_delta("delta_g_s2_bitmask", "bitmask=0x40 on step 2 (type_id stays Hold=0x00)", [
    (rec_offset(1) + 0, 0x40),
])

# ── Test H: Change ONLY type_id of step 16 (last record) ──────────
print("Test H: Change ONLY type_id of step 16 (0x00 → 0x05)")
make_delta("delta_h_s16_typeid", "type_id=0x05 on step 16 (last record, no separator after)", [
    (rec_offset(15) + 3, 0x05),
])

# ── Test I: Change separator AND type_id+bitmask, ALSO fix return sep
print("Test I: Full Random on step 5 + return sep=0x0B for step 6")
make_delta("delta_i_full_with_return", "full Random step 5 + sep=0x0B before step 6", [
    (sep_offset(3), 0x06),      # sep before step 5 (Random intro)
    (rec_offset(4) + 0, 0x40),  # bitmask = Random
    (rec_offset(4) + 3, 0x05),  # type_id = Random
    (sep_offset(4), 0x0B),      # sep before step 6 (return to Hold)
])

# ── Test J: Random on step 5 with BACKWARD separator formula ──────
# Backward formula: sep = 11 - count(distinct type_ids seen in preceding records)
# Before step 5: only Hold (0x00) seen → sep = 11-1 = 10 = 0x0A (unchanged!)
# After step 5: Hold+Random (0x00,0x05) seen → sep = 11-2 = 9 = 0x09
# This means seps 0-3 stay at 0x0A, seps 4-14 change to 0x09
print("Test J: Random step 5 with backward separator formula (seps AFTER drop to 0x09)")
changes_j = [
    (rec_offset(4) + 0, 0x40),  # bitmask = Random
    (rec_offset(4) + 3, 0x05),  # type_id = Random
]
# Change seps 4-14 (before steps 6-16) from 0x0A to 0x09
for i in range(4, 15):
    changes_j.append((sep_offset(i), 0x09))
make_delta("delta_j_backward_formula", "Random step 5 + seps after→0x09 (backward formula)", changes_j)

# ── Test K: Random on step 2 with backward formula ───────────────
# Same logic: sep[0] (before step 2) stays 0x0A, seps 1-14 → 0x09
print("Test K: Random step 2 with backward separator formula")
changes_k = [
    (rec_offset(1) + 0, 0x40),  # bitmask = Random
    (rec_offset(1) + 3, 0x05),  # type_id = Random
]
for i in range(1, 15):
    changes_k.append((sep_offset(i), 0x09))
make_delta("delta_k_s2_backward", "Random step 2 + seps after→0x09", changes_k)

# ── Test L: Random on step 16 with backward formula ──────────────
# Step 16 is last record — no separator after it. Only seps before need updating: none!
# But wait: we also need to check if the sep BEFORE step 16 matters.
# Backward: before step 16, only Hold seen → sep[14] stays 0x0A
# Actually sep[14] is the sep before step 16. Since only Hold seen through step 15,
# sep should stay 0x0A. No sep changes needed — just type_id + bitmask.
# But delta_h (type_id only on step 16) crashed! So something else is wrong.
# Maybe the issue is that step 16 has no sep AFTER, but the firmware expects
# the PRECEDING seps to account for the new type_id. Let's test both ways:
print("Test L: Random step 16, sep[14] stays 0x0A (backward formula says unchanged)")
make_delta("delta_l_s16_backward", "Random step 16 + no sep changes (backward formula)", [
    (rec_offset(15) + 0, 0x40),  # bitmask = Random
    (rec_offset(15) + 3, 0x05),  # type_id = Random
])

# ── Verify all delta files ─────────────────────────────────────────
print("=== Verification ===\n")
for name in sorted(OUTPUT_DIR.glob("delta_*.xy")):
    data = name.read_bytes()
    proj = XYProject.from_bytes(data)
    body = proj.tracks[0].body
    # Show modified region around step 5 (steps 4-6)
    s4 = rec_offset(3)
    s7 = rec_offset(6) + 7
    snippet = body[s4:s7]
    print(f"  {name.name:35s} steps 4-6: {snippet.hex(' ')}")

print(f"""
=== Test Priority ===

  HIGH PRIORITY (test first — isolates which field crashes):
    delta_a_typeid_only    — if crashes, type_id validation is the issue
    delta_b_bitmask_only   — if crashes, bitmask validation is the issue
    delta_e_sep_only       — if crashes, separator validation is the issue

  MEDIUM (confirms combinations):
    delta_c_type_and_mask  — type_id + bitmask but original separator
    delta_d_full_change    — all three fields changed
    delta_i_full_with_return — all fields + corrected return separator

  LOW (tests position-dependence):
    delta_f_s2_typeid      — type_id change on step 2 (early position)
    delta_g_s2_bitmask     — bitmask change on step 2
    delta_h_s16_typeid     — type_id change on step 16 (no trailing sep)
""")
