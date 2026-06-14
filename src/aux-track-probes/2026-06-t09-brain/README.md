# 2026-06 T9 Brain Probe Plan

Baseline: `t09-brain-baseline.xy`, copied from
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`.

Goal: isolate Brain track settings, routing, linked-track state, and any
recorded Brain sequence storage.

## Planned Captures

| File | Device action |
| --- | --- |
| `t09-brain-mode-manual.xy` | Set Brain mode to manual. |
| `t09-brain-mode-auto.xy` | Set Brain mode to auto. |
| `t09-brain-key-c.xy` | Set key/root to C or another visible non-default if C is baseline. |
| `t09-brain-scale-minor.xy` | Set scale to minor. |
| `t09-brain-link-t1.xy` | Link/control only T1. |
| `t09-brain-link-t1-t8.xy` | Link/control T1 through T8. |
| `t09-brain-route-t1-only.xy` | Route output to T1 only if routing is separate from link state. |
| `t09-brain-seq-two-notes.xy` | Record the smallest useful Brain sequence, e.g. two notes/chords. |

## Notes

Use one-variable captures first. If the UI requires changing both mode and
route before a field is visible, record that dependency in this README.
