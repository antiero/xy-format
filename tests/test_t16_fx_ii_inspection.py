from pathlib import Path

from tests.decoded_image_layout import (
    ENGINE_PARAM1_OFFSET,
    ENGINE_PARAM2_OFFSET,
    ENGINE_PARAM3_OFFSET,
    ENGINE_PARAM4_OFFSET,
    SEND_FX2_OFFSET,
    track_base_from_project,
)
from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t16-fx-ii")


def _data(filename: str) -> bytes:
    return (PROBES / filename).read_bytes()


def _image(filename: str) -> bytes:
    return decode_project(_data(filename))[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _track_base(filename: str, track: int) -> int:
    return track_base_from_project(_data(filename), track)


def _field(filename: str, track: int, relative_offset: int) -> int:
    return _u32(_image(filename), _track_base(filename, track) + relative_offset)


def test_t16_fx_ii_type_enum_and_baseline_reverb_params() -> None:
    baseline_base = _track_base("t16-fx-ii-baseline.xy", 16)
    baseline = _image("t16-fx-ii-baseline.xy")
    assert baseline[baseline_base + 0x14] == 0x05
    assert _field("t16-fx-ii-baseline.xy", 16, ENGINE_PARAM1_OFFSET) == 0x5999999A
    assert _field("t16-fx-ii-baseline.xy", 16, ENGINE_PARAM2_OFFSET) == 0
    assert _field("t16-fx-ii-baseline.xy", 16, ENGINE_PARAM3_OFFSET) == 0x26666666
    assert _field("t16-fx-ii-baseline.xy", 16, ENGINE_PARAM4_OFFSET) == 0x7FFFFFFF

    type_cases = {
        "t16-fx-ii-type-delay.xy": 0x00,
        "t16-fx-ii-type-reverb.xy": 0x05,
        "t16-fx-ii-type-chorus.xy": 0x0C,
        "t16-fx-ii-type-phaser.xy": 0x0D,
        "t16-fx-ii-type-distortion.xy": 0x0E,
        "t16-fx-ii-type-lofi.xy": 0x0F,
    }
    for filename, type_byte in type_cases.items():
        assert _image(filename)[_track_base(filename, 16) + 0x14] == type_byte


def test_t16_fx_ii_delay_param_captures() -> None:
    assert _field("t16-fx-ii-delay-p1-min.xy", 16, ENGINE_PARAM1_OFFSET) == 0
    assert _field("t16-fx-ii-delay-p1-max.xy", 16, ENGINE_PARAM1_OFFSET) == 0x7FFFFFFF
    assert _field("t16-fx-ii-delay-p2-mid.xy", 16, ENGINE_PARAM2_OFFSET) == 0x6E149C00
    assert _field("t16-fx-ii-delay-p3-mid.xy", 16, ENGINE_PARAM3_OFFSET) == 0x68F5E000
    assert _field("t16-fx-ii-delay-p4-mid.xy", 16, ENGINE_PARAM4_OFFSET) == 0x11EA3600


def test_t16_fx_ii_send_t1_uses_source_track_fx2_send_word() -> None:
    baseline = _image("t16-fx-ii-baseline.xy")
    assert [_u32(baseline, _track_base("t16-fx-ii-baseline.xy", track) + SEND_FX2_OFFSET) for track in range(1, 9)] == [
        0,
        0,
        0,
        0x1EB80000,
        0x33330000,
        0x147A0000,
        0x43FE0000,
        0,
    ]

    image = _image("t16-fx-ii-send-t1-99.xy")
    assert [_u32(image, _track_base("t16-fx-ii-send-t1-99.xy", track) + SEND_FX2_OFFSET) for track in range(1, 9)] == [
        0x7FFFFFFF,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
