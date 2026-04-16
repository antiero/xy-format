#!/usr/bin/env python3
"""Generate a small pack of musical showcase files on the validated strict scaffold."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xy.json_build_spec import build_xy_bytes, parse_build_spec


TEMPLATE = REPO_ROOT / "src" / "one-off-changes-from-default" / "unnamed 1.xy"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "showcase"
DEFAULT_SPEC_DIR = REPO_ROOT / "specs" / "showcase"
DEFAULT_MANIFEST = DEFAULT_OUTPUT_DIR / "README.md"

KICK = 48
ALT_KICK = 52
SNARE = 50
CLAP = 53
HAT = 56
OPEN_HAT = 57

QUALITY_INTERVALS = {
    "m7": (0, 3, 7, 10),
    "maj7": (0, 4, 7, 11),
    "dom7": (0, 4, 7, 10),
    "add9": (0, 4, 7, 14),
    "m9": (0, 3, 7, 14),
    "sus2": (0, 2, 7, 14),
}

MID_MOTIFS = {
    "hook": (
        (1, 1, 2, 98, 360),
        (4, 2, 2, 100, 280),
        (7, 3, 2, 102, 320),
        (10, 2, 2, 98, 280),
        (13, 1, 2, 96, 300),
        (16, 0, 2, 98, 420),
    ),
    "answer": (
        (2, 0, 2, 94, 260),
        (6, 1, 2, 96, 260),
        (9, 2, 2, 100, 320),
        (12, 1, 2, 96, 260),
        (15, 0, 2, 94, 300),
    ),
    "pad": (
        (1, 0, 2, 88, 760),
        (5, 1, 2, 90, 640),
        (9, 2, 2, 92, 720),
        (13, 1, 2, 90, 640),
    ),
    "climb": (
        (1, 0, 2, 96, 220),
        (3, 1, 2, 98, 220),
        (5, 2, 2, 100, 220),
        (7, 3, 2, 102, 260),
        (9, 1, 2, 98, 220),
        (11, 2, 2, 100, 220),
        (13, 3, 2, 102, 260),
        (15, 0, 3, 104, 320),
    ),
}

HIGH_MOTIFS = {
    "spark": (
        (3, 1, 3, 88, 240),
        (7, 2, 3, 90, 240),
        (11, 3, 3, 94, 280),
        (15, 2, 3, 90, 240),
    ),
    "echo": (
        (2, 1, 3, 86, 220),
        (6, 2, 3, 88, 220),
        (10, 1, 3, 86, 220),
        (14, 0, 3, 84, 240),
    ),
    "sustain": (
        (1, 2, 3, 86, 760),
        (9, 3, 3, 90, 760),
    ),
    "riser": (
        (4, 0, 3, 88, 220),
        (8, 1, 3, 90, 220),
        (12, 2, 3, 92, 220),
        (16, 3, 3, 96, 260),
    ),
}


@dataclass(frozen=True)
class Chord:
    root: int
    quality: str


@dataclass(frozen=True)
class PatternPlan:
    chords: tuple[Chord, Chord, Chord, Chord]
    kick_mode: str
    hat_mode: str
    bass_mode: str
    lead_mode: str
    counter_mode: str
    accent_mode: str
    chord_mode: str


@dataclass(frozen=True)
class ShowcasePiece:
    slug: str
    title: str
    style: str
    summary: str
    tempo_tenths: int
    groove_amount: int
    patterns: tuple[PatternPlan, ...]
    suggested_pattern_order: tuple[int, ...]


def _note(
    step: int,
    note: int,
    *,
    velocity: int = 100,
    gate_ticks: int = 0,
    tick_offset: int = 0,
) -> dict[str, int]:
    out = {
        "step": step,
        "note": note,
        "velocity": velocity,
        "gate_ticks": gate_ticks,
    }
    if tick_offset:
        out["tick_offset"] = tick_offset
    return out


def _sorted_notes(notes: Iterable[dict[str, int]]) -> list[dict[str, int]]:
    return sorted(notes, key=lambda item: (item["step"], item.get("tick_offset", 0), item["note"]))


def _chord_interval(chord: Chord, tone_index: int) -> int:
    intervals = QUALITY_INTERVALS[chord.quality]
    return intervals[tone_index % len(intervals)]


def _chord_note(chord: Chord, tone_index: int, octave_shift: int) -> int:
    return chord.root + _chord_interval(chord, tone_index) + 12 * octave_shift


def _chord_for_step(chords: tuple[Chord, Chord, Chord, Chord], step: int) -> Chord:
    return chords[(step - 1) // 4]


def _render_kick(mode: str) -> list[dict[str, int]]:
    if mode == "steady":
        return _sorted_notes(
            (
                _note(1, KICK, velocity=116, gate_ticks=420),
                _note(5, KICK, velocity=108, gate_ticks=360),
                _note(9, KICK, velocity=118, gate_ticks=420),
                _note(13, KICK, velocity=110, gate_ticks=360),
            )
        )
    if mode == "broken":
        return _sorted_notes(
            (
                _note(1, KICK, velocity=116, gate_ticks=420),
                _note(4, KICK, velocity=96, gate_ticks=320),
                _note(7, KICK, velocity=102, gate_ticks=320),
                _note(9, KICK, velocity=116, gate_ticks=420),
                _note(12, KICK, velocity=96, gate_ticks=320),
                _note(15, KICK, velocity=104, gate_ticks=320),
            )
        )
    if mode == "drive":
        return _sorted_notes(
            (
                _note(1, KICK, velocity=114, gate_ticks=360),
                _note(3, KICK, velocity=100, gate_ticks=260),
                _note(5, KICK, velocity=112, gate_ticks=360),
                _note(7, KICK, velocity=102, gate_ticks=260),
                _note(9, KICK, velocity=114, gate_ticks=360),
                _note(11, KICK, velocity=102, gate_ticks=260),
                _note(13, KICK, velocity=116, gate_ticks=360),
                _note(15, KICK, velocity=108, gate_ticks=260),
            )
        )
    if mode == "pulse":
        return _sorted_notes(
            _note(step, KICK, velocity=98 + ((idx % 2) * 10), gate_ticks=220)
            for idx, step in enumerate((1, 3, 5, 7, 9, 11, 13, 15))
        )
    if mode == "half":
        return _sorted_notes(
            (
                _note(1, KICK, velocity=116, gate_ticks=420),
                _note(9, KICK, velocity=114, gate_ticks=420),
                _note(13, KICK, velocity=104, gate_ticks=320),
            )
        )
    if mode == "fill":
        return _sorted_notes(
            (
                _note(1, KICK, velocity=118, gate_ticks=360),
                _note(5, KICK, velocity=110, gate_ticks=320),
                _note(9, KICK, velocity=116, gate_ticks=360),
                _note(12, KICK, velocity=96, gate_ticks=240),
                _note(13, KICK, velocity=112, gate_ticks=320),
                _note(15, KICK, velocity=106, gate_ticks=240),
                _note(16, ALT_KICK, velocity=100, gate_ticks=220),
            )
        )
    raise ValueError(f"unknown kick mode: {mode}")


def _render_hat(mode: str) -> list[dict[str, int]]:
    if mode == "backbeat":
        notes = [
            _note(5, SNARE, velocity=108, gate_ticks=340),
            _note(5, CLAP, velocity=84, gate_ticks=280),
            _note(13, SNARE, velocity=112, gate_ticks=340),
            _note(13, CLAP, velocity=88, gate_ticks=280),
        ]
        notes.extend(
            _note(step, HAT, velocity=74 + ((idx % 3) * 4), gate_ticks=220)
            for idx, step in enumerate((3, 7, 11, 15))
        )
        return _sorted_notes(notes)
    if mode == "shimmer":
        notes = [
            _note(5, SNARE, velocity=110, gate_ticks=340),
            _note(5, CLAP, velocity=86, gate_ticks=280),
            _note(13, SNARE, velocity=114, gate_ticks=340),
            _note(13, CLAP, velocity=88, gate_ticks=280),
            _note(16, OPEN_HAT, velocity=96, gate_ticks=260),
        ]
        notes.extend(
            _note(step, HAT, velocity=72 + ((idx % 4) * 3), gate_ticks=180)
            for idx, step in enumerate((2, 4, 6, 8, 10, 12, 14))
        )
        return _sorted_notes(notes)
    if mode == "drive":
        notes = [
            _note(5, SNARE, velocity=112, gate_ticks=340),
            _note(5, CLAP, velocity=92, gate_ticks=280),
            _note(13, SNARE, velocity=116, gate_ticks=340),
            _note(13, CLAP, velocity=94, gate_ticks=280),
            _note(16, OPEN_HAT, velocity=104, gate_ticks=280),
        ]
        notes.extend(
            _note(step, HAT, velocity=76 + ((idx % 4) * 3), gate_ticks=180)
            for idx, step in enumerate((2, 4, 6, 8, 10, 12, 14, 15))
        )
        return _sorted_notes(notes)
    if mode == "crisp":
        return _sorted_notes(
            (
                _note(5, SNARE, velocity=104, gate_ticks=320),
                _note(13, SNARE, velocity=110, gate_ticks=320),
                _note(4, HAT, velocity=70, gate_ticks=160),
                _note(12, HAT, velocity=72, gate_ticks=160),
                _note(16, OPEN_HAT, velocity=88, gate_ticks=220),
            )
        )
    if mode == "break":
        return _sorted_notes(
            (
                _note(4, HAT, velocity=72, gate_ticks=160),
                _note(8, HAT, velocity=76, gate_ticks=160),
                _note(9, SNARE, velocity=110, gate_ticks=300),
                _note(12, HAT, velocity=74, gate_ticks=160),
                _note(15, HAT, velocity=82, gate_ticks=180),
                _note(16, OPEN_HAT, velocity=94, gate_ticks=240),
            )
        )
    raise ValueError(f"unknown hat mode: {mode}")


def _render_bass(chords: tuple[Chord, Chord, Chord, Chord], mode: str) -> list[dict[str, int]]:
    notes: list[dict[str, int]] = []
    if mode == "anchors":
        for idx, chord in enumerate(chords):
            step = 1 + idx * 4
            notes.append(_note(step, chord.root, velocity=104 - (idx % 2) * 4, gate_ticks=640))
        return notes
    if mode == "pulse":
        for idx, chord in enumerate(chords):
            step = 1 + idx * 4
            notes.append(_note(step, chord.root, velocity=104, gate_ticks=420))
            notes.append(_note(step + 2, chord.root + 12, velocity=92, gate_ticks=220))
        return _sorted_notes(notes)
    if mode == "walk":
        for idx, chord in enumerate(chords):
            step = 1 + idx * 4
            next_root = chords[(idx + 1) % 4].root
            notes.append(_note(step, chord.root, velocity=100, gate_ticks=360))
            guide = chord.root + 7 if next_root >= chord.root else chord.root + 3
            notes.append(_note(step + 2, guide, velocity=92, gate_ticks=220))
        return _sorted_notes(notes)
    if mode == "drive":
        for idx, chord in enumerate(chords):
            step = 1 + idx * 4
            notes.append(_note(step, chord.root, velocity=106, gate_ticks=260))
            notes.append(_note(step + 1, chord.root + 12, velocity=90, gate_ticks=180))
            notes.append(_note(step + 2, chord.root + 7, velocity=94, gate_ticks=180))
        return _sorted_notes(notes)
    raise ValueError(f"unknown bass mode: {mode}")


def _render_motif(
    chords: tuple[Chord, Chord, Chord, Chord],
    motif_name: str,
    *,
    high: bool,
) -> list[dict[str, int]]:
    motif = HIGH_MOTIFS[motif_name] if high else MID_MOTIFS[motif_name]
    notes = []
    for step, tone_index, octave_shift, velocity, gate_ticks in motif:
        chord = _chord_for_step(chords, step)
        notes.append(
            _note(
                step,
                _chord_note(chord, tone_index, octave_shift),
                velocity=velocity,
                gate_ticks=gate_ticks,
            )
        )
    return _sorted_notes(notes)


def _render_accents(chords: tuple[Chord, Chord, Chord, Chord], mode: str) -> list[dict[str, int]]:
    if mode == "none":
        return []
    if mode == "tail":
        chord = chords[-1]
        return [_note(16, _chord_note(chord, 2, 2), velocity=86, gate_ticks=240)]
    if mode == "midfill":
        return [
            _note(8, _chord_note(chords[1], 1, 2), velocity=80, gate_ticks=220),
            _note(16, _chord_note(chords[3], 2, 2), velocity=88, gate_ticks=260),
        ]
    if mode == "lift":
        return [
            _note(4, _chord_note(chords[0], 0, 2), velocity=78, gate_ticks=180),
            _note(8, _chord_note(chords[1], 1, 2), velocity=82, gate_ticks=180),
            _note(12, _chord_note(chords[2], 2, 2), velocity=86, gate_ticks=180),
            _note(16, _chord_note(chords[3], 3, 2), velocity=92, gate_ticks=220),
        ]
    raise ValueError(f"unknown accent mode: {mode}")


def _render_chord_voice(
    chords: tuple[Chord, Chord, Chord, Chord],
    mode: str,
    *,
    high: bool,
) -> list[dict[str, int]]:
    notes: list[dict[str, int]] = []
    if mode == "glow":
        low_picks = (0, 2, 1, 2)
        high_picks = (1, 3, 2, 3)
        for idx, chord in enumerate(chords):
            step = 1 + idx * 4
            tone_index = high_picks[idx] if high else low_picks[idx]
            octave_shift = 2 if high else 1
            notes.append(
                _note(
                    step,
                    _chord_note(chord, tone_index, octave_shift),
                    velocity=92 + idx * 2,
                    gate_ticks=360,
                )
            )
        return notes
    if mode == "lift":
        low_picks = (0, 1, 2, 3)
        high_picks = (2, 1, 3, 2)
        for idx, chord in enumerate(chords):
            step = 1 + idx * 4
            tone_index = high_picks[idx] if high else low_picks[idx]
            octave_shift = 2 if high else 1
            notes.append(
                _note(
                    step,
                    _chord_note(chord, tone_index, octave_shift),
                    velocity=94 + idx * 2,
                    gate_ticks=320,
                )
            )
        return notes
    if mode == "pulse":
        picks = (0, 2, 1, 2)
        high_picks = (1, 3, 2, 3)
        for idx, chord in enumerate(chords):
            base = 1 + idx * 4
            tone_index = high_picks[idx] if high else picks[idx]
            octave_shift = 2 if high else 1
            notes.append(
                _note(
                    base,
                    _chord_note(chord, tone_index, octave_shift),
                    velocity=92,
                    gate_ticks=220,
                )
            )
            notes.append(
                _note(
                    base + 2,
                    _chord_note(chord, tone_index + 1, octave_shift),
                    velocity=88,
                    gate_ticks=200,
                )
            )
        return _sorted_notes(notes)
    raise ValueError(f"unknown chord mode: {mode}")


def _render_track_pattern(track: int, plan: PatternPlan) -> list[dict[str, int]]:
    if track == 1:
        return _render_kick(plan.kick_mode)
    if track == 2:
        return _render_hat(plan.hat_mode)
    if track == 3:
        return _render_bass(plan.chords, plan.bass_mode)
    if track == 4:
        return _sorted_notes(_render_accents(plan.chords, plan.accent_mode))
    if track == 5:
        return _render_motif(plan.chords, plan.lead_mode, high=False)
    if track == 6:
        return _render_motif(plan.chords, plan.counter_mode, high=True)
    if track == 7:
        return _sorted_notes(_render_chord_voice(plan.chords, plan.chord_mode, high=False))
    if track == 8:
        return _sorted_notes(_render_chord_voice(plan.chords, plan.chord_mode, high=True))
    raise ValueError(f"unsupported showcase track: T{track}")


def _payload_for_piece(
    piece: ShowcasePiece,
    *,
    output_dir: Path,
) -> dict[str, object]:
    tracks = []
    for track in range(1, 9):
        patterns = [_render_track_pattern(track, plan) for plan in piece.patterns]
        tracks.append({"track": track, "patterns": patterns})

    return {
        "version": 1,
        "mode": "multi_pattern",
        "profile": "bootstrap_t1_t8_p9",
        "template": str(TEMPLATE),
        "output": str((output_dir / f"{piece.slug}.xy").resolve()),
        "descriptor_strategy": "strict",
        "topology_policy": "bootstrap_t1_t8_p9",
        "header": {
            "tempo_tenths": piece.tempo_tenths,
            "groove_type": 0,
            "groove_amount": piece.groove_amount,
        },
        "tracks": tracks,
        "composition_notes": {
            "title": piece.title,
            "style": piece.style,
            "summary": piece.summary,
            "suggested_pattern_order": [f"P{pattern_id}" for pattern_id in piece.suggested_pattern_order],
        },
    }


def build_showcase_payloads(*, output_dir: Path) -> list[tuple[ShowcasePiece, dict[str, object]]]:
    return [(piece, _payload_for_piece(piece, output_dir=output_dir)) for piece in _showcase_pieces()]


def _showcase_pieces() -> tuple[ShowcasePiece, ...]:
    return (
        ShowcasePiece(
            slug="01_neon_rain_runner",
            title="Neon Rain Runner",
            style="synthwave drive",
            summary="A synthwave drive that moves from cool cruise patterns into brighter payoff patterns.",
            tempo_tenths=1180,
            groove_amount=14,
            patterns=(
                PatternPlan((Chord(45, "m9"), Chord(41, "maj7"), Chord(36, "maj7"), Chord(43, "add9")), "steady", "backbeat", "anchors", "hook", "spark", "tail", "glow"),
                PatternPlan((Chord(45, "m7"), Chord(41, "maj7"), Chord(38, "m7"), Chord(43, "add9")), "broken", "shimmer", "pulse", "answer", "echo", "midfill", "pulse"),
                PatternPlan((Chord(36, "maj7"), Chord(43, "add9"), Chord(45, "m7"), Chord(41, "maj7")), "broken", "drive", "walk", "climb", "riser", "lift", "lift"),
                PatternPlan((Chord(45, "m9"), Chord(43, "add9"), Chord(41, "maj7"), Chord(43, "add9")), "drive", "drive", "drive", "hook", "riser", "lift", "pulse"),
                PatternPlan((Chord(45, "m7"), Chord(45, "m7"), Chord(41, "maj7"), Chord(40, "dom7")), "half", "crisp", "anchors", "pad", "sustain", "none", "glow"),
                PatternPlan((Chord(38, "m7"), Chord(41, "maj7"), Chord(36, "maj7"), Chord(43, "add9")), "steady", "backbeat", "walk", "answer", "echo", "tail", "glow"),
                PatternPlan((Chord(45, "m7"), Chord(43, "add9"), Chord(41, "maj7"), Chord(40, "dom7")), "fill", "break", "drive", "climb", "riser", "lift", "lift"),
                PatternPlan((Chord(45, "m9"), Chord(41, "maj7"), Chord(36, "maj7"), Chord(40, "dom7")), "pulse", "drive", "pulse", "hook", "spark", "lift", "pulse"),
                PatternPlan((Chord(45, "m7"), Chord(41, "maj7"), Chord(45, "m7"), Chord(40, "dom7")), "steady", "crisp", "anchors", "pad", "sustain", "tail", "glow"),
            ),
            suggested_pattern_order=(1, 2, 3, 1, 4, 5, 6, 7, 8, 9),
        ),
        ShowcasePiece(
            slug="02_dustlight_cascade",
            title="Dustlight Cascade",
            style="downtempo dusk pulse",
            summary="A slower dusk pulse that leans from haze into wider-open lift patterns.",
            tempo_tenths=980,
            groove_amount=22,
            patterns=(
                PatternPlan((Chord(38, "m7"), Chord(34, "maj7"), Chord(41, "add9"), Chord(36, "add9")), "steady", "backbeat", "anchors", "pad", "sustain", "tail", "glow"),
                PatternPlan((Chord(38, "m7"), Chord(36, "add9"), Chord(34, "maj7"), Chord(41, "add9")), "broken", "shimmer", "pulse", "answer", "echo", "midfill", "pulse"),
                PatternPlan((Chord(43, "m7"), Chord(34, "maj7"), Chord(36, "add9"), Chord(38, "m9")), "broken", "backbeat", "walk", "hook", "spark", "tail", "lift"),
                PatternPlan((Chord(41, "add9"), Chord(36, "add9"), Chord(38, "m9"), Chord(34, "maj7")), "pulse", "drive", "pulse", "climb", "riser", "lift", "pulse"),
                PatternPlan((Chord(38, "m7"), Chord(38, "m7"), Chord(34, "maj7"), Chord(45, "sus2")), "half", "crisp", "anchors", "pad", "sustain", "none", "glow"),
                PatternPlan((Chord(43, "m7"), Chord(36, "add9"), Chord(41, "add9"), Chord(41, "add9")), "steady", "shimmer", "walk", "answer", "echo", "tail", "glow"),
                PatternPlan((Chord(38, "m9"), Chord(34, "maj7"), Chord(43, "m7"), Chord(45, "sus2")), "fill", "break", "drive", "climb", "riser", "lift", "lift"),
                PatternPlan((Chord(41, "add9"), Chord(36, "add9"), Chord(34, "maj7"), Chord(38, "m9")), "pulse", "drive", "pulse", "hook", "spark", "lift", "pulse"),
                PatternPlan((Chord(38, "m7"), Chord(36, "add9"), Chord(38, "m7"), Chord(45, "sus2")), "steady", "crisp", "anchors", "pad", "sustain", "tail", "glow"),
            ),
            suggested_pattern_order=(5, 1, 2, 3, 5, 4, 6, 7, 8, 9),
        ),
        ShowcasePiece(
            slug="03_voltage_meridian",
            title="Voltage Meridian",
            style="electro chase",
            summary="A tighter electro chase that starts lean and escalates into denser payoff patterns.",
            tempo_tenths=1320,
            groove_amount=18,
            patterns=(
                PatternPlan((Chord(40, "m7"), Chord(36, "maj7"), Chord(43, "maj7"), Chord(38, "sus2")), "steady", "backbeat", "anchors", "hook", "spark", "tail", "glow"),
                PatternPlan((Chord(40, "m7"), Chord(38, "sus2"), Chord(36, "maj7"), Chord(47, "m7")), "broken", "drive", "pulse", "answer", "echo", "midfill", "pulse"),
                PatternPlan((Chord(43, "maj7"), Chord(38, "sus2"), Chord(40, "m7"), Chord(36, "maj7")), "drive", "drive", "walk", "climb", "riser", "lift", "lift"),
                PatternPlan((Chord(40, "m9"), Chord(36, "maj7"), Chord(38, "sus2"), Chord(47, "m7")), "drive", "drive", "drive", "hook", "riser", "lift", "pulse"),
                PatternPlan((Chord(40, "m7"), Chord(40, "m7"), Chord(36, "maj7"), Chord(38, "sus2")), "half", "crisp", "anchors", "pad", "sustain", "none", "glow"),
                PatternPlan((Chord(36, "maj7"), Chord(43, "maj7"), Chord(38, "sus2"), Chord(40, "m7")), "steady", "break", "walk", "answer", "echo", "tail", "glow"),
                PatternPlan((Chord(47, "m7"), Chord(38, "sus2"), Chord(40, "m7"), Chord(36, "maj7")), "fill", "break", "drive", "climb", "riser", "lift", "lift"),
                PatternPlan((Chord(40, "m9"), Chord(43, "maj7"), Chord(36, "maj7"), Chord(47, "m7")), "pulse", "drive", "pulse", "hook", "spark", "lift", "pulse"),
                PatternPlan((Chord(40, "m7"), Chord(38, "sus2"), Chord(40, "m7"), Chord(47, "m7")), "steady", "crisp", "anchors", "pad", "sustain", "tail", "glow"),
            ),
            suggested_pattern_order=(1, 2, 3, 4, 3, 5, 6, 7, 8, 9),
        ),
    )


def _sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _manifest_text(rows: list[dict[str, object]]) -> str:
    lines = [
        "# Music Showcase Pack",
        "",
        "Generated from the validated `unnamed 1` strict bootstrap path.",
        "These files avoid scene and Track16 song-order edits entirely.",
        "",
    ]
    for row in rows:
        pattern_order = " -> ".join(f"P{pattern}" for pattern in row["suggested_pattern_order"])
        lines.extend(
            [
                f"## {row['title']}",
                f"- File: `{row['file_name']}`",
                f"- Style: {row['style']}",
                f"- Tempo: {row['tempo_tenths'] / 10:.1f} BPM",
                f"- Patterns: {row['pattern_count']}",
                f"- Suggested Pattern Order: {pattern_order}",
                f"- Summary: {row['summary']}",
                "",
            ]
        )
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        nargs="*",
        metavar="SLUG",
        help="Only build the listed showcase pieces",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize without writing specs or .xy files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated .xy files",
    )
    parser.add_argument(
        "--spec-dir",
        type=Path,
        default=DEFAULT_SPEC_DIR,
        help="Directory for generated JSON specs",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path for generated showcase manifest",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    output_dir = args.output_dir.expanduser().resolve()
    spec_dir = args.spec_dir.expanduser().resolve()
    manifest_path = args.manifest.expanduser().resolve()

    wanted = set(args.only or [])
    payloads = build_showcase_payloads(output_dir=output_dir)
    if wanted:
        payloads = [(piece, payload) for piece, payload in payloads if piece.slug in wanted]
        missing = sorted(wanted - {piece.slug for piece, _ in payloads})
        if missing:
            raise ValueError(f"unknown showcase slug(s): {', '.join(missing)}")

    manifest_rows: list[dict[str, object]] = []
    for piece, payload in payloads:
        spec = parse_build_spec(payload, base_dir=REPO_ROOT)
        xy_bytes = build_xy_bytes(spec)

        xy_path = output_dir / f"{piece.slug}.xy"
        spec_path = spec_dir / f"{piece.slug}.json"
        if not args.dry_run:
            _write_json(spec_path, payload)
            xy_path.parent.mkdir(parents=True, exist_ok=True)
            xy_path.write_bytes(xy_bytes)

        manifest_rows.append(
            {
                "title": piece.title,
                "style": piece.style,
                "summary": piece.summary,
                "tempo_tenths": piece.tempo_tenths,
                "pattern_count": len(piece.patterns),
                "suggested_pattern_order": piece.suggested_pattern_order,
                "file_name": xy_path.name,
                "sha1": _sha1(xy_bytes),
                "size": len(xy_bytes),
            }
        )

        print(
            f"{piece.slug}: patterns={len(piece.patterns)} "
            f"suggested_order={len(piece.suggested_pattern_order)} "
            f"size={len(xy_bytes)} sha1={_sha1(xy_bytes)}"
        )

    if not args.dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(_manifest_text(manifest_rows), encoding="utf-8")
        print(f"manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
