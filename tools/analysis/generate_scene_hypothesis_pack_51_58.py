#!/usr/bin/env python3
"""Generate staged scene hypothesis files (51-58) on an all-tracks base.

Base characteristics:
- Scene2 context bytes already set (`pre[0x0F:0x12] = 01 01 00`)
- Tracks 1..8 all have 9 patterns available
- No existing scene-record payload between descriptor tail and sentinel
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xy.container import XYProject


BASE_PATH = ROOT / "output/from-midi/03_time-after-time_song_arranged_s2_with_pretrack.xy"
OUT_DIR = ROOT / "output/scene-probes"


@dataclass(frozen=True)
class Case:
    filename: str
    insert_hex: str
    risk: str
    approach: str


CASES: tuple[Case, ...] = (
    Case("51_s2_base_ctrl.xy", "", "safe", "control"),
    Case("52_s2_t4p2_tail8.xy", "010100001a010000", "safe", "tail8"),
    Case("53_s2_t4p3_tail8.xy", "010200001a010000", "safe", "tail8"),
    Case("54_s2_t5p2_tail8.xy", "0201000019010000", "medium", "tail8"),
    Case("55_s2_t5p2_tail9.xy", "000201000019010000", "medium", "tail9"),
    Case(
        "56_s2_t4p2_t5p2_two8.xy",
        "010100001a0100000201000019010000",
        "medium-high",
        "two-tail8",
    ),
    Case("57_s2_bleez_r11.xy", "0808000008080300001601", "high", "bleez-r11"),
    Case("58_s2_bleez_r11_t5guess.xy", "0808020008080100001601", "high", "bleez-r11-variant"),
)


def _find_insert_offset(pre: bytes) -> int:
    # Branch layout: ... descriptor_tail ... 00 00 FF 00 00 ...
    handle_start = None
    for i in range(0x50, len(pre) - 2):
        if pre[i : i + 3] == b"\xff\x00\x00":
            handle_start = i
            break
    if handle_start is None:
        raise ValueError("failed to locate pre-track handle table")
    if handle_start < 2:
        raise ValueError("handle table too early")
    if pre[handle_start - 2 : handle_start] != b"\x00\x00":
        raise ValueError("expected 00 00 sentinel immediately before handle table")
    return handle_start - 2


def main() -> int:
    base_raw = BASE_PATH.read_bytes()
    base = XYProject.from_bytes(base_raw)
    base_pre = base.pre_track
    insert_at = _find_insert_offset(base_pre)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Base: {BASE_PATH}")
    print(
        f"Base size={len(base_raw)} pre={len(base_pre)} ctl={base_pre[0x0F:0x12].hex()} "
        f"insert_at=0x{insert_at:02x}"
    )

    for case in CASES:
        insert = bytes.fromhex(case.insert_hex)
        pre = bytearray(base_pre[:insert_at] + insert + base_pre[insert_at:])
        # Keep Scene2 target control tuple fixed.
        pre[0x0F:0x12] = b"\x01\x01\x00"

        project = XYProject(pre_track=bytes(pre), tracks=base.tracks)
        raw = project.to_bytes()
        if XYProject.from_bytes(raw).to_bytes() != raw:
            raise RuntimeError(f"round-trip validation failed for {case.filename}")

        out_path = OUT_DIR / case.filename
        out_path.write_bytes(raw)
        print(
            f"{case.filename:28s} size={len(raw):5d} pre={len(pre):3d} "
            f"insert={insert.hex()} risk={case.risk} approach={case.approach}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
