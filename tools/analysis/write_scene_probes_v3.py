#!/usr/bin/env python3
"""
Generate v3 scene probe files for device testing.

All probes use file 07 (07_scene_s3_t4p3.xy) as base, which has:
  - T3: P1+P2 (2 patterns)
  - T4: P1+P2+P3 (3 patterns)
  - Scenes: S1 (default), S2 (T3→P2), S3 (T4→P3)
  - 2 scene records, ordinal=2, T1 preamble[0]=0x73
  - T16 scene count=3, IDs=[0,1,2]

Probe sets:
  A (safe): within pattern-existence constraints
  B (hypothesis): general encoder validation, edge cases
  C (bold): testing new track tags (T1, T2)

Uses the generalized scene record encoder (encode_scene_record_general)
and the batch scene adder (patch_add_scenes).
"""

import sys

sys.path.insert(0, ".")
from xy.container import XYProject, TrackBlock
from xy.scene_records import (
    encode_scene_record_general,
    decode_scene_region,
    describe_record,
    find_scene_region,
    read_t16_scene_list,
    t1_preamble_for_record_count,
)
from xy.scene_patcher import patch_add_scenes, patch_modify_scene_record
from pathlib import Path

OUTPUT = Path("output/scene-probes")
OUTPUT.mkdir(parents=True, exist_ok=True)
SRC = Path("src/one-off-changes-from-default")


def load(name):
    data = (SRC / name).read_bytes()
    return XYProject.from_bytes(data)


def save(proj, name, label):
    out = OUTPUT / name
    data = proj.to_bytes()
    out.write_bytes(data)
    print(f"  {label}: {out}  ({len(data)} bytes)")
    return data


def show_state(proj, label=""):
    pre = proj.pre_track
    records = decode_scene_region(pre)
    count, ids = read_t16_scene_list(proj.tracks[15].body)
    t1p = proj.tracks[0].preamble[0]
    print(f"  {label}Records: {len(records)}, ordinal=0x{pre[0x0F]:02X}, "
          f"T1p=0x{t1p:02X}, T16: count={count} ids={ids}")
    for i, r in enumerate(records):
        print(f"    [{i}] {describe_record(r)}")


# ── Load base file ──────────────────────────────────────────────────

proj07 = load("07_scene_s3_t4p3.xy")
pre = proj07.pre_track

# Verify expected layout
assert pre[0x0F] == 0x02, f"Expected ordinal 0x02, got 0x{pre[0x0F]:02X}"
assert proj07.tracks[0].preamble[0] == 0x73, "T1 preamble mismatch"
t16_body = proj07.tracks[15].body
assert t16_body[0x6E7] == 0x03, "T16 scene count mismatch"
assert list(t16_body[0x6E8:0x6EB]) == [0, 1, 2], "T16 scene IDs mismatch"
print("Base file 07 loaded and verified.")
show_state(proj07, "Base: ")

probes = []

# ══════════════════════════════════════════════════════════════════════
# PROBE SET A — Safe (within pattern-existence constraints)
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("PROBE SET A — Safe (within pattern-existence)")
print("=" * 60)

# ── v3-A1: Add S4→T4→P2 ─────────────────────────────────────────────
#
# T4 has P1-P3 → P2 is valid. Add as 3rd record via general encoder.
# Expected: 3 records, ordinal=3, T1p=0x52, T16 count=4

print("\nv3-A1: Add S4→T4→P2")
v3_a1 = patch_add_scenes(proj07, [(3, [(4, 1)])])
show_state(v3_a1)
save(v3_a1, "v3-A1_s4_t4p2.xy", "v3-A1")
probes.append(("v3-A1", v3_a1))

# ── v3-A2: Add S4→T3→P2 + S5→T4→P3 ─────────────────────────────────
#
# Both valid (T3 has P2, T4 has P3). Adds 2 records + 2 scene IDs.
# Expected: 4 records, ordinal=4, T1p=0x31, T16 count=5

print("\nv3-A2: Add S4→T3→P2 + S5→T4→P3")
v3_a2 = patch_add_scenes(proj07, [
    (3, [(3, 1)]),  # S4: T3→P2
    (4, [(4, 2)]),  # S5: T4→P3
])
show_state(v3_a2)
save(v3_a2, "v3-A2_s4_t3p2_s5_t4p3.xy", "v3-A2")
probes.append(("v3-A2", v3_a2))

