"""Shared decoded-image offsets used by fixture-level tests."""

from xy.image_writer import ImageProject

ENGINE_TYPE_OFFSET = 0x0014
BRAIN_ROUTE_MASK_OFFSET = 0x0009
EDITED_FLAG_OFFSET = 0x0011
M4_PAGE_OFFSET = 0x0020
FILTER_ENABLED_OFFSET = 0x0025
NOTE_VECTOR_OFFSET = 0x456F

ENGINE_PARAM1_OFFSET = 0x3857
ENGINE_PARAM2_OFFSET = 0x385B
ENGINE_PARAM3_OFFSET = 0x385F
ENGINE_PARAM4_OFFSET = 0x3863

EXTERNAL_MIDI_CC_TABLE_OFFSET = 0x3877
EXTERNAL_MIDI_CC_TABLE_END_OFFSET = 0x3897

AUX_FILTER_HPF_OFFSET = 0x3897
AUX_FILTER_PARAM2_OFFSET = 0x389B
AUX_FILTER_PARAM3_OFFSET = 0x389F
AUX_FILTER_LPF_OFFSET = 0x38A3

AUX_LFO_SPEED_OFFSET = 0x38B7
AUX_LFO_AMOUNT_OFFSET = 0x38BB
AUX_LFO_DESTINATION_OFFSET = 0x38BF
AUX_LFO_PARAM_DEST_OFFSET = 0x38C3

SEND_EXT_OFFSET = 0x38A7
SEND_TAPE_OFFSET = 0x38AB
SEND_FX1_OFFSET = 0x38AF
SEND_FX2_OFFSET = 0x38B3
SAVE_SIDE_EFFECT_A_OFFSET = 0x38F2
SAVE_SIDE_EFFECT_B_OFFSET = 0x38F6
TRACK_PAN_OFFSET = 0x38F7
TRACK_VOLUME_OFFSET = 0x38FB


def track_base_from_project(data: bytes, track: int) -> int:
    """Return a 1-based track base using the production decoded-image locator."""

    return ImageProject.from_bytes(data).track_start(track)


def track_window_from_project(data: bytes, track: int) -> tuple[int, int]:
    """Return the decoded-image byte window for a 1-based track in this project."""

    project = ImageProject.from_bytes(data)
    start = project.track_start(track)
    if track >= 16:
        return start, len(project.image)
    return start, project.track_start(track + 1)
