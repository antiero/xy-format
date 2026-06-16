from pathlib import Path

from tests.decoded_image_layout import (
    EDITED_FLAG_OFFSET,
    NOTE_VECTOR_OFFSET,
    SAVE_SIDE_EFFECT_A_OFFSET,
    SAVE_SIDE_EFFECT_B_OFFSET,
    track_base_from_project,
)
from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t12-external-cv")


def _data(filename: str) -> bytes:
    return (PROBES / filename).read_bytes()


def _image(filename: str) -> bytes:
    return decode_project(_data(filename))[1]


def _track_base(filename: str, track: int) -> int:
    return track_base_from_project(_data(filename), track)


def _note_vector(filename: str) -> int:
    return _track_base(filename, 12) + NOTE_VECTOR_OFFSET


def _notes(filename: str) -> list[tuple[int, int, int, int, tuple[int, int]]]:
    image = _image(filename)
    note_vector = _note_vector(filename)
    count = image[note_vector]
    notes = []
    for index in range(count):
        offset = note_vector + 1 + index * 12
        record = image[offset : offset + 12]
        notes.append(
            (
                int.from_bytes(record[0:4], "little"),
                int.from_bytes(record[4:8], "little"),
                record[8],
                record[9],
                (record[10], record[11]),
            )
        )
    return notes


def test_t12_cv_baseline_has_no_notes() -> None:
    assert _notes("t12-external-cv-baseline.xy") == []


def test_t12_cv_step1_uses_generic_note_vector() -> None:
    assert _notes("t12-cv-note-step1.xy") == [
        (0, 240, 29, 100, (0, 0)),
    ]


def test_t12_cv_step9_uses_generic_note_vector() -> None:
    assert _notes("t12-cv-note-step9.xy") == [
        (3840, 240, 53, 100, (0, 0)),
    ]


def test_t12_cv_note_captures_only_add_one_note_plus_known_save_noise() -> None:
    baseline_filename = "t12-external-cv-baseline.xy"
    base = _image("t12-external-cv-baseline.xy")
    t12_base = _track_base(baseline_filename, 12)
    note_vector = t12_base + NOTE_VECTOR_OFFSET
    allowed = {
        0x48,
        t12_base + EDITED_FLAG_OFFSET,
        t12_base + SAVE_SIDE_EFFECT_A_OFFSET,
        t12_base + SAVE_SIDE_EFFECT_B_OFFSET,
        note_vector,
        *range(note_vector + 1, note_vector + 13),
    }
    for track in range(9, 17):
        track_base = _track_base(baseline_filename, track)
        allowed.add(track_base + SAVE_SIDE_EFFECT_A_OFFSET)
        allowed.add(track_base + SAVE_SIDE_EFFECT_B_OFFSET)

    for filename in ("t12-cv-note-step1.xy", "t12-cv-note-step9.xy"):
        image = _image(filename)
        diffs_before_vector = {
            offset
            for offset, (a, b) in enumerate(zip(base[: note_vector + 13], image[: note_vector + 13]))
            if a != b
        }
        assert diffs_before_vector <= allowed, filename
