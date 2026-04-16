#!/usr/bin/env python3
"""
Generate v2 scene probe files for device testing.

All probes use file 07 (07_scene_s3_t4p3.xy) as base, which has:
  - T3: P1+P2 (2 patterns)
  - T4: P1+P2+P3 (3 patterns)
  - Scenes: S1 (default), S2 (T3→P2), S3 (T4→P3)
  - pre_track_len=144, pre[0x0F]=0x02, T1 preamble[0]=0x73
  - T16 scene count=3, IDs=[0,1,2]

Scene region layout (file 07):
  descriptor @ 0x57: 1e 01 00 00
  S2 record  @ 0x5B: 00 01 00 00 1b 01 00 00          (8B, T3→P2)
  S3 record  @ 0x63: 00 01 02 00 00 1a 01 00 00       (9B, T4→P3)
  handle tbl @ 0x6C: ff 00 00 ff 00 00 ...

Probes respect pattern-existence constraint: only reference patterns that exist
on the target track (v1 finding: all 3 crashes were pattern-not-found).

v2-1: Compact T4→P2 record in S2          (same length swap)
v2-2: Full T4→P2 dual-override in S2      (+2B growth)
v2-3: S2 T4→P3 override                   (+1B growth)
v2-4: 5 scenes (add S5 T3→P2)             (+8B pre-track, +1B T16)
v2-5a: Scene 3 deletion (full revert)     (-9B pre-track, -1B T16)
v2-5b: Scene 3 deletion (pre-track only)  (-9B pre-track, T16 unchanged)
"""

import sys

sys.path.insert(0, ".")
from xy.container import XYProject, TrackBlock
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


# ── Load base file ──────────────────────────────────────────────────

proj07 = load("07_scene_s3_t4p3.xy")
pre = proj07.pre_track

# Verify expected layout
assert pre[0x0F] == 0x02, f"Expected ordinal 0x02, got 0x{pre[0x0F]:02X}"
assert pre[0x57:0x5B] == b"\x1e\x01\x00\x00", "Descriptor mismatch"
assert pre[0x5B:0x63] == bytes([0x00, 0x01, 0x00, 0x00, 0x1B, 0x01, 0x00, 0x00]), \
    f"S2 record mismatch: {pre[0x5B:0x63].hex()}"
assert pre[0x63:0x6C] == bytes([0x00, 0x01, 0x02, 0x00, 0x00, 0x1A, 0x01, 0x00, 0x00]), \
    f"S3 record mismatch: {pre[0x63:0x6C].hex()}"
assert pre[0x6C:0x6F] == b"\xff\x00\x00", "Handle table start mismatch"
assert proj07.tracks[0].preamble[0] == 0x73, "T1 preamble mismatch"
t16_body = proj07.tracks[15].body
assert t16_body[0x6E7] == 0x03, "T16 scene count mismatch"
assert list(t16_body[0x6E8:0x6EB]) == [0, 1, 2], "T16 scene IDs mismatch"

# Known-good record forms from corpus:
S2_T3_P2_8B = bytes([0x00, 0x01, 0x00, 0x00, 0x1B, 0x01, 0x00, 0x00])
S3_T4_P3_9B = bytes([0x00, 0x01, 0x02, 0x00, 0x00, 0x1A, 0x01, 0x00, 0x00])
COMPACT_T4_P2_8B = bytes([0x01, 0x01, 0x00, 0x00, 0x1A, 0x01, 0x00, 0x00])  # from file 12
DUAL_T4_P2_10B = bytes([0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x1A, 0x01, 0x00, 0x00])  # from file 05/11


# ── v2-1 (Low Risk): Compact T4→P2 record in S2 ────────────────────
#
# Replace S2's 8B T3→P2 record with compact 8B T4→P2 from file 12.
# Same pre-track length (both 8B). Tests compact record form.
# T4 has P2 → valid. T3 should revert to P1.

print("v2-1 (Low Risk): Compact T4→P2 in S2")
pt1 = bytearray(pre)
pt1[0x5B:0x63] = COMPACT_T4_P2_8B
assert len(pt1) == len(pre), "Length changed unexpectedly"
v2_1 = XYProject(bytes(pt1), proj07.tracks)
save(v2_1, "v2-1_s2_compact_t4p2.xy", "v2-1")
print(f"  Check: Scene 2 — does T4 play P2? Does T3 revert to P1?")


# ── v2-2 (Low-Med): Full T4→P2 dual-override in S2 ─────────────────
#
# Replace S2's 8B record with 10B dual form from file 05/11.
# Pre-track grows +2B. Tests dual-override record.
# Expected: BOTH T3 and T4 play P2 in Scene 2.

