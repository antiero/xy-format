# inspect_xy.py

`tools/inspect_xy.py` emits a multi-section report for a single `.xy` file.

## Current Coverage
- Header summary.
- Pattern directory/pre-track observations.
- Drum-engine track sample paths (24-voice table via `xy/drum_sample_inspection.py`).
- Per-track scan and event summaries.
- EQ/global snippets.

## Usage
- `python tools/inspect_xy.py 'src/one-off-changes-from-default/unnamed 1.xy'`

## Notes
- Pointer-tail and pointer-21 note decode is still incomplete; see `docs/issues/pointer_tail_decoding.md`.
- Use with `docs/workflows/inspector_sweep.md` for structured corpus validation.
