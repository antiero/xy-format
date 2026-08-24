#!/usr/bin/env python3
"""Build short, ordered OP-XY limit-certification projects.

The files are generated from a known-good baseline through the decoded-image
writer, then preflighted before they are written. They are intentionally kept
out of git; record device outcomes with ``tools/corpus_lab.py record``.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from xy.image_writer import ImageProject, build_arrangement  # noqa: E402
from xy.project_validation import validate_project_bytes  # noqa: E402

DEFAULT_BASELINE = REPO_ROOT / "src/one-off-changes-from-default/unnamed 1.xy"
PROBE_NAMES = (
    "01_scenes99.xy",
    "02_song96.xy",
    "03_patterns16.xy",
    "04_notes120.xy",
)


def _patterns(count: int) -> list[list[dict[str, int]]]:
    return [
        [{"step": (index % 16) + 1, "note": 48 + index, "gate_ticks": 120}]
        for index in range(count)
    ]


def _scenes(count: int, pattern_count: int) -> list[dict[int, int]]:
    return [{1: index % pattern_count} for index in range(count)]


def _notes120() -> list[dict[str, int]]:
    return [
        {
            "step": (index % 60) + 1,
            "note": 48 + (index // 60) * 12,
            "velocity": 72 + (index % 24),
            "gate_ticks": 120,
        }
        for index in range(120)
    ]


def build_probe_bytes(baseline: Path = DEFAULT_BASELINE) -> dict[str, bytes]:
    patterns16 = _patterns(16)
    scenes99 = _scenes(99, len(patterns16))
    probes = {
        "01_scenes99.xy": build_arrangement(
            str(baseline),
            {1: patterns16},
            scenes=scenes99,
            song_chain=[0],
            force_scene_presence=True,
        ),
        "02_song96.xy": build_arrangement(
            str(baseline),
            {1: patterns16},
            scenes=scenes99,
            song_chain=list(range(96)),
            force_scene_presence=True,
        ),
        "03_patterns16.xy": build_arrangement(
            str(baseline),
            {1: patterns16},
            scenes=_scenes(16, len(patterns16)),
            song_chain=list(range(16)),
            force_scene_presence=True,
        ),
        "04_notes120.xy": build_arrangement(
            str(baseline),
            {1: [{"steps": 64, "notes": _notes120()}]},
            scenes=[{1: 0}],
            song_chain=[0],
            force_scene_presence=True,
        ),
    }

    for name, data in probes.items():
        project = ImageProject.from_bytes(data)
        project.set_click_volume(0)
        data = project.to_bytes()
        report = validate_project_bytes(data, generated=True)
        if report.errors:
            raise ValueError(f"{name} failed preflight:\n{report.describe()}")
        probes[name] = data
    return probes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "output/limit-probes",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    probes = build_probe_bytes(args.baseline)
    for name in PROBE_NAMES:
        data = probes[name]
        destination = args.output_dir / name
        destination.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()[:12]
        print(f"{name}: {len(data):,} bytes sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
