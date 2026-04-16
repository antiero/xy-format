#!/usr/bin/env python3
"""P-lock crash diagnostics — isolate root cause.

Creates pairs of files to test:
  A: transplant without value modification (is transplant the issue?)
  B: full donor file with value modification (is value modification the issue?)
  C: round-trip of donor file (is the donor itself the issue?)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xy.container import XYProject, TrackBlock
from xy.plocks import rewrite_standard_nonempty_values
BASELINE = "src/one-off-changes-from-default/unnamed 1.xy"
CORPUS = "src/one-off-changes-from-default"


def load(path):
    with open(path, "rb") as f:
        return XYProject.from_bytes(f.read())


def save(proj, path):
    data = proj.to_bytes()
    assert XYProject.from_bytes(data).to_bytes() == data
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    print(f"  {path} ({len(data)} bytes)")


def modify_single_param(body, new_values):
    return rewrite_standard_nonempty_values(body, new_values)


def make_ramp(n, start=0, end=32767):
    if n <= 1:
        return [end]
    return [start + (end - start) * i // (n - 1) for i in range(n)]


def main():
    base = load(BASELINE)

    # ── Test set 1: unnamed 121 T2 ──

    d121 = load(os.path.join(CORPUS, "unnamed 121.xy"))

    # C: round-trip donor (no changes)
    print("Diag C: round-trip unnamed 121")
    save(d121, "output/plock_diag/C_rt_121.xy")

    # A: transplant T2 body into baseline, no value modification
    print("Diag A: baseline + unnamed 121 T2 body (no value mod)")
    tracks = list(base.tracks)
    tracks[1] = TrackBlock(
        index=1,
        preamble=d121.tracks[1].preamble,
        body=d121.tracks[1].body,
    )
    save(XYProject(pre_track=base.pre_track, tracks=tracks), "output/plock_diag/A_transplant_t2.xy")

    # B: modify T2 values in full donor file (no transplant)
    print("Diag B: unnamed 121 + T2 values modified (no transplant)")
    mod_body = modify_single_param(d121.tracks[1].body, make_ramp(14))
    tracks_121 = list(d121.tracks)
    tracks_121[1] = TrackBlock(
        index=1,
        preamble=d121.tracks[1].preamble,
        body=mod_body,
    )
    save(XYProject(pre_track=d121.pre_track, tracks=tracks_121), "output/plock_diag/B_valmod_121.xy")

    # ── Test set 2: unnamed 35 T3 ──

    d35 = load(os.path.join(CORPUS, "unnamed 35.xy"))

    print("Diag D: round-trip unnamed 35")
    save(d35, "output/plock_diag/D_rt_35.xy")

    print("Diag E: baseline + unnamed 35 T3 body (no value mod)")
    tracks = list(base.tracks)
    tracks[2] = TrackBlock(
        index=2,
        preamble=d35.tracks[2].preamble,
        body=d35.tracks[2].body,
    )
    save(XYProject(pre_track=base.pre_track, tracks=tracks), "output/plock_diag/E_transplant_t3.xy")

    print("Diag F: unnamed 35 + T3 values modified (no transplant)")
    mod_body = modify_single_param(d35.tracks[2].body, make_ramp(16))
    tracks_35 = list(d35.tracks)
    tracks_35[2] = TrackBlock(
        index=2,
        preamble=d35.tracks[2].preamble,
        body=mod_body,
    )
    save(XYProject(pre_track=d35.pre_track, tracks=tracks_35), "output/plock_diag/F_valmod_35.xy")

    print("\nTest matrix:")
    print("  C_rt_121.xy      — raw round-trip of unnamed 121 (should work)")
    print("  A_transplant_t2  — baseline + T2 body, no value change")
    print("  B_valmod_121     — full 121 + T2 values changed")
    print("  D_rt_35.xy       — raw round-trip of unnamed 35 (should work)")
    print("  E_transplant_t3  — baseline + T3 body, no value change")
    print("  F_valmod_35      — full 35 + T3 values changed")
    print()
    print("If C crashes → donor file is bad for device")
    print("If C works, A crashes → transplant approach is wrong")
    print("If C,A work, B crashes → value modification is wrong")


if __name__ == "__main__":
    main()
