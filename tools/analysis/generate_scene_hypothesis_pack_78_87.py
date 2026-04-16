#!/usr/bin/env python3
"""Generate scene probes 78-87 from bleez35 hybrid baseline.

Goals:
1. Test whether Scene2/T3=P9 is represented by "no override" in the R11 lane.
2. Sweep Scene3/T7 across P2..P9 using the decoded matrix-vector byte lane.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xy.container import XYProject


BASE_PATH = ROOT / "output/scene-probes/66_a_bleez35_baseline.xy"
OUT_DIR = ROOT / "output/scene-probes"

# Baseline structure guard (66 / bleez35 family).
_REGION_START = 0x55
_REGION_END = 0x76
_REC2_START = 0x5C
_REC2_END = 0x67  # exclusive
_T7_BYTE = 0x6E

_EXPECTED_REGION = bytes.fromhex(
    "08 08 06 00 00 16 01"
    " 08 08 00 00 08 08 03 00 00 16 01"
    " 08 08 01 00 00 00 08 08 01 00 00 16 01"
    " 00 00"
)


@dataclass(frozen=True)
class Case:
    filename: str
    mode: str
    t7_value: int | None = None
    hypothesis: str = ""


CASES: tuple[Case, ...] = (
    Case(
        "78_a_s2_t3p9_nooverride_droprec2.xy",
        mode="drop_rec2",
        hypothesis="remove 11B R11 rec2 override record entirely (S2/T3 no-override P9 hypothesis)",
    ),
    Case(
        "79_b_s2_t3p9_nooverride_droprec2_ord01.xy",
        mode="drop_rec2_ord01",
        hypothesis="drop rec2 + pre[0x0F] 02->01 (count-coupled no-override hypothesis)",
    ),
    Case(
        "80_c_s3_t7p2_matrix_lane.xy",
        mode="t7_sweep",
        t7_value=0x01,
        hypothesis="matrix lane byte @0x6E = 0x01 (Scene3/T7 P2 candidate)",
    ),
    Case(
        "81_d_s3_t7p3_matrix_lane.xy",
        mode="t7_sweep",
        t7_value=0x02,
        hypothesis="matrix lane byte @0x6E = 0x02 (Scene3/T7 P3 candidate)",
    ),
    Case(
        "82_e_s3_t7p4_matrix_lane.xy",
        mode="t7_sweep",
        t7_value=0x03,
        hypothesis="matrix lane byte @0x6E = 0x03 (Scene3/T7 P4 candidate)",
    ),
    Case(
        "83_f_s3_t7p5_matrix_lane.xy",
        mode="t7_sweep",
        t7_value=0x04,
        hypothesis="matrix lane byte @0x6E = 0x04 (Scene3/T7 P5 candidate)",
    ),
    Case(
        "84_g_s3_t7p6_matrix_lane.xy",
        mode="t7_sweep",
        t7_value=0x05,
        hypothesis="matrix lane byte @0x6E = 0x05 (Scene3/T7 P6 candidate)",
    ),
    Case(
        "85_h_s3_t7p7_matrix_lane.xy",
        mode="t7_sweep",
        t7_value=0x06,
        hypothesis="matrix lane byte @0x6E = 0x06 (Scene3/T7 P7 candidate)",
    ),
    Case(
        "86_i_s3_t7p8_matrix_lane.xy",
        mode="t7_sweep",
        t7_value=0x07,
        hypothesis="matrix lane byte @0x6E = 0x07 (Scene3/T7 P8 candidate)",
    ),
    Case(
        "87_j_s3_t7p9_matrix_lane_ctrl.xy",
        mode="t7_sweep",
        t7_value=0x08,
        hypothesis="matrix lane byte @0x6E = 0x08 (Scene3/T7 P9 control, baseline value)",
    ),
)


def _assert_base(pre: bytes) -> None:
    if pre[_REGION_START:_REGION_END] != _EXPECTED_REGION:
        raise ValueError("baseline scene region mismatch; aborting to avoid unsafe patching")
    if pre[_T7_BYTE] != 0x08:
        raise ValueError(f"unexpected baseline T7 lane byte at 0x{_T7_BYTE:02X}")
    if pre[0x0F] != 0x02:
        raise ValueError(f"unexpected baseline pre[0x0F]=0x{pre[0x0F]:02X} (expected 0x02)")


def _build_pre(base_pre: bytes, case: Case) -> bytes:
    if case.mode == "drop_rec2":
        return base_pre[:_REC2_START] + base_pre[_REC2_END:]
    if case.mode == "drop_rec2_ord01":
        out = bytearray(base_pre[:_REC2_START] + base_pre[_REC2_END:])
        out[0x0F] = 0x01
        return bytes(out)
    if case.mode == "t7_sweep":
        if case.t7_value is None:
            raise ValueError("t7_sweep case missing t7_value")
        out = bytearray(base_pre)
        out[_T7_BYTE] = case.t7_value
        return bytes(out)
    raise ValueError(f"unknown mode: {case.mode}")


def main() -> int:
    base_raw = BASE_PATH.read_bytes()
    base = XYProject.from_bytes(base_raw)
    _assert_base(base.pre_track)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Base: {BASE_PATH}")
    print(
        f"Base size={len(base_raw)} pre={len(base.pre_track)} ctl={base.pre_track[0x0F:0x12].hex()}"
    )

    for case in CASES:
        new_pre = _build_pre(base.pre_track, case)
        project = XYProject(pre_track=new_pre, tracks=base.tracks)
        raw = project.to_bytes()
        if XYProject.from_bytes(raw).to_bytes() != raw:
            raise RuntimeError(f"round-trip validation failed for {case.filename}")

        out_path = OUT_DIR / case.filename
        out_path.write_bytes(raw)
        print(
            f"{case.filename:34s} size={len(raw):5d} pre={len(new_pre):3d} "
            f"ctl={new_pre[0x0F:0x12].hex()} | {case.hypothesis}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
