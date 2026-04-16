#!/usr/bin/env python3
"""Write p-lock demonstration .xy files.

Creates 3 demo files using template transplant from corpus specimens.
Each file copies a known-good track body (with p-lock data) from a corpus
file, modifies p-lock value bytes in-place, and transplants the body into
a baseline project.  All structural bytes (signatures, markers, constants)
are preserved exactly — only u16 LE value fields change.

Output files:
  1. plock_drum_t2.xy   — alternating high/low on T2 Drum (param_id 0x5E)
  2. plock_synth_t3.xy  — smooth ramp on T3 Prism (param_id 0x08)
  3. plock_multi_t3.xy  — two-lane ramps on T3 Prism (3 CCs, 2 modified)

None of these contain note events — p-lock automation only.  Visible in
device step-view but not audible without adding notes on-device.

IMPORTANT: All p-lock values must be >= 256.  The firmware uses val_hi
(byte[2] of each 5-byte entry) to distinguish 3-byte empty entries from
5-byte data entries.  When val_hi is 0x00 (value < 256), the firmware
reads only 3 bytes, gets misaligned, and crashes with num_patterns > 0.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xy.container import XYProject
from xy.plocks import (
    list_standard_nonempty_values,
    rewrite_standard_values_for_param_groups,
)
from xy.project_builder import (
    rewrite_track_standard_plock_groups,
    rewrite_track_standard_plock_values,
    transplant_track,
)

BASELINE = "src/one-off-changes-from-default/unnamed 1.xy"
CORPUS = "src/one-off-changes-from-default"

# Minimum valid p-lock value.  The firmware uses val_hi (value >> 8) to
# distinguish 3-byte empty entries from 5-byte data entries.  Values below
# 256 have val_hi == 0x00, causing the parser to read only 3 bytes and
# misalign all subsequent entries → crash (num_patterns > 0).
MIN_PLOCK_VALUE = 256


def load_project(path: str) -> XYProject:
    with open(path, "rb") as f:
        return XYProject.from_bytes(f.read())


def modify_multi_param(
    body: bytes,
    lane_a_ids: set[int],
    lane_b_ids: set[int],
    lane_a_values: list[int],
    lane_b_values: list[int],
) -> bytes:
    """Rewrite value bytes for two lanes in a multi-param body.

    Entries whose param_id is in lane_a_ids get values from lane_a_values.
    Entries whose param_id is in lane_b_ids get values from lane_b_values.
    All other entries (separators, third lane) are left unchanged.
    """
    modified, _counts = rewrite_standard_values_for_param_groups(
        body,
        [
            (lane_a_ids, lane_a_values),
            (lane_b_ids, lane_b_values),
        ],
    )
    return modified


def read_values(body: bytes) -> list[tuple[int, int]]:
    """Read back all (param_id, u16_value) pairs from a body's p-lock table."""
    return list_standard_nonempty_values(body)


