# 2026-06-15 T10 Punch-in FX Probe

Probe source: `src/aux-track-probes/2026-06-t10-punch-in-fx/`.

## Result

Punch-in FX triggers are stored as generic note-vector records in the T10
track struct at track-relative `+0x456F`.

| Capture | Count | Tick | Step | Gate | Note | Velocity | Flags |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `t10-punch-in-fx-baseline.xy` | 0 | - | - | - | - | - | - |
| `t10-punch-trigger-step1.xy` | 1 | 0 | 1 | 240 | 101 | 100 | `00 00` |
| `t10-punch-trigger-step9.xy` | 1 | 3840 | 9 | 240 | 101 | 100 | `00 00` |

The record shape is the same 12-byte vector element used by regular track
notes and T9 Brain notes:

```
struct NoteRecord {
    u32 tick_le;
    u32 gate_ticks_le;
    u8 note;
    u8 velocity;
    u8 flags[2];
}
```

The two captures confirm event placement and the T10 record format. They do
not map the complete punch key range because both landed on note byte `101`.

## Save noise

The captures also carry the known aux-track save side effect at T9/T10
track-relative `+0x38F2` and `+0x38F6` (`0x00 -> 0x40`). The remaining large
decoded diff regions after T10 `+0x456F` are downstream shifts caused by the
12-byte note-vector insertion, not independent T11-T16 edits.
