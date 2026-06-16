# 2026-06 T13 External Audio Probe Plan

> **Status:** captured/analyzed · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`

## What T13 actually is

Track 13 (External Audio) configures the **audio input bus** and per-track
sends. Filter (M3) and LFO (M4) use the **shared aux layouts** — probed
separately, not in this pack.


| Page   | Controls                                                                                                                                                                                                                        |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **M1** | Param 1: input **source** (1 builtin mic, 2 headphones, 3 line in, 4 USB-C, 5 main output loop). **Param 1 click:** input active/inactive. Param 2: **drive** 0–20 (21 values). Param 3: **level** 0–99. Param 4: **mix** 0–99. |
| **M2** | T1–T8 **send levels**, each 0–99.                                                                                                                                                                                               |
| **M3** | Filter — see `../2026-06-aux-filter/` (probe vehicle can be T13).                                                                                                                                                               |
| **M4** | LFO — see `../2026-06-aux-lfo/`.                                                                                                                                                                                                |


**Goal:** isolate M1 input/source/drive/level/mix and M2 send-level storage.

## Scope

Scene **1**, Track **13**. Re-copy baseline before each row.

## Rules

1. One control change per capture → **Save**.
2. Do not touch M3/M4 (shared probe packs).
3. For M2 sends: change **one** track send only; leave T1–T8 others at default.

---

## Capture procedure — M1


| PC filename                      | Procedure                                            |
| -------------------------------- | ---------------------------------------------------- |
| `t13-external-audio-baseline.xy` | T13. Factory defaults. Save.                         |
| `t13-audio-source-mic.xy`        | M1 param 1 → **builtin mic**. = default              |
| `t13-audio-source-hp.xy`         | M1 param 1 → **headphones**.                         |
| `t13-audio-source-line.xy`       | M1 param 1 → **line in**.                            |
| `t13-audio-source-usbc.xy`       | M1 param 1 → **USB-C**.                              |
| `t13-audio-source-main.xy`       | M1 param 1 → **main output** (out-in).               |
| `t13-audio-input-on.xy`          | M1 param 1 **click** → input **active**.             |
| `t13-audio-input-off.xy`         | M1 param 1 **click** → input **inactive**. = default |
| `t13-audio-drive-00.xy`          | M1 param 2 → drive **0**. = default                  |
| `t13-audio-drive-20.xy`          | M1 param 2 → drive **20**.                           |
| `t13-audio-level-00.xy`          | M1 param 3 → level **0**. (default = 75)             |
| `t13-audio-level-99.xy`          | M1 param 3 → level **99**. (default = 75)            |
| `t13-audio-mix-00.xy`            | M1 param 4 → mix **0**.                              |
| `t13-audio-mix-99.xy`            | M1 param 4 → mix **99**. = default                   |


## Capture procedure — M2 (sends). Note: baseline had T5=39, others 0.


| PC filename               | Procedure                        |
| ------------------------- | -------------------------------- |
| `t13-audio-send-t1-99.xy` | M2: T1 send → **99** (others 0). |
| `t13-audio-send-t2-99.xy` | M2: T2 send → **99**.            |
| `t13-audio-send-t3-99.xy` | M2: T3 send → **99**.            |
| `t13-audio-send-t4-99.xy` | M2: T4 send → **99**.            |
| `t13-audio-send-t5-99.xy` | M2: T5 send → **99**.            |
| `t13-audio-send-t6-99.xy` | M2: T6 send → **99**.            |
| `t13-audio-send-t7-99.xy` | M2: T7 send → **99**.            |
| `t13-audio-send-t8-99.xy` | M2: T8 send → **99**.            |


---

## Analysis Results

Device-returned captures, 2026-06-15:

### M1 fields

| UI field | Storage | Baseline | Captures |
| --- | ---: | ---: | --- |
| Source | T13 `+0x3857` | `0x00000000` = mic | hp `0x1FFFFFFE`, line `0x46666662`, USB-C `0x5FFFFFFA`, main `0x79999992` |
| Drive | T13 `+0x385B` | `0x00000000` = 0 | drive 20 `0x7FFFFFFF` |
| Level | T13 `+0x38FB` | `0x60000000` = 75 | level 0 `0x00000000`, level 99 `0x7FFFFFFF` |
| Mix | T13 `+0x3863` | `0x7FFFFFFF` = 99 | mix 0 `0x00000000` |

`t13-audio-input-off.xy` is byte-identical to baseline. `t13-audio-input-on.xy`
only has known aux save noise, so this pass did not find a distinct persisted
input-active field.

These are device-authored value anchors; exact bucket/display boundaries are
not PC-generated verified.

### M2 sends

T13 sends are stored on source tracks at track-relative `+0x38A7`, not in the
T13 struct. Baseline had T5 nonzero:

```text
T1 00000000  T2 00000000  T3 00000000  T4 00000000
T5 33330000  T6 00000000  T7 00000000  T8 00000000
```

Each returned `t13-audio-send-tN-99.xy` sets only one T1-T8 send word to
`0x7FFFFFFF`; all other T1-T8 send words are `0x00000000`.

Note: `t13-audio-send-t6-99.xy` appears to be a capture mismatch. It sets the
T7 send word, matching `t13-audio-send-t7-99.xy`, rather than T6.

Known non-semantic save noise: T9-T16 `+0x38F2/+0x38F6` (`0x00 -> 0x40`).
Edited captures also clear the edited track's `+0x11` (`0x08 -> 0x00`).
