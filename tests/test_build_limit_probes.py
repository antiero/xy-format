import pytest

from tools.build_limit_probes import PROBE_NAMES, build_probe_bytes
from xy.image_writer import (
    SCENE_SLOT_SIZE,
    ImageProject,
    pattern_starts_by_track_from_image,
)
from xy.project_validation import validate_project_bytes


@pytest.fixture(scope="module")
def probes() -> dict[str, bytes]:
    return build_probe_bytes()


def test_probe_names_match_alphabetical_device_order() -> None:
    assert PROBE_NAMES == tuple(sorted(PROBE_NAMES))


@pytest.mark.parametrize("name", PROBE_NAMES)
def test_every_limit_probe_passes_generated_preflight(
    probes: dict[str, bytes], name: str
) -> None:
    assert validate_project_bytes(probes[name], generated=True).ok


def test_scenes99_populates_exactly_rows_zero_through_98(
    probes: dict[str, bytes],
) -> None:
    project = ImageProject.from_bytes(probes["01_scenes99.xy"])
    flags = [
        project.image[project.scene_slot0 + index * SCENE_SLOT_SIZE + 32]
        for index in range(99)
    ]
    assert flags == [1] * 99
    assert project.image[project.scene_slot0 + 98 * SCENE_SLOT_SIZE] == 2


def test_song96_serializes_the_full_scene_chain(probes: dict[str, bytes]) -> None:
    project = ImageProject.from_bytes(probes["02_song96.xy"])
    assert project.get_song_chain(1) == (list(range(96)), True)


def test_patterns16_and_notes120_hit_the_writer_ceilings(
    probes: dict[str, bytes],
) -> None:
    patterns = ImageProject.from_bytes(probes["03_patterns16.xy"])
    notes = ImageProject.from_bytes(probes["04_notes120.xy"])
    assert len(pattern_starts_by_track_from_image(patterns.image)[0]) == 16
    assert notes.note_count(1) == 120
    with pytest.raises(ValueError, match="note limit"):
        notes.add_note(1, step=1, note=72)
