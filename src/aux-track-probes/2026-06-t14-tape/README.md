# 2026-06 T14 Tape Probe Plan

> **Status:** captured/analyzed · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`

## What T14 actually is

Track 14 (Tape) controls **tape playback parameters** and per-track sends.
Filter (M3) and LFO (M4) are shared aux layouts — out of scope here.

| Page | Controls |
| --- | --- |
| **M1** | Param 1: **pitch** ×1–×10 (discrete). Param 2: **speed** 50%–200% (every step, default **100%**). Param 3: **length** 1–10 (discrete). Param 4: **mix** 0–99. |
| **M2** | T1–T8 send levels, each 0–99. |
| **M3** | Filter — see `../2026-06-aux-filter/`. |
| **M4** | LFO — see `../2026-06-aux-lfo/`. |

There is **no** separate reverse/loop/slice transport UI in scope for this
pack — only the four M1 parameters above plus M2 sends.

**Goal:** isolate pitch, speed, length, mix, and send-level storage.

## Scope

Scene **1**, Track **14**. Re-copy baseline before each row.

## Rules

1. One control change per capture → **Save**.
2. Do not touch M3/M4.
3. M2 sends: one track at **99**, others default.

---

## Capture procedure — M1

| PC filename | Procedure |
| --- | --- |
| `t14-tape-baseline.xy` | T14. Factory defaults (speed **100%**). Save. |
| `t14-tape-pitch-x01.xy` | M1 param 1 → pitch **×1**. = default|
| `t14-tape-pitch-x10.xy` | M1 param 1 → pitch **×10**. |
| `t14-tape-speed-050.xy` | M1 param 2 → speed **50%**. |
| `t14-tape-speed-200.xy` | M1 param 2 → speed **200%**. |
| `t14-tape-length-01.xy` | M1 param 3 → length **1**. = default |
| `t14-tape-length-10.xy` | M1 param 3 → length **10**. |
| `t14-tape-mix-00.xy` | M1 param 4 → mix **0**. = default |
| `t14-tape-mix-99.xy` | M1 param 4 → mix **99**. |

## Capture procedure — M2 (sends)

| PC filename | Procedure |
| --- | --- |
| `t14-tape-send-t1-99.xy` | M2: T1 send → **99**. (others 0) |
| `t14-tape-send-t8-99.xy` | M2: T8 send → **99**. (others 0) |

default is ALL 99 (t1-t8).

We only do two probes since this likely is encoded the same as for t13 (and t15 and t16). More probes if this turns out not to be the case.

---

## Analysis Results

Device-returned captures, 2026-06-15:

### M1 fields

| UI field | Storage | Baseline | Captures |
| --- | ---: | ---: | --- |
| Pitch | T14 `+0x3857` | `0x00000000` = x1 | x10 `0x780A3037` |
| Speed | T14 `+0x385B` | `0x40000000` = 100% | 50% `0x00A237C3`, 200% `0x7FAE7C9F` |
| Length | T14 `+0x385F` | `0x00000000` = 1 | length 10 `0x5C05180F` |
| Mix | T14 `+0x3863` | `0x00000000` = 0 | mix 99 `0x7FAE7C9F` |

`t14-tape-pitch-x01.xy`, `t14-tape-length-01.xy`, and `t14-tape-mix-00.xy`
are byte-identical to baseline because those are defaults.

Note: `t14-tape-pitch-x10.xy` also nudged the speed word from `0x40000000` to
`0x3FFFFFE7`. Treat this as capture/detent jitter unless a follow-up proves
pitch x10 intentionally edits speed.

These are device-authored anchors; exact bucket/display boundaries are not
PC-generated verified.

### M2 sends

T14 Tape sends are stored on source tracks at track-relative `+0x38AB`, not in
the T14 struct. Baseline has every T1-T8 Tape send at `0x7FFFFFFF` (UI 99).

```text
t14-tape-send-t1-99.xy: T1=7FFFFFFF, T2-T8=00000000
t14-tape-send-t8-99.xy: T1-T7=00000000, T8=7FFFFFFF
```

Known non-semantic save noise: T9-T16 `+0x38F2/+0x38F6` (`0x00 -> 0x40`).
Edited captures also clear the edited track's `+0x11` (`0x08 -> 0x00`).
