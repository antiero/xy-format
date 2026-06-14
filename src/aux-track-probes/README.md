# Auxiliary Track Probe Plans

Probe scaffolds for OP-XY auxiliary tracks T9-T16.

Each subdirectory contains a per-track baseline copied from
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`. Use that baseline as the
starting point for one-variable device captures. Save new captures into the
matching directory with the names listed in each README.

## Directories

| Track | Directory | Baseline |
| --- | --- | --- |
| T9 Brain | `2026-06-t09-brain/` | `t09-brain-baseline.xy` |
| T10 Punch-in FX | `2026-06-t10-punch-in-fx/` | `t10-punch-in-fx-baseline.xy` |
| T11 External MIDI | `2026-06-t11-external-midi/` | `t11-external-midi-baseline.xy` |
| T12 External CV | `2026-06-t12-external-cv/` | `t12-external-cv-baseline.xy` |
| T13 External Audio | `2026-06-t13-external-audio/` | `t13-external-audio-baseline.xy` |
| T14 Tape | `2026-06-t14-tape/` | `t14-tape-baseline.xy` |
| T15 FX I | `2026-06-t15-fx-i/` | `t15-fx-i-baseline.xy` |
| T16 FX II | `2026-06-t16-fx-ii/` | `t16-fx-ii-baseline.xy` |

## Capture Rules

1. Start every capture from the directory baseline unless the README says
   otherwise.
2. Change exactly one visible control, setting, route, or mode.
3. Use a conspicuous non-default value, but avoid musical content unless the
   target is a sequenced behavior.
4. Save the project and copy the resulting `.xy` using the planned filename.
5. Record the device-visible value in the README before analysis.
6. After analysis, promote confirmed offsets into docs and tests.
