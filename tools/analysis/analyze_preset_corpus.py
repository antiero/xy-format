"""Analyze paired `.preset` folders and device-authored project captures.

The corpus under ``src/presets`` pairs ``presets/<name>.preset/patch.json``
with ``presetprojs/<name>.xy`` where track 1 was assigned that preset on the
device.  This script checks which ``patch.json`` fields can be found back in
the decoded project image.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xy.image_writer import ImageProject

DEFAULT_CORPUS = ROOT / "src" / "presets"

ENGINE_IDS = {
    "sampler": 0x02,
    "drum": 0x03,
    "organ": 0x06,
    "epiano": 0x07,
    "prism": 0x12,
    "hardsync": 0x13,
    "dissolve": 0x14,
    "axis": 0x16,
    "wavetable": 0x1F,
    "simple": 0x20,
}

Q16_FIELDS = {
    "envelope.amp.attack": 0x3877,
    "envelope.amp.decay": 0x387B,
    "envelope.amp.sustain": 0x387F,
    "envelope.amp.release": 0x3883,
    "engine.portamento.amount": 0x388B,
    "engine.bendrange": 0x388F,
    "engine.volume": 0x3893,
    "envelope.filter.attack": 0x38D7,
    "envelope.filter.decay": 0x38DB,
    "envelope.filter.sustain": 0x38DF,
    "envelope.filter.release": 0x38E3,
    "engine.modulation.modwheel.target": 0x38FF,
    "engine.modulation.modwheel.amount": 0x3903,
    "engine.modulation.aftertouch.target": 0x3907,
    "engine.modulation.aftertouch.amount": 0x390B,
    "engine.modulation.pitchbend.target": 0x390F,
    "engine.modulation.pitchbend.amount": 0x3913,
    "engine.velocity.sensitivity": 0x3917,
    "engine.portamento.type": 0x391B,
    "engine.tuning.scale": 0x391F,
    "engine.width": 0x3923,
    "engine.tuning.root": 0x392B,
    "engine.highpass": 0x392F,
    "engine.modulation.velocity.target": 0x3933,
    "engine.modulation.velocity.amount": 0x3937,
}

ENGINE_PARAM_OFFSETS = [0x3857, 0x385B, 0x385F, 0x3863, 0x3867, 0x386B, 0x386F, 0x3873]
FX_PARAM_OFFSETS = [0x3897, 0x389B, 0x389F, 0x38A3, 0x38A7, 0x38AB, 0x38AF, 0x38B3]
LFO_PARAM_OFFSETS = [0x38B7, 0x38BB, 0x38BF, 0x38C3, 0x38C7, 0x38CB, 0x38CF, 0x38D3]

SAMPLER_U32_FIELDS = {
    "regions.0.framecount": 0x393F,
    "regions.0.sample.start": 0x3943,
    "regions.0.sample.end": 0x3947,
    "regions.0.loop.start": 0x394B,
    "regions.0.loop.end": 0x394F,
}

PRESET_LABEL_OFFSET = 0x453F
PRESET_LABEL_MAX = 0x30
SAMPLER_SAMPLE_PATH_OFFSET = 0x395F
SAMPLER_SAMPLE_PATH_MAX = 0x60
SAMPLER_SLOT_ROOT_KEY_OFFSET = 0x3957
SAMPLER_SLOT_GAIN_OFFSET = 0x395C
SAMPLER_SLOT_DIRECTION_OFFSET = 0x395E
TRACK1_OCTAVE_OFFSET = 0x003D

PLAYMODE_WORDS = {
    "poly": 0x15555555,
    "mono": 0x3FFFFFFF,
}

LFO_TYPE_BYTES = {
    "tremolo": 0x00,
    "value": 0x01,
    "random": 0x02,
    "element": 0x03,
}

FX_TYPE_BYTES = {
    "z lowpass": 0x09,
    "svf": 0x0A,
    "ladder": 0x10,
    "z hipass": 0x11,
}

FIELD_COVERAGE = [
    ("platform", "metadata", "Preset file marker; not expected to be stored as track sound state."),
    ("version", "metadata", "Preset schema version; not expected to be stored as track sound state."),
    ("type", "confirmed", "Engine byte at `track+0x14`."),
    ("octave", "confirmed-for-track-1", "Signed byte at decoded-image `0x003D` for T1 in this corpus. Manual testing confirms octave is track-global, not pattern-local; T2-T16 table offsets still need a multi-track fixture."),
    ("engine.params[0..7]", "confirmed", "q16 words at `track+0x3857..0x3873`."),
    ("engine.playmode", "confirmed", "Raw word at `track+0x3887`: `poly=0x15555555`, `mono=0x3FFFFFFF`."),
    ("engine.portamento.amount", "confirmed", "q16 word at `track+0x388B`."),
    ("engine.bendrange", "confirmed", "q16 word at `track+0x388F`."),
    ("engine.volume", "confirmed", "q16 word at `track+0x3893`."),
    ("engine.tuning.scale", "confirmed", "q16 word at `track+0x391F`."),
    ("engine.width", "confirmed", "q16 word at `track+0x3923`."),
    ("engine.transpose", "candidate", "Raw word at `track+0x3927`; observed `0 -> 0x3FFFFFF8`, `12 -> 0x550A8538`. Encoding not generalized."),
    ("engine.tuning.root", "confirmed", "q16 word at `track+0x392B`."),
    ("engine.highpass", "confirmed", "q16 word at `track+0x392F`."),
    ("engine.velocity.sensitivity", "confirmed", "q16 word at `track+0x3917`."),
    ("engine.portamento.type", "confirmed", "q16 word at `track+0x391B`."),
    ("engine.modulation.*.target/amount", "confirmed", "q16 words at `track+0x38FF..0x3937`."),
    ("engine.tuning[]", "unresolved", "Observed on some organ/epiano/drum/wavetable presets. The paired captures all use the same 12-value table, and no direct float/int/q16 byte table has been found yet."),
    ("envelope.amp.*", "confirmed", "q16 words at `track+0x3877..0x3883`."),
    ("envelope.filter.*", "confirmed", "q16 words at `track+0x38D7..0x38E3`."),
    ("fx.type", "confirmed", "Byte at `track+0x21`: `z lowpass=9`, `svf=10`, `ladder=16`, `z hipass=17`."),
    ("fx.active", "confirmed", "Boolean byte at `track+0x25`."),
    ("fx.params[0..7]", "confirmed-with-exception", "q16 words at `track+0x3897..0x38B3`; `params[5]` serializes as max for ten paired synth-engine captures with JSON `21954`."),
    ("lfo.type", "confirmed", "Byte at `track+0x1C`: `tremolo=0`, `value=1`, `random=2`, `element=3`."),
    ("lfo.active", "confirmed", "Boolean byte at `track+0x20`."),
    ("lfo.params[0..7]", "confirmed", "q16 words at `track+0x38B7..0x38D3`."),
    ("regions[0].sample (sampler)", "confirmed", "C string at `track+0x395F`: `/fat32/presets/1/<preset>.preset/<sample>`."),
    ("regions[0].hikey/pitch.keycenter (sampler)", "confirmed", "Root/keycenter byte at `track+0x3957`; these match each other in the current corpus."),
    ("regions[0].framecount/sample.end/loop.start/loop.end (sampler)", "confirmed", "u32 words at `track+0x393F/0x3947/0x394B/0x394F`."),
    ("regions[0].sample.start (sampler)", "partial", "u32 word at `track+0x3943` when present; absence in JSON means no expectation."),
    ("regions[0].loop.crossfade (sampler)", "confirmed", "Byte at `track+0x3956` is `floor(loop.crossfade * 128 / framecount)`."),
    ("regions[0].reverse/gain (sampler)", "confirmed-for-observed-values", "`reverse=false` maps to `track+0x395E == 0`; observed `gain` values map directly to byte `track+0x395C`."),
    ("regions[0].loop.onrelease/tune (sampler)", "unresolved", "`loop.onrelease=true` does not map to the current loop-type byte assumption in this corpus. `tune` is always zero, while slot `+0x00` is keycenter/root."),
    ("regions[].sample/hikey/reverse/pan/transpose/tune/playmode (drum)", "partial", "Ten clean 24-region kits align with `track+0x3957 + (hikey - 53) * 0x80`; current paired captures only show `oneshot` as byte `1`."),
    ("regions[].sample.end/framecount/fade.* (drum)", "candidate", "Ten clean 24-region kits store `sample.end`/`framecount` for voices 1-23 at the previous slot's `+0x70`. Voice 0 and suspect kit alignments remain unresolved."),
    ("regions[].lokey/pitch.keycenter", "ignored-or-unresolved", "Often redundant with `hikey`/default keycenter, but no independent project field is confirmed."),
]


@dataclass(frozen=True)
class Pair:
    name: str
    preset_dir: Path
    project_path: Path
    patch: dict[str, Any]
    project: ImageProject
    track_start: int


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = parser.parse_args()
    print(analyze(args.corpus))


def analyze(corpus: Path) -> str:
    preset_dirs = {path.name.removesuffix(".preset"): path for path in (corpus / "presets").glob("*.preset")}
    project_paths = {path.stem: path for path in (corpus / "presetprojs").glob("*.xy")}
    pair_names = sorted(set(preset_dirs) & set(project_paths))
    pairs = [_load_pair(name, preset_dirs[name], project_paths[name]) for name in pair_names]

    type_counts = Counter(pair.patch.get("type", "<missing>") for pair in pairs)
    all_type_counts = Counter(
        _read_patch(path / "patch.json").get("type", "<missing>")
        for path in preset_dirs.values()
        if (path / "patch.json").exists()
    )

    sections = [
        "# Preset Corpus Analysis",
        "",
        f"Corpus: `{corpus.as_posix()}`",
        "",
        "## Inventory",
        "",
        f"- Preset folders: {len(preset_dirs)}",
        f"- Project captures: {len(project_paths)}",
        f"- Paired captures: {len(pairs)}",
        f"- Presets without project capture: {len(set(preset_dirs) - set(project_paths))}",
        f"- Projects without preset folder: {len(set(project_paths) - set(preset_dirs))}",
        "",
        "Paired project types:",
        _counter_table(type_counts, ("type", "count")),
        "",
        "All preset types:",
        _counter_table(all_type_counts, ("type", "count")),
    ]

    mismatches: dict[str, list[str]] = defaultdict(list)
    _check_engine_ids(pairs, mismatches)
    _check_track1_octave(pairs, mismatches)
    _check_playmode(pairs, mismatches)
    _check_header_bytes(pairs, mismatches)
    _check_preset_labels(pairs, mismatches)
    _check_q16_fields(pairs, mismatches)
    _check_array_q16(pairs, "engine.params", ENGINE_PARAM_OFFSETS, mismatches)
    _check_array_q16(pairs, "fx.params", FX_PARAM_OFFSETS, mismatches)
    _check_array_q16(pairs, "lfo.params", LFO_PARAM_OFFSETS, mismatches)
    _check_sampler_fields(pairs, mismatches)

    sections.extend(
        [
            "",
            "## Field Coverage",
            "",
            _coverage_table(),
            "",
            "## Confirmed Direct Mappings",
            "",
            "- `patch.json.type` maps to the track engine byte at `track+0x14` for all paired captures.",
            "- `patch.json.octave` maps to decoded-image `0x003D` for T1 as a signed byte. Manual device testing confirms octave is track-global, not pattern-local.",
            "- The short preset label at `track+0x453F` is `1/<preset folder name>` for all paired captures except the duplicate/mismatched sample noted below.",
            "- `engine.params[0..7]` map directly as q16 values to `track+0x3857..0x3873`.",
            "- `engine.playmode` maps to the raw word at `track+0x3887` (`poly=0x15555555`, `mono=0x3FFFFFFF`).",
            "- `envelope.amp.*`, `envelope.filter.*`, most `engine.*` lanes, most `fx.params[0..7]`, and `lfo.params[0..7]` map as the high 16 bits of 4-byte words in the known sound-state block.",
            "- Sampler project sample windows store full u32 values at `track+0x393F..0x394F`, not u16 values.",
            "- Sampler `loop.crossfade` stores a normalized byte: `floor(loop.crossfade * 128 / framecount)` at `track+0x3956`.",
            "- Ten clean drum-kit captures map path/key/tune/pan/reverse/playmode by `hikey - 53`; their voice 1-23 `sample.end` values appear at previous slot `+0x70`.",
            "",
            "## Mismatches / Exceptions",
            "",
        ]
    )
    if mismatches:
        for key in sorted(mismatches, key=lambda item: (-len(mismatches[item]), item)):
            examples = mismatches[key][:8]
            sections.append(f"### {key} ({len(mismatches[key])})")
            sections.extend(f"- {example}" for example in examples)
            if len(mismatches[key]) > len(examples):
                sections.append(f"- ... {len(mismatches[key]) - len(examples)} more")
            sections.append("")
    else:
        sections.append("No mismatches found.")
        sections.append("")

    sections.extend(
        [
            "## Immediate Follow-Ups",
            "",
            "- Treat `nt-dx analog.xy` as suspect: it appears to contain the `nt-dx legend` sample path/window even though the matching `patch.json` is `nt-dx analog.preset`.",
            "- Drum `sample.end`/`framecount` writing is not preset-load exact yet: clean loaded kits shift voices 1-23 to previous slot `+0x70`, while the generic drum voice writer still writes the direct edit field and voice 0 remains unresolved.",
            "- Use this script after adding more project captures; it is corpus-size independent and should scale to the planned 300+ files.",
        ]
    )
    return "\n".join(sections)


def _load_pair(name: str, preset_dir: Path, project_path: Path) -> Pair:
    patch = _read_patch(preset_dir / "patch.json")
    project = ImageProject.from_file(str(project_path))
    return Pair(name, preset_dir, project_path, patch, project, project.track_start(1))


def _read_patch(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be an object")
    return data


def _check_engine_ids(pairs: list[Pair], mismatches: dict[str, list[str]]) -> None:
    for pair in pairs:
        patch_type = str(pair.patch.get("type", ""))
        expected = ENGINE_IDS.get(patch_type)
        got = pair.project.image[pair.track_start + 0x14]
        if expected is not None and got != expected:
            mismatches["engine id"].append(
                f"`{pair.name}`: `{patch_type}` expected `0x{expected:02X}`, got `0x{got:02X}`"
            )


def _check_preset_labels(pairs: list[Pair], mismatches: dict[str, list[str]]) -> None:
    for pair in pairs:
        expected = f"1/{pair.name}"
        got = _cstr(pair.project.image, pair.track_start + PRESET_LABEL_OFFSET, PRESET_LABEL_MAX)
        if got != expected:
            mismatches["preset label"].append(f"`{pair.name}`: expected `{expected}`, got `{got}`")


def _check_track1_octave(pairs: list[Pair], mismatches: dict[str, list[str]]) -> None:
    for pair in pairs:
        expected = _lookup(pair.patch, "octave")
        if not isinstance(expected, int):
            continue
        got = _s8(pair.project.image[TRACK1_OCTAVE_OFFSET])
        if got != expected:
            mismatches["octave"].append(f"`{pair.name}`: expected `{expected}`, got `{got}`")


def _check_playmode(pairs: list[Pair], mismatches: dict[str, list[str]]) -> None:
    for pair in pairs:
        playmode = _lookup(pair.patch, "engine.playmode")
        expected = PLAYMODE_WORDS.get(playmode)
        if expected is None:
            continue
        got = _u32(pair.project.image, pair.track_start + 0x3887)
        if got != expected:
            mismatches["engine.playmode"].append(
                f"`{pair.name}`: `{playmode}` expected `0x{expected:08X}`, got `0x{got:08X}`"
            )


def _check_header_bytes(pairs: list[Pair], mismatches: dict[str, list[str]]) -> None:
    for pair in pairs:
        lfo_type = _lookup(pair.patch, "lfo.type")
        expected_lfo_type = LFO_TYPE_BYTES.get(lfo_type)
        if expected_lfo_type is not None:
            got = pair.project.image[pair.track_start + 0x1C]
            if got != expected_lfo_type:
                mismatches["lfo.type"].append(
                    f"`{pair.name}`: `{lfo_type}` expected `0x{expected_lfo_type:02X}`, got `0x{got:02X}`"
                )

        lfo_active = _lookup(pair.patch, "lfo.active")
        if isinstance(lfo_active, bool):
            expected_lfo_active = 1 if lfo_active else 0
            got = pair.project.image[pair.track_start + 0x20]
            if got != expected_lfo_active:
                mismatches["lfo.active"].append(
                    f"`{pair.name}`: expected `{expected_lfo_active}`, got `{got}`"
                )

        fx_type = _lookup(pair.patch, "fx.type")
        expected_fx_type = FX_TYPE_BYTES.get(fx_type)
        if expected_fx_type is not None:
            got = pair.project.image[pair.track_start + 0x21]
            if got != expected_fx_type:
                mismatches["fx.type"].append(
                    f"`{pair.name}`: `{fx_type}` expected `0x{expected_fx_type:02X}`, got `0x{got:02X}`"
                )

        fx_active = _lookup(pair.patch, "fx.active")
        if isinstance(fx_active, bool):
            expected_fx_active = 1 if fx_active else 0
            got = pair.project.image[pair.track_start + 0x25]
            if got != expected_fx_active:
                mismatches["fx.active"].append(
                    f"`{pair.name}`: expected `{expected_fx_active}`, got `{got}`"
                )


def _check_q16_fields(pairs: list[Pair], mismatches: dict[str, list[str]]) -> None:
    for pair in pairs:
        for path, offset in Q16_FIELDS.items():
            expected = _lookup(pair.patch, path)
            if isinstance(expected, int):
                got = _q16(pair.project.image, pair.track_start + offset)
                if got != expected:
                    mismatches[path].append(
                        f"`{pair.name}`: expected `{expected}`, got `{got}` "
                        f"(raw `0x{_u32(pair.project.image, pair.track_start + offset):08X}`)"
                    )


def _check_array_q16(
    pairs: list[Pair],
    path: str,
    offsets: list[int],
    mismatches: dict[str, list[str]],
) -> None:
    for pair in pairs:
        values = _lookup(pair.patch, path)
        if not isinstance(values, list):
            continue
        for index, offset in enumerate(offsets):
            if index >= len(values) or not isinstance(values[index], int):
                continue
            expected = values[index]
            got = _q16(pair.project.image, pair.track_start + offset)
            if got != expected:
                mismatches[f"{path}.{index}"].append(
                    f"`{pair.name}`: expected `{expected}`, got `{got}` "
                    f"(raw `0x{_u32(pair.project.image, pair.track_start + offset):08X}`)"
                )


def _check_sampler_fields(pairs: list[Pair], mismatches: dict[str, list[str]]) -> None:
    for pair in pairs:
        if pair.patch.get("type") != "sampler":
            continue
        regions = pair.patch.get("regions")
        if not isinstance(regions, list) or not regions or not isinstance(regions[0], dict):
            continue
        region = regions[0]
        sample = region.get("sample")
        if isinstance(sample, str):
            expected = f"/fat32/presets/1/{pair.name}.preset/{sample}"
            got = _cstr(pair.project.image, pair.track_start + SAMPLER_SAMPLE_PATH_OFFSET, SAMPLER_SAMPLE_PATH_MAX)
            if got != expected:
                mismatches["sampler sample path"].append(
                    f"`{pair.name}`: expected `{expected}`, got `{got}`"
                )
        for path, offset in SAMPLER_U32_FIELDS.items():
            expected = _lookup(pair.patch, path)
            if isinstance(expected, int):
                got = _u32(pair.project.image, pair.track_start + offset)
                if got != expected:
                    mismatches[path].append(f"`{pair.name}`: expected `{expected}`, got `{got}`")
        keycenter = region.get("pitch.keycenter")
        hikey = region.get("hikey")
        expected_key = keycenter if isinstance(keycenter, int) else hikey
        if isinstance(expected_key, int):
            got = pair.project.image[pair.track_start + SAMPLER_SLOT_ROOT_KEY_OFFSET]
            if got != expected_key:
                mismatches["regions.0.pitch.keycenter"].append(
                    f"`{pair.name}`: expected `{expected_key}`, got `{got}`"
                )
        framecount = region.get("framecount")
        crossfade = region.get("loop.crossfade")
        if isinstance(framecount, int) and framecount > 0 and isinstance(crossfade, int):
            expected_crossfade = min(255, (crossfade * 128) // framecount)
            got = pair.project.image[pair.track_start + 0x3956]
            if got != expected_crossfade:
                mismatches["regions.0.loop.crossfade"].append(
                    f"`{pair.name}`: expected `{expected_crossfade}` from `{crossfade}`/`{framecount}`, got `{got}`"
                )
        reverse = region.get("reverse")
        if isinstance(reverse, bool):
            expected_direction = 1 if reverse else 0
            got = pair.project.image[pair.track_start + SAMPLER_SLOT_DIRECTION_OFFSET]
            if got != expected_direction:
                mismatches["regions.0.reverse"].append(
                    f"`{pair.name}`: expected `{expected_direction}`, got `{got}`"
                )
        gain = region.get("gain")
        if isinstance(gain, int):
            got = _s8(pair.project.image[pair.track_start + SAMPLER_SLOT_GAIN_OFFSET])
            if got != gain:
                mismatches["regions.0.gain"].append(f"`{pair.name}`: expected `{gain}`, got `{got}`")


def _lookup(data: dict[str, Any], dotted_path: str) -> Any:
    if dotted_path in data:
        return data[dotted_path]
    parts = dotted_path.split(".")
    return _lookup_parts(data, parts)


def _lookup_parts(current: Any, parts: list[str]) -> Any:
    if not parts:
        return current
    remainder = ".".join(parts)
    if isinstance(current, dict):
        if remainder in current:
            return current[remainder]
        head, *tail = parts
        if head not in current:
            return None
        return _lookup_parts(current[head], tail)
    if isinstance(current, list):
        head, *tail = parts
        if not head.isdigit():
            return None
        index = int(head)
        if index >= len(current):
            return None
        return _lookup_parts(current[index], tail)
    return None


def _u32(image: bytearray, offset: int) -> int:
    return int.from_bytes(image[offset : offset + 4], "little")


def _q16(image: bytearray, offset: int) -> int:
    return _u32(image, offset) >> 16


def _cstr(image: bytearray, offset: int, max_len: int) -> str:
    return bytes(image[offset : offset + max_len]).split(b"\x00", 1)[0].decode("utf-8", "replace")


def _s8(value: int) -> int:
    return value - 0x100 if value >= 0x80 else value


def _counter_table(counter: Counter[str], columns: tuple[str, str]) -> str:
    lines = [f"| {columns[0]} | {columns[1]} |", "| --- | ---: |"]
    lines.extend(f"| `{key}` | {value} |" for key, value in counter.most_common())
    return "\n".join(lines)


def _coverage_table() -> str:
    lines = ["| Field | Status | Notes |", "| --- | --- | --- |"]
    lines.extend(f"| `{field}` | {status} | {notes} |" for field, status, notes in FIELD_COVERAGE)
    return "\n".join(lines)


if __name__ == "__main__":
    main()
