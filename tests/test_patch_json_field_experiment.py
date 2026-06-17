import json
from pathlib import Path

from xy.image_writer import ImageProject
from xy.patch_json import drum_kit_patch_from_patch_json, sampler_patch_from_patch_json
from xy.sampler_sample_inspection import encode_sampler_loop_crossfade_frames

ROOT = Path("src/preset-load-experiments/2026-06-patch-json-fields")
PRESETS = ROOT / "presets"
PROJECTS = ROOT / "presetprojs"


def _patch(case: str) -> dict:
    return json.loads((PRESETS / f"{case}.preset" / "patch.json").read_text(encoding="utf-8"))


def _project(case: str) -> ImageProject:
    return ImageProject.from_file(str(PROJECTS / f"{case}.xy"))


def _slot(case: str) -> tuple[bytearray, int]:
    project = _project(case)
    base = project.track_start(1)
    return project.image, base + 0x3957


def test_patch_json_field_experiment_confirms_drum_playmode_strings() -> None:
    expected = {
        "dpm-str-gate": 0,
        "dpm-str-key": 1,
        "dpm-str-oneshot": 1,
        "dpm-str-group": 2,
        "dpm-str-loop": 3,
    }
    for case, byte in expected.items():
        patch = drum_kit_patch_from_patch_json(_patch(case))
        image, slot = _slot(case)
        assert patch.pads[0].play_mode == byte
        assert image[slot + 0x03] == byte


def test_patch_json_field_experiment_numeric_drum_playmodes_are_not_preserved() -> None:
    for case in ("dpm-num-1", "dpm-num-2", "dpm-num-3", "dpm-num-4"):
        image, slot = _slot(case)
        assert image[slot + 0x03] == 1


def test_patch_json_field_experiment_confirms_sampler_loop_type_bits() -> None:
    expected = {
        "slt-missing-onrelease": 0x00,
        "slt-missing-enabled": 0x80,
        "slt-enabled-false": 0xC0,
    }
    for case, byte in expected.items():
        patch = sampler_patch_from_patch_json(_patch(case))
        image, slot = _slot(case)
        assert patch.loop_type == byte
        assert image[slot + 0x03] == byte


def test_patch_json_field_experiment_confirms_sampler_key_tune_gain_direction() -> None:
    key_cases = {
        "skey-hikey-64": 60,
        "skey-pitch-64": 64,
        "skey-both-64": 64,
        "skey-lokey-12": 60,
        "skey-conflict-h72-p48": 48,
        "skey-conflict-h48-p72": 72,
    }
    for case, root_key in key_cases.items():
        patch = sampler_patch_from_patch_json(_patch(case))
        image, slot = _slot(case)
        assert patch.root_key == root_key
        assert image[slot] == root_key

    field_cases = {
        "sfld-tune-pos4": (60, 4, 0, 0),
        "sfld-tune-neg5": (60, 0xFB, 0, 0),
        "sfld-gain-064": (60, 0, 64, 0),
        "sfld-reverse-true": (60, 0, 0, 1),
    }
    for case, expected in field_cases.items():
        image, slot = _slot(case)
        assert tuple(image[slot + offset] for offset in (0x00, 0x04, 0x05, 0x07)) == expected


def test_patch_json_field_experiment_confirms_sampler_crossfade_float32_encoder() -> None:
    for case in (
        "scf-00000",
        "scf-00001",
        "scf-02048",
        "scf-24702",
        "scf-49404",
        "scf-74105",
        "scf-98806",
        "scf-98807",
    ):
        patch = _patch(case)
        region = patch["regions"][0]
        image, slot = _slot(case)
        base = slot - 0x3957
        expected = encode_sampler_loop_crossfade_frames(
            region["loop.crossfade"],
            region["framecount"],
        )
        assert int.from_bytes(image[base + 0x3953 : base + 0x3957], "little") == expected