# ── v3-A3: Replace S2 record with T4→P2 (compact form) ──────────────
#
# Replace the existing S2 record (T3→P2, 8B) with T4→P2 compact (8B).
# Same-length swap. T4 has P2 → valid.
# Note: The S2 record is the FIRST record in the region, so we use
# compact form (is_first=True).

print("\nv3-A3: Replace S2→T3→P2 with S2→T4→P2 (compact)")
region_start, _ = find_scene_region(proj07.pre_track)
# S2 record is at region_start, 8 bytes
s2_end = region_start + 8
new_record = encode_scene_record_general(4, 1, is_first=True)
assert len(new_record) == 8, "compact form should be 8B"
v3_a3 = patch_modify_scene_record(proj07, region_start, s2_end, new_record)
show_state(v3_a3)
save(v3_a3, "v3-A3_s2_t4p2_compact.xy", "v3-A3")
probes.append(("v3-A3", v3_a3))


# ══════════════════════════════════════════════════════════════════════
# PROBE SET B — Hypothesis (general encoder validation)
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("PROBE SET B — Hypothesis (general encoder validation)")
print("=" * 60)

# ── v3-B1: S4→T4→P3 using general encoder (standard form) ───────────
#
# Uses general encoder for a known-valid combo (T4→P3 exists).
# Standard form for P3: 9B with explicit pattern byte.
# This tests whether the general encoder's standard P3 form is
# accepted when corpus form was only seen in compact and first positions.

print("\nv3-B1: S4→T4→P3 via general encoder (standard 9B)")
v3_b1 = patch_add_scenes(proj07, [(3, [(4, 2)])])
show_state(v3_b1)
save(v3_b1, "v3-B1_s4_t4p3_general.xy", "v3-B1")
probes.append(("v3-B1", v3_b1))

# ── v3-B2: S2→T4 with explicit pattern byte 03 (P4 = index 3) ───────
#
# T4 has P1-P3 only. Pattern index 3 = P4 which DOESN'T EXIST.
# Expected: CRASH (num_patterns). If it crashes, confirms 03 = P4 encoding.
# If different crash type, suggests tag/structure issue.
#
# Build manually to test specific byte encoding.

print("\nv3-B2: S4→T4 with explicit pattern=03 (P4 doesn't exist)")
# Standard P4 form: [00] [01] [03] [00 00] [1A] [01 00 00]
p4_record = bytes([0x00, 0x01, 0x03, 0x00, 0x00, 0x1A, 0x01, 0x00, 0x00])
_, ht_start = find_scene_region(proj07.pre_track)
new_pre_b2 = bytearray(proj07.pre_track)
# Insert before handle table
new_pre_b2 = bytes(new_pre_b2[:ht_start]) + p4_record + bytes(new_pre_b2[ht_start:])
# Update ordinal
new_pre_b2 = bytearray(new_pre_b2)
new_pre_b2[0x0F] = 0x03
new_pre_b2 = bytes(new_pre_b2)
# Update T1 preamble (3 records now)
t1 = proj07.tracks[0]
new_t1_b2 = TrackBlock(
    index=0,
    preamble=bytes([t1_preamble_for_record_count(3)]) + t1.preamble[1:],
    body=t1.body,
)
# Update T16 (add scene 3)
from xy.scene_records import write_t16_scene_list
t16 = proj07.tracks[15]
new_t16_body_b2 = write_t16_scene_list(t16.body, [0, 1, 2, 3])
new_t16_b2 = TrackBlock(index=15, preamble=t16.preamble, body=new_t16_body_b2)
tracks_b2 = [new_t1_b2] + list(proj07.tracks[1:15]) + [new_t16_b2]
v3_b2 = XYProject(new_pre_b2, tracks_b2)
show_state(v3_b2)
save(v3_b2, "v3-B2_s4_t4_p4_nonexist.xy", "v3-B2")
probes.append(("v3-B2", v3_b2))

