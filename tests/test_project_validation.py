from xy.image_writer import ImageProject
from xy.project_validation import validate_project


BASE = "src/one-off-changes-from-default/unnamed 1.xy"


def _codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def test_device_baseline_has_no_structural_validation_errors() -> None:
    report = validate_project(ImageProject.from_file(BASE))
    assert report.ok
    assert not report.errors


def test_generated_preflight_reports_click_and_opaque_multisampler_zones() -> None:
    report = validate_project(ImageProject.from_file(BASE), generated=True)
    assert report.ok
    assert {"metronome-enabled", "multisampler-zones-unvalidated"} <= _codes(report)


def test_unknown_track_scale_is_reported_without_rejecting_preserved_bytes() -> None:
    project = ImageProject.from_file(BASE)
    project.image[project.track_start(1) + project.TRK_SCALE] = 0x02
    report = validate_project(project)
    assert report.ok
    assert "track-scale-unknown" in _codes(report)


def test_generated_sampler_requires_path_framecount_and_audible_window() -> None:
    project = ImageProject.from_file(BASE)
    start = project.track_start(1)
    project.image[start + project.TRK_ENGINE] = project.SAMPLER_ENGINE
    project.image[start + project.DRUM_TABLE + project.SAMPLER_SLOT_PATH :
                  start + project.DRUM_TABLE + project.SAMPLER_SLOT_PATH + 72] = b"\x00" * 72
    for offset in (
        project.SAMPLER_FRAMECOUNT,
        project.SAMPLER_SAMPLE_START,
        project.SAMPLER_SAMPLE_END,
    ):
        project.image[start + offset : start + offset + 4] = b"\x00" * 4

    report = validate_project(project, generated=True)
    assert {"sampler-path-empty", "sampler-framecount-zero"} <= _codes(report)
    assert not report.ok


def test_scene_cannot_select_a_pattern_that_is_not_present() -> None:
    project = ImageProject.from_file(BASE)
    scene = project.scene_slot0
    project.image[scene] = 15
    project.image[scene + 32] = 1

    report = validate_project(project)
    assert "scene-pattern-missing" in _codes(report)
    assert not report.ok
