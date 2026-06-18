"""Read confirmed patch.json-derived sound-state lanes from a project image."""

from __future__ import annotations

from dataclasses import dataclass

from .image_writer import ImageProject
from .rle import decode_project

ENGINE_ID_OFFSET = 0x14
LFO_TYPE_OFFSET = 0x1C
LFO_ACTIVE_OFFSET = 0x20
FX_TYPE_OFFSET = 0x21
FX_ACTIVE_OFFSET = 0x25

ENGINE_PARAM_OFFSETS = (0x3857, 0x385B, 0x385F, 0x3863, 0x3867, 0x386B, 0x386F, 0x3873)
AMP_ENV_OFFSETS = (0x3877, 0x387B, 0x387F, 0x3883)
FX_PARAM_OFFSETS = (0x3897, 0x389B, 0x389F, 0x38A3, 0x38A7, 0x38AB, 0x38AF, 0x38B3)
LFO_PARAM_OFFSETS = (0x38B7, 0x38BB, 0x38BF, 0x38C3, 0x38C7, 0x38CB, 0x38CF, 0x38D3)
FILTER_ENV_OFFSETS = (0x38D7, 0x38DB, 0x38DF, 0x38E3)


@dataclass(frozen=True)
class PatchSoundState:
    """Confirmed common patch sound-state fields for one track."""

    track: int
    engine_id: int
    lfo_type: int
    lfo_active: bool
    fx_type: int
    fx_active: bool
    engine_params: tuple[int, ...]
    playmode_raw: int
    portamento_amount: int
    bendrange: int
    volume: int
    amp_envelope: tuple[int, int, int, int]
    fx_params: tuple[int, ...]
    lfo_params: tuple[int, ...]
    filter_envelope: tuple[int, int, int, int]
    modwheel_target: int
    modwheel_amount: int
    aftertouch_target: int
    aftertouch_amount: int
    pitchbend_target: int
    pitchbend_amount: int
    velocity_sensitivity: int
    portamento_type: int
    tuning_scale: int
    width: int
    tuning_root: int
    highpass: int
    velocity_target: int
    velocity_amount: int


def _u32(img: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(img[offset : offset + 4], "little")


def _q16(img: bytes | bytearray, offset: int) -> int:
    return _u32(img, offset) >> 16


def _q16_tuple(img: bytes | bytearray, base: int, offsets: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(_q16(img, base + offset) for offset in offsets)


def read_patch_sound_state(project: ImageProject, track: int = 1) -> PatchSoundState:
    """Read the confirmed common patch sound-state lanes for ``track``."""

    base = project.track_start(track)
    img = project.image
    return PatchSoundState(
        track=track,
        engine_id=img[base + ENGINE_ID_OFFSET],
        lfo_type=img[base + LFO_TYPE_OFFSET],
        lfo_active=bool(img[base + LFO_ACTIVE_OFFSET]),
        fx_type=img[base + FX_TYPE_OFFSET],
        fx_active=bool(img[base + FX_ACTIVE_OFFSET]),
        engine_params=_q16_tuple(img, base, ENGINE_PARAM_OFFSETS),
        playmode_raw=_u32(img, base + 0x3887),
        portamento_amount=_q16(img, base + 0x388B),
        bendrange=_q16(img, base + 0x388F),
        volume=_q16(img, base + 0x3893),
        amp_envelope=_q16_tuple(img, base, AMP_ENV_OFFSETS),  # type: ignore[assignment]
        fx_params=_q16_tuple(img, base, FX_PARAM_OFFSETS),
        lfo_params=_q16_tuple(img, base, LFO_PARAM_OFFSETS),
        filter_envelope=_q16_tuple(img, base, FILTER_ENV_OFFSETS),  # type: ignore[assignment]
        modwheel_target=_q16(img, base + 0x38FF),
        modwheel_amount=_q16(img, base + 0x3903),
        aftertouch_target=_q16(img, base + 0x3907),
        aftertouch_amount=_q16(img, base + 0x390B),
        pitchbend_target=_q16(img, base + 0x390F),
        pitchbend_amount=_q16(img, base + 0x3913),
        velocity_sensitivity=_q16(img, base + 0x3917),
        portamento_type=_q16(img, base + 0x391B),
        tuning_scale=_q16(img, base + 0x391F),
        width=_q16(img, base + 0x3923),
        tuning_root=_q16(img, base + 0x392B),
        highpass=_q16(img, base + 0x392F),
        velocity_target=_q16(img, base + 0x3933),
        velocity_amount=_q16(img, base + 0x3937),
    )


def inspect_patch_sound_state_bytes(data: bytes, track: int = 1) -> PatchSoundState:
    """Decode a project file and read one track's patch sound state."""

    header, image = decode_project(data)
    project = ImageProject(header, bytearray(image))
    project._rescan()
    return read_patch_sound_state(project, track)
