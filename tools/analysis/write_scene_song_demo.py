#!/usr/bin/env python3
"""
Generate a scene + song demo file for the OP-XY.

Builds on file 07 (07_scene_s3_t4p3.xy) which already has:
  - T3: P1+P2 (2 patterns)
  - T4: P1+P2+P3 (3 patterns)
  - Scenes: S1 (default), S2 (T3→P2), S3 (T4→P3)
  - 2 scene records, ordinal=2, T1 preamble[0]=0x73
  - T16 scene count=3, IDs=[0,1,2]

This demo:
  1. Adds Scene 4 with T4→P2
  2. Adds Scene 5 with T3→P2
  → 5 scenes total, 4 scene records

Song 2 auto-sequences all scenes in order (confirmed by v2-4 probe).
No separate song-slot patching needed — the scenes are available in
Song 2 by default in this file family.

Scene sequence in Song 2:
  S1 (default) → S2 (T3→P2) → S3 (T4→P3) → S4 (T4→P2) → S5 (T3→P2)
"""

import sys

sys.path.insert(0, ".")
from xy.container import XYProject
from xy.scene_records import (
    decode_scene_region,
    describe_record,
    read_t16_scene_list,
    t1_preamble_for_record_count,
)
from xy.scene_patcher import patch_add_scenes
from pathlib import Path

OUTPUT = Path("output")
OUTPUT.mkdir(parents=True, exist_ok=True)
SRC = Path("src/one-off-changes-from-default")


# ── Load base file ──────────────────────────────────────────────────

base_path = SRC / "07_scene_s3_t4p3.xy"
proj = XYProject.from_bytes(base_path.read_bytes())

print("Base file: 07_scene_s3_t4p3.xy")
print(f"  Pre-track: {len(proj.pre_track)} bytes")
print(f"  Ordinal: 0x{proj.pre_track[0x0F]:02X}")
print(f"  T1 preamble[0]: 0x{proj.tracks[0].preamble[0]:02X}")
records = decode_scene_region(proj.pre_track)
print(f"  Scene records: {len(records)}")
for i, r in enumerate(records):
    print(f"    [{i}] {describe_record(r)}")
count, ids = read_t16_scene_list(proj.tracks[15].body)
print(f"  T16 scene list: count={count}, IDs={ids}")


# ── Add Scene 4 (T4→P2) and Scene 5 (T3→P2) ────────────────────────

print("\nAdding Scene 4 (T4→P2) and Scene 5 (T3→P2)...")
result = patch_add_scenes(proj, [
    (3, [(4, 1)]),  # Scene 4: T4→P2
    (4, [(3, 1)]),  # Scene 5: T3→P2
])


# ── Verify ──────────────────────────────────────────────────────────

print("\nResult:")
print(f"  Pre-track: {len(result.pre_track)} bytes")
print(f"  Ordinal: 0x{result.pre_track[0x0F]:02X}")
print(f"  T1 preamble[0]: 0x{result.tracks[0].preamble[0]:02X}")
records = decode_scene_region(result.pre_track)
print(f"  Scene records: {len(records)}")
for i, r in enumerate(records):
    print(f"    [{i}] {describe_record(r)}")
count, ids = read_t16_scene_list(result.tracks[15].body)
print(f"  T16 scene list: count={count}, IDs={ids}")

# Verify T1 preamble formula
expected_t1p = t1_preamble_for_record_count(len(records))
actual_t1p = result.tracks[0].preamble[0]
assert actual_t1p == expected_t1p, \
    f"T1 preamble mismatch: 0x{actual_t1p:02X} != 0x{expected_t1p:02X}"
print(f"  T1 preamble formula verified: 0x{actual_t1p:02X} (4 records → 0xD6 - 5*0x21)")

# Round-trip
rebuilt = XYProject.from_bytes(result.to_bytes())
assert rebuilt.to_bytes() == result.to_bytes(), "Round-trip FAILED"
assert len(rebuilt.tracks) == 16
print(f"  Round-trip: OK ({len(rebuilt.tracks)} tracks)")


# ── Save ────────────────────────────────────────────────────────────

out_path = OUTPUT / "scene_song_demo.xy"
data = result.to_bytes()
out_path.write_bytes(data)
print(f"\nSaved: {out_path} ({len(data)} bytes)")


# ── Testing checklist ──────────────────────────────────────────────

print("\n" + "=" * 60)
print("DEVICE TESTING CHECKLIST")
print("=" * 60)
print("""
1. Load scene_song_demo.xy on OP-XY

2. Scene verification:
   [ ] Scene 1 (default): T3=P1, T4=P1
   [ ] Scene 2: T3=P2
   [ ] Scene 3: T4=P3
   [ ] Scene 4: T4=P2
   [ ] Scene 5: T3=P2

3. Song 2 sequencing:
   [ ] Switch to Song 2 mode
   [ ] Does it sequence S1 → S2 → S3 → S4 → S5?
   [ ] Does each scene apply the correct overrides?

4. Navigation:
   [ ] Can you manually switch between all 5 scenes?
   [ ] Are scene names/numbers visible in the UI?
""")

# ── Device round-trip path for full 8×9 + scenes ────────────────────

print("=" * 60)
print("FUTURE: Full 8×9 + Scenes (Device Round-Trip Path)")
print("=" * 60)
print("""
To achieve 8 tracks × 9 patterns with scenes (the ultimate goal):

1. Load output/diag_A_minimal.xy on OP-XY
   (8 tracks × 9 patterns, confirmed working)

2. On the device: add any scene override
   (e.g., Scene 2 with T3→P2)

3. Save project, transfer .xy file back to computer

4. The captured file will have:
   - 9 patterns per track (block-rotation layout)
   - Scene activation (normalized-branch layout)
   - These layouts are incompatible when generated separately,
     but device-authored files have the correct combined layout

5. Use patch_add_scenes() to programmatically add more scenes
   to the device-captured file

This bypasses the layout incompatibility between scene-activated
and multi-pattern files by letting the device handle the initial
normalization.
""")
