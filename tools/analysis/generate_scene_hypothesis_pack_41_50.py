#!/usr/bin/env python3
"""Generate staged scene hypothesis files (41-50) from a known-safe base.

Pack design:
- 41-42: safe controls (known family, same scene target)
- 43-46: medium-risk extrapolation to T5-T8 using descriptor-like track tags
- 47-50: high-risk T2/T1 encodings with two alternative schema guesses each
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xy.container import XYProject
BASE_PATH = ROOT / "src/one-off-changes-from-default/12_scene_s2_t3p1.xy"
OUT_DIR = ROOT / "output/scene-probes"


@dataclass(frozen=True)
class Case:
    filename: str
    scene_region_hex: str
    risk: str
    hypothesis: str


CASES: tuple[Case, ...] = (
    Case(
        "41_s2_t4p2_ctrl.xy",
        "010100001a010000",
        "safe",
        "Control: should match base behavior (Scene2 T4=P2 only).",
    ),
    Case(
        "42_s2_t4p3_safe.xy",
        "010200001a010000",
        "safe",
        "Pattern-index bump on known T4 form (expect Scene2 T4=P3).",
    ),
    Case(
        "43_s2_t5p2_gap.xy",
        "0201000019010000",
        "medium",
        "Descriptor-like extrapolation to T5 tag/gap.",
    ),
    Case(
        "44_s2_t6p2_gap.xy",
        "0301000018010000",
        "medium",
        "Descriptor-like extrapolation to T6 tag/gap.",
    ),
    Case(
        "45_s2_t7p2_gap.xy",
        "0401000017010000",
        "medium",
        "Descriptor-like extrapolation to T7 tag/gap.",
    ),
    Case(
        "46_s2_t8p2_gap.xy",
        "0501000016010000",
        "medium",
        "Descriptor-like extrapolation to T8 tag/gap.",
    ),
    Case(
        "47_s2_t2p2_a.xy",
        "000100001c010000",
        "high",
        "T2 variant A: pseudo-gap form with T2 tag.",
    ),
    Case(
        "48_s2_t2p2_b.xy",
        "00001c010000",
        "high",
        "T2 variant B: short descriptor-like tail (length-changing).",
    ),
    Case(
        "49_s2_t1p2_a.xy",
        "000100001d010000",
        "high",
        "T1 variant A: pseudo-gap form with T1 tag.",
    ),
    Case(
        "50_s2_t1p2_b.xy",
        "001d010000",
        "high",
        "T1 variant B: short descriptor-like tail (length-changing).",
    ),
)


def _find_scene_region_bounds(pre: bytes) -> tuple[int, int]:
    handle_start = None
    for i in range(0x50, len(pre) - 2):
        if pre[i : i + 3] == b"\xff\x00\x00":
            handle_start = i
            break
    if handle_start is None:
        raise ValueError("failed to locate pre-track handle table")

    desc_start = None
    for i in range(0x50, handle_start):
        if pre[i] == 0x1E:
            desc_start = i
            break
    if desc_start is None:
        raise ValueError("failed to locate descriptor token 0x1E")

    region_start = desc_start + 4
    region_end = handle_start
    if region_end < region_start:
        raise ValueError("invalid scene-region bounds")
    return region_start, region_end


def _iter_generated(base_project: XYProject, cases: Iterable[Case]) -> Iterable[tuple[Case, XYProject, bytes]]:
    base_pre = base_project.pre_track
    start, end = _find_scene_region_bounds(base_pre)

    for case in cases:
        scene_region = bytes.fromhex(case.scene_region_hex)
        new_pre = bytearray(base_pre[:start] + scene_region + base_pre[end:])

        # Keep Scene2 target control tuple fixed in this pack.
        if len(new_pre) < 0x12:
            raise ValueError("pre-track too short after patch")
        new_pre[0x0F:0x12] = b"\x01\x01\x00"

        project = XYProject(pre_track=bytes(new_pre), tracks=base_project.tracks)
        yield case, project, scene_region


def main() -> int:
    base = XYProject.from_bytes(BASE_PATH.read_bytes())
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Base: {BASE_PATH}")
    print(f"Base pre-track len: {len(base.pre_track)}")

    for case, project, scene_region in _iter_generated(base, CASES):
        out_path = OUT_DIR / case.filename
        raw = project.to_bytes()
        reparsed = XYProject.from_bytes(raw)
        if reparsed.to_bytes() != raw:
            raise RuntimeError(f"round-trip validation failed for {case.filename}")
        out_path.write_bytes(raw)

        pre = project.pre_track
        print(
            f"{case.filename:24s} size={len(raw):5d} pre={len(pre):3d} "
            f"ctl={pre[0x0F:0x12].hex()} scene={scene_region.hex()} risk={case.risk}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
