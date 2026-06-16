# 2026-06 T11 External MIDI Probe Plan

> **Status:** captured/analyzed · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`

## What T11 actually is

Track 11 (External MIDI) sends MIDI to an external synth. **M3 has no filter**
— M2 and M3 are identical CC-mapping pages.


| Page        | Controls                                                                                                                                                                   |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **M1**      | Param 1: MIDI channel **1–16**. Param 2: bank **off / 1 … 128**. Param 3: program **off / 1 … 128**.                                                                       |
| **M2 / M3** | Four CC slots. Each slot: **param** = available CC number (**0–127**); **shift+param** = CC message (**off + 0–127**). Probe all **8** fields on **M2** (M3 is redundant). |
| **M4**      | Shared aux LFO — see `../2026-06-aux-lfo/` (includes T11-only destinations).                                                                                               |


**Goal:** locate channel/bank/program words and the four CC map pairs. Optionally
confirm note sequence storage matches generic `track+0x456F`.

## Scope

Scene **1**, Track **11**, Pattern **1**. Re-copy baseline before each row.

## Rules

1. Change **one** control per capture → **Save**.
2. Do not touch M4 (LFO probe pack), bar menu, or other tracks.
3. CC captures: stay on **M2**; leave the other seven CC fields at default.

---

## Capture procedure — M1 (channel / bank / program)


| PC filename                                    | Procedure                                  |
| ---------------------------------------------- | ------------------------------------------ |
| `t11-external-midi-baseline.xy`                | T11 / P1. Factory defaults. Save.          |
| `t11-midi-channel-01.xy (NEEDS RENAME ----->)` | M1 param 1 → channel **2**. (default = 1). |
| `t11-midi-channel-16.xy`                       | M1 param 1 → channel **16**.               |
| `t11-midi-bank-off.xy`                         | M1 param 2 → bank **off**. = default       |
| `t11-midi-bank-001.xy`                         | M1 param 2 → bank **1**.                   |
| `t11-midi-bank-128.xy`                         | M1 param 2 → bank **128**.                 |
| `t11-midi-program-off.xy`                      | M1 param 3 → program **off**. = default    |
| `t11-midi-program-001.xy`                      | M1 param 3 → program **1**.                |
| `t11-midi-program-128.xy`                      | M1 param 3 → program **128**.              |


## Capture procedure — M2 (CC map, 8 fields)

Slot numbering follows M2 param order (param 1 … param 4, each with shift variant).


| PC filename               | Procedure                                                                                    |
| ------------------------- | -------------------------------------------------------------------------------------------- |
| `t11-midi-cc1-num-074.xy` | Slot 1 **param** → CC **74**. impossible without shift+param1 not off. so that is set to 0.  |
| `t11-midi-cc1-msg-001.xy` | Slot 1 **shift+param** → message **1** (not off).                                            |
| `t11-midi-cc2-num-010.xy` | Slot 2 **param** → CC **10**. impossible without shift+param2 not off. so that is set to 0.  |
| `t11-midi-cc2-msg-off.xy` | Slot 2 **shift+param** → **off**. = default                                                  |
| `t11-midi-cc3-num-127.xy` | Slot 3 **param** → CC **127**. impossible without shift+param3 not off. so that is set to 0. |
| `t11-midi-cc3-msg-127.xy` | Slot 3 **shift+param** → message **127**.                                                    |
| `t11-midi-cc4-num-000.xy` | Slot 4 **param** → CC **0**. impossible without shift+param4 not off. so that is set to 0.   |
| `t11-midi-cc4-msg-074.xy` | Slot 4 **shift+param** → message **74**.                                                     |


## Capture procedure — sequencer (optional)


| PC filename              | Procedure                                                   |
| ------------------------ | ----------------------------------------------------------- |
| `t11-midi-note-step1.xy` | One note on step **1** (confirm generic note vector). Save. |


---

## Analysis Results

Device-returned captures, 2026-06-15:

- T11 M1 fields are in the common aux/engine parameter word area:
  - channel: T11 `+0x3857`, 16 buckets; UI channel = bucket index + 1.
  - bank: T11 `+0x385B`, 129 buckets; bucket 0 = off, buckets 1-128 = bank.
  - program: T11 `+0x385F`, 129 buckets; bucket 0 = off, buckets 1-128 = program.
- `t11-midi-channel-01.xy` is misnamed: the procedure changed channel **2**
  from the channel-1 default. It encodes bucket index 1 (`0x09FFFFFD`).
- M1 anchor raws:

| Capture | Field | Raw | Bucket |
| --- | --- | ---: | ---: |
| `t11-midi-channel-01.xy` | channel | `0x09FFFFFD` | 1 = channel 2 |
| `t11-midi-channel-16.xy` | channel | `0x7DFFFFE0` | 15 = channel 16 |
| `t11-midi-bank-001.xy` | bank | `0x017D05F4` | 1 |
| `t11-midi-bank-128.xy` | bank | `0x7F80FDFC` | 128 |
| `t11-midi-program-001.xy` | program | `0x017D05F4` | 1 |
| `t11-midi-program-128.xy` | program | `0x7F80FDFC` | 128 |

Bucket index hypothesis that matches the device-authored detents:

```text
index = floor(raw * bucket_count / 0x80000000)
```

This is **hypothesized only**. It is correct for the returned device-authored
captures in this directory, but should not be used as a boundary-safe decoder
or PC authoring rule until PC-generated boundary fixtures are verified on
device. Brain key/scale probes already showed that detent-fitting formulas can
put bucket boundaries in the wrong place.

### CC map result: table located, ownership still partial

M2/M3 CC assignment changes are localized to T11 `+0x3877..+0x3896`
(eight u32 words). The returned files prove the table location and show
bucket-readable values, but the current set does **not** cleanly prove which
word owns every "CC number" vs "CC message" field. Some captures necessarily
changed both number and message state.

| Capture | Offset | Raw | Bucket interpretation |
| --- | ---: | ---: | --- |
| `t11-midi-cc1-num-074.xy` | `+0x3877` | `0x4A2AAA5F` | 128-bucket index 74 |
| `t11-midi-cc1-msg-001.xy` | `+0x3877` | `0x012AAAA8` | 129-bucket index 1 |
| `t11-midi-cc2-num-010.xy` | `+0x387B` | `0x0A2AAA9D` | 128-bucket index 10 |
| `t11-midi-cc3-msg-127.xy` | `+0x387F` | `0x7F7FFF7A` | 129-bucket index 128 |
| `t11-midi-cc3-num-127.xy` | `+0x388F` | `0x7F7FFF80` | 128-bucket index 127 |
| `t11-midi-cc4-msg-074.xy` | `+0x3893` | `0x4A7FFFB5` | 128-bucket index 74 |

`t11-midi-note-step1.xy` still matches the baseline byte-for-byte, so it was
not captured yet and does not confirm T11 note sequencing.

Known non-semantic save noise: T9-T16 `+0x38F2/+0x38F6` (`0x00 -> 0x40`).
T11 edited captures also clear T11 `+0x11` (`0x08 -> 0x00`).
