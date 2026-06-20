# 2026-06-15 Aux LFO Probe

Probe folder: `src/aux-track-probes/2026-06-aux-lfo/`

Firmware: 1.1.4

## Summary

The shared aux M4 LFO block is stored in the track struct at the same
track-relative offsets used by the broader M4/LFO area:

| Field | Track-relative offset | Notes |
| --- | ---: | --- |
| LFO enabled/touched flag | `+0x0020` | Edited captures set first byte from `0x00` to `0x01`. |
| Speed | `+0x38B7` | T13 default/min `0x40000000`; max `0x7FFFFFFF`. |
| Amount | `+0x38BB` | T13 min `0x00000000`; zero/default `0x40000000`; max `0x7FFFFFFF`. |
| Destination | `+0x38BF` | T13 generic destinations and T11 MIDI-only destinations share this word. |
| Param-dest | `+0x38C3` | T13 param targets 1-4 captured. |
| Aux save side effects | `+0x38F2`, `+0x38F6` | Edited captures write `0x00000040`. |

## T13 generic destination values

| Destination | Raw |
| --- | ---: |
| syn | `0x00000000` |
| filter | `0x4AAAAAA9` |
| amp | `0x75555553` |

## T13 param-dest values

| Param target | Raw |
| --- | ---: |
| 1 | `0x07FFFFFF` |
| 2 | `0x27FFFFFD` |
| 3 | `0x47FFFFFB` |
| 4 | `0x77FFFFF8` |

`aux-lfo-param-dest-3.xy` also changed `+0x38BF` to `0x0AAAAAAA`; this is
treated as capture co-change/jitter, not as a separate destination.

## T11 MIDI destination values

| Destination | Raw at `+0x38BF` |
| --- | ---: |
| off | `0x00000000` |
| cc1 | `0x3AAAAAA7` |
| cc2 | `0x7AAAAAA3` |

The `cc1` capture also changed `+0x38BB` to `0x028F5E00`. That neighboring
word should be isolated in a follow-up if T11 amount behavior matters.

## Caveats

These are device-authored detent values. Bucket formulas and true boundaries
for destination and param-destination selection are still hypotheses until
PC-generated boundary fixtures are inspected on-device.
