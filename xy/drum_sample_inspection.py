"""Read drum-sampler voice sample paths from a decoded project image.

Drum voices are 24 slots × 128 bytes at track struct +0x3957; the sample
path string starts at slot +0x08 (see docs/format/decoded_image_map.md).
This module reads from the decoded RAM image (via ``ImageProject``), not
from scaffold logical-entry bodies, which are shorter track-block slices.
"""

from __future__ import annotations

from dataclasses import dataclass

from .image_writer import ImageProject
from .rle import decode_project

DRUM_ENGINE_ID = 0x03
DRUM_TABLE_OFFSET = 0x3957
DRUM_SLOT_SIZE = 0x80
DRUM_PATH_OFFSET = 0x08
DRUM_PAN_OFFSET = 0x06
DRUM_GAIN_OFFSET = 0x7C
DRUM_VOICE_COUNT = 24
ENGINE_ID_OFFSET = 0x14
# Loop-crossfade UI 0..99 → u32 at preceding voice slot +0x7C (M3 probes).
DRUM_FADE_STEP = 0x0147AF00
DRUM_FADE_HI_SCALE = DRUM_FADE_STEP >> 8  # 0x0147AF
DRUM_FADE_U32_MAX = 0x7FFFFFFF
DRUM_FADE_UI_MAX = 99


def encode_drum_fade_ui(ui: int) -> int:
    """Encode drum pad loop-crossfade UI (0..99) to device u32 @ slot+0x7C."""
    if ui <= 0:
        return 0
    if ui >= DRUM_FADE_UI_MAX:
        return DRUM_FADE_U32_MAX
    return ui * DRUM_FADE_STEP


def decode_drum_fade_u32(u32: int) -> int:
    """Decode loop-crossfade u32 back to UI 0..99."""
    if u32 <= 0:
        return 0
    if u32 >= DRUM_FADE_U32_MAX:
        return DRUM_FADE_UI_MAX
    return (u32 >> 8) // DRUM_FADE_HI_SCALE


def drum_fade_storage_voice(edited_voice: int) -> int:
    """Pad fade edited on *edited_voice* is stored on the previous slot (v23→v22)."""
    return edited_voice - 1


@dataclass(frozen=True)
class DrumVoiceSample:
    voice: int
    path: str
    tune: int
    key_assignment: int
    play_mode: int
    pan: int  # signed byte @ slot+0x06 (device ±100)
    slot_gain_u32: int  # u32 @ slot+0x7C (gain / loop-crossfade field)

    @property
    def fade_ui(self) -> int:
        """Loop-crossfade UI decoded from this slot's +0x7C u32."""
        return decode_drum_fade_u32(self.slot_gain_u32)


@dataclass(frozen=True)
class DrumTrackSamples:
    track: int
    engine_id: int
    voices: tuple[DrumVoiceSample, ...]

    @property
    def assigned_paths(self) -> tuple[DrumVoiceSample, ...]:
        """Voices whose path is non-empty (typical kit has all 24 populated)."""
        return tuple(v for v in self.voices if v.path)


@dataclass(frozen=True)
class ProjectDrumSamples:
    tracks: tuple[DrumTrackSamples, ...]


def inspect_drum_samples_bytes(data: bytes) -> ProjectDrumSamples:
    header, image = decode_project(data)
    project = ImageProject(header, bytearray(image))
    project._rescan()
    return inspect_drum_samples(project)


def inspect_drum_samples(project: ImageProject) -> ProjectDrumSamples:
    tracks: list[DrumTrackSamples] = []
    for track in range(1, len(project._starts) + 1):
        engine_id = project.image[project.track_start(track) + ENGINE_ID_OFFSET]
        if engine_id != DRUM_ENGINE_ID:
            continue
        tracks.append(
            DrumTrackSamples(
                track=track,
                engine_id=engine_id,
                voices=_read_voice_table(project, track),
            )
        )
    return ProjectDrumSamples(tracks=tuple(tracks))


def _read_voice_table(project: ImageProject, track: int) -> tuple[DrumVoiceSample, ...]:
    base = project.track_start(track) + DRUM_TABLE_OFFSET
    voices: list[DrumVoiceSample] = []
    for voice in range(DRUM_VOICE_COUNT):
        slot = project.image[base + voice * DRUM_SLOT_SIZE : base + (voice + 1) * DRUM_SLOT_SIZE]
        voices.append(
            DrumVoiceSample(
                voice=voice,
                path=_read_path(slot),
                tune=slot[0],
                key_assignment=slot[2],
                play_mode=slot[3],
                pan=_signed_byte(slot[DRUM_PAN_OFFSET]),
                slot_gain_u32=int.from_bytes(
                    slot[DRUM_GAIN_OFFSET : DRUM_GAIN_OFFSET + 4], "little"
                ),
            )
        )
    return tuple(voices)


def _signed_byte(value: int) -> int:
    return value if value < 128 else value - 256


def _read_path(slot: bytes) -> str:
    raw = slot[DRUM_PATH_OFFSET : DRUM_PATH_OFFSET + 72]
    end = raw.find(0)
    if end < 0:
        end = len(raw)
    return raw[:end].decode("latin1", errors="replace").strip()
