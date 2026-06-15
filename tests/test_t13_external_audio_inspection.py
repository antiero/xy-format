from pathlib import Path

from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t13-external-audio")

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4
T13_BASE = TRACK_BASE0 + 12 * TRACK_STRIDE


def _image(filename: str) -> bytes:
    return decode_project((PROBES / filename).read_bytes())[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _track_base(track: int) -> int:
    return TRACK_BASE0 + (track - 1) * TRACK_STRIDE


def test_t13_external_audio_m1_fields() -> None:
    baseline = _image("t13-external-audio-baseline.xy")
    assert _u32(baseline, T13_BASE + 0x3857) == 0
    assert _u32(baseline, T13_BASE + 0x385B) == 0
    assert _u32(baseline, T13_BASE + 0x3863) == 0x7FFFFFFF
    assert _u32(baseline, T13_BASE + 0x38FB) == 0x60000000

    source_cases = {
        "t13-audio-source-hp.xy": 0x1FFFFFFE,
        "t13-audio-source-line.xy": 0x46666662,
        "t13-audio-source-usbc.xy": 0x5FFFFFFA,
        "t13-audio-source-main.xy": 0x79999992,
    }
    for filename, raw in source_cases.items():
        assert _u32(_image(filename), T13_BASE + 0x3857) == raw

    assert _u32(_image("t13-audio-drive-20.xy"), T13_BASE + 0x385B) == 0x7FFFFFFF
    assert _u32(_image("t13-audio-level-00.xy"), T13_BASE + 0x38FB) == 0
    assert _u32(_image("t13-audio-level-99.xy"), T13_BASE + 0x38FB) == 0x7FFFFFFF
    assert _u32(_image("t13-audio-mix-00.xy"), T13_BASE + 0x3863) == 0


def test_t13_external_audio_default_captures_are_noops_or_save_only() -> None:
    baseline = _image("t13-external-audio-baseline.xy")
    assert _image("t13-audio-input-off.xy") == baseline
    for filename in ("t13-audio-source-mic.xy", "t13-audio-drive-00.xy", "t13-audio-mix-99.xy"):
        image = _image(filename)
        t13_diffs = {
            offset - T13_BASE
            for offset in range(T13_BASE, T13_BASE + TRACK_STRIDE)
            if baseline[offset] != image[offset]
        }
        assert t13_diffs <= {0x38F2, 0x38F6}, filename


def test_t13_external_audio_sends_live_on_source_tracks() -> None:
    baseline = _image("t13-external-audio-baseline.xy")
    assert [_u32(baseline, _track_base(track) + 0x38A7) for track in range(1, 9)] == [
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
        image = _image(f"t13-audio-send-t{track}-99.xy")
        assert [_u32(image, _track_base(t) + 0x38A7) for t in range(1, 9)] == [
            0x7FFFFFFF if t == observed_target[track] else 0 for t in range(1, 9)
        ]
