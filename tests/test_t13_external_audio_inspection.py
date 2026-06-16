from pathlib import Path

from tests.decoded_image_layout import (
    ENGINE_PARAM1_OFFSET,
    ENGINE_PARAM2_OFFSET,
    ENGINE_PARAM4_OFFSET,
    SEND_EXT_OFFSET,
    TRACK_VOLUME_OFFSET,
    track_base_from_project,
    track_window_from_project,
)
from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t13-external-audio")


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


def test_t13_external_audio_m1_fields() -> None:
    assert _field("t13-external-audio-baseline.xy", 13, ENGINE_PARAM1_OFFSET) == 0
    assert _field("t13-external-audio-baseline.xy", 13, ENGINE_PARAM2_OFFSET) == 0
    assert _field("t13-external-audio-baseline.xy", 13, ENGINE_PARAM4_OFFSET) == 0x7FFFFFFF
    assert _field("t13-external-audio-baseline.xy", 13, TRACK_VOLUME_OFFSET) == 0x60000000

    source_cases = {
        "t13-audio-source-hp.xy": 0x1FFFFFFE,
        "t13-audio-source-line.xy": 0x46666662,
        "t13-audio-source-usbc.xy": 0x5FFFFFFA,
        "t13-audio-source-main.xy": 0x79999992,
    }
    for filename, raw in source_cases.items():
        assert _field(filename, 13, ENGINE_PARAM1_OFFSET) == raw

    assert _field("t13-audio-drive-20.xy", 13, ENGINE_PARAM2_OFFSET) == 0x7FFFFFFF
    assert _field("t13-audio-level-00.xy", 13, TRACK_VOLUME_OFFSET) == 0
    assert _field("t13-audio-level-99.xy", 13, TRACK_VOLUME_OFFSET) == 0x7FFFFFFF
    assert _field("t13-audio-mix-00.xy", 13, ENGINE_PARAM4_OFFSET) == 0


def test_t13_external_audio_default_captures_are_noops_or_save_only() -> None:
    baseline_data = _data("t13-external-audio-baseline.xy")
    baseline = _image("t13-external-audio-baseline.xy")
    t13_base, t13_end = track_window_from_project(baseline_data, 13)
    assert _image("t13-audio-input-off.xy") == baseline
    for filename in ("t13-audio-source-mic.xy", "t13-audio-drive-00.xy", "t13-audio-mix-99.xy"):
        image = _image(filename)
        t13_diffs = {
            offset - t13_base
            for offset in range(t13_base, t13_end)
            if baseline[offset] != image[offset]
        }
        assert t13_diffs <= {0x38F2, 0x38F6}, filename


def test_t13_external_audio_sends_live_on_source_tracks() -> None:
    baseline = _image("t13-external-audio-baseline.xy")
    assert [_u32(baseline, _track_base("t13-external-audio-baseline.xy", track) + SEND_EXT_OFFSET) for track in range(1, 9)] == [
        0,
        0,
        0,
        0,
        0x33330000,
        0,
        0,
        0,
    ]

    observed_target = {track: track for track in range(1, 9)}
    observed_target[6] = 7  # Capture mismatch: t6 file contains the same T7 send as t7.
    for track in range(1, 9):
        filename = f"t13-audio-send-t{track}-99.xy"
        image = _image(filename)
        assert [_u32(image, _track_base(filename, t) + SEND_EXT_OFFSET) for t in range(1, 9)] == [
            0x7FFFFFFF if t == observed_target[track] else 0 for t in range(1, 9)
        ]
