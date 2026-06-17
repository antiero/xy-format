from pathlib import Path

from tests.decoded_image_layout import (
    EDITED_FLAG_OFFSET,
    ENGINE_PARAM1_OFFSET,
    ENGINE_PARAM2_OFFSET,
    ENGINE_PARAM3_OFFSET,
    EXTERNAL_MIDI_CC_TABLE_END_OFFSET,
    EXTERNAL_MIDI_CC_TABLE_OFFSET,
    SAVE_SIDE_EFFECT_A_OFFSET,
    SAVE_SIDE_EFFECT_B_OFFSET,
    track_base_from_project,
    track_window_from_project,
)
from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t11-external-midi")

ENCODER_DOMAIN = 0x80000000


def _data(filename: str) -> bytes:
    return (PROBES / filename).read_bytes()


def _image(filename: str) -> bytes:
    return decode_project(_data(filename))[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _track_base(filename: str, track: int) -> int:
    return track_base_from_project(_data(filename), track)


def _field(filename: str, relative_offset: int) -> int:
    return _u32(_image(filename), _track_base(filename, 11) + relative_offset)


def _bucket(raw: int, count: int) -> int:
    return min(count - 1, max(0, raw) * count // ENCODER_DOMAIN)


def test_t11_m1_channel_bank_program_words() -> None:
    baseline = _image("t11-external-midi-baseline.xy")
    baseline_base = _track_base("t11-external-midi-baseline.xy", 11)
    assert _u32(baseline, baseline_base + ENGINE_PARAM1_OFFSET) == 0
    assert _u32(baseline, baseline_base + ENGINE_PARAM2_OFFSET) == 0
    assert _u32(baseline, baseline_base + ENGINE_PARAM3_OFFSET) == 0

    channel_2 = _field("t11-midi-channel-01.xy", ENGINE_PARAM1_OFFSET)
    channel_16 = _field("t11-midi-channel-16.xy", ENGINE_PARAM1_OFFSET)
    assert channel_2 == 0x09FFFFFD
    assert channel_16 == 0x7DFFFFE0
    assert _bucket(channel_2, 16) == 1
    assert _bucket(channel_16, 16) == 15

    bank_1 = _field("t11-midi-bank-001.xy", ENGINE_PARAM2_OFFSET)
    bank_128 = _field("t11-midi-bank-128.xy", ENGINE_PARAM2_OFFSET)
    assert bank_1 == 0x017D05F4
    assert bank_128 == 0x7F80FDFC
    assert _bucket(bank_1, 129) == 1
    assert _bucket(bank_128, 129) == 128
    assert _field("t11-midi-bank-off.xy", ENGINE_PARAM2_OFFSET) == 0

    program_1 = _field("t11-midi-program-001.xy", ENGINE_PARAM3_OFFSET)
    program_128 = _field("t11-midi-program-128.xy", ENGINE_PARAM3_OFFSET)
    assert program_1 == 0x017D05F4
    assert program_128 == 0x7F80FDFC
    assert _bucket(program_1, 129) == 1
    assert _bucket(program_128, 129) == 128
    assert _field("t11-midi-program-off.xy", ENGINE_PARAM3_OFFSET) == 0


def test_t11_cc_captures_are_localized_to_m2_m3_table() -> None:
    baseline_data = _data("t11-external-midi-baseline.xy")
    baseline = _image("t11-external-midi-baseline.xy")
    t11_base, t11_end = track_window_from_project(baseline_data, 11)
    allowed_t11 = {
        t11_base + EDITED_FLAG_OFFSET,
        t11_base + SAVE_SIDE_EFFECT_A_OFFSET,
        t11_base + SAVE_SIDE_EFFECT_B_OFFSET,
        *range(
            t11_base + EXTERNAL_MIDI_CC_TABLE_OFFSET,
            t11_base + EXTERNAL_MIDI_CC_TABLE_END_OFFSET,
        ),
    }
    for filename in (
        "t11-midi-cc1-num-074.xy",
        "t11-midi-cc1-msg-001.xy",
        "t11-midi-cc2-num-010.xy",
        "t11-midi-cc2-msg-off.xy",
        "t11-midi-cc3-num-127.xy",
        "t11-midi-cc3-msg-127.xy",
        "t11-midi-cc4-num-000.xy",
        "t11-midi-cc4-msg-074.xy",
    ):
        image = _image(filename)
        t11_diffs = {
            offset
            for offset in range(t11_base, t11_end)
            if baseline[offset] != image[offset]
        }
        assert t11_diffs <= allowed_t11, filename


def test_t11_cc_probe_words_bucket_decode_to_named_values() -> None:
    cases = (
        ("t11-midi-cc1-num-074.xy", EXTERNAL_MIDI_CC_TABLE_OFFSET, 128, 74, 0x4A2AAA5F),
        ("t11-midi-cc1-msg-001.xy", EXTERNAL_MIDI_CC_TABLE_OFFSET, 129, 1, 0x012AAAA8),
        ("t11-midi-cc2-num-010.xy", EXTERNAL_MIDI_CC_TABLE_OFFSET + 4, 128, 10, 0x0A2AAA9D),
        ("t11-midi-cc3-num-127.xy", 0x388F, 128, 127, 0x7F7FFF80),
        ("t11-midi-cc3-msg-127.xy", 0x387F, 129, 128, 0x7F7FFF7A),
        ("t11-midi-cc4-msg-074.xy", 0x3893, 128, 74, 0x4A7FFFB5),
    )
    for filename, rel, bucket_count, expected_index, expected_raw in cases:
        raw = _field(filename, rel)
        assert raw == expected_raw
        assert _bucket(raw, bucket_count) == expected_index


def test_t11_note_probe_was_not_captured_yet() -> None:
    assert _image("t11-midi-note-step1.xy") == _image("t11-external-midi-baseline.xy")
