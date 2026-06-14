# 2026-06 T11 External MIDI Probe Plan

Baseline: `t11-external-midi-baseline.xy`, copied from
`src/bar-menu-probes/2026-06-bar-menu/bar0.xy`.

Goal: isolate External MIDI track channel, bank, program, and assignable CC
control storage.

## Planned Captures

| File | Device action |
| --- | --- |
| `t11-midi-channel-01.xy` | Set External MIDI channel to 1. |
| `t11-midi-channel-16.xy` | Set External MIDI channel to 16. |
| `t11-midi-bank-001.xy` | Set bank to 1 or the smallest visible non-default. |
| `t11-midi-bank-127.xy` | Set bank to 127 or max visible value. |
| `t11-midi-program-001.xy` | Set program to 1 or the smallest visible non-default. |
| `t11-midi-program-127.xy` | Set program to 127 or max visible value. |
| `t11-midi-cc1-num-074.xy` | Assign CC slot 1 to CC 74. |
| `t11-midi-cc1-value-064.xy` | Set CC slot 1 value to 64 after assigning CC 74. |
| `t11-midi-cc8-num-001.xy` | Assign CC slot 8 to CC 1. |
| `t11-midi-note-step1.xy` | Add one note on step 1 to test generic note storage on T11. |

## Notes

Separate channel/bank/program captures from CC assignment captures. CC number
and CC value may be distinct fields; capture both when possible.
