from pathlib import Path

from xy.drum_sample_inspection import inspect_drum_samples, inspect_drum_samples_bytes
from xy.image_writer import ImageProject
from xy.rle import decode_project

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT / "src" / "app-sample-probes" / "2026-06-drum-pan-fade"
BASELINE = PROBES / "d0-baseline-pp.xy"
VOICE = 23  # low F kick pad on pp kit (key 53)


def _voice(path: Path, voice: int = VOICE):
    inspection = inspect_drum_samples_bytes(path.read_bytes())
    track = next(t for t in inspection.tracks if t.track == 1)
    return track.voices[voice]


def _image_u32(path: Path, image_offset: int) -> int:
    _, image = decode_project(path.read_bytes())
    return int.from_bytes(image[image_offset : image_offset + 4], "little")


def test_baseline_voice23_is_neutral_pan() -> None:
    voice = _voice(BASELINE)
    assert voice.key_assignment == 53
    assert voice.pan == 0


def test_pan_hard_left_and_right_are_isolated_on_voice23() -> None:
    baseline = _voice(BASELINE)
    left = _voice(PROBES / "d1-v23-pan-hard-left.xy")
    right = _voice(PROBES / "d2-v23-pan-hard-right.xy")

    assert left.pan == -100
    assert right.pan == 100

    for other, before, after in zip(range(24), inspect_drum_samples_bytes(BASELINE.read_bytes()).tracks[0].voices, inspect_drum_samples_bytes((PROBES / "d1-v23-pan-hard-left.xy").read_bytes()).tracks[0].voices):
        if other == VOICE:
            continue
        assert after.pan == before.pan


def test_fade_ui_writes_four_bytes_at_voice22_slot_gain() -> None:
    """Fade edits on the v23 pad changed only v22 slot+0x7C (image 0x524c..0x524f)."""
    cases = [
        ("d3-v23-fade-99.xy", 0x7FFFFFFF),
        ("d3-v23-fade-27.xy", 0x23D6C7FF),
        ("d3-v23-fade-63.xy", 0x51EB63FF),
    ]
    for filename, expected in cases:
        assert _image_u32(PROBES / filename, 0x524C) == expected
        voice22 = _voice(PROBES / filename, voice=22)
        assert voice22.slot_gain_u32 == expected


def test_set_drum_voice_pan_reproduces_left_capture() -> None:
    project = ImageProject.from_file(str(BASELINE))
    project.set_drum_voice(1, VOICE, pan=-100)
    assert _voice_from_project(project).pan == -100


def _voice_from_project(project: ImageProject):
    inspection = inspect_drum_samples(project)
    return next(t for t in inspection.tracks if t.track == 1).voices[VOICE]


def test_set_drum_voice_pan_matches_device_bytes() -> None:
    project = ImageProject.from_file(str(BASELINE))
    project.set_drum_voice(1, VOICE, pan=-100)
    _, ours = decode_project(project.to_bytes())
    _, cap = decode_project((PROBES / "d1-v23-pan-hard-left.xy").read_bytes())
    off = ImageProject.from_file(str(BASELINE)).track_start(1) + 0x3957 + VOICE * 0x80 + 0x06
    assert ours[off] == cap[off]
