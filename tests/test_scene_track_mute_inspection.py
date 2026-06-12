from pathlib import Path

import pytest

from xy.image_writer import ImageProject, SCENE_SLOT0, SCENE_SLOT_SIZE
from xy.rle import decode_project
from xy.scene_volume_inspection import (
    SCENE_MUTE_OFFSET,
    SCENE_MUTE_VALUE,
    read_scene_muted_tracks,
    read_scene_slot_mute_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT / "src" / "app-scene-probes" / "2026-06-track-mutes"
BASELINE = PROBES / "mute-#-#-#-#.xy"
SLOT0 = 0  # scene 1 on single-scene project (firmware 1.1.4)


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("mute-1-3-6-7.xy", (1, 3, 6, 7)),
        ("mute-2-7-8-#.xy", (2, 7, 8)),
        ("mute-3-4-5-6.xy", (3, 4, 5, 6)),
    ],
)
def test_scene1_mutes_are_in_slot0_mute_region(filename: str, expected: tuple[int, ...]) -> None:
    project = ImageProject.from_file(str(PROBES / filename))
    assert read_scene_muted_tracks(project, SLOT0) == expected
    for track in expected:
        mutes = read_scene_slot_mute_bytes(project, SLOT0)
        assert mutes[track - 1] == SCENE_MUTE_VALUE


def test_baseline_has_no_muted_tracks() -> None:
    project = ImageProject.from_file(str(BASELINE))
    assert read_scene_muted_tracks(project, SLOT0) == ()
    assert all(b == 0 for b in read_scene_slot_mute_bytes(project, SLOT0))


def test_mute_diffs_are_only_slot0_mute_bytes() -> None:
    base_img = BASELINE.read_bytes()
    _, base = decode_project(base_img)
    for filename in ("mute-2-7-8-#.xy", "mute-3-4-5-6.xy"):
        _, var = decode_project((PROBES / filename).read_bytes())
        diffs = [i for i in range(len(base)) if base[i] != var[i]]
        mute_start = SCENE_SLOT0 + SLOT0 * SCENE_SLOT_SIZE + SCENE_MUTE_OFFSET
        mute_end = mute_start + 16
        assert all(mute_start <= d < mute_end for d in diffs)
