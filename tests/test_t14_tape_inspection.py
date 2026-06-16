from pathlib import Path

from tests.decoded_image_layout import (
    ENGINE_PARAM1_OFFSET,
    ENGINE_PARAM2_OFFSET,
    ENGINE_PARAM3_OFFSET,
    ENGINE_PARAM4_OFFSET,
    SEND_TAPE_OFFSET,
    track_base_from_project,
)
from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t14-tape")


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


def test_t14_tape_m1_fields() -> None:
    baseline = _image("t14-tape-baseline.xy")
    assert _field("t14-tape-baseline.xy", 14, ENGINE_PARAM1_OFFSET) == 0
    assert _field("t14-tape-baseline.xy", 14, ENGINE_PARAM2_OFFSET) == 0x40000000
    assert _field("t14-tape-baseline.xy", 14, ENGINE_PARAM3_OFFSET) == 0
    assert _field("t14-tape-baseline.xy", 14, ENGINE_PARAM4_OFFSET) == 0

    assert _image("t14-tape-pitch-x01.xy") == baseline
    assert _image("t14-tape-length-01.xy") == baseline
    assert _image("t14-tape-mix-00.xy") == baseline

    assert _field("t14-tape-pitch-x10.xy", 14, ENGINE_PARAM1_OFFSET) == 0x780A3037
    # Selecting pitch x10 also nudged the speed word just below the default.
    assert _field("t14-tape-pitch-x10.xy", 14, ENGINE_PARAM2_OFFSET) == 0x3FFFFFE7

    assert _field("t14-tape-speed-050.xy", 14, ENGINE_PARAM2_OFFSET) == 0x00A237C3
    assert _field("t14-tape-speed-200.xy", 14, ENGINE_PARAM2_OFFSET) == 0x7FAE7C9F
    assert _field("t14-tape-length-10.xy", 14, ENGINE_PARAM3_OFFSET) == 0x5C05180F
    assert _field("t14-tape-mix-99.xy", 14, ENGINE_PARAM4_OFFSET) == 0x7FAE7C9F


def test_t14_tape_sends_live_on_source_tracks() -> None:
    baseline = _image("t14-tape-baseline.xy")
    assert [_u32(baseline, _track_base("t14-tape-baseline.xy", track) + SEND_TAPE_OFFSET) for track in range(1, 9)] == [
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
        assert [_u32(image, _track_base(filename, track) + SEND_TAPE_OFFSET) for track in range(1, 9)] == [
            0x7FFFFFFF if track == target else 0 for track in range(1, 9)
        ]
