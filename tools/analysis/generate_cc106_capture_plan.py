#!/usr/bin/env python3
"""Generate a detailed CC106-assisted device capture manifest.

This planner targets the "no encoder twist/click" workflow:
  - key/button automation via CC106/CC107 (+ optional Shift hold)
  - external MIDI note/CC/AT/PB injection
  - device-authored .xy exports for reverse-engineering deltas

It emits a deterministic manifest in CSV/JSON/Markdown with:
  - ordered filenames (sortable, device-friendly)
  - capture mode and generator source
  - what bytes/signals each file is expected to lay down
  - why each case helps decode unresolved format questions
  - MIDI command templates where applicable
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = ROOT / "output" / "cc106_capture_plan"
MIDI_SENTINEL_PACKS = {"B", "C", "D", "E"}


def _shell_join(parts: Sequence[str]) -> str:
    rendered: list[str] = []
    for part in parts:
        if part in {"$PORT", "$KEY_PORT"}:
            rendered.append(f'"{part}"')
        else:
            rendered.append(shlex.quote(part))
    return " ".join(rendered)


@dataclass(frozen=True)
class CaptureCase:
    pack: str
    pack_label: str
    ordinal: int
    filename: str
    subdir: str
    mode: str
    generator: str
    action: str
    info_laid_down: str
    reverse_engineering_value: str
    analysis_hint: str
    notes_spec: str = ""
    ccs_spec: str = ""
    aftertouch_spec: str = ""
    pitchbend_spec: str = ""
    bars: int = 1
    post_roll: int = 1

    @property
    def case_id(self) -> str:
        return f"{self.pack}{self.ordinal:02d}"

    @property
    def capture_relpath(self) -> str:
        return f"{self.subdir}/{self.filename}"

    def midi_command(self, port_var: str = "$PORT") -> str:
        """Return a runnable midi_harness command template when applicable."""
        if self.mode not in {"midi_experiment", "midi_custom", "manual_ui_plus_midi"}:
            return ""

        cmd: list[str] = ["python", "tools/midi_harness.py", "--port", port_var]

        if self.mode == "midi_experiment":
            if not self.generator.startswith("experiment:"):
                return ""
            exp = self.generator.split(":", 1)[1]
            cmd.extend(["--experiment", exp])
        else:
            if self.notes_spec:
                cmd.extend(["--notes", self.notes_spec])
            if self.ccs_spec:
                cmd.extend(["--ccs", self.ccs_spec])
            if self.aftertouch_spec:
                cmd.extend(["--aftertouch", self.aftertouch_spec])
            if self.pitchbend_spec:
                cmd.extend(["--pitchbend", self.pitchbend_spec])
            cmd.extend(["--bars", str(self.bars)])
            cmd.extend(["--post-roll", str(self.post_roll)])

        cmd.append("--no-countdown")
        return _shell_join(cmd)


def _join_specs(*specs: str) -> str:
    return " ".join(part for part in specs if part).strip()


def _render_custom_midi_command(
    notes_spec: str,
    ccs_spec: str,
    aftertouch_spec: str,
    pitchbend_spec: str,
    bars: int,
    post_roll: int,
    port_var: str = "$PORT",
) -> str:
    if not any([notes_spec, ccs_spec, aftertouch_spec, pitchbend_spec]):
        return ""

    cmd: list[str] = ["python", "tools/midi_harness.py", "--port", port_var]
    if notes_spec:
        cmd.extend(["--notes", notes_spec])
    if ccs_spec:
        cmd.extend(["--ccs", ccs_spec])
    if aftertouch_spec:
        cmd.extend(["--aftertouch", aftertouch_spec])
    if pitchbend_spec:
        cmd.extend(["--pitchbend", pitchbend_spec])
    cmd.extend(["--bars", str(bars)])
    cmd.extend(["--post-roll", str(post_roll)])
    cmd.append("--no-countdown")
    return _shell_join(cmd)


def _build_midi_sentinel_index(cases: Sequence[CaptureCase]) -> dict[str, int]:
    eligible = [
        case
        for case in cases
        if case.pack in MIDI_SENTINEL_PACKS
        and case.mode in {"midi_experiment", "midi_custom", "manual_ui_plus_midi"}
    ]
    return {case.case_id: idx for idx, case in enumerate(eligible, 1)}


def _selection_sentinel(case: CaptureCase) -> tuple[str, str, str]:
    if case.pack == "A":
        return (
            "intrinsic",
            "",
            "Action itself is the selection sentinel; no extra key presses.",
        )

    track = ((case.ordinal - 1) % 8) + 1
    pattern = ((case.ordinal - 1) // 8) % 4 + 1
    label = f"T{track}/P{pattern}"
    command = (
        f'python tools/cc106_keys.py --port "$KEY_PORT" tap instrument track{track} m{pattern} --hold 0.25'
    )
    signal = (
        f"Pre-track focus bytes should encode Track {track}, Pattern {pattern}."
    )
    return label, command, signal


def _midi_sentinel_notes_spec(
    case: CaptureCase, midi_sentinel_index: dict[str, int]
) -> str:
    idx_1based = midi_sentinel_index.get(case.case_id)
    if idx_1based is None:
        return ""

    idx0 = idx_1based - 1
    high_bits = idx0 >> 3          # 0..15
    low_bits = idx0 & 0x07         # 0..7
    # Two-note marker on Track 8. Notes avoid the note==velocity crash pitfall.
    note_a = 16 + high_bits        # 16..31
    note_b = 40 + low_bits         # 40..47
    return f"8:15:{note_a}:100:1 8:16:{note_b}:100:1"


def _sentinel_payload(
    case: CaptureCase, midi_sentinel_index: dict[str, int], port_var: str = "$PORT"
) -> dict[str, str]:
    selection_label, selection_cmd, selection_signal = _selection_sentinel(case)
    midi_primary = case.midi_command(port_var=port_var)
    midi_sentinel_notes = _midi_sentinel_notes_spec(case, midi_sentinel_index)
    midi_with_sentinel = midi_primary
    midi_sentinel_cmd = ""

    if midi_sentinel_notes:
        if case.mode in {"midi_custom", "manual_ui_plus_midi"}:
            midi_with_sentinel = _render_custom_midi_command(
                notes_spec=_join_specs(case.notes_spec, midi_sentinel_notes),
                ccs_spec=case.ccs_spec,
                aftertouch_spec=case.aftertouch_spec,
                pitchbend_spec=case.pitchbend_spec,
                bars=case.bars,
                post_roll=case.post_roll,
                port_var=port_var,
            )
        elif case.mode == "midi_experiment":
            midi_sentinel_cmd = _render_custom_midi_command(
                notes_spec=midi_sentinel_notes,
                ccs_spec="",
                aftertouch_spec="",
                pitchbend_spec="",
                bars=1,
                post_roll=0,
                port_var=port_var,
            )

    signals: list[str] = [selection_signal]
    if midi_sentinel_notes:
        signals.append(
            "Track 8 carries a 2-note marker at steps 15/16 encoding manifest index."
        )

    return {
        "sentinel_selection": selection_label,
        "sentinel_selection_command": selection_cmd,
        "sentinel_midi_notes_spec": midi_sentinel_notes,
        "sentinel_midi_command": midi_sentinel_cmd,
        "sentinel_expected_signal": " ".join(signals),
        "midi_primary_command": midi_primary,
        "midi_command": midi_with_sentinel,
    }


def _ramp_value(step_1based: int) -> int:
    return min(int(((step_1based - 1) / 15) * 127), 127)


def _cc_ramp_spec(channel_1based: int, cc: int) -> str:
    parts = []
    for step in range(1, 17):
        parts.append(f"{channel_1based}:{step}:{cc}:{_ramp_value(step)}")
    return " ".join(parts)


def _cc_toggle_spec(channel_1based: int, cc: int, period_steps: int = 4) -> str:
    parts = []
    for step in range(1, 17):
        val = 0 if ((step - 1) // period_steps) % 2 == 0 else 127
        parts.append(f"{channel_1based}:{step}:{cc}:{val}")
    return " ".join(parts)


def _cc_constant_spec(channel_1based: int, cc: int, value: int) -> str:
    parts = []
    for step in range(1, 17):
        parts.append(f"{channel_1based}:{step}:{cc}:{value}")
    return " ".join(parts)


def _note_spec(channel_1based: int, step: int, notes: Sequence[int], gate_steps: int, velocity: int = 100) -> str:
    return " ".join(
        f"{channel_1based}:{step}:{note}:{velocity}:{gate_steps}" for note in notes
    )


def _bars_for_step_and_gate(step_1based: int, gate_steps: int) -> int:
    return 2 if step_1based + gate_steps > 16 else 1


def _pack_a_selection() -> list[CaptureCase]:
    label = "Selection-State Fingerprints"
    cases_data = [
        (
            "01_u150_nullsave.xy",
            "Load unnamed150 branch seed and save immediately with no edits.",
            "Null-save serializer fingerprint in unnamed150 family.",
            "Anchors branch-normalization baseline for selection-only deltas.",
        ),
        (
            "02_u150_song2_select.xy",
            "From unnamed150 seed, select Song 2 and save.",
            "Song-selector lane mutation in pre-track control bytes.",
            "Separates active-song metadata from arrangement payload writes.",
        ),
        (
            "03_u150_song3_select.xy",
            "From unnamed150 seed, select Song 3 and save.",
            "Song-selector lane mutation for second target value.",
            "Confirms song-select encoding range and branch coupling behavior.",
        ),
        (
            "04_u150_t2p1_focus.xy",
            "From unnamed150 seed, focus Track 2 Pattern 1 and save.",
            "Track/pattern focus state serialized with no musical edits.",
            "Measures focus-only branch flips versus null-save output.",
        ),
        (
            "05_u150_t2p2_focus.xy",
            "From unnamed150 seed, focus Track 2 Pattern 2 and save.",
            "Pattern index focus lane in same seed family.",
            "Compares P1-focus vs P2-focus serialization outcomes.",
        ),
        (
            "06_u091_nullsave.xy",
            "Load unnamed91 seed and save immediately with no edits.",
            "Null-save fingerprint in hybrid/matrix scene family.",
            "Baseline for scene-selection deltas in matrix branch.",
        ),
        (
            "07_u091_scene1_select.xy",
            "From unnamed91 seed, select Scene 1 and save.",
            "Active-scene selector bytes and possible pre-track reshapes.",
            "Pins Scene 1 selector encoding in matrix family.",
        ),
        (
            "08_u091_scene2_select.xy",
            "From unnamed91 seed, select Scene 2 and save.",
            "Active-scene selector mutation for Scene 2.",
            "Distinguishes slot-index arithmetic from scene-map payload changes.",
        ),
        (
            "09_u091_scene3_select.xy",
            "From unnamed91 seed, select Scene 3 and save.",
            "Active-scene selector mutation for Scene 3.",
            "Completes contiguous selector triplet for matrix branch.",
        ),
        (
            "10_b35_nullsave.xy",
            "Load bleez35 seed and save immediately with no edits.",
            "Null-save fingerprint in bleez35 hybrid family.",
            "Baseline for R11/R13 lane-selection probes in same branch.",
        ),
        (
            "11_b35_scene1_select.xy",
            "From bleez35 seed, select Scene 1 and save.",
            "Scene-select metadata in bleez35 family.",
            "Checks whether bleez selector semantics match unnamed91 family.",
        ),
        (
            "12_b35_scene2_select.xy",
            "From bleez35 seed, select Scene 2 and save.",
            "Scene-select metadata for alternate slot.",
            "Confirms scene-slot arithmetic and pre-track rewrite coupling.",
        ),
        (
            "13_b35_scene3_select.xy",
            "From bleez35 seed, select Scene 3 and save.",
            "Scene-select metadata for current/default slot control.",
            "Null-action equivalence check against bleez null-save.",
        ),
        (
            "14_b35_t7p1_focus.xy",
            "From bleez35 seed, focus Track 7 Pattern 1 and save.",
            "Coupled lane update in matrix record region for T7 focus.",
            "Maps targeted focus to decoded scene-matrix lane movement.",
        ),
        (
            "15_b35_t7p2_focus.xy",
            "From bleez35 seed, focus Track 7 Pattern 2 and save.",
            "Second coupled lane update for T7 focus path.",
            "Differentiates P1 vs P2 focus encoding under same branch.",
        ),
    ]

    out: list[CaptureCase] = []
    for idx, (filename, action, laid_down, value) in enumerate(cases_data, 1):
        out.append(
            CaptureCase(
                pack="A",
                pack_label=label,
                ordinal=idx,
                filename=filename,
                subdir="a_selection",
                mode="manual_ui",
                generator="cc106_keys+manual-save",
                action=action,
                info_laid_down=laid_down,
                reverse_engineering_value=value,
                analysis_hint="python tools/analyze_scene_delta.py <seed.xy> <capture.xy> --decode",
            )
        )
    return out


def _pack_b_pointer_tail_t3() -> list[CaptureCase]:
    label = "Pointer-Tail Decode Matrix (Track 3)"
    out: list[CaptureCase] = []
    forms = [
        ("single", [60]),
        ("triad", [60, 64, 67]),
        ("dyad", [60, 67]),
    ]
    steps = [1, 5, 9, 13]
    gates = [1, 2, 4, 8]

    ordinal = 1
    for form_name, notes in forms:
        for step in steps:
            for gate in gates:
                bars = _bars_for_step_and_gate(step, gate)
                filename = f"{ordinal:02d}_t3_{form_name}_s{step:02d}_g{gate:02d}.xy"
                out.append(
                    CaptureCase(
                        pack="B",
                        pack_label=label,
                        ordinal=ordinal,
                        filename=filename,
                        subdir="b_ptrtail_t3",
                        mode="midi_custom",
                        generator="midi_harness:custom",
                        action=f"Arm Track 3 capture, send {form_name} at step {step} with gate {gate}, export file.",
                        info_laid_down=(
                            f"Track 3 pointer-tail/hybrid note payload with voice_count={len(notes)}, "
                            f"step={step}, gate={gate}."
                        ),
                        reverse_engineering_value=(
                            "Contributes controlled evidence for step_token and gate decoding in pointer-tail slabs."
                        ),
                        analysis_hint="python tools/inspect_xy.py <capture.xy>",
                        notes_spec=_note_spec(3, step, notes, gate),
                        bars=bars,
                        post_roll=1,
                    )
                )
                ordinal += 1
    return out


def _pack_c_pointer21_t4() -> list[CaptureCase]:
    label = "Pointer-21 Decode Matrix (Track 4)"
    out: list[CaptureCase] = []
    ordinal = 1

    # C01-C16: step/gate matrix, single-note.
    for step in [1, 5, 9, 13]:
        for gate in [1, 2, 4, 8]:
            bars = _bars_for_step_and_gate(step, gate)
            filename = f"{ordinal:02d}_t4_single_s{step:02d}_g{gate:02d}.xy"
            out.append(
                CaptureCase(
                    pack="C",
                    pack_label=label,
                    ordinal=ordinal,
                    filename=filename,
                    subdir="c_ptr21_t4",
                    mode="midi_custom",
                    generator="midi_harness:custom",
                    action=f"Arm Track 4 capture, send single note at step {step}, gate {gate}, export file.",
                    info_laid_down=f"Pointer-21 candidate event on T4 with step={step}, gate={gate}.",
                    reverse_engineering_value="Isolates pointer-21 step/gate control words under fixed engine context.",
                    analysis_hint="python tools/inspect_xy.py <capture.xy>",
                    notes_spec=_note_spec(4, step, [60], gate),
                    bars=bars,
                    post_roll=1,
                )
            )
            ordinal += 1

    # C17-C21: pitch-range sweep.
    for note in [0, 24, 60, 96, 124]:
        filename = f"{ordinal:02d}_t4_note{note:03d}.xy"
        out.append(
            CaptureCase(
                pack="C",
                pack_label=label,
                ordinal=ordinal,
                filename=filename,
                subdir="c_ptr21_t4",
                mode="midi_custom",
                generator="midi_harness:custom",
                action=f"Arm Track 4 capture, send single note {note} at step 1 gate 2, export file.",
                info_laid_down=f"Pointer-21 candidate with extreme note={note}.",
                reverse_engineering_value="Disambiguates note-word placement vs control words in pointer-21 slabs.",
                analysis_hint="python tools/inspect_xy.py <capture.xy>",
                notes_spec=_note_spec(4, 1, [note], 2),
                bars=1,
                post_roll=1,
            )
        )
        ordinal += 1

    # C22-C32: chord variants.
    chord_variants = [
        ("a_s01_dyad", "4:1:60:100:2 4:1:67:100:2"),
        ("b_s01_triad", "4:1:60:100:2 4:1:64:100:2 4:1:67:100:2"),
        ("c_s05_dyad", "4:5:62:100:2 4:5:69:100:2"),
        ("d_s05_triad", "4:5:62:100:2 4:5:65:100:2 4:5:69:100:2"),
        ("e_s09_dyad", "4:9:64:100:2 4:9:71:100:2"),
        ("f_s09_triad", "4:9:64:100:2 4:9:67:100:2 4:9:71:100:2"),
        ("g_s13_dyad", "4:13:65:100:2 4:13:72:100:2"),
        ("h_s13_triad", "4:13:65:100:2 4:13:69:100:2 4:13:72:100:2"),
        ("i_s01_plus_s09", "4:1:60:100:2 4:1:67:100:2 4:9:64:100:2"),
        ("j_s05_plus_s13", "4:5:62:100:2 4:5:65:100:2 4:13:72:100:2"),
        ("k_dense_multi", "4:1:60:100:2 4:1:64:100:2 4:5:67:100:2 4:9:71:100:2"),
    ]
    for suffix, notes_spec in chord_variants:
        filename = f"{ordinal:02d}_t4_chord_{suffix}.xy"
        out.append(
            CaptureCase(
                pack="C",
                pack_label=label,
                ordinal=ordinal,
                filename=filename,
                subdir="c_ptr21_t4",
                mode="midi_custom",
                generator="midi_harness:custom",
                action="Arm Track 4 capture, send predefined chord variant phrase, export file.",
                info_laid_down="Pointer-21 multi-voice slabs with controlled simultaneous-note structure.",
                reverse_engineering_value="Separates pointer-21 voice allocation records from timing metadata.",
                analysis_hint="python tools/inspect_xy.py <capture.xy>",
                notes_spec=notes_spec,
                bars=1,
                post_roll=1,
            )
        )
        ordinal += 1

    return out


def _pack_d_plock_cc() -> list[CaptureCase]:
    label = "CC/P-Lock Closure and Aux Mapping"
    out: list[CaptureCase] = []
    exp_cases = [
        ("01_cc_map_1a.xy", "cc_map_1a"),
        ("02_cc_map_1b.xy", "cc_map_1b"),
        ("03_cc_map_1c.xy", "cc_map_1c"),
        ("04_cc_map_1d.xy", "cc_map_1d"),
        ("05_cc_map_2a.xy", "cc_map_2a"),
        ("06_cc_map_2b_fix.xy", "cc_map_2b"),
        ("07_cc_map_2c_fix.xy", "cc_map_2c"),
        ("08_cc_map_2d_fix.xy", "cc_map_2d"),
        ("09_cc_map_multi.xy", "cc_map_multi"),
    ]
    ordinal = 1
    for filename, exp in exp_cases:
        out.append(
            CaptureCase(
                pack="D",
                pack_label=label,
                ordinal=ordinal,
                filename=filename,
                subdir="d_cc_plock",
                mode="midi_experiment",
                generator=f"experiment:{exp}",
                action=f"Run built-in midi_harness experiment `{exp}` in hold-record workflow, export file.",
                info_laid_down="P-lock lane payloads and param_id mappings for configured CC sweep.",
                reverse_engineering_value="Extends/validates per-track param_id map and entry-format families.",
                analysis_hint="python tools/extract_plocks.py <capture.xy>",
            )
        )
        ordinal += 1

    custom_cases = [
        (
            "10_t4_cc9_toggle.xy",
            _cc_toggle_spec(4, 9),
            "Toggle CC9 mute pattern on T4 to test mute lock encoding.",
        ),
        (
            "11_t4_cc9_hold127.xy",
            _cc_constant_spec(4, 9, 127),
            "Sustained CC9=127 on T4 to test binary latch behavior.",
        ),
        (
            "12_t3_cc32_holdrecord.xy",
            _cc_ramp_spec(3, 32),
            "CC32 cutoff ramp on T3 with no notes (pure hold-record path).",
        ),
    ]
    for filename, ccs, laid_down in custom_cases:
        out.append(
            CaptureCase(
                pack="D",
                pack_label=label,
                ordinal=ordinal,
                filename=filename,
                subdir="d_cc_plock",
                mode="midi_custom",
                generator="midi_harness:custom",
                action="Hold record on device, send CC-only phrase, export file.",
                info_laid_down=laid_down,
                reverse_engineering_value="Clarifies CC-only capture gate and non-linear mute/lock storage semantics.",
                analysis_hint="python tools/extract_plocks.py <capture.xy>",
                ccs_spec=ccs,
                bars=1,
                post_roll=1,
            )
        )
        ordinal += 1

    out.append(
        CaptureCase(
            pack="D",
            pack_label=label,
            ordinal=ordinal,
            filename="13_t3_cc32_with_notes.xy",
            subdir="d_cc_plock",
            mode="midi_experiment",
            generator="experiment:cc_cutoff_steps",
            action="Run cc_cutoff_steps to contrast CC+note behavior vs hold-record CC-only.",
            info_laid_down="Mixed note+CC capture path on T3.",
            reverse_engineering_value="Isolates suppression/branch differences between CC-only and note+CC recording.",
            analysis_hint="python tools/extract_plocks.py <capture.xy>",
        )
    )
    ordinal += 1

    tail_cases = [
        ("14_t10_cc10_pan.xy", _cc_ramp_spec(10, 10), "T10 pan ramp (9-byte entry-family cross-check)."),
        ("15_t10_cc12_param.xy", _cc_ramp_spec(10, 12), "T10 CC12 ramp for aux param-id domain."),
        ("16_t10_cc40_lfo.xy", _cc_ramp_spec(10, 40), "T10 LFO lane ramp for aux modulation slots."),
        ("17_t13_send_tape.xy", _cc_ramp_spec(13, 37), "T13 send-to-tape CC ramp."),
        ("18_t13_send_fxi.xy", _cc_ramp_spec(13, 38), "T13 send-to-FX1 CC ramp."),
        ("19_t14_send_fxi.xy", _cc_ramp_spec(14, 38), "T14 send-to-FX1 CC ramp."),
        ("20_t15_send_fxii.xy", _cc_ramp_spec(15, 39), "T15 send-to-FX2 CC ramp."),
    ]
    for filename, ccs, laid_down in tail_cases:
        out.append(
            CaptureCase(
                pack="D",
                pack_label=label,
                ordinal=ordinal,
                filename=filename,
                subdir="d_cc_plock",
                mode="midi_custom",
                generator="midi_harness:custom",
                action="Hold record on device, send CC-only ramp, export file.",
                info_laid_down=laid_down,
                reverse_engineering_value="Fills remaining aux/send parameter slots and table layout gaps.",
                analysis_hint="python tools/extract_plocks.py <capture.xy>",
                ccs_spec=ccs,
                bars=1,
                post_roll=1,
            )
        )
        ordinal += 1

    return out


def _pack_e_performance() -> list[CaptureCase]:
    label = "Performance Automation Slab Decode"
    experiments = [
        "pb_control",
        "pitchbend_steps",
        "pitchbend_sweep",
        "modwheel_steps",
        "modwheel_sweep",
        "aftertouch_steps",
        "aftertouch_sweep",
        "perf_all_sweep",
        "cc_with_pb_cutoff",
        "cc_with_pb_param1",
        "cc_with_at_cutoff",
        "velocity_levels",
    ]

    out: list[CaptureCase] = []
    for idx, exp in enumerate(experiments, 1):
        out.append(
            CaptureCase(
                pack="E",
                pack_label=label,
                ordinal=idx,
                filename=f"{idx:02d}_{exp}.xy",
                subdir="e_perf_mod",
                mode="midi_experiment",
                generator=f"experiment:{exp}",
                action=f"Run midi_harness experiment `{exp}`, export file.",
                info_laid_down="Performance-controller or mixed-controller automation lane bytes.",
                reverse_engineering_value="Improves decode coverage for mod routing slab and controller dispatch paths.",
                analysis_hint="python tools/inspect_xy.py <capture.xy>",
            )
        )
    return out


def _pack_f_scene_song() -> list[CaptureCase]:
    label = "Scene/Song Record Semantics"
    cases_data = [
        ("01_s2_t3p3.xy", "Set Scene2 Track3->Pattern3 and save."),
        ("02_s1_t3p2.xy", "Set Scene1 Track3->Pattern2 and save."),
        ("03_s1_t3p2_t4p2.xy", "From prior file, add Scene1 Track4->Pattern2 and save."),
        ("04_s2_mute_t4.xy", "Mute Track4 in Scene2 and save."),
        ("05_song2_add_s4.xy", "In Song2 arrangement, add Scene4 and save."),
        ("06_s4_t4p3.xy", "Set Scene4 Track4->Pattern3 and save."),
        ("07_song2_remove_s3.xy", "In Song2 arrangement, remove Scene3 and save."),
        ("08_s3_t4p2.xy", "Set Scene3 Track4->Pattern2 and save."),
        ("09_s3_t4p1.xy", "Set Scene3 Track4->Pattern1 and save."),
        ("10_s2_t3p1.xy", "Set Scene2 Track3->Pattern1 and save."),
        ("11_s2_t4p3.xy", "Set Scene2 Track4->Pattern3 and save."),
        ("12_s2_t4p2.xy", "Set Scene2 Track4->Pattern2 and save."),
        ("13_scene5_copy_s2.xy", "Create Scene5 by copying Scene2 and save."),
        ("14_scene5_t3p2.xy", "Set Scene5 Track3->Pattern2 and save."),
        ("15_scene5_t4p3.xy", "Set Scene5 Track4->Pattern3 and save."),
    ]
    out: list[CaptureCase] = []
    for idx, (filename, action) in enumerate(cases_data, 1):
        out.append(
            CaptureCase(
                pack="F",
                pack_label=label,
                ordinal=idx,
                filename=filename,
                subdir="f_scene_song",
                mode="manual_ui",
                generator="cc106_keys+arranger-manual-save",
                action=action,
                info_laid_down="Scene-record and/or Track16 scene-list mutations under controlled UI edits.",
                reverse_engineering_value="Refines scene field/tag/pattern encoding and add/remove semantics.",
                analysis_hint="python tools/analyze_scene_delta.py <seed.xy> <capture.xy> --decode",
            )
        )
    return out


def _pack_g_topology() -> list[CaptureCase]:
    label = "Topology/Descriptor/Preamble State Machine"
    out: list[CaptureCase] = []
    cases_data = [
        ("01_t1_p2_note.xy", "T1 x2 topology + note capture", "1:1:60:100:1"),
        ("02_t2_p2_note.xy", "T2 x2 topology + note capture", "2:1:60:100:1"),
        ("03_t3_p2_note.xy", "T3 x2 topology + note capture", "3:1:60:100:1"),
        ("04_t4_p2_note.xy", "T4 x2 topology + note capture", "4:1:60:100:1"),
        ("05_t5_p2_note.xy", "T5 x2 topology + note capture", "5:1:60:100:1"),
        ("06_t6_p2_note.xy", "T6 x2 topology + note capture", "6:1:60:100:1"),
        ("07_t7_p2_note.xy", "T7 x2 topology + note capture", "7:1:60:100:1"),
        ("08_t8_p2_note.xy", "T8 x2 topology + note capture", "8:1:60:100:1"),
        ("09_t1t3_p2_note.xy", "T1+T3 x2 topology + dual-track note capture", "1:1:60:100:1 3:1:60:100:1"),
        ("10_t1t3_p3_note.xy", "T1+T3 x3 topology + dual-track note capture", "1:1:60:100:1 3:1:60:100:1"),
        ("11_t1t3_p4_note.xy", "T1+T3 x4 topology + dual-track note capture", "1:1:60:100:1 3:1:60:100:1"),
        ("12_t1t4_p2_note.xy", "T1+T4 x2 topology + dual-track note capture", "1:1:60:100:1 4:1:60:100:1"),
        ("13_t2t3_p2_note.xy", "T2+T3 x2 topology + dual-track note capture", "2:1:60:100:1 3:1:60:100:1"),
        ("14_t3t7_p2_note.xy", "T3+T7 x2 topology + dual-track note capture", "3:1:60:100:1 7:1:60:100:1"),
        ("15_t1t2_p2_note.xy", "T1+T2 x2 topology + dual-track note capture", "1:1:60:100:1 2:1:60:100:1"),
        ("16_t1t2t3_p2_note.xy", "T1+T2+T3 x2 topology + three-track note capture", "1:1:60:100:1 2:1:60:100:1 3:1:60:100:1"),
        ("17_all8_p9_blank.xy", "All tracks T1..T8 x9 blank topology capture", ""),
        ("18_all8_p9_notesweep.xy", "All tracks T1..T8 x9 round-note sweep capture", ""),
        ("19_all8_p9_sparse_notes.xy", "All tracks x9 topology with sparse note placement", ""),
        ("20_all8_p9_dense_notes.xy", "All tracks x9 topology with dense note placement", ""),
    ]

    for idx, (filename, action, notes_spec) in enumerate(cases_data, 1):
        if idx <= 16:
            mode = "manual_ui_plus_midi"
            generator = "manual-topology+custom-midi"
        elif filename == "18_all8_p9_notesweep.xy":
            mode = "manual_ui"
            generator = "capture_9pat"
        else:
            mode = "manual_ui"
            generator = "manual-topology-save"

        out.append(
            CaptureCase(
                pack="G",
                pack_label=label,
                ordinal=idx,
                filename=filename,
                subdir="g_topology",
                mode=mode,
                generator=generator,
                action=(
                    f"Set target topology branch on device (no knobs), then {action.lower()}."
                    if idx <= 16
                    else action
                ),
                info_laid_down="Descriptor/preamble branch bytes tied to explicit topology state.",
                reverse_engineering_value="Tightens deterministic descriptor and preamble state-machine modeling.",
                analysis_hint="python tools/hypothesis_tests.py h2-automaton && python tools/hypothesis_tests.py h7-compositional",
                notes_spec=notes_spec,
                bars=1,
                post_roll=1,
            )
        )

    return out


def _build_full_manifest() -> list[CaptureCase]:
    out: list[CaptureCase] = []
    out.extend(_pack_a_selection())
    out.extend(_pack_b_pointer_tail_t3())
    out.extend(_pack_c_pointer21_t4())
    out.extend(_pack_d_plock_cc())
    out.extend(_pack_e_performance())
    out.extend(_pack_f_scene_song())
    out.extend(_pack_g_topology())
    return out


def _filter_profile(cases: Sequence[CaptureCase], profile: str) -> list[CaptureCase]:
    profile = profile.lower()
    if profile == "full":
        return list(cases)
    if profile == "starter":
        keep = {"A", "D", "E"}
        return [c for c in cases if c.pack in keep]
    raise ValueError(f"unknown profile: {profile}")


def _to_row(case: CaptureCase, midi_sentinel_index: dict[str, int]) -> dict[str, object]:
    base = asdict(case)
    base["case_id"] = case.case_id
    base["capture_relpath"] = case.capture_relpath
    base.update(_sentinel_payload(case, midi_sentinel_index))
    return base


def _write_csv(rows: Sequence[dict[str, object]], path: Path) -> None:
    if not rows:
        return
    fieldnames = [
        "case_id",
        "pack",
        "pack_label",
        "ordinal",
        "subdir",
        "filename",
        "capture_relpath",
        "mode",
        "generator",
        "action",
        "info_laid_down",
        "reverse_engineering_value",
        "analysis_hint",
        "sentinel_selection",
        "sentinel_selection_command",
        "sentinel_midi_notes_spec",
        "sentinel_midi_command",
        "sentinel_expected_signal",
        "midi_primary_command",
        "midi_command",
        "notes_spec",
        "ccs_spec",
        "aftertouch_spec",
        "pitchbend_spec",
        "bars",
        "post_roll",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(rows: Sequence[dict[str, object]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(list(rows), handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def _pack_counts(cases: Iterable[CaptureCase]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        counts[case.pack] = counts.get(case.pack, 0) + 1
    return counts


def _write_markdown(
    cases: Sequence[CaptureCase],
    path: Path,
    profile: str,
    midi_sentinel_index: dict[str, int],
) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    counts = _pack_counts(cases)
    total = len(cases)

    lines: list[str] = []
    lines.append("# CC106 Capture Plan Manifest")
    lines.append("")
    lines.append(f"- Generated (UTC): `{now}`")
    lines.append(f"- Profile: `{profile}`")
    lines.append(f"- Total cases: `{total}`")
    lines.append("")
    lines.append("## Pack Summary")
    lines.append("")
    lines.append("| Pack | Label | Cases |")
    lines.append("|---|---|---:|")
    labels: dict[str, str] = {}
    for case in cases:
        labels[case.pack] = case.pack_label
    for pack in sorted(counts):
        lines.append(f"| {pack} | {labels[pack]} | {counts[pack]} |")
    lines.append("")
    lines.append("## Detailed Cases")
    lines.append("")

    current_pack = ""
    for case in cases:
        if case.pack != current_pack:
            current_pack = case.pack
            lines.append(f"### Pack {case.pack}: {case.pack_label}")
            lines.append("")
            lines.append(
                "| ID | File | Mode | Generator | Action | Information Laid Down | Why It Helps | Sentinels | Commands |"
            )
            lines.append("|---|---|---|---|---|---|---|---|---|")
        sentinel = _sentinel_payload(case, midi_sentinel_index)
        midi_cmd = sentinel["midi_command"].replace("|", "\\|")
        sentinel_midi_cmd = sentinel["sentinel_midi_command"].replace("|", "\\|")
        sentinel_keys_cmd = sentinel["sentinel_selection_command"].replace("|", "\\|")
        action = case.action.replace("|", "\\|")
        laid = case.info_laid_down.replace("|", "\\|")
        why = case.reverse_engineering_value.replace("|", "\\|")
        sentinel_text_parts = [f"`{sentinel['sentinel_selection']}`"]
        if sentinel["sentinel_midi_notes_spec"]:
            sentinel_text_parts.append(f"`{sentinel['sentinel_midi_notes_spec']}`")
        sentinel_text = "<br>".join(sentinel_text_parts).replace("|", "\\|")

        command_parts = []
        if midi_cmd:
            command_parts.append(f"midi: `{midi_cmd}`")
        if sentinel_midi_cmd:
            command_parts.append(f"sentinel-midi: `{sentinel_midi_cmd}`")
        if sentinel_keys_cmd:
            command_parts.append(f"sentinel-keys: `{sentinel_keys_cmd}`")
        commands = "<br>".join(command_parts).replace("|", "\\|")

        lines.append(
            f"| {case.case_id} | `{case.capture_relpath}` | `{case.mode}` | `{case.generator}` | {action} | {laid} | {why} | {sentinel_text} | {commands} |"
        )
    lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validate_counts(cases: Sequence[CaptureCase], profile: str) -> None:
    if profile == "full" and len(cases) != 162:
        raise RuntimeError(f"expected 162 cases in full profile, found {len(cases)}")
    if profile == "starter" and len(cases) != 47:
        raise RuntimeError(f"expected 47 cases in starter profile, found {len(cases)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate detailed CC106-assisted capture manifest for OP-XY reverse engineering."
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--profile",
        choices=["full", "starter"],
        default="full",
        help="Manifest profile: full=all packs, starter=A+D+E only.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    full_cases = _build_full_manifest()
    midi_sentinel_index = _build_midi_sentinel_index(full_cases)
    cases = _filter_profile(full_cases, args.profile)
    _validate_counts(cases, args.profile)
    rows = [_to_row(case, midi_sentinel_index) for case in cases]

    csv_path = out_dir / "manifest.csv"
    json_path = out_dir / "manifest.json"
    md_path = out_dir / "manifest.md"

    _write_csv(rows, csv_path)
    _write_json(rows, json_path)
    _write_markdown(cases, md_path, args.profile, midi_sentinel_index)

    counts = _pack_counts(cases)
    print(f"Wrote {len(cases)} cases to {out_dir}")
    print(f"- {csv_path}")
    print(f"- {json_path}")
    print(f"- {md_path}")
    print("Pack counts:")
    for pack in sorted(counts):
        print(f"  {pack}: {counts[pack]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
