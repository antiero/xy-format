from pathlib import Path

from tests.decoded_image_layout import (
    AUX_FILTER_HPF_OFFSET,
    AUX_FILTER_LPF_OFFSET,
    AUX_FILTER_PARAM2_OFFSET,
    AUX_FILTER_PARAM3_OFFSET,
    EDITED_FLAG_OFFSET,
    FILTER_ENABLED_OFFSET,
    SAVE_SIDE_EFFECT_A_OFFSET,
    SAVE_SIDE_EFFECT_B_OFFSET,
    track_base_from_project,
)
from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-aux-filter")


def _data(filename: str) -> bytes:
    return (PROBES / filename).read_bytes()


def _image(filename: str) -> bytes:
    return decode_project(_data(filename))[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _track_base(filename: str, track: int) -> int:
    return track_base_from_project(_data(filename), track)


def _field(filename: str, relative_offset: int) -> int:
    return _u32(_image(filename), _track_base(filename, 13) + relative_offset)


def test_aux_filter_t13_m3_fields() -> None:
    baseline = _image("aux-filter-baseline.xy")
    t13_base = _track_base("aux-filter-baseline.xy", 13)
    assert _u32(baseline, t13_base + FILTER_ENABLED_OFFSET) == 0
    assert _u32(baseline, t13_base + AUX_FILTER_HPF_OFFSET) == 0
    assert _u32(baseline, t13_base + AUX_FILTER_PARAM2_OFFSET) == 0
    assert _u32(baseline, t13_base + AUX_FILTER_PARAM3_OFFSET) == 0
    assert _u32(baseline, t13_base + AUX_FILTER_LPF_OFFSET) == 0x7FFFFFFF

    assert _field("aux-filter-hpf-min.xy", AUX_FILTER_HPF_OFFSET) == 0
    assert _field("aux-filter-hpf-max.xy", AUX_FILTER_HPF_OFFSET) == 0x7FFFFFFF

    assert _field("aux-filter-lpf-min.xy", AUX_FILTER_LPF_OFFSET) == 0
    assert _field("aux-filter-lpf-max.xy", AUX_FILTER_LPF_OFFSET) == 0x7FFFFFFF

    assert _field("aux-filter-p2-mid.xy", AUX_FILTER_PARAM2_OFFSET) == 0x7C28F2FF
    assert _field("aux-filter-p3-mid.xy", AUX_FILTER_PARAM3_OFFSET) == 0x3570CA40


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
        t13_base = _track_base(filename, 13)
        assert _u32(image, t13_base + EDITED_FLAG_OFFSET) == 0x12010000
        assert _u32(image, t13_base + FILTER_ENABLED_OFFSET) == 1
        assert _u32(image, t13_base + SAVE_SIDE_EFFECT_A_OFFSET) == 0x40
        assert _u32(image, t13_base + SAVE_SIDE_EFFECT_B_OFFSET) == 0x40


def test_aux_filter_lpf_min_capture_has_p2_co_change() -> None:
    assert _field("aux-filter-lpf-min.xy", AUX_FILTER_PARAM2_OFFSET) == 0x0147AF00