def make_ramp(n: int, start: int = MIN_PLOCK_VALUE, end: int = 32767) -> list[int]:
    """Generate n values ramping linearly from start to end.

    Both start and end are clamped to [MIN_PLOCK_VALUE, 32767].
    """
    start = max(MIN_PLOCK_VALUE, start)
    end = max(MIN_PLOCK_VALUE, end)
    if n <= 1:
        return [end]
    return [start + (end - start) * i // (n - 1) for i in range(n)]


def make_alternating(n: int, lo: int = MIN_PLOCK_VALUE, hi: int = 32767) -> list[int]:
    """Generate n alternating low/high values.

    Both lo and hi are clamped to [MIN_PLOCK_VALUE, 32767].
    """
    lo = max(MIN_PLOCK_VALUE, lo)
    hi = max(MIN_PLOCK_VALUE, hi)
    return [lo if i % 2 == 0 else hi for i in range(n)]


def byte_diff_summary(orig: bytes, modified: bytes) -> str:
    """Return a short summary of byte differences between two bodies."""
    if len(orig) != len(modified):
        return f"length differs: {len(orig)} vs {len(modified)}"
    diffs = sum(1 for a, b in zip(orig, modified) if a != b)
    return f"{diffs} bytes differ out of {len(orig)}"


def write_output(project: XYProject, path: str) -> None:
    data = project.to_bytes()
    # Round-trip sanity check
    check = XYProject.from_bytes(data)
    assert check.to_bytes() == data, "Round-trip verification failed!"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    print(f"  Written: {path} ({len(data)} bytes)")


# ── File 1 ────────────────────────────────────────────────────────────


def build_plock_drum_t2() -> None:
    """Alternating high/low p-lock on T2 Drum (param_id 0x5E = CC13)."""
    print("\n--- File 1: plock_drum_t2.xy ---")
    print("  Template: unnamed 121, T2 (Drum, type 0x05)")
    print(f"  Pattern:  alternating {MIN_PLOCK_VALUE} / 32767 on 14 steps")

    base = load_project(BASELINE)
    donor = load_project(os.path.join(CORPUS, "unnamed 121.xy"))

    donor_body = donor.tracks[1].body   # T2 = index 1

    # 14 active p-lock values for param_id 0x5E
    values = make_alternating(14)
    proj = transplant_track(base, donor, track_index=2, copy_preamble=True)
    proj = rewrite_track_standard_plock_values(
        proj,
        track_index=2,
        values=values,
    )
    modified = proj.tracks[1].body

    # Verify read-back
    entries = read_values(modified)
    non_sep = [(p, v) for p, v in entries]
    assert len(non_sep) == 14, f"expected 14 entries, got {len(non_sep)}"
    for i, (pid, val) in enumerate(non_sep):
        expected = values[i]
        assert val == expected, f"entry {i}: got {val}, expected {expected}"

    print(f"  Diff: {byte_diff_summary(donor_body, modified)}")
    print(f"  Verified: {len(non_sep)} values match pattern")

    write_output(proj, "output/plock_drum_t2.xy")


# ── File 2 ────────────────────────────────────────────────────────────


def build_plock_synth_t3() -> None:
    """Smooth ramp p-lock on T3 Prism (param_id 0x08 = CC12 grid-entered)."""
    print("\n--- File 2: plock_synth_t3.xy ---")
    print("  Template: unnamed 35, T3 (Prism, type 0x07)")
    print(f"  Pattern:  ramp {MIN_PLOCK_VALUE} -> 32767 over 16 steps")

    base = load_project(BASELINE)
    donor = load_project(os.path.join(CORPUS, "unnamed 35.xy"))

    donor_body = donor.tracks[2].body   # T3 = index 2

    # 16 active p-lock values for param_id 0x08
    values = make_ramp(16, start=MIN_PLOCK_VALUE, end=32767)
    proj = transplant_track(base, donor, track_index=3, copy_preamble=True)
    proj = rewrite_track_standard_plock_values(
        proj,
        track_index=3,
        values=values,
    )
    modified = proj.tracks[2].body

    entries = read_values(modified)
    assert len(entries) == 16, f"expected 16 entries, got {len(entries)}"
    for i, (pid, val) in enumerate(entries):
        assert val == values[i], f"entry {i}: got {val}, expected {values[i]}"

    print(f"  Diff: {byte_diff_summary(donor_body, modified)}")
    print(f"  Verified: {len(entries)} values match ramp")

    write_output(proj, "output/plock_synth_t3.xy")


# ── File 3 ────────────────────────────────────────────────────────────


def build_plock_multi_t3() -> None:
    """Two-lane ramps on T3 Prism (3 CCs: CC32+CC12+CC14, 2 modified)."""
    print("\n--- File 3: plock_multi_t3.xy ---")
    print("  Template: unnamed 125, T3 (Prism, type 0x07, multi-CC)")
    print(f"  Pattern:  lane A ramp {MIN_PLOCK_VALUE}->32767 (12 vals), "
          f"lane B ramp 32767->{MIN_PLOCK_VALUE} (11 vals)")

    base = load_project(BASELINE)
    donor = load_project(os.path.join(CORPUS, "unnamed 125.xy"))

    donor_body = donor.tracks[2].body

    # Multi-param entry layout (from corpus analysis):
    #   Lane A: param_ids {0x08, 0x18} — 12 entries (CC12 = Param 1)
    #   Lane B: param_ids {0x4C, 0x30} — 11 entries (CC14 = Param 3)
    #   Lane C: param_id  0xD8         —  1 entry   (CC32 = Filter Cutoff)
    #   Separators: param_id 0x00      — 12 entries  (step boundaries)
    # We modify lanes A and B; leave C and separators unchanged.
    lane_a_ids = {0x08, 0x18}
    lane_b_ids = {0x4C, 0x30}

    lane_a_values = make_ramp(12, start=MIN_PLOCK_VALUE, end=32767)
    lane_b_values = make_ramp(11, start=32767, end=MIN_PLOCK_VALUE)

    proj = transplant_track(base, donor, track_index=3, copy_preamble=True)
    proj, counts = rewrite_track_standard_plock_groups(
        proj,
        track_index=3,
        groups=[
            (lane_a_ids, lane_a_values),
            (lane_b_ids, lane_b_values),
        ],
    )
    assert counts == [12, 11], f"unexpected consumption counts: {counts}"

    # Keep a direct parser-path cross-check for script diagnostics.
    direct_modified = modify_multi_param(
        donor_body, lane_a_ids, lane_b_ids, lane_a_values, lane_b_values
    )
    proj_body_entries = read_values(proj.tracks[2].body)
    direct_body_entries = read_values(direct_modified)
    assert proj_body_entries == direct_body_entries, "builder rewrite diverged from direct rewrite"

    # Verify
    entries = read_values(proj.tracks[2].body)
    a_vals = [v for p, v in entries if p in lane_a_ids]
    b_vals = [v for p, v in entries if p in lane_b_ids]
    sep_vals = [v for p, v in entries if p == 0x00]
    c_vals = [v for p, v in entries if p == 0xD8]

    assert len(a_vals) == 12, f"lane A: expected 12, got {len(a_vals)}"
    assert len(b_vals) == 11, f"lane B: expected 11, got {len(b_vals)}"
    assert a_vals == lane_a_values, "lane A values mismatch"
    assert b_vals == lane_b_values, "lane B values mismatch"

    # Separators and lane C should be unchanged
    orig_entries = read_values(donor_body)
    orig_seps = [v for p, v in orig_entries if p == 0x00]
    orig_c = [v for p, v in orig_entries if p == 0xD8]
    assert sep_vals == orig_seps, "separator values changed unexpectedly"
    assert c_vals == orig_c, "lane C values changed unexpectedly"

    print(f"  Diff: {byte_diff_summary(donor_body, proj.tracks[2].body)}")
    print(f"  Verified: lane A={len(a_vals)}, lane B={len(b_vals)}, "
          f"seps={len(sep_vals)} (unchanged), lane C={len(c_vals)} (unchanged)")

    write_output(proj, "output/plock_multi_t3.xy")


# ── Main ──────────────────────────────────────────────────────────────


def main():
    print("P-Lock Demonstration File Generator")
    print("=" * 50)

    build_plock_drum_t2()
    build_plock_synth_t3()
    build_plock_multi_t3()

    print("\n" + "=" * 50)
    print("All 3 files written successfully.")
    print("Load on OP-XY to verify p-lock data visible in step view.")


if __name__ == "__main__":
    main()
