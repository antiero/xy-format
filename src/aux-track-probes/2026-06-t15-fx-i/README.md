# 2026-06 T15 FX I Probe Plan

Baseline: `t15-fx-i-baseline.xy`, copied from
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`.

Goal: isolate FX I type enum and effect parameter storage.

## Planned Captures

| File | Device action |
| --- | --- |
| `t15-fx-i-type-chorus.xy` | Select chorus. |
| `t15-fx-i-type-delay.xy` | Select delay. |
| `t15-fx-i-type-distortion.xy` | Select distortion. |
| `t15-fx-i-type-lofi.xy` | Select lofi. |
| `t15-fx-i-type-phaser.xy` | Select phaser. |
| `t15-fx-i-type-reverb.xy` | Select reverb if available on FX I. |
| `t15-fx-i-param1-min.xy` | Move parameter 1 to minimum for one fixed type. |
| `t15-fx-i-param1-max.xy` | Move parameter 1 to maximum for the same fixed type. |
| `t15-fx-i-param2-mid.xy` | Move parameter 2 to a middle non-default value. |
| `t15-fx-i-plock-step1-param1.xy` | Add one p-lock for parameter 1 on step 1. |

## Notes

Capture type sweeps separately from parameter sweeps. For parameter captures,
keep the effect type fixed and write that type in the device notes.
