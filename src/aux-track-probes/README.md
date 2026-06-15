# Auxiliary Track Probe Plans

Probe packs for OP-XY auxiliary tracks T9–T16 and **shared** M3/M4 layouts.

Baseline for all per-track packs: copy
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`.

## Per-track packs

| Track | Directory | Status |
| --- | --- | --- |
| T9 Brain | `2026-06-t09-brain/` | **Good** — route, key/scale, link, sequence |
| T10 Punch-in FX | `2026-06-t10-punch-in-fx/` | **Good** — sequencer triggers only |
| T11 External MIDI | `2026-06-t11-external-midi/` | M1 channel/bank/program; M2/M3 CC map localized |
| T12 External CV | `2026-06-t12-external-cv/` | Sequencer notes (octave free); no CV params |
| T13 External Audio | `2026-06-t13-external-audio/` | M1 input bus; source-track aux sends |
| T14 Tape | `2026-06-t14-tape/` | M1 pitch/speed/length/mix; M2 sends |
| T15 FX I | `2026-06-t15-fx-i/` | type enum + delay params; source-track FX I sends |
| T16 FX II | `2026-06-t16-fx-ii/` | type enum + delay params; source-track FX II sends |

## Shared packs (do not duplicate in per-track READMEs)

| Layout | Directory | Vehicle track |
| --- | --- | --- |
| M3 filter (HPF/LPF) | `2026-06-aux-filter/` | T13 (applies to T13–T16) |
| M4 LFO | `2026-06-aux-lfo/` | T13 generic; T11 for off/cc1/cc2 dest |

## Capture rules

1. Re-copy **`bar0.xy`** (or pack baseline) before each one-variable capture.
2. Change **one** control → **Save** → MTP back with planned filename.
3. Record device-visible values in each pack's **Analysis Results** section.
4. Filter and LFO are **not** captured inside T11–T16 track packs.

## Promotion

Confirmed offsets → `docs/format/decoded_image_map.md`, inspection module,
`tests/test_*`, dated log under `docs/logs/`.
