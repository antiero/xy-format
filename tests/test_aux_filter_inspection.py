from pathlib import Path

from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-aux-filter")

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4
T13_BASE = TRACK_BASE0 + 12 * TRACK_STRIDE


def _image(filename: str) -> bytes:
    return decode_project((PROBES / filename).read_bytes())[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _field(filename: str, relative_offset: int) -> int:
    return _u32(_image(filename), T13_BASE + relative_offset)


def test_aux_filter_t13_m3_fields() -> None:
    baseline = _image("aux-filter-baseline.xy")
    assert _u32(baseline, T13_BASE + 0x0025) == 0
    assert _u32(baseline, T13_BASE + 0x3897) == 0
    assert _u32(baseline, T13_BASE + 0x389B) == 0
    assert _u32(baseline, T13_BASE + 0x389F) == 0
    assert _u32(baseline, T13_BASE + 0x38A3) == 0x7FFFFFFF

    assert _field("aux-filter-hpf-min.xy", 0x3897) == 0
    assert _field("aux-filter-hpf-max.xy", 0x3897) == 0x7FFFFFFF

    assert _field("aux-filter-lpf-min.xy", 0x38A3) == 0
    assert _field("aux-filter-lpf-max.xy", 0x38A3) == 0x7FFFFFFF

    assert _field("aux-filter-p2-mid.xy", 0x389B) == 0x7C28F2FF
    assert _field("aux-filter-p3-mid.xy", 0x389F) == 0x3570CA40


def test_aux_filter_enable_and_save_side_effects() -> None:
    for filename in (
        "aux-filter-hpf-min.xy",
        "aux-filter-hpf-max.xy",
        "aux-filter-lpf-min.xy",
        "aux-filter-lpf-max.xy",
        "aux-filter-p2-mid.xy",
        "aux-filter-p3-mid.xy",
    ):
        image = _image(filename)
        assert _u32(image, T13_BASE + 0x0011) == 0x12010000
        assert _u32(image, T13_BASE + 0x0025) == 1
        assert _u32(image, T13_BASE + 0x38F2) == 0x40
        assert _u32(image, T13_BASE + 0x38F6) == 0x40


def test_aux_filter_lpf_min_capture_has_p2_co_change() -> None:
    assert _field("aux-filter-lpf-min.xy", 0x389B) == 0x0147AF00
