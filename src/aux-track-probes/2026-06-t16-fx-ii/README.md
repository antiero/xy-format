# 2026-06 T16 FX II Probe Plan

Baseline: `t16-fx-ii-baseline.xy`, copied from
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`.

Goal: isolate FX II type enum and effect parameter storage. Compare against
T15 to see whether FX I and FX II share enum/parameter layouts.

## Planned Captures

| File | Device action |
| --- | --- |
| `t16-fx-ii-type-chorus.xy` | Select chorus if available on FX II. |
| `t16-fx-ii-type-delay.xy` | Select delay. |
| `t16-fx-ii-type-distortion.xy` | Select distortion. |
| `t16-fx-ii-type-lofi.xy` | Select lofi. |
| `t16-fx-ii-type-phaser.xy` | Select phaser. |
| `t16-fx-ii-type-reverb.xy` | Select reverb. |
| `t16-fx-ii-param1-min.xy` | Move parameter 1 to minimum for one fixed type. |
| `t16-fx-ii-param1-max.xy` | Move parameter 1 to maximum for the same fixed type. |
| `t16-fx-ii-param2-mid.xy` | Move parameter 2 to a middle non-default value. |
| `t16-fx-ii-plock-step1-param1.xy` | Add one p-lock for parameter 1 on step 1. |

## Notes

T16 also participates in song/footer behavior in older docs. Keep FX parameter
captures free of scene/song edits.
