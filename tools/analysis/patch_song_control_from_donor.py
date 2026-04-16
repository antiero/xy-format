#!/usr/bin/env python3
"""Patch minimal song-control bytes from a donor project into a target project.

Current conservative mode only copies Track 9 pattern-1 preamble byte0.
This is used for crash-safe A/B experiments on top of known-pass files.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xy.container import TrackBlock, XYProject
from xy.scaffold_writer import LogicalEntry, extract_logical_entries


def _rebuild_project(template: XYProject, entries: list[LogicalEntry]) -> XYProject:
    if len(entries) < 16:
        raise ValueError(f"need >=16 logical entries, got {len(entries)}")

    tracks: list[TrackBlock] = []
    for i in range(15):
        entry = entries[i]
        tracks.append(TrackBlock(index=i, preamble=entry.preamble, body=entry.body))

    overflow = entries[15:]
    first = overflow[0]
    parts = [first.body]
    for entry in overflow[1:]:
        parts.append(entry.preamble)
        parts.append(entry.body)
    tracks.append(TrackBlock(index=15, preamble=first.preamble, body=b"".join(parts)))
    return XYProject(pre_track=template.pre_track, tracks=tracks)


def _index(entries: list[LogicalEntry]) -> dict[tuple[int, int], int]:
    return {(entry.track, entry.pattern): i for i, entry in enumerate(entries)}


def _patch_t9_pre0_from_donor(target: list[LogicalEntry], donor: list[LogicalEntry]) -> list[LogicalEntry]:
    t_idx = _index(target)
    d_idx = _index(donor)

    key = (9, 1)
    if key not in t_idx or key not in d_idx:
        raise ValueError("missing logical entry for track 9 pattern 1")

    ti = t_idx[key]
    di = d_idx[key]
    target_entry = target[ti]
    donor_entry = donor[di]

    pre = bytearray(target_entry.preamble)
    pre[0] = donor_entry.preamble[0]
    target[ti] = replace(target_entry, preamble=bytes(pre))
    return target


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True, help="target .xy (base content)")
    p.add_argument("--donor", required=True, help="donor .xy (song-control source)")
    p.add_argument("-o", "--output", required=True, help="output .xy path")
    return p


def main() -> int:
    args = _parser().parse_args()

    target_path = Path(args.target).expanduser().resolve()
    donor_path = Path(args.donor).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    target = XYProject.from_bytes(target_path.read_bytes())
    donor = XYProject.from_bytes(donor_path.read_bytes())

    target_entries = extract_logical_entries(target)
    donor_entries = extract_logical_entries(donor)
    target_entries = _patch_t9_pre0_from_donor(target_entries, donor_entries)

    patched = _rebuild_project(target, target_entries)
    raw = patched.to_bytes()

    # Structural sanity
    reparsed = XYProject.from_bytes(raw)
    if reparsed.to_bytes() != raw:
        raise RuntimeError("round-trip validation failed")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    print(f"Wrote {len(raw)} bytes -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
