#!/usr/bin/env python3
"""Generate targeted follow-up probes 88-92 from bleez35 baseline.

Focus:
1) Test long-form encoding hypotheses for Scene3/T7=P2 matrix lane.
2) Test whether dropping rec2 requires coordinated T1 preamble correction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xy.container import XYProject, TrackBlock


BASE_PATH = ROOT / "output/scene-probes/66_a_bleez35_baseline.xy"
OUT_DIR = ROOT / "output/scene-probes"

_REC2_START = 0x5C
_REC2_END = 0x67
_REC3_START = 0x67
_REC3_END = 0x74

_REC2_BASE = bytes.fromhex("08 08 00 00 08 08 03 00 00 16 01")
_REC3_BASE = bytes.fromhex("08 08 01 00 00 00 08 08 01 00 00 16 01")


@dataclass(frozen=True)
class Case:
    filename: str
    mode: str
    rec3_hex: str | None = None
    set_ord_0f: int | None = None
    set_t1_pre0: int | None = None
    hypothesis: str = ""


CASES: tuple[Case, ...] = (
    Case(
        "88_a_s3_t7p2_longform_plus1.xy",
        mode="replace_rec3",
        rec3_hex="08 08 01 00 00 00 08 01 00 01 00 00 16 01",
        hypothesis="T7=P2 as long-form 01 00 with T8 kept at P2 (adds +1 byte)",
    ),
    Case(
        "89_b_s3_t7p2_longform_t8p1.xy",
        mode="replace_rec3",
        rec3_hex="08 08 01 00 00 00 08 01 00 00 00 00 16 01",
        hypothesis="T7=P2 long-form while forcing T8=P1 to isolate adjacent token coupling",
    ),
    Case(
        "90_c_s3_t8p2_longform_ctrl.xy",
        mode="replace_rec3",
        rec3_hex="08 08 01 00 00 00 08 08 01 00 00 00 16 01",
        hypothesis="No semantic target change; only force long-form token for final P2 lane",
    ),
    Case(
        "91_d_s2_t3p9_drop_rec2_t1pre94.xy",
        mode="drop_rec2",
        set_t1_pre0=0x94,
        hypothesis="Drop rec2 and retune T1 preamble from 0x73->0x94",
    ),
    Case(
        "92_e_s2_t3p9_drop_rec2_ord01_t1pre94.xy",
        mode="drop_rec2",
        set_ord_0f=0x01,
        set_t1_pre0=0x94,
        hypothesis="Drop rec2 + ord 02->01 + T1 preamble 0x73->0x94",
    ),
)


def _assert_base(project: XYProject) -> None:
    pre = project.pre_track
    if pre[_REC2_START:_REC2_END] != _REC2_BASE:
        raise ValueError("unexpected rec2 baseline bytes")
    if pre[_REC3_START:_REC3_END] != _REC3_BASE:
        raise ValueError("unexpected rec3 baseline bytes")
    if project.tracks[0].preamble[0] != 0x73:
        raise ValueError("unexpected T1 preamble[0] baseline")
    if pre[0x0F] != 0x02:
        raise ValueError("unexpected pre[0x0F] baseline")


def _apply_pre(case: Case, base_pre: bytes) -> bytes:
    if case.mode == "replace_rec3":
        if case.rec3_hex is None:
            raise ValueError("replace_rec3 missing rec3_hex")
        rec3_new = bytes.fromhex(case.rec3_hex)
        pre = bytearray(base_pre[:_REC3_START] + rec3_new + base_pre[_REC3_END:])
    elif case.mode == "drop_rec2":
        pre = bytearray(base_pre[:_REC2_START] + base_pre[_REC2_END:])
    else:
        raise ValueError(f"unknown mode: {case.mode}")

    if case.set_ord_0f is not None:
        pre[0x0F] = case.set_ord_0f
    return bytes(pre)


def _apply_tracks(case: Case, base_tracks: tuple[TrackBlock, ...]) -> tuple[TrackBlock, ...]:
    if case.set_t1_pre0 is None:
        return base_tracks
    t1 = base_tracks[0]
    new_t1 = TrackBlock(
        index=t1.index,
        preamble=bytes([case.set_t1_pre0]) + t1.preamble[1:],
        body=t1.body,
    )
    return (new_t1,) + tuple(base_tracks[1:])


def main() -> int:
    base = XYProject.from_bytes(BASE_PATH.read_bytes())
    _assert_base(base)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Base: {BASE_PATH}")
    print(
        f"Base size={len(base.to_bytes())} pre={len(base.pre_track)} "
        f"ctl={base.pre_track[0x0F:0x12].hex()} t1pre0=0x{base.tracks[0].preamble[0]:02x}"
    )

    for case in CASES:
        new_pre = _apply_pre(case, base.pre_track)
        new_tracks = _apply_tracks(case, base.tracks)
        project = XYProject(pre_track=new_pre, tracks=new_tracks)
        raw = project.to_bytes()
        if XYProject.from_bytes(raw).to_bytes() != raw:
            raise RuntimeError(f"round-trip validation failed for {case.filename}")

        out_path = OUT_DIR / case.filename
        out_path.write_bytes(raw)
        print(
            f"{case.filename:36s} size={len(raw):5d} pre={len(new_pre):3d} "
            f"ctl={new_pre[0x0F:0x12].hex()} t1pre0=0x{new_tracks[0].preamble[0]:02x} "
            f"| {case.hypothesis}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
