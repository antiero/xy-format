# Human Explainer: How `.xy` Project Files Work

## Who This Is For

This is for engineers who know basic binary formats but are new to this repo
and OP-XY reverse engineering.

Goal: give you the current practical model without requiring byte-level mastery
on day one.

## TL;DR

An `.xy` file is:

```text
8-byte wrapper header + RLE(decoded project image)
```

The decoded project image is the firmware's project state: little-endian
C-style structs with count-prefixed vectors. The old descriptor, preamble,
event-type, tail-byte, and note-token theories came from reading compressed
bytes as if they were the real struct bytes.

## The Current Mental Model

Work in decoded image space:

1. Read the file with `xy.rle.decode_project`.
2. Edit stable fields and vectors in the decoded image.
3. Encode with `xy.rle.encode_project`.
4. Validate by byte-exact fixture replication and device testing.

Authoring code lives in `xy/image_writer.py`. The arrangement builder writes
track pattern structs, scene rows, mute rows, and the Song 1 footer table.

## Layout At A Glance

The baseline decoded image is:

```text
global header      3,449 bytes
track structs      16 logical tracks, 17,876 bytes each before note/vector growth
clone structs      inserted after a leader when a track has extra patterns
footer             song table
```

Important examples:

- Global tempo, groove, click, active scene/song, MIDI channels, and master
  state live in the global header.
- Each track struct has pattern length, engine state, sound-state blocks,
  step components, p-locks, drum/sample regions, and the note vector.
- Notes are fixed 12-byte records:
  `u32 tick; u32 gate; u8 note; u8 velocity; u8 flags[2]`.
- Step components are fixed decoded-image per-step slots.
- P-locks are a decoded-image table, not variable raw-byte entries.
- Scenes are 33-byte rows: pattern selections, mute values, and a present flag.

## What Not To Reintroduce

Do not add authoring code based on:

- scaffold templates
- descriptor schemes
- pre-track or preamble propagation
- event-type bytes
- note/gate token grammars
- velocity nudges for `note == velocity`
- raw compressed-byte transplants

Those were artifacts of the pre-RLE model. If a new feature cannot be expressed
through the decoded image yet, map the decoded field first.

## Practical Ramp-Up Path

Read in this order:

1. `docs/format/record_structure.md`
2. `docs/format/decoded_image_map.md`
3. `docs/engineering/authoring.md`
4. `docs/parse_capability_checklist.md`
5. `docs/state_of_understanding.md`

Historical wrong turns remain in `docs/logs/*` for provenance, not as current
format reference.
