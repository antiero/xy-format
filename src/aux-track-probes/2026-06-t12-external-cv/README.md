# 2026-06 T12 External CV Probe Plan

Baseline: `t12-external-cv-baseline.xy`, copied from
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`.

Goal: isolate External CV output mode, pitch/CV calibration fields, gate
behavior, and visible track parameters.

## Planned Captures

| File | Device action |
| --- | --- |
| `t12-cv-mode-v-oct.xy` | Set CV mode to V/oct or the nearest named pitch mode. |
| `t12-cv-mode-hz-v.xy` | Set CV mode to Hz/V if available. |
| `t12-cv-gate-high.xy` | Set gate polarity/level to high/non-default. |
| `t12-cv-gate-low.xy` | Set gate polarity/level to low/opposite value. |
| `t12-cv-param1-min.xy` | Move visible parameter 1 to minimum. |
| `t12-cv-param1-max.xy` | Move visible parameter 1 to maximum. |
| `t12-cv-param2-mid.xy` | Move visible parameter 2 to a middle non-default value. |
| `t12-cv-note-step1.xy` | Add one note on step 1 to test generic note storage on T12. |

## Notes

If calibration changes require connected hardware, record the device condition
in this README before analysis.
