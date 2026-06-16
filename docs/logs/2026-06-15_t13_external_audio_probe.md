# 2026-06-15 T13 External Audio Probe

Probe source: `src/aux-track-probes/2026-06-t13-external-audio/`.

## Confirmed fields

T13 External Audio M1 fields:

| UI field | Storage | Baseline | Captures |
| --- | ---: | ---: | --- |
| Source | T13 `+0x3857` | `0x00000000` = mic | hp `0x1FFFFFFE`, line `0x46666662`, USB-C `0x5FFFFFFA`, main `0x79999992` |
| Drive | T13 `+0x385B` | `0x00000000` = 0 | drive 20 `0x7FFFFFFF` |
| Level | T13 `+0x38FB` | `0x60000000` = 75 | level 0 `0x00000000`, level 99 `0x7FFFFFFF` |
| Mix | T13 `+0x3863` | `0x7FFFFFFF` = 99 | mix 0 `0x00000000` |

The input active/inactive click did not produce a distinct project-field delta
in this fixture set: `t13-audio-input-off.xy` is byte-identical to baseline,
and `t13-audio-input-on.xy` only carries known aux save noise.

The source/drive/level/mix values are strong device-authored anchors, but exact
bucket/display boundaries are not PC-generated verified.

## M2 sends

T13 sends are stored on the **source tracks**, not in the T13 track struct. The
per-track T13 send word is at source track-relative `+0x38A7`.

Baseline had T5 nonzero:

```text
T1 00000000  T2 00000000  T3 00000000  T4 00000000
T5 33330000  T6 00000000  T7 00000000  T8 00000000
```

Each returned `t13-audio-send-tN-99.xy` sets only one source-track send word to
`0x7FFFFFFF`; all other source-track T13 send words are `0x00000000`.

Note: `t13-audio-send-t6-99.xy` appears to be a capture mismatch. It sets the
T7 send word, matching `t13-audio-send-t7-99.xy`, rather than T6.

## Save noise

Device-saved T13 captures carry the known aux-track save side effect at T9-T16
track-relative `+0x38F2` and `+0x38F6` (`0x00 -> 0x40`). Edited T13 captures
also clear T13 `+0x11` from `0x08` to `0x00`.
