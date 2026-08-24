"""Preflight validation for generated or edited OP-XY projects."""

from __future__ import annotations

from dataclasses import dataclass

from .image_writer import (
    MAX_PATTERNS_PER_TRACK,
    NOTE_SIZE,
    OFF_NOTE_COUNT,
    OFF_PATTERN_STEPS,
    OFF_SCALE,
    TRACK_COUNT,
    ImageProject,
    pattern_starts_by_track_from_image,
)

KNOWN_INSTRUMENT_ENGINES = {0x02, 0x03, 0x06, 0x07, 0x12, 0x13, 0x14, 0x16, 0x1E, 0x1F, 0x20}
SAMPLER_ENGINE = 0x02
DRUM_ENGINE = 0x03
MULTISAMPLER_ENGINE = 0x1E
ENGINE_OFFSET = 0x14
PRESET_PATH_OFFSET = ImageProject.PRESET_PATH
PRESET_PATH_SIZE = ImageProject.PRESET_PATH_MAX
SAMPLE_TABLE_OFFSET = 0x3957
SAMPLE_SLOT_SIZE = 0x80
SAMPLE_PATH_OFFSET = 0x08
SAMPLE_PATH_SIZE = 72
SAMPLER_FRAMECOUNT_OFFSET = 0x393F
SAMPLER_START_OFFSET = 0x3943
SAMPLER_END_OFFSET = 0x3947
SAMPLER_GAIN_OFFSET = SAMPLE_TABLE_OFFSET + 0x05


@dataclass(frozen=True)
class ProjectValidationIssue:
    severity: str
    code: str
    message: str
    track: int | None = None
    pattern: int | None = None

    def describe(self) -> str:
        location = ""
        if self.track is not None:
            location = f" T{self.track}"
            if self.pattern is not None:
                location += f" P{self.pattern}"
        return f"{self.severity.upper()} {self.code}{location}: {self.message}"


