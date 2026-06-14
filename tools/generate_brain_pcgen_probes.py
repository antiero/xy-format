"""Generate T9 Brain key/scale PC-authored bucket edge-case probes.

Writes lo/hi raw encoder words per bucket using:

    bucket = floor(raw * N / 0x80000000)
    lo(k)  = ceil(k * M / N)
    hi(k)  = floor(((k + 1) * M - 1) / N)

See src/aux-track-probes/2026-06-t09-brain/pc-generated-validation/README.md.
"""

from __future__ import annotations

from pathlib import Path

from xy.image_writer import ImageProject
from xy.rle import encode_project

M = 0x80000000
BRAIN_TRACK = 9
BRAIN_PARAM_BASE = 0x3857
MODE_MANUAL = 0x0FFFFFFF
MODE_KEY_EDIT = 0x2FFFFFFE

KEY_LABELS = (
    "c",
    "csharp",
    "d",
    "dsharp",
    "e",
    "f",
    "fsharp",
    "g",
    "gsharp",
    "a",
    "asharp",
    "b",
)
SCALE_LABELS = (
    "major",
    "dorian",
    "phrygian",
    "lydian",
    "mixolydian",
    "minor",
    "locrian",
)

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "src/aux-track-probes/2026-06-t09-brain/t09-brain-baseline.xy"
OUT_DIR = ROOT / "src/aux-track-probes/2026-06-t09-brain/pc-generated-validation"


def bucket_ranges(n: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for k in range(n):
        lo = (k * M + n - 1) // n
        hi = ((k + 1) * M - 1) // n
        ranges.append((lo, hi))
    return ranges


def _set_brain_param_words(
    project: ImageProject,
    *,
    mode: int,
    key: int,
    scale: int,
    link: int = 0,
) -> None:
    base = project.track_start(BRAIN_TRACK) + BRAIN_PARAM_BASE
    for index, value in enumerate((mode, key, scale, link)):
        project.image[base + index * 4 : base + index * 4 + 4] = value.to_bytes(
            4, "little"
        )
    project.mark_edited(BRAIN_TRACK)


def _write_probe(path: Path, *, mode: int, key: int, scale: int) -> None:
    project = ImageProject.from_file(str(BASELINE))
    _set_brain_param_words(project, mode=mode, key=key, scale=scale)
    path.write_bytes(encode_project(project.header, bytes(project.image)))


def _slug(label: str) -> str:
    return label.replace("#", "sharp").lower()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("pcgen-*.xy"):
        old.unlink()

    for index, label in enumerate(KEY_LABELS):
        lo, hi = bucket_ranges(12)[index]
        for edge, raw in (("lo", lo), ("hi", hi)):
            name = f"pcgen-expect-key-{_slug(label)}-{edge}-{raw:08x}.xy"
            _write_probe(OUT_DIR / name, mode=MODE_KEY_EDIT, key=raw, scale=0)

    for index, label in enumerate(SCALE_LABELS):
        lo, hi = bucket_ranges(7)[index]
        for edge, raw in (("lo", lo), ("hi", hi)):
            name = f"pcgen-expect-scale-{label}-{edge}-{raw:08x}.xy"
            _write_probe(OUT_DIR / name, mode=MODE_MANUAL, key=0, scale=raw)

    print(f"Wrote {len(list(OUT_DIR.glob('pcgen-*.xy')))} probes to {OUT_DIR}")


if __name__ == "__main__":
    main()
