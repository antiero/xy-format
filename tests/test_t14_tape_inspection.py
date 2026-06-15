from pathlib import Path

from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t14-tape")

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4
T14_BASE = TRACK_BASE0 + 13 * TRACK_STRIDE


def _image(filename: str) -> bytes:
    return decode_project((PROBES / filename).read_bytes())[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _track_base(track: int) -> int:
    return TRACK_BASE0 + (track - 1) * TRACK_STRIDE


def test_t14_tape_m1_fields() -> None:
    baseline = _image("t14-tape-baseline.xy")
    assert _u32(baseline, T14_BASE + 0x3857) == 0
    assert _u32(baseline, T14_BASE + 0x385B) == 0x40000000
    assert _u32(baseline, T14_BASE + 0x385F) == 0
    assert _u32(baseline, T14_BASE + 0x3863) == 0

    assert _image("t14-tape-pitch-x01.xy") == baseline
    assert _image("t14-tape-length-01.xy") == baseline
    assert _image("t14-tape-mix-00.xy") == baseline

    pitch_x10 = _image("t14-tape-pitch-x10.xy")
    assert _u32(pitch_x10, T14_BASE + 0x3857) == 0x780A3037
    # Selecting pitch x10 also nudged the speed word just below the default.
    assert _u32(pitch_x10, T14_BASE + 0x385B) == 0x3FFFFFE7

    assert _u32(_image("t14-tape-speed-050.xy"), T14_BASE + 0x385B) == 0x00A237C3
    assert _u32(_image("t14-tape-speed-200.xy"), T14_BASE + 0x385B) == 0x7FAE7C9F
    assert _u32(_image("t14-tape-length-10.xy"), T14_BASE + 0x385F) == 0x5C05180F
    assert _u32(_image("t14-tape-mix-99.xy"), T14_BASE + 0x3863) == 0x7FAE7C9F


def test_t14_tape_sends_live_on_source_tracks() -> None:
    baseline = _image("t14-tape-baseline.xy")
    assert [_u32(baseline, _track_base(track) + 0x38AB) for track in range(1, 9)] == [
        0x7FFFFFFF,
        0x7FFFFFFF,
        0x7FFFFFFF,
        0x7FFFFFFF,
        0x7FFFFFFF,
        0x7FFFFFFF,
        0x7FFFFFFF,
        0x7FFFFFFF,
    ]

    for filename, target in (("t14-tape-send-t1-99.xy", 1), ("t14-tape-send-t8-99.xy", 8)):
        image = _image(filename)
        assert [_u32(image, _track_base(track) + 0x38AB) for track in range(1, 9)] == [
            0x7FFFFFFF if track == target else 0 for track in range(1, 9)
        ]
