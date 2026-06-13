from pathlib import Path

import pytest

from xy.bar_menu_inspection import (
    TRACK_DEFAULT_STEP_LENGTH_OFFSET,
    TRACK_GROOVE_OFFSET,
    TRACK_PLOCK_SHAPE_OFFSET,
    TRACK_QUANTIZATION_OFFSET,
    TRACK_GROOVE_UI_SEQUENCE,
    inspect_bar_menu_bytes,
)
from xy.image_writer import ImageProject
from xy.rle import decode_project

PROBES = Path("src/bar-menu-probes/2026-06-bar-menu")
BASELINE = PROBES / "bar0.xy"


def _bar(filename: str):
    return inspect_bar_menu_bytes((PROBES / filename).read_bytes(), tracks=1)[0]


def test_bar_menu_baseline_defaults() -> None:
    bar = _bar("bar0.xy")
    assert bar.track == 1
    assert bar.default_step_length_ticks == 240
    assert bar.default_step_length_ui == 50
    assert bar.quantization_raw == 0xFF
    assert bar.quantization_ui_approx == 100
    assert bar.groove_raw == 0
    assert bar.groove_signed_raw == 0
    assert bar.groove_index == 0
    assert bar.groove_ui_value == 0
    assert bar.plock_shape_raw == 0
    assert bar.plock_shape_signed_raw == 0


@pytest.mark.parametrize(
    "filename,ticks,ui",
    [
        ("bar-l-000.xy", 4, 0),
        ("bar-l-001.xy", 8, 1),
        ("bar-l-002.xy", 12, 2),
        ("bar-l-048.xy", 232, 48),
        ("bar-l-049.xy", 236, 49),
        ("bar-l-051.xy", 244, 51),
        ("bar-l-052.xy", 248, 52),
        ("bar-l-053.xy", 252, 53),
        ("bar-l-098.xy", 472, 98),
        ("bar-l-099.xy", 476, 99),
        ("bar-l-100.xy", 480, 100),
    ],
)
def test_default_step_length_ticks(filename: str, ticks: int, ui: int) -> None:
    bar = _bar(filename)
    assert bar.default_step_length_ticks == ticks
    assert bar.default_step_length_ui == ui


@pytest.mark.parametrize(
    "filename,raw,ui_approx",
    [
        ("bar-q-000.xy", 0x00, 0),
        ("bar-q-001.xy", 0x04, 2),
        ("bar-q-002.xy", 0x07, 3),
        ("bar-q-098.xy", 0xFC, 99),
        ("bar-q-099.xy", 0xFE, 100),
    ],
)
def test_quantization_raw_byte(filename: str, raw: int, ui_approx: int) -> None:
    bar = _bar(filename)
    assert bar.quantization_raw == raw
    assert bar.quantization_ui_approx == ui_approx


@pytest.mark.parametrize(
    "filename,raw,signed,index,ui",
    [
        ("bar-gn011.xy", 0xF1, -15, -5, -11),
        ("bar-gn009.xy", 0xF4, -12, -4, -9),
        ("bar-gn007.xy", 0xF7, -9, -3, -7),
        ("bar-gn004.xy", 0xFA, -6, -2, -4),
        ("bar-gn002.xy", 0xFD, -3, -1, -2),
        ("bar-gp004.xy", 0x06, 6, 2, 4),
        ("bar-gp007.xy", 0x09, 9, 3, 7),
        ("bar-gp009.xy", 0x0C, 12, 4, 9),
        ("bar-gp011.xy", 0x0F, 15, 5, 11),
        ("bar-gp014.xy", 0x12, 18, 6, 14),
        ("bar-gp060.xy", 0x4E, 78, 26, 60),
    ],
)
def test_track_groove_partial_lut(
    filename: str, raw: int, signed: int, index: int, ui: int
) -> None:
    bar = _bar(filename)
    assert bar.groove_raw == raw
    assert bar.groove_signed_raw == signed
    assert bar.groove_index == index
    assert bar.groove_ui_value == ui


def test_track_groove_uses_handwritten_ui_sequence() -> None:
    assert TRACK_GROOVE_UI_SEQUENCE[:8] == (2, 4, 7, 9, 11, 14, 16, 18)


def test_bar_gp002_capture_decodes_as_gp007_index() -> None:
    bar = _bar("bar-gp002.xy")
    assert bar.groove_raw == 0x09
    assert bar.groove_index == 3
    assert bar.groove_ui_value == 7


@pytest.mark.parametrize(
    "filename,raw,signed",
    [
        ("bar-s-min.xy", 0x00, 0),
        ("bar-s-minp1.xy", 0x04, 4),
        ("bar-s-minp2.xy", 0x08, 8),
        ("bar-s-maxm2.xy", 0xF7, -9),
        ("bar-s-maxm1.xy", 0xFB, -5),
        ("bar-s-max.xy", 0xFF, -1),
    ],
)
def test_plock_shape_raw_byte(filename: str, raw: int, signed: int) -> None:
    bar = _bar(filename)
    assert bar.plock_shape_raw == raw
    assert bar.plock_shape_signed_raw == signed


def test_former_bar_q_max_capture_is_length_051_not_quantization() -> None:
    bar = _bar("bar-l-051.xy")
    assert bar.quantization_raw == 0xFF
    assert bar.default_step_length_ticks == 244
    assert bar.default_step_length_ui == 51


def test_bar_menu_setters_write_decoded_bytes() -> None:
    project = ImageProject.from_file(str(BASELINE))
    start = project.track_start(1)
    project.set_default_step_length_ticks(1, 480)
    project.set_track_quantization_raw(1, 0)
    project.set_track_groove_raw(1, 0xF1)
    project.set_plock_shape_raw(1, 0xFB)

    image = project.image
    assert image[start + TRACK_DEFAULT_STEP_LENGTH_OFFSET : start + 4] == b"\xE0\x01"
    assert image[start + TRACK_QUANTIZATION_OFFSET] == 0
    assert image[start + TRACK_GROOVE_OFFSET] == 0xF1
    assert image[start + TRACK_PLOCK_SHAPE_OFFSET] == 0xFB


def test_bar_menu_captures_are_isolated_to_bar_fields_plus_save_noise() -> None:
    base = decode_project(BASELINE.read_bytes())[1]
    aux_save_noise = {
        0x2750B,
        0x2750F,
        0x2BADF,
        0x2BAE3,
        0x300B3,
        0x300B7,
        0x34687,
        0x3468B,
        0x38C5B,
        0x38C5F,
        0x3D22F,
        0x3D233,
        0x41803,
        0x41807,
        0x45DD7,
        0x45DDB,
    }
    bar_offsets = {
        0x0D79 + TRACK_DEFAULT_STEP_LENGTH_OFFSET,
        0x0D79 + TRACK_DEFAULT_STEP_LENGTH_OFFSET + 1,
        0x0D79 + TRACK_QUANTIZATION_OFFSET,
        0x0D79 + TRACK_GROOVE_OFFSET,
        0x0D79 + 0x11,
        0x0D79 + TRACK_PLOCK_SHAPE_OFFSET,
    }
    allowed = aux_save_noise | bar_offsets
    for path in PROBES.glob("bar-*.xy"):
        image = decode_project(path.read_bytes())[1]
        diffs = {i for i, (a, b) in enumerate(zip(base, image)) if a != b}
        assert diffs <= allowed, path.name
