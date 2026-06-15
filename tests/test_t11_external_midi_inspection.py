from pathlib import Path

from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t11-external-midi")

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4
T11_BASE = TRACK_BASE0 + 10 * TRACK_STRIDE
ENCODER_DOMAIN = 0x80000000

CHANNEL = T11_BASE + 0x3857
BANK = T11_BASE + 0x385B
PROGRAM = T11_BASE + 0x385F
CC_TABLE_START = T11_BASE + 0x3877
CC_TABLE_END = T11_BASE + 0x3897


def _image(filename: str) -> bytes:
    return decode_project((PROBES / filename).read_bytes())[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _bucket(raw: int, count: int) -> int:
    return min(count - 1, max(0, raw) * count // ENCODER_DOMAIN)


def test_t11_m1_channel_bank_program_words() -> None:
    baseline = _image("t11-external-midi-baseline.xy")
    assert _u32(baseline, CHANNEL) == 0
    assert _u32(baseline, BANK) == 0
    assert _u32(baseline, PROGRAM) == 0

    channel_2 = _u32(_image("t11-midi-channel-01.xy"), CHANNEL)
    channel_16 = _u32(_image("t11-midi-channel-16.xy"), CHANNEL)
    assert channel_2 == 0x09FFFFFD
    assert channel_16 == 0x7DFFFFE0
    assert _bucket(channel_2, 16) == 1
    assert _bucket(channel_16, 16) == 15

    bank_1 = _u32(_image("t11-midi-bank-001.xy"), BANK)
    bank_128 = _u32(_image("t11-midi-bank-128.xy"), BANK)
    assert bank_1 == 0x017D05F4
    assert bank_128 == 0x7F80FDFC
    assert _bucket(bank_1, 129) == 1
    assert _bucket(bank_128, 129) == 128
    assert _u32(_image("t11-midi-bank-off.xy"), BANK) == 0

    program_1 = _u32(_image("t11-midi-program-001.xy"), PROGRAM)
    program_128 = _u32(_image("t11-midi-program-128.xy"), PROGRAM)
    assert program_1 == 0x017D05F4
    assert program_128 == 0x7F80FDFC
    assert _bucket(program_1, 129) == 1
    assert _bucket(program_128, 129) == 128
    assert _u32(_image("t11-midi-program-off.xy"), PROGRAM) == 0


def test_t11_cc_captures_are_localized_to_m2_m3_table() -> None:
    baseline = _image("t11-external-midi-baseline.xy")
    allowed_t11 = {
        T11_BASE + 0x11,
        T11_BASE + 0x38F2,
        T11_BASE + 0x38F6,
        *range(CC_TABLE_START, CC_TABLE_END),
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
            for offset in range(T11_BASE, T11_BASE + TRACK_STRIDE)
            if baseline[offset] != image[offset]
        }
        assert t11_diffs <= allowed_t11, filename


def test_t11_cc_probe_words_bucket_decode_to_named_values() -> None:
    cases = (
        ("t11-midi-cc1-num-074.xy", 0x3877, 128, 74, 0x4A2AAA5F),
        ("t11-midi-cc1-msg-001.xy", 0x3877, 129, 1, 0x012AAAA8),
        ("t11-midi-cc2-num-010.xy", 0x387B, 128, 10, 0x0A2AAA9D),
        ("t11-midi-cc3-num-127.xy", 0x388F, 128, 127, 0x7F7FFF80),
        ("t11-midi-cc3-msg-127.xy", 0x387F, 129, 128, 0x7F7FFF7A),
        ("t11-midi-cc4-msg-074.xy", 0x3893, 128, 74, 0x4A7FFFB5),
    )
    for filename, rel, bucket_count, expected_index, expected_raw in cases:
        raw = _u32(_image(filename), T11_BASE + rel)
        assert raw == expected_raw
        assert _bucket(raw, bucket_count) == expected_index


def test_t11_note_probe_was_not_captured_yet() -> None:
    assert _image("t11-midi-note-step1.xy") == _image("t11-external-midi-baseline.xy")
