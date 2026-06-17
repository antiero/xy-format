import json

import pytest

from xy import (
    apply_patch_json_file,
    PatchJsonSoundPatchOptions,
    apply_patch_json_sound,
    apply_patch_json_text,
    read_patch_sound_state,
    drum_kit_patch_from_patch_json,
    inspect_drum_samples,
    inspect_preset_paths,
    read_sampler_sample_edit,
    sampler_patch_from_patch_json,
    sound_patch_from_patch_json_file,
    sound_patch_from_patch_json_text,
    sound_patch_from_patch_json,
)
from xy.image_writer import ImageProject
from xy.sampler_sample_inspection import encode_sampler_loop_crossfade_frames

BASE = "src/one-off-changes-from-default/unnamed 1.xy"
UNIQUE_SAMPLER_PATCH = (
    "src/sampler-project-state/2026-06-15/presets/t7-map-unique.preset/patch.json"
)


def test_maps_drum_regions_to_pad_patches_by_op_xy_key_order() -> None:
    patch = drum_kit_patch_from_patch_json(
        {
            "type": "drum",
            "regions": [
                {
                    "sample": "kick-f#2-0.wav",
                    "hikey": 53,
                    "pan": -12,
                    "playmode": "oneshot",
                    "reverse": True,
                    "transpose": -3,
                    "gain": 1234,
                    "sample.start": 10,
                    "sample.end": 3000,
                    "fade.out": 42,
                },
                {"sample": "ignored.wav", "hikey": 80},
            ],
        },
        PatchJsonSoundPatchOptions(preset_device_path="/fat32/presets/drum/live kit.preset"),
    )

    assert patch.preset_path == "drum/live kit"
    assert patch.pads.keys() == {0}
    assert patch.pads[0].path == "/fat32/presets/drum/live kit.preset/kick-f#2-0.wav"
    assert patch.pads[0].tune == -3
    assert patch.pads[0].key_assignment == 53
    assert patch.pads[0].play_mode == 1
    assert patch.pads[0].direction == 1
    assert patch.pads[0].pan == -12
    assert patch.pads[0].start == 10
    assert patch.pads[0].end == 3000
    assert patch.pads[0].gain == 1234
    assert patch.pads[0].fade == 42


def test_maps_sampler_patch_region_to_one_shot_sampler_patch_shape() -> None:
    patch = sampler_patch_from_patch_json(
        {
            "type": "sampler",
            "regions": [
                {
                    "sample": "bass-c3-0.wav",
                    "framecount": 5000,
                    "reverse": False,
                    "gain": 99,
                    "tune": -5,
                    "sample.start": 12,
                    "loop.start": 123,
                    "loop.end": 2345,
                    "loop.enabled": True,
                    "loop.onrelease": False,
                    "loop.crossfade": 55,
                }
            ],
        },
        PatchJsonSoundPatchOptions(preset_device_path="/fat32/presets/bass/nt bass.preset"),
    )

    assert patch.preset_path == "bass/nt bass"
    assert patch.path == "/fat32/presets/bass/nt bass.preset/bass-c3-0.wav"
    assert patch.framecount == 5000
    assert patch.sample_start == 12
    assert patch.sample_end == 5000
    assert patch.loop_start == 123
    assert patch.loop_end == 2345
    assert patch.loop_crossfade == 55
    assert patch.loop_crossfade_raw == encode_sampler_loop_crossfade_frames(55, 5000)
    assert patch.root_key is None
    assert patch.tune_cents == -5
    assert patch.tune_tenths is None
    assert patch.loop_type == 0
    assert patch.gain == 99
    assert patch.direction == 0


def test_maps_disabled_sampler_loops_to_loop_off_storage() -> None:
    patch = sampler_patch_from_patch_json(
        {"type": "sampler", "regions": [{"sample": "one.wav", "loop.enabled": False}]}
    )

    assert patch.loop_type == 0x40


def test_maps_sampler_patch_json_onrelease_to_loop_type_bit() -> None:
    patch = sampler_patch_from_patch_json(
        {"type": "sampler", "regions": [{"sample": "one.wav", "loop.onrelease": True}]}
    )

    assert patch.loop_type == 0x80


def test_maps_sampler_patch_json_root_key_from_pitch_keycenter() -> None:
    patch = sampler_patch_from_patch_json(
        {
            "type": "sampler",
            "regions": [
                {
                    "sample": "one.wav",
                    "hikey": 48,
                    "pitch.keycenter": 72,
                }
            ],
        }
    )

    assert patch.root_key == 72


