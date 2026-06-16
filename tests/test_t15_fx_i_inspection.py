from pathlib import Path

from tests.decoded_image_layout import (
    ENGINE_PARAM1_OFFSET,
    ENGINE_PARAM2_OFFSET,
    ENGINE_PARAM3_OFFSET,
    ENGINE_PARAM4_OFFSET,
    SEND_FX1_OFFSET,
    track_base_from_project,
)
from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t15-fx-i")


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


def test_t15_fx_i_type_enum_and_default_delay_params() -> None:
    baseline_base = _track_base("t15-fx-i-baseline.xy", 15)
    baseline = _image("t15-fx-i-baseline.xy")
    assert baseline[baseline_base + 0x14] == 0x00
    assert _field("t15-fx-i-baseline.xy", 15, ENGINE_PARAM1_OFFSET) == 0x53F7CED9
    assert _field("t15-fx-i-baseline.xy", 15, ENGINE_PARAM2_OFFSET) == 0x40000000
    assert _field("t15-fx-i-baseline.xy", 15, ENGINE_PARAM3_OFFSET) == 0x40000000
    assert _field("t15-fx-i-baseline.xy", 15, ENGINE_PARAM4_OFFSET) == 0x7FFFFFFF

    type_cases = {
        "t15-fx-i-type-delay.xy": 0x00,
        "t15-fx-i-type-reverb.xy": 0x05,
        "t15-fx-i-type-chorus.xy": 0x0C,
        "t15-fx-i-type-phaser.xy": 0x0D,
        "t15-fx-i-type-distortion.xy": 0x0E,
        "t15-fx-i-type-lofi.xy": 0x0F,
    }
    for filename, type_byte in type_cases.items():
        assert _image(filename)[_track_base(filename, 15) + 0x14] == type_byte


def test_t15_fx_i_delay_param_captures() -> None:
    assert _field("t15-fx-i-delay-p1-min.xy", 15, ENGINE_PARAM1_OFFSET) == 0
    assert _field("t15-fx-i-delay-p1-max.xy", 15, ENGINE_PARAM1_OFFSET) == 0x7FFFFFFF
    assert _field("t15-fx-i-delay-p2-mid.xy", 15, ENGINE_PARAM2_OFFSET) == 0x6CCCED00
    assert _field("t15-fx-i-delay-p3-mid.xy", 15, ENGINE_PARAM3_OFFSET) == 0x63D72400
    assert _image("t15-fx-i-delay-p4-mid.xy") == _image("t15-fx-i-baseline.xy")


def test_t15_fx_i_send_t1_uses_source_track_fx1_send_word() -> None:
    baseline = _image("t15-fx-i-baseline.xy")
    assert [_u32(baseline, _track_base("t15-fx-i-baseline.xy", track) + SEND_FX1_OFFSET) for track in range(1, 9)] == [
        0,
        0,
        0,
        0,
        0x0F5C0000,
        0,
        0x57FF0000,
        0,
    ]

    image = _image("t15-fx-i-send-t1-99.xy")
    assert [_u32(image, _track_base("t15-fx-i-send-t1-99.xy", track) + SEND_FX1_OFFSET) for track in range(1, 9)] == [
        0x7FFFFFFF,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