print("\nv2-2 (Low-Med): Full T4→P2 dual-override in S2")
new_pt2 = pre[:0x5B] + DUAL_T4_P2_10B + pre[0x63:]
assert len(new_pt2) == len(pre) + 2, f"Expected +2, got {len(new_pt2) - len(pre)}"
v2_2 = XYProject(new_pt2, proj07.tracks)
save(v2_2, "v2-2_s2_dual_t4p2.xy", "v2-2")
print(f"  Pre-track: {len(pre)} → {len(new_pt2)} bytes (+2)")
print(f"  Check: Scene 2 — do BOTH T3 and T4 play P2?")


# ── v2-3 (Medium): S2 T4→P3 override ────────────────────────────────
#
# Replace S2's 8B T3→P2 record with 9B T4→P3 record (same form as S3).
# Pre-track grows +1B. T4 has P3 → valid.
# Tests cross-track cross-pattern override in S2 position.

print("\nv2-3 (Medium): S2 T4→P3 override")
# Use the same byte pattern as the S3 T4→P3 record
S2_T4_P3_9B = bytes([0x00, 0x01, 0x02, 0x00, 0x00, 0x1A, 0x01, 0x00, 0x00])
new_pt3 = pre[:0x5B] + S2_T4_P3_9B + pre[0x63:]
assert len(new_pt3) == len(pre) + 1, f"Expected +1, got {len(new_pt3) - len(pre)}"
v2_3 = XYProject(new_pt3, proj07.tracks)
save(v2_3, "v2-3_s2_t4p3.xy", "v2-3")
print(f"  Pre-track: {len(pre)} → {len(new_pt3)} bytes (+1)")
print(f"  Check: Scene 2 — does T4 play P3? Does T3 revert to P1?")


# ── v2-4 (Med-High): 5 scenes ───────────────────────────────────────
#
# Base: Probe 5 output (4 scenes). Add Scene 5 with T3→P2.
# Changes: ordinal 3→4, T1 preamble 0x52→0x31, T16 count 4→5, insert ID 4.

print("\nv2-4 (Med-High): 5 scenes")
probe5_path = OUTPUT / "probe5_scene4_t3p2.xy"
assert probe5_path.exists(), f"Probe 5 output not found at {probe5_path}"
proj5 = XYProject.from_bytes(probe5_path.read_bytes())
p5_pre = proj5.pre_track

# Verify probe 5 layout
assert p5_pre[0x0F] == 0x03, f"Expected ordinal 0x03, got 0x{p5_pre[0x0F]:02X}"
assert proj5.tracks[0].preamble[0] == 0x52, f"Expected T1 0x52, got 0x{proj5.tracks[0].preamble[0]:02X}"
p5_t16 = proj5.tracks[15].body
assert p5_t16[0x6E7] == 0x04, f"Expected T16 count 4, got {p5_t16[0x6E7]}"

# Find handle table in probe 5
p5_ht = None
for i in range(0x50, len(p5_pre) - 2):
    if p5_pre[i : i + 3] == b"\xff\x00\x00":
        p5_ht = i
        break
assert p5_ht == 0x74, f"Expected handle table at 0x74, got 0x{p5_ht:02X}"

# A. Scene ordinal 3→4
pt4 = bytearray(p5_pre)
pt4[0x0F] = 0x04

# B. Insert S5 record before handle table
s5_record = S2_T3_P2_8B  # Same 8B T3→P2 as S2/S4
new_pt4 = bytes(pt4[:p5_ht]) + s5_record + bytes(pt4[p5_ht:])

# C. T1 preamble: 0x52 → 0x31 (−0x21)
t1_5 = proj5.tracks[0]
assert t1_5.preamble[0] == 0x52
new_t1_preamble = bytes([0x31]) + t1_5.preamble[1:]
new_t1 = TrackBlock(index=0, preamble=new_t1_preamble, body=t1_5.body)

# D. T16 scene count 4→5
p5_t16_body = bytearray(p5_t16)
p5_t16_body[0x6E7] = 0x05

# E. Insert scene ID 4 after existing IDs [0,1,2,3]
# Existing IDs at 0x6E8-0x6EB: [0,1,2,3]. Insert 0x04 at 0x6EC.
new_t16_body = bytes(p5_t16_body[:0x6EC]) + bytes([0x04]) + bytes(p5_t16_body[0x6EC:])
new_t16 = TrackBlock(index=15, preamble=proj5.tracks[15].preamble, body=new_t16_body)

# Rebuild
new_tracks4 = [new_t1] + list(proj5.tracks[1:15]) + [new_t16]
v2_4 = XYProject(new_pt4, new_tracks4)
save(v2_4, "v2-4_5scenes.xy", "v2-4")
print(f"  Pre-track: {len(p5_pre)} → {len(new_pt4)} bytes (+8)")
print(f"  T1 preamble: 0x52 → 0x31")
print(f"  T16 scene count: 4 → 5, IDs: [0,1,2,3] → [0,1,2,3,4]")
print(f"  Check: Does Scene 5 appear? Does T3 play P2 in Scene 5?")