def test_sampler_patch_json_requires_frame_count_for_crossfade_frames() -> None:
    with pytest.raises(ValueError, match="requires framecount"):
        sampler_patch_from_patch_json(
            {"type": "sampler", "regions": [{"sample": "one.wav", "loop.crossfade": 12}]}
        )


def test_reads_patch_json_text_and_file(tmp_path) -> None:
    payload = {
        "type": "sampler",
        "regions": [{"sample": "one.wav", "framecount": 99}],
    }
    text = json.dumps(payload)
    file_path = tmp_path / "patch.json"
    file_path.write_text(text, encoding="utf-8")

    text_patch = sound_patch_from_patch_json_text(text)
    file_patch = sound_patch_from_patch_json_file(file_path)

    assert text_patch.path == "one.wav"
    assert text_patch.framecount == 99
    assert text_patch.sample_end == 99
    assert file_patch == text_patch


def test_rejects_non_object_patch_json_text() -> None:
    with pytest.raises(ValueError, match="root must be an object"):
        sound_patch_from_patch_json_text("[]")


def test_rejects_synth_patch_json_because_it_is_not_template_safe() -> None:
    with pytest.raises(ValueError, match="cannot be written"):
        sound_patch_from_patch_json({"type": "axis", "regions": []})


def test_apply_drum_patch_json_writes_readable_project_fields() -> None:
    project = ImageProject.from_file(BASE)
    apply_patch_json_sound(
        project,
        1,
        {
            "type": "drum",
            "regions": [
                {
                    "sample": "kick.wav",
                    "hikey": 54,
                    "playmode": "oneshot",
                    "reverse": True,
                    "transpose": 7,
                    "pan": -25,
                    "sample.start": 100,
                    "sample.end": 1000,
                    "gain": 0x12345678,
                }
            ],
        },
        PatchJsonSoundPatchOptions(preset_device_path="/fat32/presets/drum/live kit.preset"),
    )

    preset = inspect_preset_paths(project).tracks[0]
    voice = inspect_drum_samples(project).tracks[0].voices[1]
    assert preset.path == "drum/live kit"
    assert voice.path == "/fat32/presets/drum/live kit.preset/kick.wav"
    assert voice.tune_semitones == 7
    assert voice.key_assignment == 54
    assert voice.play_mode == 1
    assert voice.direction == 1
    assert voice.pan == -25
    assert voice.start == 100
    assert voice.end == 1000
    assert voice.gain_u32 == 0x12345678


def test_apply_sampler_patch_json_writes_readable_project_fields() -> None:
    project = ImageProject.from_file(BASE)
    apply_patch_json_sound(
        project,
        3,
        {
            "type": "sampler",
            "regions": [
                {
                    "sample": "bass.wav",
                    "framecount": 4321,
                    "reverse": True,
                    "gain": 88,
                    "tune": 4,
                    "pitch.keycenter": 64,
                    "sample.start": 12,
                    "loop.start": 123,
                    "loop.end": 2345,
                    "loop.enabled": False,
                    "loop.onrelease": True,
                    "loop.crossfade": 55,
                }
            ],
        },
        PatchJsonSoundPatchOptions(preset_device_path="/fat32/presets/bass/nt bass.preset"),
    )

    preset = inspect_preset_paths(project).tracks[2]
    sampler = read_sampler_sample_edit(project, 3)
    assert preset.path == "bass/nt bass"
    assert sampler.path == "/fat32/presets/bass/nt bass.preset/bass.wav"
    assert sampler.framecount == 4321
    assert sampler.sample_start == 12
    assert sampler.sample_end == 4321
    assert sampler.loop_start == 123
    assert sampler.loop_end == 2345
    assert sampler.loop_crossfade_raw == encode_sampler_loop_crossfade_frames(55, 4321)
    assert sampler.loop_crossfade == (sampler.loop_crossfade_raw >> 24)
    assert sampler.tune_byte == 64
    assert sampler.tune_aux_byte == 4
    assert sampler.loop_type_byte == 0xC0
    assert sampler.gain == 88
    assert sampler.direction == 1


