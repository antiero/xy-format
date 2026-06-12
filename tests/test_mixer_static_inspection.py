from pathlib import Path

import pytest

from xy.mixer_static_inspection import (
    MIX_VOL_U32_MAX,
    PAN_BYTE_CENTER,
    inspect_static_mixer_bytes,
)
from xy.rle import decode_project
from xy.scene_volume_inspection import encode_mix_vol_byte

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT / "src" / "app-mixer-probes" / "2026-06-static"
BASELINE = PROBES / "f0-baseline-mix-default.xy"


@pytest.fixture(scope="module")
def base_img():
    return decode_project(BASELINE.read_bytes())[1]


def _primary_diffs(base_img: bytes, path: Path) -> list[int]:
    var_img = decode_project(path.read_bytes())[1]
    return [i for i in range(len(base_img)) if base_img[i] != var_img[i]]


def test_baseline_defaults() -> None:
    mixer = inspect_static_mixer_bytes(BASELINE.read_bytes())
    t1 = mixer.tracks[0]
    assert t1.volume.byte == 0x60
    assert t1.pan.byte == PAN_BYTE_CENTER
    assert t1.send_fx1.byte == 0
    assert t1.send_fx2.byte == 0
    assert mixer.master.percussion.byte == 0x40
    assert mixer.master.melody.byte == 0x40
    assert mixer.master.compressor.byte == 0x0C
    assert mixer.master.master.byte == 0x40


@pytest.mark.parametrize(
    "filename,field,expected",
    [
        ("f1-t1-vol-min.xy", "volume", 0x00),
        ("f2-t1-vol-max.xy", "volume", 0x7F),
        ("f3-t1-pan-hard-left.xy", "pan", 0x00),
        ("f4-t1-pan-hard-right.xy", "pan", 0x7F),
        ("f6-t1-send-fx1-max.xy", "send_fx1", 0x7F),
        ("f8-t1-send-fx2-max.xy", "send_fx2", 0x7F),
        ("f10-master-perc-vol-0.xy", "percussion", 0x00),
        ("f11-master-perc-vol-100.xy", "percussion", 0x7F),
        ("f12-master-melody-vol-0.xy", "melody", 0x00),
        ("f13-master-melody-vol-100.xy", "melody", 0x7F),
        ("f14-master-compressor-min.xy", "compressor", 0x00),
        ("f15-master-compressor-max.xy", "compressor", 0x7F),
    ],
)
def test_t1_and_master_fields(filename: str, field: str, expected: int) -> None:
    path = PROBES / filename
    mixer = inspect_static_mixer_bytes(path.read_bytes())
    if field in {"percussion", "melody", "compressor"}:
        assert getattr(mixer.master, field).byte == expected
    else:
        assert getattr(mixer.tracks[0], field).byte == expected


def test_t1_vol_max_uses_full_u32_pattern() -> None:
    mixer = inspect_static_mixer_bytes((PROBES / "f2-t1-vol-max.xy").read_bytes())
    assert mixer.tracks[0].volume.u32 == MIX_VOL_U32_MAX


def test_pan_center_matches_baseline(base_img: bytes) -> None:
    path = PROBES / "f5-t1-pan-center.xy"
    mixer = inspect_static_mixer_bytes(path.read_bytes())
    assert mixer.tracks[0].pan.byte == PAN_BYTE_CENTER
    t1_pan_diffs = [d for d in _primary_diffs(base_img, path) if 0x4670 <= d <= 0x4677]
    assert not t1_pan_diffs


def test_send_mins_are_unchanged_from_baseline() -> None:
    mixer = inspect_static_mixer_bytes((PROBES / "f7-t1-send-fx1-min.xy").read_bytes())
    assert mixer.tracks[0].send_fx1.byte == 0
    mixer = inspect_static_mixer_bytes((PROBES / "f9-t1-send-fx2-min.xy").read_bytes())
    assert mixer.tracks[0].send_fx2.byte == 0
