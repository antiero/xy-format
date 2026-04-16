#!/usr/bin/env python3
"""Isolate which changes between unnamed 118 and unnamed 118b are crash-critical.

Creates test files that mix tracks from A (118) and B (118b) to narrow down
which track changes are necessary / sufficient.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from xy.container import XYProject, TrackBlock


def load(name: str) -> tuple[bytes, XYProject]:
    path = Path(__file__).resolve().parent.parent / "src" / "one-off-changes-from-default" / name
    raw = path.read_bytes()
    proj = XYProject.from_bytes(raw)
    return raw, proj


def save(proj: XYProject, name: str) -> bytes:
    outdir = Path(__file__).resolve().parent.parent / "output" / "multistep"
    outdir.mkdir(parents=True, exist_ok=True)
    data = proj.to_bytes()
    (outdir / name).write_bytes(data)
    return data


def replace_tracks(base: XYProject, donor: XYProject, indices: list[int]) -> XYProject:
    """Return a new XYProject using base, but replacing tracks at given indices with donor's."""
    new_tracks = []
    for i in range(16):
        if i in indices:
            t = donor.tracks[i]
            # Rebuild with correct index (should already match, but be safe)
            new_tracks.append(TrackBlock(index=i, preamble=t.preamble, body=t.body))
        else:
            new_tracks.append(base.tracks[i])
    return XYProject(pre_track=base.pre_track, tracks=new_tracks)


def main():
    raw_a, proj_a = load("unnamed 118.xy")
    raw_b, proj_b = load("unnamed 118b.xy")

    print(f"A (unnamed 118.xy):  {len(raw_a):,} bytes, round-trip: {proj_a.to_bytes() == raw_a}")
    print(f"B (unnamed 118b.xy): {len(raw_b):,} bytes, round-trip: {proj_b.to_bytes() == raw_b}")
    print()

    # Show which tracks differ between A and B
    print("=== Track-by-track diff A vs B ===")
    for i in range(16):
        ta = proj_a.tracks[i]
        tb = proj_b.tracks[i]
        pre_match = ta.preamble == tb.preamble
        body_match = ta.body == tb.body
        if not pre_match or not body_match:
            print(f"  Track {i:2d}: preamble {'SAME' if pre_match else 'DIFF'}, "
                  f"body {'SAME' if body_match else 'DIFF'} "
                  f"(A={len(ta.body)} B={len(tb.body)} bytes)")
    pre_match = proj_a.pre_track == proj_b.pre_track
    print(f"  pre_track: {'SAME' if pre_match else 'DIFF'} "
          f"(A={len(proj_a.pre_track)} B={len(proj_b.pre_track)} bytes)")
    print()

    # ---- v5a: Full transplant (B's T1 + B's aux tracks 8-15) ----
    # Should reconstruct B exactly
    transplant_indices = [0] + list(range(8, 16))
    proj_v5a = replace_tracks(proj_a, proj_b, transplant_indices)
    # Also need B's pre_track if it differs
    if proj_a.pre_track != proj_b.pre_track:
        proj_v5a = XYProject(pre_track=proj_b.pre_track, tracks=proj_v5a.tracks)
    data_v5a = save(proj_v5a, "v5a_full_transplant.xy")
    rt_v5a = XYProject.from_bytes(data_v5a).to_bytes() == data_v5a
    identical_to_b = data_v5a == raw_b
    print(f"v5a_full_transplant.xy: {len(data_v5a):,} bytes, round-trip: {rt_v5a}, "
          f"identical to B: {identical_to_b}")
    if not identical_to_b:
        # Debug: find where they differ
        for i in range(min(len(data_v5a), len(raw_b))):
            if data_v5a[i] != raw_b[i]:
                print(f"  First diff at offset 0x{i:04X}: v5a=0x{data_v5a[i]:02X} B=0x{raw_b[i]:02X}")
                break
        if len(data_v5a) != len(raw_b):
            print(f"  Size mismatch: v5a={len(data_v5a)} B={len(raw_b)}")

    # ---- v5b: T1 body only from B, everything else from A ----
    proj_v5b = replace_tracks(proj_a, proj_b, [0])
    data_v5b = save(proj_v5b, "v5b_t1_body_only.xy")
    rt_v5b = XYProject.from_bytes(data_v5b).to_bytes() == data_v5b
    print(f"v5b_t1_body_only.xy:   {len(data_v5b):,} bytes, round-trip: {rt_v5b}")

    # ---- v5c: Aux only from B (tracks 8-15), T1 from A ----
    proj_v5c = replace_tracks(proj_a, proj_b, list(range(8, 16)))
    data_v5c = save(proj_v5c, "v5c_aux_only.xy")
    rt_v5c = XYProject.from_bytes(data_v5c).to_bytes() == data_v5c
    print(f"v5c_aux_only.xy:       {len(data_v5c):,} bytes, round-trip: {rt_v5c}")

    # ---- v5d: T1 + aux from B (same as v5a but explicit combo name) ----
    proj_v5d = replace_tracks(proj_a, proj_b, [0] + list(range(8, 16)))
    data_v5d = save(proj_v5d, "v5d_t1_plus_aux.xy")
    rt_v5d = XYProject.from_bytes(data_v5d).to_bytes() == data_v5d
    print(f"v5d_t1_plus_aux.xy:    {len(data_v5d):,} bytes, round-trip: {rt_v5d}")

    # v5d should equal v5a (same track selection, same pre_track source)
    print(f"\nv5d identical to v5a: {data_v5d == data_v5a}")

    print("\nAll files written to output/multistep/")


if __name__ == "__main__":
    main()
