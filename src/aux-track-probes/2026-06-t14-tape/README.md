# 2026-06 T14 Tape Probe Plan

Baseline: `t14-tape-baseline.xy`, copied from
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`.

Goal: isolate Tape track playback parameters, transport/loop state, slice or
clip metadata, and sequenceable controls.

## Planned Captures

| File | Device action |
| --- | --- |
| `t14-tape-speed-min.xy` | Set tape speed to minimum. |
| `t14-tape-speed-max.xy` | Set tape speed to maximum. |
| `t14-tape-pitch-min.xy` | Set pitch to minimum. |
| `t14-tape-pitch-max.xy` | Set pitch to maximum. |
| `t14-tape-direction-reverse.xy` | Set playback direction to reverse. |
| `t14-tape-loop-on.xy` | Enable tape loop. |
| `t14-tape-loop-off.xy` | Disable tape loop after enabling it from the same source state. |
| `t14-tape-slice-one.xy` | Create one slice/marker if supported. |
| `t14-tape-trigger-step1.xy` | Add one tape trigger/event on step 1. |

## Notes

Tape may create larger media/clip state than simple parameter bytes. Prefer
small, deterministic edits and record whether audio content was present.
