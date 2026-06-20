# 2026-06-15 Aux Filter Probe

Probe folder: `src/aux-track-probes/2026-06-aux-filter/`

Firmware: 1.1.4

## Summary

The shared aux M3 filter block for T13-T16 lives in the track struct at
`+0x3897..+0x38A6`, with four u32 words:

| Field | Track-relative offset | Captures |
| --- | ---: | --- |
| Filter enabled/touched flag | `+0x0025` | Edited captures write `0x00000001`. |
| Param 1 / HPF | `+0x3897` | min/default `0x00000000`; max `0x7FFFFFFF`. |
| Param 2 | `+0x389B` | mid `0x7C28F2FF`; semantic effect unknown. |
| Param 3 | `+0x389F` | mid `0x3570CA40`; semantic effect unknown. |
| Param 4 / LPF | `+0x38A3` | min `0x00000000`; max/default `0x7FFFFFFF`. |
| Aux save side effects | `+0x38F2`, `+0x38F6` | Edited captures write `0x00000040`. |

Param 2 and Param 3 were expected to be no-op controls, but they do persist raw
words when moved. Mark them as located but semantically unknown.

`aux-filter-lpf-min.xy` also changed `+0x389B` to `0x0147AF00`, likely a
neighboring encoder co-change during capture. It should not be treated as part
of the LPF field unless a follow-up confirms it.
