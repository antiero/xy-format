#!/usr/bin/env python3
"""
Generate 5 scene probe files for device testing.

Each probe modifies a known-good .xy file with targeted byte changes
to test specific hypotheses about scene record encoding.

Probe 1 (Low Risk):      S2 T4→P2  — track tag swap from T3 to T4
Probe 2 (Low-Med Risk):  S3 T3→P3  — track tag swap from T4 to T3
Probe 3 (Medium Risk):   S3 T4→P2  — pattern change (variable-length growth)
Probe 4 (Med-High Risk): S2 T2→P2  — new track in scene override
Probe 5 (High Risk):     Scene 4   — new scene creation with T3→P2 override
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


# ── Probe 1: Track tag swap — S2 T3→P2 becomes S2 T4→P2 ────────────
#
# Base: file 04 (Scene 2, T3→P2)
# Change: pre_track[0x5F]  0x1B (T3) → 0x1A (T4)
#
# Pre-track scene record layout (file 04, offsets 0x5B-0x62):
#   00 01 00 00 1B 01 00 00
#                ^^ byte 0x5F = track tag

print("Probe 1 (Low Risk): S2 T3→P2 → S2 T4→P2  [track tag swap]")
proj04 = load("04_scene_s2_t3p2.xy")
pt1 = bytearray(proj04.pre_track)
assert pt1[0x5F] == 0x1B, f"Expected 0x1B at 0x5F, got 0x{pt1[0x5F]:02X}"
pt1[0x5F] = 0x1A  # T4 = 0x1E - 4
probe1 = XYProject(bytes(pt1), proj04.tracks)
save(probe1, "probe1_s2_t4p2_tag_swap.xy", "Probe 1")


# ── Probe 2: Track tag swap — S3 T4→P3 becomes S3 T3→P3 ────────────
#
# Base: file 07 (Scene 2 T3→P2, Scene 3 T4→P3)
# Change: pre_track[0x68]  0x1A (T4) → 0x1B (T3)
#
# Pre-track S3 record (file 07, offsets 0x63-0x6B):
#   00 01 02 00 00 1A 01 00 00
#                   ^^ byte 0x68 = track tag

print("\nProbe 2 (Low-Med Risk): S3 T4→P3 → S3 T3→P3  [track tag swap]")
proj07 = load("07_scene_s3_t4p3.xy")
pt2 = bytearray(proj07.pre_track)
assert pt2[0x68] == 0x1A, f"Expected 0x1A at 0x68, got 0x{pt2[0x68]:02X}"
pt2[0x68] = 0x1B  # T3 = 0x1E - 3
probe2 = XYProject(bytes(pt2), proj07.tracks)
save(probe2, "probe2_s3_t3p3_tag_swap.xy", "Probe 2")


# ── Probe 3: Pattern change — S3 T4→P3 becomes S3 T4→P2 ────────────
#
# Base: file 07 (Scene 2 T3→P2, Scene 3 T4→P3)
# Change: Replace S3 9-byte record (P3=02) with 10-byte record (P2=01 00)
#
# From 09→10 analysis: P3 encodes as single byte 0x02, P2 as two bytes 0x01 0x00
# This tests the variable-length pattern encoding hypothesis.
#
# Old S3 record (9 bytes):  00 01 02 00 00 1A 01 00 00
# New S3 record (10 bytes): 00 01 01 00 00 00 1A 01 00 00
# Pre-track grows by 1 byte (144 → 145).

print("\nProbe 3 (Medium Risk): S3 T4→P3 → S3 T4→P2  [variable-length pattern]")
proj07 = load("07_scene_s3_t4p3.xy")
pt3 = proj07.pre_track
old_s3 = bytes([0x00, 0x01, 0x02, 0x00, 0x00, 0x1A, 0x01, 0x00, 0x00])
new_s3 = bytes([0x00, 0x01, 0x01, 0x00, 0x00, 0x00, 0x1A, 0x01, 0x00, 0x00])
assert pt3[0x63:0x6C] == old_s3, f"Record mismatch: {pt3[0x63:0x6C].hex()}"
new_pt3 = pt3[:0x63] + new_s3 + pt3[0x6C:]
probe3 = XYProject(new_pt3, proj07.tracks)
save(probe3, "probe3_s3_t4p2_varlen.xy", "Probe 3")
print(f"  Pre-track: {len(pt3)} → {len(new_pt3)} bytes (+1)")


# ── Probe 4: New track — S2 T3→P2 becomes S2 T2→P2 ─────────────────
#
# Base: file 04 (Scene 2, T3→P2)
# Change: pre_track[0x5F]  0x1B (T3) → 0x1C (T2)
#
# Track tag formula: tag = 0x1E - track_number
#   T2 = 0x1C,  T3 = 0x1B,  T4 = 0x1A  (confirmed for T3/T4)
# T2 is untested in scene records. If 0x1C = T2 is correct, Scene 2
# should override T2's pattern selection.

print("\nProbe 4 (Med-High Risk): S2 T3→P2 → S2 T2→P2  [new track tag]")
proj04 = load("04_scene_s2_t3p2.xy")
pt4 = bytearray(proj04.pre_track)
assert pt4[0x5F] == 0x1B
pt4[0x5F] = 0x1C  # T2 = 0x1E - 2
probe4 = XYProject(bytes(pt4), proj04.tracks)
save(probe4, "probe4_s2_t2p2_new_track.xy", "Probe 4")


# ── Probe 5: Scene 4 creation ───────────────────────────────────────
#
# Base: file 07 (3 scenes: S1 default, S2 T3→P2, S3 T4→P3)
# Goal: Add Scene 4 with T3→P2 override
#
# Required changes:
#   A. pre_track[0x0F]: 0x02 → 0x03  (scene ordinal)
#   B. Insert S4 record at 0x6C (before handle table FF bytes)
#      Record: 00 01 00 00 1B 01 00 00  (8 bytes, same as S2 T3→P2)
#   C. T1 preamble[0]: 0x73 → 0x52  (−0x21 per scene override)
#      Formula: 0xD6 - (ordinal + 1) * 0x21
#   D. T16 body[0x6E7]: 0x03 → 0x04  (scene count)
#   E. Insert scene ID 0x03 at T16 body[0x6EB]  (after existing IDs [0,1,2])

print("\nProbe 5 (High Risk): Add Scene 4 with T3→P2 override")
proj07 = load("07_scene_s3_t4p3.xy")

# A. Scene ordinal
pt5 = bytearray(proj07.pre_track)
assert pt5[0x0F] == 0x02, f"Expected ordinal 0x02, got 0x{pt5[0x0F]:02X}"
pt5[0x0F] = 0x03

# B. Insert S4 record before handle table
s4_record = bytes([0x00, 0x01, 0x00, 0x00, 0x1B, 0x01, 0x00, 0x00])
assert pt5[0x6C] == 0xFF, f"Expected handle table at 0x6C, got 0x{pt5[0x6C]:02X}"
new_pt5 = bytes(pt5[:0x6C]) + s4_record + bytes(pt5[0x6C:])

# C. T1 preamble: 0x73 → 0x52
t1 = proj07.tracks[0]
assert t1.preamble[0] == 0x73, f"Expected T1 preamble 0x73, got 0x{t1.preamble[0]:02X}"
new_t1_preamble = bytes([0x52]) + t1.preamble[1:]
new_t1 = TrackBlock(index=0, preamble=new_t1_preamble, body=t1.body)

# D & E. T16 scene list: count 3→4, insert ID 3
t16 = proj07.tracks[15]
t16_body = bytearray(t16.body)
assert t16_body[0x6E7] == 0x03, f"Expected count 3, got {t16_body[0x6E7]}"
t16_body[0x6E7] = 0x04
# Existing IDs at 0x6E8-0x6EA: [00, 01, 02]
# Insert 0x03 at 0x6EB
new_t16_body = bytes(t16_body[:0x6EB]) + bytes([0x03]) + bytes(t16_body[0x6EB:])
new_t16 = TrackBlock(index=15, preamble=t16.preamble, body=new_t16_body)

# Rebuild project with modified T1 and T16
new_tracks = [new_t1] + list(proj07.tracks[1:15]) + [new_t16]
probe5 = XYProject(new_pt5, new_tracks)
data5 = save(probe5, "probe5_scene4_t3p2.xy", "Probe 5")
print(f"  Pre-track: {len(proj07.pre_track)} → {len(new_pt5)} bytes (+8)")
print(f"  T16 body: {len(t16.body)} → {len(new_t16_body)} bytes (+1)")
print(f"  T1 preamble: 0x73 → 0x52")


# ── Verify all probes round-trip cleanly ─────────────────────────────
print("\nRound-trip verification:")
for name, probe in [
    ("probe1", probe1),
    ("probe2", probe2),
    ("probe3", probe3),
    ("probe4", probe4),
    ("probe5", probe5),
]:
    rebuilt = XYProject.from_bytes(probe.to_bytes())
    assert rebuilt.to_bytes() == probe.to_bytes(), f"{name} round-trip FAILED"
    assert len(rebuilt.tracks) == 16, f"{name} has {len(rebuilt.tracks)} tracks"
    print(f"  {name}: OK ({len(rebuilt.tracks)} tracks)")

print("\nAll probes generated successfully.")
