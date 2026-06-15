from pathlib import Path

from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t15-fx-i")

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4
T15_BASE = TRACK_BASE0 + 14 * TRACK_STRIDE


def _image(filename: str) -> bytes:
    return decode_project((PROBES / filename).read_bytes())[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _track_base(track: int) -> int:
    return TRACK_BASE0 + (track - 1) * TRACK_STRIDE


def test_t15_fx_i_type_enum_and_default_delay_params() -> None:
    baseline = _image("t15-fx-i-baseline.xy")
    assert baseline[T15_BASE + 0x14] == 0x00
    assert _u32(baseline, T15_BASE + 0x3857) == 0x53F7CED9
    assert _u32(baseline, T15_BASE + 0x385B) == 0x40000000
    assert _u32(baseline, T15_BASE + 0x385F) == 0x40000000
    assert _u32(baseline, T15_BASE + 0x3863) == 0x7FFFFFFF

    type_cases = {
        "t15-fx-i-type-delay.xy": 0x00,
        "t15-fx-i-type-reverb.xy": 0x05,
        "t15-fx-i-type-chorus.xy": 0x0C,
        "t15-fx-i-type-phaser.xy": 0x0D,
        "t15-fx-i-type-distortion.xy": 0x0E,
        "t15-fx-i-type-lofi.xy": 0x0F,
    }
    for filename, type_byte in type_cases.items():
        assert _image(filename)[T15_BASE + 0x14] == type_byte


def test_t15_fx_i_delay_param_captures() -> None:
    assert _u32(_image("t15-fx-i-delay-p1-min.xy"), T15_BASE + 0x3857) == 0
    assert _u32(_image("t15-fx-i-delay-p1-max.xy"), T15_BASE + 0x3857) == 0x7FFFFFFF
    assert _u32(_image("t15-fx-i-delay-p2-mid.xy"), T15_BASE + 0x385B) == 0x6CCCED00
    assert _u32(_image("t15-fx-i-delay-p3-mid.xy"), T15_BASE + 0x385F) == 0x63D72400
    assert _image("t15-fx-i-delay-p4-mid.xy") == _image("t15-fx-i-baseline.xy")


def test_t15_fx_i_send_t1_uses_source_track_fx1_send_word() -> None:
    baseline = _image("t15-fx-i-baseline.xy")
    assert [_u32(baseline, _track_base(track) + 0x38AF) for track in range(1, 9)] == [
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
    assert [_u32(image, _track_base(track) + 0x38AF) for track in range(1, 9)] == [
        0x7FFFFFFF,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
