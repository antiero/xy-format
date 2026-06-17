# Crash Catalog

## Reporting Standard
- Follow `docs/workflows/crash_capture.md` for every crash.
- Every crash entry must include:
  - failing artifact path (`.xy`)
  - source/template reference
  - generation command/parameters
  - device/firmware context
  - assertion text and stack trace (if available)
  - follow-up artifact path(s) and pass/crash outcome

## Crash #1: `num_patterns > 0`
- Context: early writer-produced file with type/padding misalignment.
- Current interpretation: impossible decoded-image state produced by the
  pre-RLE writer stack.
- Status: resolved by image-based authoring.

## Crash #2: `fixed_vector.h:77 length < thesize`
- Context: incorrect multi-note event encoding in early attempts.
- Current interpretation: compressed-byte event-type/tail artifacts were
  treated as real note grammar.
- Status: resolved by writing decoded 12-byte note records and re-encoding.

## Crash #3: `num_patterns > 0` (later-site assertion)
- Context: two-track drum authoring with incorrect raw-boundary assumptions.
- Current interpretation: impossible decoded-image state produced by the
  pre-RLE writer stack, not a required preamble propagation rule.
- Status: resolved by image-based authoring.

## Crash #4: `num_patterns > 0` from non-pristine preset donor
- Context: OP-XY `velv` generated project loaded through image-based authoring
  but copied preset identity from a generated multi-pattern project donor.
- Finding: the first failing isolation file was a one-pattern sound seed.
  T1 donor-copy loaded, T2 donor-copy crashed. T2 region isolation showed
  `0x13..0x2A0` alone loaded, `0x3457..0x456F` alone loaded, and
  `0x4570..0x45D4` alone crashed.
- Current interpretation: `track+0x456F` is note count and `track+0x4570`
  starts post-note-count storage. Copying that tail from a donor track with
  events can produce `note_count = 0` with stale note-record bytes, an
  impossible decoded-image state.
- Status: resolved by enforcing `ImageProject.set_preset()`'s pristine-donor
  precondition. Generated project donors must copy sound identity only before
  the note vector, or use an actual pristine preset-load donor.

## Notes
Full historical crash details, callouts, and screenshots references are preserved in `docs/logs/2026-02-13_agents_legacy_snapshot.md`.

## Current Regression Coverage

Crash prevention now lives in decoded-image authoring tests:

- `tests/test_rle.py`: codec round-trip and RLE escaping.
- `tests/test_image_writer.py`: byte-exact replication and generated
  arrangement invariants.
- Inspector and fixture tests under `tests/test_*_inspection.py`.