# ── v2-5a (High): Scene 3 deletion (full revert) ────────────────────
#
# Remove S3 record from file 07. Pre-track shrinks -9B.
# Changes: ordinal 2→1, T1 preamble 0x73→0x94, T16 count 3→2, remove ID 2.

print("\nv2-5a (High): Scene 3 deletion (full revert)")
# Remove S3 record (pre[0x63:0x6C])
pt5a = bytearray(pre[:0x63] + pre[0x6C:])
# Ordinal 2→1
pt5a[0x0F] = 0x01
new_pt5a = bytes(pt5a)
assert len(new_pt5a) == len(pre) - 9, f"Expected -9, got {len(new_pt5a) - len(pre)}"

# T1 preamble: 0x73 → 0x94 (+0x21)
t1_07 = proj07.tracks[0]
new_t1_5a = TrackBlock(index=0, preamble=bytes([0x94]) + t1_07.preamble[1:], body=t1_07.body)

# T16: count 3→2, remove ID 2
t16_5a = bytearray(t16_body)
t16_5a[0x6E7] = 0x02
# Remove byte at 0x6EA (ID=2, the third entry)
new_t16_5a = bytes(t16_5a[:0x6EA]) + bytes(t16_5a[0x6EB:])
new_t16_5a_track = TrackBlock(index=15, preamble=proj07.tracks[15].preamble, body=new_t16_5a)

tracks_5a = [new_t1_5a] + list(proj07.tracks[1:15]) + [new_t16_5a_track]
v2_5a = XYProject(new_pt5a, tracks_5a)
save(v2_5a, "v2-5a_delete_s3_full.xy", "v2-5a")
print(f"  Pre-track: {len(pre)} → {len(new_pt5a)} bytes (-9)")
print(f"  T1 preamble: 0x73 → 0x94")
print(f"  T16 scene count: 3 → 2, IDs: [0,1,2] → [0,1]")
print(f"  Check: Does file load? Do only Scenes 1+2 remain? Does S2 T3→P2 still work?")


# ── v2-5b (High): Scene 3 deletion (pre-track only, T16 unchanged) ──
#
# Same pre-track changes as v2-5a but leave T16 untouched.
# Tests whether orphaned T16 entries are tolerated.

print("\nv2-5b (High): Scene 3 deletion (pre-track only, T16 unchanged)")
# Same pre-track as v2-5a
# Same T1 preamble as v2-5a
# But keep T16 original (count=3, IDs=[0,1,2])
tracks_5b = [new_t1_5a] + list(proj07.tracks[1:15]) + [proj07.tracks[15]]
v2_5b = XYProject(new_pt5a, tracks_5b)
save(v2_5b, "v2-5b_delete_s3_pretrack_only.xy", "v2-5b")
print(f"  Pre-track: {len(pre)} → {len(new_pt5a)} bytes (-9)")
print(f"  T1 preamble: 0x73 → 0x94")
print(f"  T16 UNCHANGED: count=3, IDs=[0,1,2]")
print(f"  Check: Does file load? What scene list appears?")


# ── Verify all probes round-trip cleanly ─────────────────────────────

print("\nRound-trip verification:")
for name, probe in [
    ("v2-1", v2_1),
    ("v2-2", v2_2),
    ("v2-3", v2_3),
    ("v2-4", v2_4),
    ("v2-5a", v2_5a),
    ("v2-5b", v2_5b),
]:
    rebuilt = XYProject.from_bytes(probe.to_bytes())
    assert rebuilt.to_bytes() == probe.to_bytes(), f"{name} round-trip FAILED"
    assert len(rebuilt.tracks) == 16, f"{name} has {len(rebuilt.tracks)} tracks"
    print(f"  {name}: OK ({len(rebuilt.tracks)} tracks)")

print("\nAll v2 probes generated successfully.")
print("\n" + "=" * 60)
print("TESTING CHECKLIST:")
print("=" * 60)
print("""
v2-1  v2-1_s2_compact_t4p2.xy
      Scene 2: T4 plays P2? T3 reverts to P1?

v2-2  v2-2_s2_dual_t4p2.xy
      Scene 2: BOTH T3 and T4 play P2?

v2-3  v2-3_s2_t4p3.xy
      Scene 2: T4 plays P3? T3 reverts to P1?

v2-4  v2-4_5scenes.xy
      Scene 5 appears? T3 plays P2 in Scene 5?

v2-5a v2-5a_delete_s3_full.xy
      Loads? Only Scenes 1+2 remain? S2 T3→P2 works?

v2-5b v2-5b_delete_s3_pretrack_only.xy
      Loads? What scene list appears?
""")
