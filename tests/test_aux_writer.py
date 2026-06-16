from pathlib import Path

from tests.decoded_image_layout import (
    AUX_FILTER_HPF_OFFSET,
    AUX_FILTER_LPF_OFFSET,
    AUX_FILTER_PARAM2_OFFSET,
    AUX_FILTER_PARAM3_OFFSET,
    AUX_LFO_AMOUNT_OFFSET,
    AUX_LFO_DESTINATION_OFFSET,
    AUX_LFO_PARAM_DEST_OFFSET,
    AUX_LFO_SPEED_OFFSET,
    BRAIN_ROUTE_MASK_OFFSET,
    ENGINE_PARAM1_OFFSET,
    ENGINE_PARAM2_OFFSET,
    ENGINE_PARAM3_OFFSET,
    ENGINE_PARAM4_OFFSET,
    ENGINE_TYPE_OFFSET,
    EXTERNAL_MIDI_CC_TABLE_OFFSET,
    FILTER_ENABLED_OFFSET,
    M4_PAGE_OFFSET,
    SEND_EXT_OFFSET,
    SEND_FX1_OFFSET,
    SEND_FX2_OFFSET,
    SEND_TAPE_OFFSET,
    TRACK_VOLUME_OFFSET,
)
from xy.image_writer import ImageProject
from xy.rle import decode_project

ROOT = Path(__file__).resolve().parents[1]
BAR_BASE = ROOT / "src/bar-menu-probes/2026-06-bar-menu/bar0.xy"
EXTERNAL_MIDI_BASELINE = ROOT / "src/aux-track-probes/2026-06-t11-external-midi/t11-external-midi-baseline.xy"
FILTER_BASE = ROOT / "src/aux-track-probes/2026-06-aux-filter/aux-filter-baseline.xy"
LFO_BASE = ROOT / "src/aux-track-probes/2026-06-aux-lfo/aux-lfo-baseline.xy"


def _decoded(project: ImageProject) -> bytes:
    return decode_project(project.to_bytes())[1]


def _u32(image: bytes, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def test_brain_route_and_external_midi_raw_writers() -> None:
    project = ImageProject.from_file(str(EXTERNAL_MIDI_BASELINE))
    project.set_brain_routes({1, 3, 6, 8})
    project.set_external_midi_m1_raw(
        channel=0x09FFFFFD,
        bank=0x017D05F4,
        program=0x7F80FDFC,
    )
    project.set_external_midi_cc_word(3, 0x7F7FFF7A)

    image = _decoded(project)
    t9 = project.track_start(9)
    t11 = project.track_start(11)
    assert image[t9 + BRAIN_ROUTE_MASK_OFFSET] == 0xA5
    assert _u32(image, t11 + ENGINE_PARAM1_OFFSET) == 0x09FFFFFD
    assert _u32(image, t11 + ENGINE_PARAM2_OFFSET) == 0x017D05F4
    assert _u32(image, t11 + ENGINE_PARAM3_OFFSET) == 0x7F80FDFC
    assert _u32(image, t11 + EXTERNAL_MIDI_CC_TABLE_OFFSET + 8) == 0x7F7FFF7A


def test_aux_send_target_writers() -> None:
    project = ImageProject.from_file(str(BAR_BASE))
    project.set_track_send_ext_byte(1, 0x7F)
    project.set_track_send_tape_byte(2, 0)
    project.set_track_send_fx1_byte(3, 0x7F)
    project.set_track_send_fx2_byte(4, 0x7F)

    image = _decoded(project)
    assert _u32(image, project.track_start(1) + SEND_EXT_OFFSET) == 0x7FFFFFFF
    assert _u32(image, project.track_start(2) + SEND_TAPE_OFFSET) == 0
    assert _u32(image, project.track_start(3) + SEND_FX1_OFFSET) == 0x7FFFFFFF
    assert _u32(image, project.track_start(4) + SEND_FX2_OFFSET) == 0x7FFFFFFF


def test_external_audio_and_tape_m1_raw_writers() -> None:
    project = ImageProject.from_file(str(BAR_BASE))
    project.set_external_audio_source("line")
    project.set_external_audio_m1_raw(
        drive=0x7FFFFFFF,
        level=0x60000000,
        mix=0,
    )
    project.set_tape_m1_raw(
        pitch=0x780A3037,
        speed=0x00A237C3,
        length=0x5C05180F,
        mix=0x7FAE7C9F,
    )

    image = _decoded(project)
    t13 = project.track_start(13)
    t14 = project.track_start(14)
    assert _u32(image, t13 + ENGINE_PARAM1_OFFSET) == 0x46666662
    assert _u32(image, t13 + ENGINE_PARAM2_OFFSET) == 0x7FFFFFFF
    assert _u32(image, t13 + TRACK_VOLUME_OFFSET) == 0x60000000
    assert _u32(image, t13 + ENGINE_PARAM4_OFFSET) == 0
    assert _u32(image, t14 + ENGINE_PARAM1_OFFSET) == 0x780A3037
    assert _u32(image, t14 + ENGINE_PARAM2_OFFSET) == 0x00A237C3
    assert _u32(image, t14 + ENGINE_PARAM3_OFFSET) == 0x5C05180F
    assert _u32(image, t14 + ENGINE_PARAM4_OFFSET) == 0x7FAE7C9F


def test_aux_filter_lfo_and_fx_type_writers() -> None:
    project = ImageProject.from_file(str(FILTER_BASE))
    project.set_aux_filter_raw(
        13,
        hpf=0x7FFFFFFF,
        param2=0x7C28F2FF,
        param3=0x3570CA40,
        lpf=0,
    )
    image = _decoded(project)
    t13 = project.track_start(13)
    assert image[t13 + FILTER_ENABLED_OFFSET] == 1
    assert _u32(image, t13 + AUX_FILTER_HPF_OFFSET) == 0x7FFFFFFF
    assert _u32(image, t13 + AUX_FILTER_PARAM2_OFFSET) == 0x7C28F2FF
    assert _u32(image, t13 + AUX_FILTER_PARAM3_OFFSET) == 0x3570CA40
    assert _u32(image, t13 + AUX_FILTER_LPF_OFFSET) == 0

    project = ImageProject.from_file(str(LFO_BASE))
    project.set_aux_lfo_raw(
        11,
        speed=0x40000000,
        amount=0x40000000,
    )
    project.set_aux_lfo_destination(11, "cc1")
    project.set_aux_lfo_param_dest(11, 2)
    project.set_fx_type_name(15, "chorus")
    image = _decoded(project)
    t11 = project.track_start(11)
    t15 = project.track_start(15)
    assert image[t11 + M4_PAGE_OFFSET] == 1
    assert _u32(image, t11 + AUX_LFO_SPEED_OFFSET) == 0x40000000
    assert _u32(image, t11 + AUX_LFO_AMOUNT_OFFSET) == 0x40000000
    assert _u32(image, t11 + AUX_LFO_DESTINATION_OFFSET) == 0x3AAAAAA7
    assert _u32(image, t11 + AUX_LFO_PARAM_DEST_OFFSET) == 0x27FFFFFD
    assert image[t15 + ENGINE_TYPE_OFFSET] == 0x0C
