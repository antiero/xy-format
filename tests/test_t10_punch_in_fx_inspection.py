from pathlib import Path

from xy.rle import decode_project

PROBES = Path("src/aux-track-probes/2026-06-t10-punch-in-fx")

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4
T10_BASE = TRACK_BASE0 + 9 * TRACK_STRIDE
NOTE_VECTOR = T10_BASE + 0x456F


def _image(filename: str) -> bytes:
    return decode_project((PROBES / filename).read_bytes())[1]


def _notes(filename: str) -> list[tuple[int, int, int, int, tuple[int, int]]]:
    image = _image(filename)
    count = image[NOTE_VECTOR]
    notes = []
    for index in range(count):
        offset = NOTE_VECTOR + 1 + index * 12
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


def test_t10_punch_baseline_has_no_trigger_notes() -> None:
    assert _notes("t10-punch-in-fx-baseline.xy") == []


def test_t10_punch_step1_uses_generic_note_vector() -> None:
    assert _notes("t10-punch-trigger-step1.xy") == [
        (0, 240, 101, 100, (0, 0)),
    ]


def test_t10_punch_step9_uses_generic_note_vector() -> None:
    assert _notes("t10-punch-trigger-step9.xy") == [
        (3840, 240, 101, 100, (0, 0)),
    ]


def test_t10_punch_trigger_captures_only_add_one_note_plus_known_save_noise() -> None:
    base = _image("t10-punch-in-fx-baseline.xy")
    allowed = {
        T10_BASE + 0x11,
        T10_BASE + 0x38F2,
        T10_BASE + 0x38F6,
        NOTE_VECTOR,
        *range(NOTE_VECTOR + 1, NOTE_VECTOR + 13),
    }
    # Opening/saving an aux track may also touch the known T9-T16 project-config
    # save-noise bytes. Vector insertion shifts later data; compare only the
    # prefix up to the inserted note vector.
    for track in range(9, 17):
        track_base = TRACK_BASE0 + (track - 1) * TRACK_STRIDE
        allowed.add(track_base + 0x38F2)
        allowed.add(track_base + 0x38F6)

    for filename in ("t10-punch-trigger-step1.xy", "t10-punch-trigger-step9.xy"):
        image = _image(filename)
        diffs_before_vector = {
            offset
            for offset, (a, b) in enumerate(zip(base[: NOTE_VECTOR + 13], image[: NOTE_VECTOR + 13]))
            if a != b
        }
        assert diffs_before_vector <= allowed, filename
