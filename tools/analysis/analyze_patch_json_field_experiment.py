"""Summarize the 2026-06 patch.json field preset-load experiment.

The experiment pairs hand-authored ``patch.json`` presets with projects where
the OP-XY loaded each preset onto T1.  It is intentionally smaller and more
controlled than the broad preset corpus: each case changes one JSON field or a
small field pair so the stored project bytes can be attributed directly.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from xy.image_writer import ImageProject
from xy.sampler_sample_inspection import encode_sampler_loop_crossfade_frames

ROOT = Path("src/preset-load-experiments/2026-06-patch-json-fields")
PRESETS = ROOT / "presets"
PROJECTS = ROOT / "presetprojs"


def _patch(case: str) -> dict:
    return json.loads((PRESETS / f"{case}.preset" / "patch.json").read_text(encoding="utf-8"))


def _project(case: str) -> ImageProject:
    return ImageProject.from_file(str(PROJECTS / f"{case}.xy"))


def _label(project: ImageProject, base: int) -> str:
    raw = bytes(project.image[base + 0x453F : base + 0x453F + 64])
    return raw.split(b"\0", 1)[0].decode("latin1", errors="replace")


def _rows() -> list[str]:
    rows = [
        "# patch.json field experiment summary",
        "",
        "| case | JSON field(s) | stored byte/word | note |",
        "| --- | --- | --- | --- |",
    ]
    for xy_path in sorted(PROJECTS.glob("*.xy")):
        case = xy_path.stem
        patch_path = PRESETS / f"{case}.preset" / "patch.json"
        if not patch_path.exists():
            continue
        patch = _patch(case)
        region = patch["regions"][0]
        project = _project(case)
        base = project.track_start(1)
        slot = base + 0x3957
        label = _label(project, base)
        note = "" if label == f"presets/{case}" else f"label is `{label}`"

        if case.startswith("dpm"):
            rows.append(
                f"| `{case}` | `playmode={region['playmode']!r}` | "
                f"`0x{project.image[slot + 0x03]:02X}` | {note} |"
            )
        elif case.startswith("slt"):
            rows.append(
                f"| `{case}` | `loop.enabled={region.get('loop.enabled', '<missing>')}`, "
                f"`loop.onrelease={region.get('loop.onrelease', '<missing>')}` | "
                f"`0x{project.image[slot + 0x03]:02X}` | {note} |"
            )
        elif case.startswith("skey"):
            rows.append(
                f"| `{case}` | `hikey={region.get('hikey')}`, `lokey={region.get('lokey')}`, "
                f"`pitch.keycenter={region.get('pitch.keycenter')}` | "
                f"`root=0x{project.image[slot]:02X}` | {note} |"
            )
        elif case.startswith("sfld"):
            rows.append(
                f"| `{case}` | `tune={region.get('tune')}`, `gain={region.get('gain')}`, "
                f"`reverse={region.get('reverse')}` | "
                f"`root=0x{project.image[slot]:02X}`, `aux=0x{project.image[slot + 4]:02X}`, "
                f"`gain=0x{project.image[slot + 5]:02X}`, `dir=0x{project.image[slot + 7]:02X}` | {note} |"
            )
        elif case.startswith("scf"):
            raw = int.from_bytes(project.image[base + 0x3953 : base + 0x3957], "little")
            expected = encode_sampler_loop_crossfade_frames(
                region["loop.crossfade"],
                region["framecount"],
            )
            rows.append(
                f"| `{case}` | `loop.crossfade={region['loop.crossfade']}`, "
                f"`framecount={region['framecount']}` | `0x{raw:08X}` | "
                f"float32 encoder {'matches' if raw == expected else f'expected 0x{expected:08X}'} |"
            )
    return rows


def main() -> None:
    print("\n".join(_rows()))


if __name__ == "__main__":
    main()
