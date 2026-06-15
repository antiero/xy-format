from pathlib import Path

import pytest

from xy.brain_inspection import inspect_brain_bytes

PROBES = Path("src/aux-track-probes/2026-06-t09-brain")


def _brain(filename: str):
    return inspect_brain_bytes((PROBES / filename).read_bytes())


def test_brain_baseline_defaults() -> None:
    brain = _brain("t09-brain-baseline.xy")
    assert brain.route_mask == 0xFC
    assert brain.routed_tracks == (3, 4, 5, 6, 7, 8)
    assert brain.pristine_flag == 0x08
    assert not brain.edited
    assert brain.param_words == (0x7FFFFFFF, 0, 0, 0)
    assert brain.notes == ()


@pytest.mark.parametrize(
    "filename,mask,tracks",
    [
        ("t09-brain-route-t1-only.xy", 0x01, (1,)),
        ("t09-brain-route-t2-only.xy", 0x02, (2,)),
        ("t09-brain-route-t3-only.xy", 0x04, (3,)),
        ("t09-brain-route-t4-only.xy", 0x08, (4,)),
        ("t09-brain-route-t5-only.xy", 0x10, (5,)),
        ("t09-brain-route-t6-only.xy", 0x20, (6,)),
        ("t09-brain-route-t7-only.xy", 0x40, (7,)),
        ("t09-brain-route-t8-only.xy", 0x80, (8,)),
    ],
)
def test_brain_route_mask_is_t1_low_bit(filename: str, mask: int, tracks: tuple[int, ...]) -> None:
    brain = _brain(filename)
    assert brain.route_mask == mask
    assert brain.routed_tracks == tracks
    assert brain.edited


def test_brain_recorded_notes_use_generic_note_vector() -> None:
    brain = _brain("t09-brain-seq-two-notes.xy")
    assert len(brain.notes) == 2
    assert brain.notes[0].step == 1
    assert brain.notes[0].tick == 0
    assert brain.notes[0].gate_ticks == 240
    assert brain.notes[0].note == 60
    assert brain.notes[0].velocity == 100
    assert brain.notes[0].flags == (0, 0)
    assert brain.notes[1].step == 9
    assert brain.notes[1].tick == 3840
    assert brain.notes[1].gate_ticks == 240
    assert brain.notes[1].note == 67
    assert brain.notes[1].velocity == 100
    assert brain.notes[1].flags == (0, 0)


def test_brain_known_raw_parameter_words() -> None:
    assert _brain("t09-brain-mode-auto.xy").param_words == (0x7FFFFFFF, 0, 0, 0)
    assert _brain("t09-brain-mode-manual.xy").param_words == (
        0x0FFFFFFF,
        0x02AAAAAA,
        0,
        0,
    )
    assert _brain("t09-brain-key-d.xy").param_words == (
        0x2FFFFFFE,
        0x17FFFFFE,
        0,
        0,
    )
    assert _brain("t09-brain-scale-minor.xy").param_words == (
        0x0FFFFFFF,
        0,
        0x69249247,
        0,
    )


@pytest.mark.parametrize(
    "filename,index,name,raw",
    [
        ("t09-brain-key-c.xy", 0, "C", 0x02AAAAAA),
        ("t09-brain-key-c#.xy", 1, "C#", 0x12AAAAA9),
        ("t09-brain-key-d.xy", 2, "D", 0x17FFFFFE),
        ("t09-brain-key-d#.xy", 3, "D#", 0x22AAAAA8),
        ("t09-brain-key-e.xy", 4, "E", 0x2D555552),
        ("t09-brain-key-f.xy", 5, "F", 0x37FFFFFC),
        ("t09-brain-key-f#.xy", 6, "F#", 0x42AAAAA6),
        ("t09-brain-key-g.xy", 7, "G", 0x52AAAAA5),
        ("t09-brain-key-g#.xy", 8, "G#", 0x5D55554F),
        ("t09-brain-key-a.xy", 9, "A", 0x67FFFFF9),
        ("t09-brain-key-a#.xy", 10, "A#", 0x6D55554E),
        ("t09-brain-key-b.xy", 11, "B", 0x7D55554D),
    ],
)
def test_brain_key_candidate_uses_twelve_encoder_buckets(
    filename: str, index: int, name: str, raw: int
) -> None:
    brain = _brain(filename)
    assert brain.key_raw == raw
    assert brain.candidate_key_index == index
    assert brain.candidate_key_name == name


