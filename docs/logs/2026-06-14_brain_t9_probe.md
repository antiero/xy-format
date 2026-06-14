# 2026-06-14 Brain T9 Probe

Probe source: `src/aux-track-probes/2026-06-t09-brain/`.

## Confirmed fields

Brain routing is a single byte at track-relative `+0x09` in the T9 struct.
The bit order is T1-low:

| Capture | Raw |
| --- | --- |
| `t09-brain-route-none.xy` | `0x00` |
| `t09-brain-route-t1-only.xy` | `0x01` |
| `t09-brain-route-t2-only.xy` | `0x02` |
| `t09-brain-route-t3-only.xy` | `0x04` |
| `t09-brain-route-t4-only.xy` | `0x08` |
| `t09-brain-route-t5-only.xy` | `0x10` |
| `t09-brain-route-t6-only.xy` | `0x20` |
| `t09-brain-route-t7-only.xy` | `0x40` |
| `t09-brain-route-t8-only.xy` | `0x80` |
| `t09-brain-route-t1-t8.xy` | `0xFF` |

The baseline route mask is `0xFC`, matching the device default of routing
T3-T8 and excluding T1/T2 drum tracks.

The generic edited/pristine byte at track-relative `+0x11` follows the same
rule as other track edits: baseline is `0x08`, device-edited Brain captures
write `0x00`.

## Brain note sequence

`t09-brain-seq-two-notes.xy` confirms the Brain track uses the generic note
vector at track-relative `+0x456F`:

| Index | Tick | Step | Gate | Note | Velocity | Flags |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 0 | 1 | 240 | 60 | 100 | `00 00` |
| 1 | 3840 | 9 | 240 | 67 | 100 | `00 00` |

## Key and scale bucket hypothesis

Brain M1-style fields use the common engine-parameter word area:
track-relative `+0x3857`, `+0x385B`, `+0x385F`, and `+0x3863`.

The device-authored sweep fits this candidate key/root formula at `+0x385B`:

```
key_index = floor(raw * 12 / 0x80000000)
```

| Capture | Index | Key | Raw |
| --- | ---: | --- | ---: |
| `t09-brain-key-c.xy` | 0 | C | `0x02AAAAAA` |
| `t09-brain-key-c#.xy` | 1 | C# | `0x12AAAAA9` |
| `t09-brain-key-d.xy` | 2 | D | `0x17FFFFFE` |
| `t09-brain-key-d#.xy` | 3 | D# | `0x22AAAAA8` |
| `t09-brain-key-e.xy` | 4 | E | `0x2D555552` |
| `t09-brain-key-f.xy` | 5 | F | `0x37FFFFFC` |
| `t09-brain-key-f#.xy` | 6 | F# | `0x42AAAAA6` |
| `t09-brain-key-g.xy` | 7 | G | `0x52AAAAA5` |
| `t09-brain-key-g#.xy` | 8 | G# | `0x5D55554F` |
| `t09-brain-key-a.xy` | 9 | A | `0x67FFFFF9` |
| `t09-brain-key-a#.xy` | 10 | A# | `0x6D55554E` |
| `t09-brain-key-b.xy` | 11 | B | `0x7D55554D` |

The device-authored sweep fits this candidate scale formula at `+0x385F`:

```
scale_index = floor(raw * 7 / 0x80000000)
```

| Capture | Index | Scale | Raw |
| --- | ---: | --- | ---: |
| `t09-brain-scale-major.xy` | 0 | major | `0x04924924` |
| `t09-brain-scale-dorian.xy` | 1 | dorian | `0x16DB6DB6` |
| `t09-brain-scale-phrygian.xy` | 2 | phrygian | `0x29249248` |
| `t09-brain-scale-lydian.xy` | 3 | lydian | `0x3B6DB6DA` |
| `t09-brain-scale-mixolydian.xy` | 4 | mixolydian | `0x4DB6DB6C` |
| `t09-brain-scale-minor.xy` | 5 | minor | `0x69249247` |
| `t09-brain-scale-locrian.xy` | 6 | locrian | `0x7B6DB6D9` |

## Remaining raw parameter evidence

| Capture | `+3857` | `+385B` | `+385F` | `+3863` |
| --- | ---: | ---: | ---: | ---: |
| baseline / auto | `0x7FFFFFFF` | `0x00000000` | `0x00000000` | `0x00000000` |
| manual C major | `0x0FFFFFFF` | `0x02AAAAAA` | `0x00000000` | `0x00000000` |
| key D major | `0x2FFFFFFE` | `0x17FFFFFE` | `0x00000000` | `0x00000000` |
| scale C minor | `0x0FFFFFFF` | `0x00000000` | `0x69249247` | `0x00000000` |

The second and third words are strong key/scale candidates, but these formulas
are not promoted until PC-generated fixtures are verified on-device. The first
word appears to be mode/session state, but the current captures are not enough
to name all states confidently.

PC-generated validation files live in
`src/aux-track-probes/2026-06-t09-brain/pc-generated-validation/`. The pack
covers lo/hi raw edge cases for all 12 key and 7 scale buckets (38 files),
regenerated from the analytic boundary formulas in that README.

Link selection lands in the fourth parameter word at `+0x3863`, but the
device-authored captures show bucket/noise behavior from encoder detents.
The existing one-value-per-link set is enough to locate the field, not enough
to claim a stable enum mapping.

## Save noise

All device-saved Brain fixtures also carry the known aux-track save side
effect at T9-T16 track-relative `+0x38F2` and `+0x38F6`
(`0x00 -> 0x40`). This is not Brain-specific state.
