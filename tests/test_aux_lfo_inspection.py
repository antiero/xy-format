from pathlib import Path

from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-aux-lfo")

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4


def _image(filename: str) -> bytes:
    return decode_project((PROBES / filename).read_bytes())[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _track_base(track: int) -> int:
    return TRACK_BASE0 + (track - 1) * TRACK_STRIDE


def _field(filename: str, track: int, relative_offset: int) -> int:
    return _u32(_image(filename), _track_base(track) + relative_offset)


def test_aux_lfo_t13_generic_fields() -> None:
    baseline = _image("aux-lfo-baseline.xy")
    t13 = _track_base(13)

    assert _u32(baseline, t13 + 0x0020) == 0x00000A00
    assert _u32(baseline, t13 + 0x38B7) == 0x40000000
    assert _u32(baseline, t13 + 0x38BB) == 0x40000000
    assert _u32(baseline, t13 + 0x38BF) == 0
    assert _u32(baseline, t13 + 0x38C3) == 0

    assert _field("aux-lfo-speed-min.xy", 13, 0x38B7) == 0x40000000
    assert _field("aux-lfo-speed-max.xy", 13, 0x38B7) == 0x7FFFFFFF

    assert _field("aux-lfo-amount-min.xy", 13, 0x38BB) == 0
    assert _field("aux-lfo-amount-zero.xy", 13, 0x38BB) == 0x40000000
    assert _field("aux-lfo-amount-max.xy", 13, 0x38BB) == 0x7FFFFFFF

    assert _field("aux-lfo-dest-syn.xy", 13, 0x38BF) == 0
    assert _field("aux-lfo-dest-filter.xy", 13, 0x38BF) == 0x4AAAAAA9
    assert _field("aux-lfo-dest-amp.xy", 13, 0x38BF) == 0x75555553

    param_dest_cases = {
        "aux-lfo-param-dest-1.xy": 0x07FFFFFF,
        "aux-lfo-param-dest-2.xy": 0x27FFFFFD,
        "aux-lfo-param-dest-3.xy": 0x47FFFFFB,
        "aux-lfo-param-dest-4.xy": 0x77FFFFF8,
    }
    for filename, raw in param_dest_cases.items():
        assert _field(filename, 13, 0x38C3) == raw


def test_aux_lfo_activation_and_default_captures() -> None:
    baseline = _image("aux-lfo-baseline.xy")
    assert _image("aux-lfo-speed-discrete-3.xy") == baseline

    for track, filenames in {
        13: (
            "aux-lfo-speed-min.xy",
            "aux-lfo-speed-max.xy",
            "aux-lfo-amount-min.xy",
            "aux-lfo-amount-zero.xy",
            "aux-lfo-amount-max.xy",
            "aux-lfo-dest-syn.xy",
            "aux-lfo-dest-filter.xy",
            "aux-lfo-dest-amp.xy",
            "aux-lfo-param-dest-1.xy",
            "aux-lfo-param-dest-2.xy",
            "aux-lfo-param-dest-3.xy",
            "aux-lfo-param-dest-4.xy",
        ),
        11: (
            "aux-lfo-t11-dest-off.xy",
            "aux-lfo-t11-dest-cc1.xy",
            "aux-lfo-t11-dest-cc2.xy",
        ),
    }.items():
        base = _track_base(track)
        for filename in filenames:
            image = _image(filename)
            assert _u32(image, base + 0x0011) == 0x12010000
            assert _u32(image, base + 0x0020) == 0x00000A01
            assert _u32(image, base + 0x38F2) == 0x40
            assert _u32(image, base + 0x38F6) == 0x40


def test_aux_lfo_t11_midi_destination_field() -> None:
    assert _field("aux-lfo-t11-dest-off.xy", 11, 0x38BF) == 0
    assert _field("aux-lfo-t11-dest-cc1.xy", 11, 0x38BF) == 0x3AAAAAA7
    assert _field("aux-lfo-t11-dest-cc2.xy", 11, 0x38BF) == 0x7AAAAAA3

    # The cc1 capture also touched the neighboring amount-like word.
    assert _field("aux-lfo-t11-dest-cc1.xy", 11, 0x38BB) == 0x028F5E00
