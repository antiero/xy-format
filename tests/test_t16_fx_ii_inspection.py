from pathlib import Path

from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t16-fx-ii")

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4
T16_BASE = TRACK_BASE0 + 15 * TRACK_STRIDE


def _image(filename: str) -> bytes:
    return decode_project((PROBES / filename).read_bytes())[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _track_base(track: int) -> int:
    return TRACK_BASE0 + (track - 1) * TRACK_STRIDE


def test_t16_fx_ii_type_enum_and_baseline_reverb_params() -> None:
    baseline = _image("t16-fx-ii-baseline.xy")
    assert baseline[T16_BASE + 0x14] == 0x05
    assert _u32(baseline, T16_BASE + 0x3857) == 0x5999999A
    assert _u32(baseline, T16_BASE + 0x385B) == 0
    assert _u32(baseline, T16_BASE + 0x385F) == 0x26666666
    assert _u32(baseline, T16_BASE + 0x3863) == 0x7FFFFFFF

    type_cases = {
        "t16-fx-ii-type-delay.xy": 0x00,
        "t16-fx-ii-type-reverb.xy": 0x05,
        "t16-fx-ii-type-chorus.xy": 0x0C,
        "t16-fx-ii-type-phaser.xy": 0x0D,
        "t16-fx-ii-type-distortion.xy": 0x0E,
        "t16-fx-ii-type-lofi.xy": 0x0F,
    }
    for filename, type_byte in type_cases.items():
        assert _image(filename)[T16_BASE + 0x14] == type_byte


def test_t16_fx_ii_delay_param_captures() -> None:
    assert _u32(_image("t16-fx-ii-delay-p1-min.xy"), T16_BASE + 0x3857) == 0
    assert _u32(_image("t16-fx-ii-delay-p1-max.xy"), T16_BASE + 0x3857) == 0x7FFFFFFF
    assert _u32(_image("t16-fx-ii-delay-p2-mid.xy"), T16_BASE + 0x385B) == 0x6E149C00
    assert _u32(_image("t16-fx-ii-delay-p3-mid.xy"), T16_BASE + 0x385F) == 0x68F5E000
    assert _u32(_image("t16-fx-ii-delay-p4-mid.xy"), T16_BASE + 0x3863) == 0x11EA3600


def test_t16_fx_ii_send_t1_uses_source_track_fx2_send_word() -> None:
    baseline = _image("t16-fx-ii-baseline.xy")
    assert [_u32(baseline, _track_base(track) + 0x38B3) for track in range(1, 9)] == [
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
    assert [_u32(image, _track_base(track) + 0x38B3) for track in range(1, 9)] == [
        0x7FFFFFFF,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
