#!/usr/bin/env python3
"""Generate scene probes 72-77 from the validated bleez35 hybrid baseline.

Pack goals:
1. Extend the proven R11 `bb` walk for Scene2/T3 from P4 to P9.
2. Add one explicit non-T3 probe by changing Scene3/T7 in the decoded matrix
   record lane (R13 payload).
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


@dataclass(frozen=True)
class Case:
    filename: str
    edits: tuple[tuple[int, int], ...]
    hypothesis: str


CASES: tuple[Case, ...] = (
    Case(
        "72_a_r11_t3p5_candidate.xy",
        ((0x5F, 0x04),),
        "R11 rec2[3]=0x04 => Scene2/T3=P5 candidate",
    ),
    Case(
        "73_b_r11_t3p6_candidate.xy",
        ((0x5F, 0x05),),
        "R11 rec2[3]=0x05 => Scene2/T3=P6 candidate",
    ),
    Case(
        "74_c_r11_t3p7_candidate.xy",
        ((0x5F, 0x06),),
        "R11 rec2[3]=0x06 => Scene2/T3=P7 candidate",
    ),
    Case(
        "75_d_r11_t3p8_candidate.xy",
        ((0x5F, 0x07),),
        "R11 rec2[3]=0x07 => Scene2/T3=P8 candidate",
    ),
    Case(
        "76_e_r11_t3p9_candidate.xy",
        ((0x5F, 0x08),),
        "R11 rec2[3]=0x08 => Scene2/T3=P9 candidate",
    ),
    Case(
        "77_f_r13_s3_t7p1_candidate.xy",
        ((0x6E, 0x00),),
        "R13 matrix payload byte for Scene3/T7: P9->P1 candidate",
    ),
)


def _assert_base(pre: bytes) -> None:
    # Freeze against accidental baseline drift.
    expected = {
        0x5F: 0x00,  # rec2[3], proven Scene2/T3 selector lane
        0x6E: 0x08,  # rec3 matrix payload token for T7 in this family
    }
    for off, want in expected.items():
        got = pre[off]
        if got != want:
            raise ValueError(
                f"unexpected base byte at 0x{off:02X}: got 0x{got:02X}, expected 0x{want:02X}"
            )


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
        pre = bytearray(base.pre_track)
        for off, val in case.edits:
            pre[off] = val

        project = XYProject(pre_track=bytes(pre), tracks=base.tracks)
        raw = project.to_bytes()
        if XYProject.from_bytes(raw).to_bytes() != raw:
            raise RuntimeError(f"round-trip validation failed for {case.filename}")

        out_path = OUT_DIR / case.filename
        out_path.write_bytes(raw)
        pretty_edits = ", ".join(f"0x{off:02X}->0x{val:02X}" for off, val in case.edits)
        print(
            f"{case.filename:30s} size={len(raw):5d} pre={len(pre):3d} edits=[{pretty_edits}] "
            f"| {case.hypothesis}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
