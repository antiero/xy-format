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

## Notes
Full historical crash details, callouts, and screenshots references are preserved in `docs/logs/2026-02-13_agents_legacy_snapshot.md`.

## Current Regression Coverage

Crash prevention now lives in decoded-image authoring tests:

- `tests/test_rle.py`: codec round-trip and RLE escaping.
- `tests/test_image_writer.py`: byte-exact replication and generated
  arrangement invariants.
- Inspector and fixture tests under `tests/test_*_inspection.py`.
