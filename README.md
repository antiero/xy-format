# OP-XY Project Format Lab

This repo reverse-engineers Teenage Engineering OP-XY `.xy` project files and
builds tools for reading, editing, and generating them off-device.

The key breakthrough: an `.xy` project is the firmware's decoded project image
compressed with a simple byte-level RLE scheme. Once decoded, the data is mostly
little-endian C-style structs with count-prefixed vectors.

Start here:

- [State of understanding](docs/state_of_understanding.md)
- [Parse and author capability checklist](docs/parse_capability_checklist.md)
- [Decoded image map](docs/format/decoded_image_map.md)
- [Authoring guide](docs/engineering/authoring.md)
- [Docs index](docs/index.md)

## Current Format Model

The project body is one RLE stream:

```text
.xy file = 8-byte wrapper + RLE(project image)
```

The baseline decoded image layout is:

```text
global header      3,449 bytes
track structs      16 logical tracks, 17,876 bytes each before vector growth
clone structs      inserted for extra patterns
footer             56-byte song table
```

That reframes the old raw-byte model:

- Descriptor and preamble theories were artifacts of viewing compressed bytes.
- Former "event type" bytes before notes were RLE extension counts.
- The old note==velocity crash was an unescaped equal-byte pair in our writer,
  not an OP-XY musical rule.
- Current authoring should edit the decoded image, then re-encode.

## What Works Now

The current stack can:

- Decode and re-encode the corpus byte-exactly, except documented
  non-canonical RLE specimens.
- Reproduce many device-saved captures byte-exactly from semantic edits.
- Author notes, gates, velocities, pattern length, bars, step components,
  p-locks, engine params, preset donor copies, drum voice params, scenes, mutes,
  and song chains.
- Build multi-pattern arrangements through decoded track/pattern structs.
- Generate device-passing projects, including the note==velocity probe, sparse
  topology probes, preset transfer probes, and the Whitney capstone song.
- Inspect fixture-backed project state for project config, preset paths, drum
  and sampler samples, static mixer state, scene volumes/mutes, master EQ, and
  master saturator.

The latest full test run after merging PR #3 was:

```text
1759 passed, 32 skipped
```

## Canonical Tools

- `xy/rle.py` — decode/encode the project image.
- `xy/image_writer.py` — image-based editing and arrangement assembly.
- `tools/spec_to_xy_image.py` — JSON/spec to image-authored `.xy`.
- `tools/inspect_xy.py` — human-readable project inspection report.
- `tools/corpus_lab.py` — corpus/device outcome records.
- `tools/analysis/decoded_diff.py` — decoded-space field diffs.

Read-only inspection modules added by the 2026-06 contributor pass are indexed
in [the capability checklist](docs/parse_capability_checklist.md).

## What Still Needs Work

No structural format mystery remains on the critical authoring path. Remaining
work is field polish, productization, and edge-case validation:

- `midi_to_xy` v2 should route through `tools/spec_to_xy_image.py` and
  `xy/image_writer.py`.
- Some enums and user-facing labels remain partial: track-scale full enum, LFO
  subfunctions, mod-routing destination IDs, aux-track parameter labels, and
  player modes.
- Scene-stored volume bytes are mapped, but playback semantics on firmware
  1.1.4 need a focused retest.
- Multisampler zones/slicing and user `.preset` file format are not fully
  decoded.
- Limits certification remains for max scenes, visible song slots, full
  9-pattern topology, and 120-note edge cases.

For the live status, use [the roadmap](docs/roadmap.md) and
[the capability checklist](docs/parse_capability_checklist.md).

## Recommended Authoring Workflow

1. Start from a known-good `.xy` project close to the target state.
2. Decode with `xy/rle.py`.
3. Make semantic image edits with `xy/image_writer.py`.
4. Re-encode with `xy/rle.py`.
5. Inspect and decoded-diff the result.
6. Device-test new feature surfaces and record outcomes with
   `tools/corpus_lab.py`.

If a generated file crashes the device, follow
[the crash capture workflow](docs/workflows/crash_capture.md).

## Repo Guide

- `docs/format/` — stable byte-level format truth.
- `docs/logs/` — dated investigation history and contributor probe notes.
- `docs/engineering/` — implementation and authoring notes.
- `docs/workflows/` — repeatable capture, test, and crash procedures.
- `docs/reference/` — OP-XY limits and MIDI/CC references.
- `src/*-probes/` — device probe fixtures added by focused capture campaigns.
- `src/one-off-changes-from-default/` — original fixture corpus.
- `tests/` — regression coverage.
- `tools/` — user-facing and research CLIs.
- `xy/` — Python library code.

## House Rules

- Keep stable format knowledge in `docs/format/*`.
- Keep chronology and disproven paths in `docs/logs/*`.
- Preserve unknown decoded bytes until mapped.
- Prefer byte-exact replication of device captures over heuristics.
- Record device outcomes and every crash with artifacts and notes.