# ── v3-B3: S4→T4→P3 with explicit 02 via general encoder ────────────
#
# Same as B1 but confirming 02 = P3 encoding. T4 has P3 → should PASS.

print("\nv3-B3: S4→T4→P3 with explicit pattern=02 via general encoder")
# This is essentially the same as B1 — using general encoder for T4→P3.
# Including it as explicit confirmation that pattern byte 02 = P3.
v3_b3 = patch_add_scenes(proj07, [(3, [(4, 2)])])
show_state(v3_b3)
save(v3_b3, "v3-B3_s4_t4p3_explicit02.xy", "v3-B3")
probes.append(("v3-B3", v3_b3))


# ══════════════════════════════════════════════════════════════════════
# PROBE SET C — Bold (testing T1/T2 track tags)
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("PROBE SET C — Bold (new track tags)")
print("=" * 60)

# ── v3-C1: S4→T1→P2 (tag=0x1D) ──────────────────────────────────────
#
# T1 has only P1 → P2 doesn't exist → expected CRASH.
# But the CRASH TYPE is informative:
#   - num_patterns crash → tag accepted, pattern rejected (useful!)
#   - different crash → tag itself is bad

print("\nv3-C1: S4→T1→P2 (tag=0x1D, T1 has P1 only → expect CRASH)")
v3_c1 = patch_add_scenes(proj07, [(3, [(1, 1)])])
show_state(v3_c1)
save(v3_c1, "v3-C1_s4_t1p2_crash.xy", "v3-C1")
probes.append(("v3-C1", v3_c1))

# ── v3-C2: S4→T2→P2 (tag=0x1C) ──────────────────────────────────────
#
# T2 has only P1 → P2 doesn't exist → expected CRASH.
# Same diagnostic logic as C1.

print("\nv3-C2: S4→T2→P2 (tag=0x1C, T2 has P1 only → expect CRASH)")
v3_c2 = patch_add_scenes(proj07, [(3, [(2, 1)])])
show_state(v3_c2)
save(v3_c2, "v3-C2_s4_t2p2_crash.xy", "v3-C2")
probes.append(("v3-C2", v3_c2))


# ══════════════════════════════════════════════════════════════════════
# Round-trip verification
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("Round-trip verification")
print("=" * 60)

for name, probe in probes:
    rebuilt = XYProject.from_bytes(probe.to_bytes())
    assert rebuilt.to_bytes() == probe.to_bytes(), f"{name} round-trip FAILED"
    assert len(rebuilt.tracks) == 16, f"{name} has {len(rebuilt.tracks)} tracks"
    print(f"  {name}: OK ({len(rebuilt.tracks)} tracks)")

print("\nAll v3 probes generated successfully.")


# ══════════════════════════════════════════════════════════════════════
# Testing checklist
# ══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TESTING CHECKLIST")
print("=" * 60)
print("""
PROBE SET A — Should all PASS:

  v3-A1  v3-A1_s4_t4p2.xy
         Scene 4 visible? T4 plays P2 in S4?

  v3-A2  v3-A2_s4_t3p2_s5_t4p3.xy
         Scenes 4+5 visible? T3→P2 in S4? T4→P3 in S5?

  v3-A3  v3-A3_s2_t4p2_compact.xy
         Scene 2: T4 plays P2? (was T3→P2 before)

PROBE SET B — Expect PASS or informative CRASH:

  v3-B1  v3-B1_s4_t4p3_general.xy
         Does it load? S4→T4→P3?

  v3-B2  v3-B2_s4_t4_p4_nonexist.xy
         Crash type? (num_patterns → confirms 03=P4 encoding)

  v3-B3  v3-B3_s4_t4p3_explicit02.xy
         Does it load? S4→T4→P3?

PROBE SET C — Expect CRASH but informative:

  v3-C1  v3-C1_s4_t1p2_crash.xy
         Crash type? (num_patterns → tag 0x1D accepted)

  v3-C2  v3-C2_s4_t2p2_crash.xy
         Crash type? (num_patterns → tag 0x1C accepted)

NOTE: For C1/C2, "num_patterns > 0" crash (serialize_latest.cpp:90)
means the tag formula is correct — firmware parsed the tag but the
referenced pattern doesn't exist. A different crash would suggest
the tag itself is rejected.
""")
