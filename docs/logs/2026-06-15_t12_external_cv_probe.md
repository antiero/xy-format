# 2026-06-15 T12 External CV Probe

Probe source: `src/aux-track-probes/2026-06-t12-external-cv/`.

## Confirmed sequence storage

T12 External CV note captures use the generic note vector at track-relative
`+0x456F`.

| Capture | Count | Tick | Step | Gate | Note | Velocity | Flags |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `t12-external-cv-baseline.xy` | 0 | — | — | — | — | — | — |
| `t12-cv-note-step1.xy` | 1 | 0 | 1 | 240 | 29 | 100 | `00 00` |
| `t12-cv-note-step9.xy` | 1 | 3840 | 9 | 240 | 53 | 100 | `00 00` |

The octave difference is represented by the generic MIDI-note byte
(`29` vs `53`). No T12-specific CV pitch side field changed before the note
vector.

## Save noise

Device-saved T12 captures carry the known aux-track save side effect at
T9-T16 track-relative `+0x38F2` and `+0x38F6` (`0x00 -> 0x40`).
T12 edited captures also clear T12 `+0x11` from `0x08` to `0x00`.
