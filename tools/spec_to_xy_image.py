#!/usr/bin/env python3
"""Compile a midi-to-xy spec JSON into a .xy via the image writer.

This is the v2 backend: MIDI -> (existing tools/midi_to_xy.py front end)
-> spec JSON -> decoded-image assembly (xy/image_writer.build_arrangement)
-> canonical RLE encode. No scaffolds, donors, descriptor lookups,
velocity nudges, or ghost placeholder notes.

Usage:
    python tools/spec_to_xy_image.py spec.json -o out.xy [--no-scenes]
        [--no-song] [--keep-empty-tracks] [--baseline FILE]

By default: empty tracks are left untouched (sparse topologies are fine
when the state is coherent), velocity<=1 ghost notes are dropped, scene k
selects pattern k on every content track, and Song 1 chains the scenes
with loop on.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xy.image_writer import ImageProject, build_arrangement  # noqa: E402

DEFAULT_BASELINE = "src/one-off-changes-from-default/unnamed 1.xy"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--no-scenes", action="store_true")
    ap.add_argument("--no-song", action="store_true")
    ap.add_argument("--keep-empty-tracks", action="store_true",
                    help="emit pattern clones for tracks with no notes")
    ap.add_argument("--min-velocity", type=int, default=2,
                    help="drop notes below this velocity (ghost placeholders)")
    args = ap.parse_args()

    spec = json.load(open(args.spec))
    min_velocity = int(spec.get("min_velocity", args.min_velocity))
    tracks: dict[int, list[list[dict]]] = {}
    for t in spec["tracks"]:
        pats = [
            [n for n in (p or []) if n.get("velocity", 100) >= min_velocity]
            for p in t["patterns"]
        ]
        if any(pats) or args.keep_empty_tracks:
            tracks[t["track"]] = pats
    if not tracks:
        raise SystemExit("spec has no notes")

    n_pat = max(len(p) for p in tracks.values())
    scenes = None
    scene_mutes = None
    song_chain = None
    if not args.no_scenes:
        raw_scenes = spec.get("scenes")
        if raw_scenes is None:
            scenes = [
                {t: min(k, len(pats) - 1) for t, pats in tracks.items()}
                for k in range(n_pat)
            ]
            scene_mutes = None
        else:
            scenes = [
                {int(track): int(pattern) for track, pattern in row.items()}
                for row in raw_scenes
            ]
            scene_mutes = [
                [int(track) for track in muted_tracks]
                for muted_tracks in spec.get("scene_mutes", [])
            ]
        if not args.no_song:
            song_chain = [
                int(scene) for scene in spec.get("song_chain", list(range(len(scenes))))
            ]

    template_tracks = {
        int(track): int(source)
        for track, source in spec.get("track_template_sources", {}).items()
    }

    out = build_arrangement(
        args.baseline,
        tracks,
        scenes=scenes,
        scene_mutes=scene_mutes,
        song_chain=song_chain,
        template_tracks=template_tracks,
        force_scene_presence=bool(spec.get("force_scene_presence", False)),
    )
    if "tempo_bpm" in spec:
        project = ImageProject.from_bytes(out)
        project.set_tempo(float(spec["tempo_bpm"]))
        out = project.to_bytes()
    open(args.output, "wb").write(out)
    total = sum(len(p) for ps in tracks.values() for p in ps)
    print(
        f"wrote {args.output}: {len(out):,} bytes — "
        f"{len(tracks)} track(s), {n_pat} patterns, {total} notes"
        f"{', %d scenes + song chain' % len(scenes) if song_chain else ''}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
