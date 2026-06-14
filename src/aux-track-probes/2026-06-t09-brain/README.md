# 2026-06 T9 Brain Probe Plan

Baseline: `t09-brain-baseline.xy`, copied from
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`.

Goal: isolate Brain track settings, routing, linked-track state, and any
recorded Brain sequence storage.

## Planned Captures

| File | Device action | Notes |
| --- | --- |
| `t09-brain-mode-manual.xy` | Set Brain mode to manual. | Manual - c major |
| `t09-brain-mode-auto.xy` | Set Brain mode to auto. | Auto - same as default. also detects as c major. |
| `t09-brain-key-d.xy` | Set key/root to D | manual - key d major. expect increment of 2 semitones from c major.| 
| `t09-brain-scale-minor.xy` | Set scale to minor. | manual - scale C minor. |
| `t09-brain-link-t1.xy` | Link T1. | default is not linked |
| `t09-brain-link-t2.xy` | Link T2. | default is not linked |
| `t09-brain-link-t3.xy` | Link T3. | default is not linked |
| `t09-brain-link-t4.xy` | Link T4. | default is not linked |
| `t09-brain-link-t5.xy` | Link T5. | default is not linked |
| `t09-brain-link-t6.xy` | Link T6. | default is not linked |
| `t09-brain-link-t7.xy` | Link T7. | default is not linked |
| `t09-brain-link-t8.xy` | Link T8. | default is not linked |
| `t09-brain-route-t1-t8.xy` | Link/control T1 through T8. | |
| `t09-brain-route-none.xy` | Route output to none. | |
| `t09-brain-route-t1-only.xy` | Route output to T1 only. | |
| `t09-brain-route-t2-only.xy` | Route output to T2 only. | |
| `t09-brain-route-t3-only.xy` | Route output to T3 only. | |
| `t09-brain-route-t4-only.xy` | Route output to T4 only. | |
| `t09-brain-route-t5-only.xy` | Route output to T5 only. | |
| `t09-brain-route-t6-only.xy` | Route output to T6 only. | |
| `t09-brain-route-t7-only.xy` | Route output to T7 only. | |
| `t09-brain-route-t8-only.xy` | Route output to T8 only. | |
| `t09-brain-seq-two-notes.xy` | Record the smallest useful Brain sequence, e.g. two notes/chords. |

## Notes

Use one-variable captures first. If the UI requires changing both mode and
route before a field is visible, record that dependency in this README.

Important difference between link and route: link is singular selection / off. Route is on/off per track.

I expect route to be a 1 byte mask, which would make default (every track except 1 and 2, because those are drums):
0b00111111, or 0b11111100 is the endianness is the other way around. If these are not found, try the complements
route-t1-t8 should then be 0b11111111, and
route-t1-only should be 0b10000000, under that same hypothesis.

i dont exactly understand link semantics. Guide (section 15.1) says:
"""
rotate the white knob to link any of the instrument tracks to the brain track, this allows you to riff over your song, while transposing it live.
"""