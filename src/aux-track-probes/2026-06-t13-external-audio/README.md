# 2026-06 T13 External Audio Probe Plan

Baseline: `t13-external-audio-baseline.xy`, copied from
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`.

Goal: isolate External Audio input level, monitor/filter/sends, and any
sequenceable control fields on T13.

## Planned Captures

| File | Device action |
| --- | --- |
| `t13-audio-input-min.xy` | Set input level to minimum. |
| `t13-audio-input-max.xy` | Set input level to maximum. |
| `t13-audio-monitor-off.xy` | Disable monitoring if available. |
| `t13-audio-monitor-on.xy` | Enable monitoring if available. |
| `t13-audio-filter-min.xy` | Move first visible filter control to minimum. |
| `t13-audio-filter-max.xy` | Move first visible filter control to maximum. |
| `t13-audio-send-fx1-max.xy` | Set FX I send to maximum. |
| `t13-audio-send-fx2-max.xy` | Set FX II send to maximum. |
| `t13-audio-trig-step1.xy` | Add one step/event if T13 supports sequenced triggers. |

## Notes

Keep static input/monitor captures separate from mix-send captures; the latter
may overlap generic mixer fields.
