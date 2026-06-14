"""Read known Track 9 Brain fields from decoded project images."""

from __future__ import annotations

from dataclasses import dataclass

from .image_writer import ImageProject
from .rle import decode_project

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4
BRAIN_TRACK = 9

BRAIN_ROUTE_MASK_OFFSET = 0x09
BRAIN_PRISTINE_FLAG_OFFSET = 0x11
BRAIN_PARAM_BASE_OFFSET = 0x3857
BRAIN_PARAM_COUNT = 4
BRAIN_NOTE_VECTOR_OFFSET = 0x456F
BRAIN_ENCODER_SCALE = 0x80000000

BRAIN_KEY_NAMES = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)
BRAIN_SCALE_NAMES = (
    "major",
    "dorian",
    "phrygian",
    "lydian",
    "mixolydian",
    "minor",
    "locrian",
)


@dataclass(frozen=True)
class BrainNote:
    tick: int
    gate_ticks: int
    note: int
    velocity: int
    flags: tuple[int, int]

    @property
    def step(self) -> int | None:
        if self.tick % 480:
            return None
        return self.tick // 480 + 1


@dataclass(frozen=True)
class BrainInspection:
    route_mask: int
    pristine_flag: int
    param_words: tuple[int, ...]
    notes: tuple[BrainNote, ...]

    @property
    def routed_tracks(self) -> tuple[int, ...]:
        return tuple(index + 1 for index in range(8) if self.route_mask & (1 << index))

    @property
    def edited(self) -> bool:
        return self.pristine_flag == 0

    @property
    def link_raw(self) -> int:
        return self.param_words[3]

    @property
    def mode_raw(self) -> int:
        return self.param_words[0]

    @property
    def key_raw(self) -> int:
        return self.param_words[1]

    @property
    def scale_raw(self) -> int:
        return self.param_words[2]

    @property
    def candidate_key_index(self) -> int:
        return min(
            len(BRAIN_KEY_NAMES) - 1,
            (self.key_raw * len(BRAIN_KEY_NAMES)) // BRAIN_ENCODER_SCALE,
        )

    @property
    def candidate_key_name(self) -> str:
        return BRAIN_KEY_NAMES[self.candidate_key_index]

    @property
    def candidate_scale_index(self) -> int:
        return min(
            len(BRAIN_SCALE_NAMES) - 1,
            (self.scale_raw * len(BRAIN_SCALE_NAMES)) // BRAIN_ENCODER_SCALE,
        )

    @property
    def candidate_scale_name(self) -> str:
        return BRAIN_SCALE_NAMES[self.candidate_scale_index]


def _track_base(track: int) -> int:
    if not 1 <= track <= 16:
        raise ValueError("track must be 1..16")
    return TRACK_BASE0 + (track - 1) * TRACK_STRIDE


def read_brain(project: ImageProject) -> BrainInspection:
    image = project.image
    base = _track_base(BRAIN_TRACK)
    param_words = tuple(
        int.from_bytes(
            image[
                base
                + BRAIN_PARAM_BASE_OFFSET
                + index * 4 : base
                + BRAIN_PARAM_BASE_OFFSET
                + index * 4
                + 4
            ],
            "little",
        )
        for index in range(BRAIN_PARAM_COUNT)
    )
    vector = base + BRAIN_NOTE_VECTOR_OFFSET
    count = image[vector]
    notes: list[BrainNote] = []
    for index in range(count):
        offset = vector + 1 + index * 12
        record = image[offset : offset + 12]
        if len(record) < 12:
            break
        notes.append(
            BrainNote(
                tick=int.from_bytes(record[0:4], "little"),
                gate_ticks=int.from_bytes(record[4:8], "little"),
                note=record[8],
                velocity=record[9],
                flags=(record[10], record[11]),
            )
        )
    return BrainInspection(
        route_mask=image[base + BRAIN_ROUTE_MASK_OFFSET],
        pristine_flag=image[base + BRAIN_PRISTINE_FLAG_OFFSET],
        param_words=param_words,
        notes=tuple(notes),
    )


def inspect_brain_bytes(data: bytes) -> BrainInspection:
    header, image = decode_project(data)
    project = ImageProject(header, bytearray(image))
    project._rescan()
    return read_brain(project)