@pytest.mark.parametrize(
    "filename,index,name,raw",
    [
        ("t09-brain-scale-major.xy", 0, "major", 0x04924924),
        ("t09-brain-scale-dorian.xy", 1, "dorian", 0x16DB6DB6),
        ("t09-brain-scale-phrygian.xy", 2, "phrygian", 0x29249248),
        ("t09-brain-scale-lydian.xy", 3, "lydian", 0x3B6DB6DA),
        ("t09-brain-scale-mixolydian.xy", 4, "mixolydian", 0x4DB6DB6C),
        ("t09-brain-scale-minor.xy", 5, "minor", 0x69249247),
        ("t09-brain-scale-locrian.xy", 6, "locrian", 0x7B6DB6D9),
    ],
)
def test_brain_scale_candidate_uses_seven_encoder_buckets(
    filename: str, index: int, name: str, raw: int
) -> None:
    brain = _brain(filename)
    assert brain.scale_raw == raw
    assert brain.candidate_scale_index == index
    assert brain.candidate_scale_name == name


PCGEN_A = Path(
    "src/aux-track-probes/2026-06-t09-brain/pc-generated-formula-validation-fixtures/phase-a-wrong-hyp"
)
PHASE_B = Path(
    "src/aux-track-probes/2026-06-t09-brain/pc-generated-formula-validation-fixtures/phase-b"
)
KEY_STEP = 178956972
SCALE_STEP = 306783380
KEY_SLUGS = {
    "c": "C",
    "csharp": "C#",
    "d": "D",
    "dsharp": "D#",
    "e": "E",
    "f": "F",
    "fsharp": "F#",
    "g": "G",
    "gsharp": "G#",
    "a": "A",
    "asharp": "A#",
    "b": "B",
}


@pytest.mark.parametrize(
    "filename",
    sorted(PCGEN_A.glob("pcgen-expect-key-*.xy")),
    ids=lambda path: path.name,
)
def test_pcgen_brain_key_edge_probes_preserve_raw_formula_inputs(filename: Path) -> None:
    stem = filename.stem.removeprefix("pcgen-expect-key-")
    label, edge, raw_hex = stem.rsplit("-", 2)
    raw = int(raw_hex, 16)
    brain = inspect_brain_bytes(filename.read_bytes())
    assert edge in {"lo", "hi"}
    assert brain.key_raw == raw
    if edge == "hi":
        assert brain.candidate_key_name == KEY_SLUGS[label]


@pytest.mark.parametrize(
    "filename",
    sorted(PCGEN_A.glob("pcgen-expect-scale-*.xy")),
    ids=lambda path: path.name,
)
def test_pcgen_brain_scale_edge_probes_preserve_raw_formula_inputs(filename: Path) -> None:
    stem = filename.stem.removeprefix("pcgen-expect-scale-")
    label, edge, raw_hex = stem.rsplit("-", 2)
    raw = int(raw_hex, 16)
    brain = inspect_brain_bytes(filename.read_bytes())
    assert edge in {"lo", "hi"}
    assert brain.scale_raw == raw
    if edge == "hi":
        assert brain.candidate_scale_name == label


def _step_key_index(raw: int) -> int:
    return min(11, raw // KEY_STEP)


def _step_scale_index(raw: int) -> int:
    return min(6, raw // SCALE_STEP)


def _raw_from_flip_filename(filename: Path) -> int:
    return int(filename.stem.rsplit("-", 1)[-1], 16)


@pytest.mark.parametrize(
    "filename",
    sorted(PHASE_B.glob("pcgen-key-*.xy")),
    ids=lambda path: path.name,
)
def test_phase_b_key_flip_probes_use_step_formula(filename: Path) -> None:
    raw = _raw_from_flip_filename(filename)
    brain = inspect_brain_bytes(filename.read_bytes())
    assert brain.key_raw == raw
    assert _step_key_index(raw) >= 1


@pytest.mark.parametrize(
    "filename",
    sorted(PHASE_B.glob("pcgen-scale-*.xy")),
    ids=lambda path: path.name,
)
def test_phase_b_scale_flip_probes_use_step_formula(filename: Path) -> None:
    raw = _raw_from_flip_filename(filename)
    brain = inspect_brain_bytes(filename.read_bytes())
    assert brain.scale_raw == raw
    assert _step_scale_index(raw) >= 1
