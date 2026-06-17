# 2026-06-15 T11 External MIDI Probe

Probe source: `src/aux-track-probes/2026-06-t11-external-midi/`.

## Confirmed M1 fields

T11 uses the same track-relative engine parameter area as the other aux
tracks. The M1 fields are stored as u32 words:

| UI field | Track-relative offset | Domain | Evidence |
| --- | ---: | --- | --- |
| MIDI channel | `+0x3857` | 16 buckets, channel = index + 1 | channel 2 `0x09FFFFFD`, channel 16 `0x7DFFFFE0` |
| Bank | `+0x385B` | 129 buckets, index 0 = off, 1-128 = bank | bank 1 `0x017D05F4`, bank 128 `0x7F80FDFC` |
| Program | `+0x385F` | 129 buckets, index 0 = off, 1-128 = program | program 1 `0x017D05F4`, program 128 `0x7F80FDFC` |

The baseline stores `0x00000000` in all three fields, matching channel 1,
bank off, and program off. The file named `t11-midi-channel-01.xy` was used
for a channel-2 capture, as noted in the probe README; it should not be read
as a channel-1 change.

For these captures, the bucket-index hypothesis is:

```text
index = floor(raw * bucket_count / 0x80000000)
```

That formula is **hypothesized only**. It matches the returned device-authored
detent captures, but it is not boundary-safe until PC-generated boundary
fixtures are checked on device. Brain key/scale work already showed that a
formula can fit detents while placing bucket edges incorrectly.

## CC map table

The CC captures localize the M2/M3 CC assignment table to T11
track-relative `+0x3877..+0x3896` (eight 4-byte words). Nonzero words bucket
decode to the named UI values in the captures:

| Capture | Offset | Raw | Bucket interpretation |
| --- | ---: | ---: | --- |
| `t11-midi-cc1-num-074.xy` | `+0x3877` | `0x4A2AAA5F` | 128-bucket index 74 |
| `t11-midi-cc1-msg-001.xy` | `+0x3877` | `0x012AAAA8` | 129-bucket index 1 |
| `t11-midi-cc2-num-010.xy` | `+0x387B` | `0x0A2AAA9D` | 128-bucket index 10 |
| `t11-midi-cc3-msg-127.xy` | `+0x387F` | `0x7F7FFF7A` | 129-bucket index 128 |
| `t11-midi-cc3-num-127.xy` | `+0x388F` | `0x7F7FFF80` | 128-bucket index 127 |
| `t11-midi-cc4-msg-074.xy` | `+0x3893` | `0x4A7FFFB5` | 128-bucket index 74 |

The current CC fixture set proves the table location and bucket-readable
values, but not a clean ownership map for all eight fields. Several captures
necessarily coupled a CC number with a non-off message state, and at least
slot 3/4 evidence is not clean enough to label every word as either "CC
number" or "CC message" without another targeted pass.

## Uncaptured note confirmation

`t11-midi-note-step1.xy` still decodes byte-identical to the baseline, so it
does not yet confirm the generic note vector on T11.

## Save noise

Device-saved T11 menu fixtures also carry the known aux-track save side
effect at T9-T16 track-relative `+0x38F2` and `+0x38F6`
(`0x00 -> 0x40`). T11-edited captures also clear T11 `+0x11`
from `0x08` to `0x00`.