def test_apply_sampler_patch_json_writes_confirmed_common_sound_state() -> None:
    patch = json.loads(open(UNIQUE_SAMPLER_PATCH, encoding="utf-8").read())
    project = ImageProject.from_file(BASE)

    apply_patch_json_file(
        project,
        7,
        UNIQUE_SAMPLER_PATCH,
        PatchJsonSoundPatchOptions(preset_device_path="/fat32/presets/snapshot/t7-map-unique.preset"),
    )

    state = read_patch_sound_state(project, 7)
    assert state.engine_id == 0x02
    assert state.engine_params == tuple(patch["engine"]["params"])
    assert state.playmode_raw == 0x15555555
    assert state.amp_envelope == (
        patch["envelope"]["amp"]["attack"],
        patch["envelope"]["amp"]["decay"],
        patch["envelope"]["amp"]["sustain"],
        patch["envelope"]["amp"]["release"],
    )
    assert state.fx_type == 0x10
    assert state.fx_active is True
    assert state.fx_params[:5] == tuple(patch["fx"]["params"][:5])
    assert state.fx_params[5] == 0x7FFF
    assert state.fx_params[6:] == tuple(patch["fx"]["params"][6:])
    assert state.lfo_type == 0x03
    assert state.lfo_active is True
    assert state.lfo_params == tuple(patch["lfo"]["params"])
    assert state.filter_envelope == (
        patch["envelope"]["filter"]["attack"],
        patch["envelope"]["filter"]["decay"],
        patch["envelope"]["filter"]["sustain"],
        patch["envelope"]["filter"]["release"],
    )
    assert state.portamento_amount == patch["engine"]["portamento.amount"]
    assert state.bendrange == patch["engine"]["bendrange"]
    assert state.volume == patch["engine"]["volume"]
    assert state.modwheel_amount == patch["engine"]["modulation"]["modwheel"]["amount"]
    assert state.velocity_target == patch["engine"]["modulation"]["velocity"]["target"]
    assert state.highpass == patch["engine"]["highpass"]


def test_apply_sampler_patch_json_writes_u32_sample_points() -> None:
    project = ImageProject.from_file(BASE)
    apply_patch_json_sound(
        project,
        3,
        {
            "type": "sampler",
            "regions": [
                {
                    "sample": "long.wav",
                    "framecount": 0x176B1,
                    "sample.start": 0x1F65,
                    "loop.start": 0x14D1A,
                    "loop.end": 0x178AC,
                }
            ],
        },
    )

    sampler = read_sampler_sample_edit(project, 3)
    assert sampler.sample_start == 0x1F65
    assert sampler.sample_end == 0x176B1
    assert sampler.loop_start == 0x14D1A
    assert sampler.loop_end == 0x178AC


def test_apply_patch_json_text_and_file_write_project_fields(tmp_path) -> None:
    payload = {
        "type": "drum",
        "regions": [
            {
                "sample": "snare.wav",
                "hikey": 55,
                "playmode": "oneshot",
                "sample.end": 222,
            }
        ],
    }
    text = json.dumps(payload)
    file_path = tmp_path / "patch.json"
    file_path.write_text(text, encoding="utf-8")

    text_project = ImageProject.from_file(BASE)
    file_project = ImageProject.from_file(BASE)
    options = PatchJsonSoundPatchOptions(preset_device_path="/fat32/presets/drum/kit.preset")

    apply_patch_json_text(text_project, 1, text, options)
    apply_patch_json_file(file_project, 1, file_path, options)

    text_voice = inspect_drum_samples(text_project).tracks[0].voices[2]
    file_voice = inspect_drum_samples(file_project).tracks[0].voices[2]
    assert text_voice.path == "/fat32/presets/drum/kit.preset/snare.wav"
    assert text_voice.play_mode == 1
    assert text_voice.end == 222
    assert file_voice == text_voice


def test_maps_confirmed_drum_playmode_strings() -> None:
    expected = {
        "gate": 0,
        "key": 1,
        "oneshot": 1,
        "group": 2,
        "loop": 3,
    }
    for playmode, byte in expected.items():
        patch = drum_kit_patch_from_patch_json(
            {"type": "drum", "regions": [{"sample": "x.wav", "hikey": 53, "playmode": playmode}]}
        )
        assert patch.pads[0].play_mode == byte


def test_rejects_unmapped_drum_playmode_strings() -> None:
    with pytest.raises(ValueError, match="unknown drum playmode"):
        drum_kit_patch_from_patch_json(
            {"type": "drum", "regions": [{"sample": "x.wav", "hikey": 53, "playmode": "solo"}]}
        )


def test_rejects_numeric_drum_playmode_values() -> None:
    with pytest.raises(ValueError, match="not preserved"):
        drum_kit_patch_from_patch_json(
            {"type": "drum", "regions": [{"sample": "x.wav", "hikey": 53, "playmode": 3}]}
        )