@dataclass(frozen=True)
class ProjectValidationReport:
    issues: tuple[ProjectValidationIssue, ...]

    @property
    def errors(self) -> tuple[ProjectValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ProjectValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors

    def describe(self) -> str:
        if not self.issues:
            return "project validation passed"
        return "\n".join(issue.describe() for issue in self.issues)


def _u32(image: bytearray, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _c_string(image: bytearray, offset: int, size: int) -> tuple[str, bool]:
    raw = bytes(image[offset : offset + size])
    end = raw.find(0)
    terminated = end >= 0
    if not terminated:
        end = len(raw)
    return raw[:end].decode("latin1", errors="replace"), terminated


def validate_project(project: ImageProject, *, generated: bool = False) -> ProjectValidationReport:
    """Validate invariants that can be checked before a project reaches hardware.

    ``generated=True`` also checks product expectations such as metronome-off
    output and populated sample paths. Unknown bytes remain untouched.
    """
    issues: list[ProjectValidationIssue] = []
    patterns_by_track = pattern_starts_by_track_from_image(project.image)
    if len(patterns_by_track) != TRACK_COUNT:
        issues.append(
            ProjectValidationIssue(
                "error",
                "track-layout",
                f"expected {TRACK_COUNT} logical tracks, found {len(patterns_by_track)}",
            )
        )
        return ProjectValidationReport(tuple(issues))

    if generated and project.image[project.GLOBAL_CLICK] != 0:
        issues.append(
            ProjectValidationIssue(
                "warning",
                "metronome-enabled",
                "generated project retains a nonzero click level",
            )
        )

    known_scales = set(ImageProject.SCALE_BYTES.values())
    multisampler_warned_tracks: set[int] = set()
    for track, starts in enumerate(patterns_by_track, start=1):
        if not 1 <= len(starts) <= MAX_PATTERNS_PER_TRACK:
            issues.append(
                ProjectValidationIssue(
                    "error",
                    "pattern-count",
                    f"found {len(starts)} patterns",
                    track,
                )
            )
            continue
        for pattern, start in enumerate(starts, start=1):
            active_steps = project.image[start + OFF_PATTERN_STEPS]
            if not 1 <= active_steps <= 64:
                issues.append(
                    ProjectValidationIssue(
                        "error", "pattern-length", f"invalid active-step count {active_steps}", track, pattern
                    )
                )
            scale = project.image[start + OFF_SCALE]
            if scale not in known_scales:
                issues.append(
                    ProjectValidationIssue(
                        "warning",
                        "track-scale-unknown",
                        f"raw scale byte 0x{scale:02X} is not decoded",
                        track,
                        pattern,
                    )
                )
            note_count = project.image[start + OFF_NOTE_COUNT]
            if note_count > 120:
                issues.append(
                    ProjectValidationIssue(
                        "error", "note-limit", f"contains {note_count} notes", track, pattern
                    )
                )
            note_end = start + OFF_NOTE_COUNT + 1 + note_count * NOTE_SIZE
            if note_end > len(project.image):
                issues.append(
                    ProjectValidationIssue(
                        "error", "note-vector-truncated", "note vector exceeds decoded image", track, pattern
                    )
                )

            engine = project.image[start + ENGINE_OFFSET]
            if track <= 8 and engine not in KNOWN_INSTRUMENT_ENGINES:
                issues.append(
                    ProjectValidationIssue(
                        "warning",
                        "engine-unknown",
                        f"instrument engine 0x{engine:02X} is not labelled",
                        track,
                        pattern,
                    )
                )
            preset_path, preset_terminated = _c_string(
                project.image, start + PRESET_PATH_OFFSET, PRESET_PATH_SIZE
            )
            if not preset_terminated:
                issues.append(
                    ProjectValidationIssue(
                        "error", "preset-path-unterminated", "preset path fills its fixed field", track, pattern
                    )
                )
            if generated and track <= 8 and engine in KNOWN_INSTRUMENT_ENGINES and not preset_path:
                issues.append(
                    ProjectValidationIssue(
                        "warning", "preset-path-empty", "instrument has no preset identity", track, pattern
                    )
                )

            if engine == SAMPLER_ENGINE:
                _validate_sampler(project, issues, start, track, pattern, generated)
            elif engine == DRUM_ENGINE:
                _validate_drum(project, issues, start, track, pattern, generated)
            elif engine == MULTISAMPLER_ENGINE and track not in multisampler_warned_tracks:
                multisampler_warned_tracks.add(track)
                issues.append(
                    ProjectValidationIssue(
                        "warning",
                        "multisampler-zones-unvalidated",
                        "zone boundaries/root keys remain opaque; bytes are preserved but not preflighted",
                        track,
                        pattern,
                    )
                )

    _validate_scenes(project, patterns_by_track, issues)
    _validate_songs(project, issues)
    return ProjectValidationReport(tuple(issues))


def _validate_sampler(
    project: ImageProject,
    issues: list[ProjectValidationIssue],
    start: int,
    track: int,
    pattern: int,
    generated: bool,
) -> None:
    path, terminated = _c_string(
        project.image, start + SAMPLE_TABLE_OFFSET + SAMPLE_PATH_OFFSET, SAMPLE_PATH_SIZE
    )
    framecount = _u32(project.image, start + SAMPLER_FRAMECOUNT_OFFSET)
    sample_start = _u32(project.image, start + SAMPLER_START_OFFSET)
    sample_end = _u32(project.image, start + SAMPLER_END_OFFSET)
    if not terminated:
        issues.append(ProjectValidationIssue("error", "sample-path-unterminated", "sampler path fills its fixed field", track, pattern))
    if generated and not path:
        issues.append(ProjectValidationIssue("error", "sampler-path-empty", "sampler has no audible sample path", track, pattern))
    if generated and framecount == 0:
        issues.append(ProjectValidationIssue("error", "sampler-framecount-zero", "sampler frame count is zero", track, pattern))
    if path and sample_end <= sample_start:
        issues.append(ProjectValidationIssue("error", "sampler-window-empty", f"sample window {sample_start}..{sample_end} is empty", track, pattern))
    if generated and path and project.image[start + SAMPLER_GAIN_OFFSET] == 0:
        issues.append(ProjectValidationIssue("warning", "sampler-gain-zero", "sampler gain byte is zero; confirm the sample is audible", track, pattern))


def _validate_drum(
    project: ImageProject,
    issues: list[ProjectValidationIssue],
    start: int,
    track: int,
    pattern: int,
    generated: bool,
) -> None:
    assigned = 0
    keys: list[int] = []
    for voice in range(24):
        slot = start + SAMPLE_TABLE_OFFSET + voice * SAMPLE_SLOT_SIZE
        path, terminated = _c_string(project.image, slot + SAMPLE_PATH_OFFSET, SAMPLE_PATH_SIZE)
        if not terminated:
            issues.append(ProjectValidationIssue("error", "sample-path-unterminated", f"drum voice {voice} path fills its fixed field", track, pattern))
        if path:
            assigned += 1
            keys.append(project.image[slot + 0x02])
    if generated and assigned == 0:
        issues.append(ProjectValidationIssue("error", "drum-kit-empty", "drum engine has no mapped sample slots", track, pattern))
    if generated and len(keys) != len(set(keys)):
        issues.append(ProjectValidationIssue("warning", "drum-keys-duplicate", "assigned drum voices contain duplicate key mappings", track, pattern))


def _validate_scenes(
    project: ImageProject,
    patterns_by_track: list[list[int]],
    issues: list[ProjectValidationIssue],
) -> None:
    track1_start = patterns_by_track[0][0]
    for scene in range(99):
        slot = project.scene_slot0 + scene * 33
        if slot + 33 > track1_start:
            break
        if project.image[slot + 32] == 0:
            continue
        for track in range(TRACK_COUNT):
            selected = project.image[slot + track]
            if selected >= len(patterns_by_track[track]):
                issues.append(
                    ProjectValidationIssue(
                        "error",
                        "scene-pattern-missing",
                        f"scene {scene + 1} selects unavailable pattern {selected + 1}",
                        track + 1,
                    )
                )


def _validate_songs(
    project: ImageProject,
    issues: list[ProjectValidationIssue],
) -> None:
    for song in range(1, project.SONG_SLOT_COUNT + 1):
        try:
            offset = project._song_slot_offset(song)
            scene_chain, _loop = project.get_song_chain(song)
        except ValueError as error:
            issues.append(
                ProjectValidationIssue(
                    "error",
                    "song-footer-invalid",
                    f"Song {song} cannot be parsed: {error}",
                )
            )
            return

        count = project.image[offset]
        loop_offset = offset + 1 + count
        loop_raw = project.image[loop_offset]
        reserved = project.image[loop_offset + 1]
        if loop_raw not in (0, 1):
            issues.append(
                ProjectValidationIssue(
                    "error",
                    "song-loop-invalid",
                    f"Song {song} has loop byte {loop_raw}; expected 0 or 1",
                )
            )
        if reserved != 0:
            issues.append(
                ProjectValidationIssue(
                    "warning",
                    "song-reserved-nonzero",
                    f"Song {song} reserved byte is 0x{reserved:02X}",
                )
            )
        for scene in scene_chain:
            if scene >= 99:
                issues.append(
                    ProjectValidationIssue(
                        "error",
                        "song-scene-range",
                        f"Song {song} references scene {scene + 1}; maximum is 99",
                    )
                )
                continue
            if scene == 0:
                continue
            slot = project.scene_slot0 + scene * 33
            if project.image[slot + 32] == 0:
                issues.append(
                    ProjectValidationIssue(
                        "warning",
                        "song-scene-empty",
                        f"Song {song} references Scene {scene + 1}, whose row is not marked present",
                    )
                )


def validate_project_bytes(data: bytes, *, generated: bool = False) -> ProjectValidationReport:
    return validate_project(ImageProject.from_bytes(data), generated=generated)
