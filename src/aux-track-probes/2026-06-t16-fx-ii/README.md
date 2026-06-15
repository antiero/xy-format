# 2026-06 T16 FX II Probe Plan

> **Status:** todo · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`

## What T16 actually is

Track 16 (FX II) mirrors FX I (T15): effect type + four M1 params, M2 sends,
shared filter/LFO on M3/M4.

| Page | Controls |
| --- | --- |
| **M1** | Effect type + 4 params (per-effect detail deferred). |
| **M2** | T1–T8 send levels, each 0–99. |
| **M3** | Filter — see `../2026-06-aux-filter/`. |
| **M4** | LFO — see `../2026-06-aux-lfo/`. |

**Goal (this pass):** FX II **type enum** + param layout on **delay**, compared
against T15.

## Scope

Scene **1**, Track **16**. Re-copy baseline before each row.

## Rules

Same as T15. Do not mix scene/song edits into FX captures.

---

## Capture procedure — M1 type enum

| PC filename | Procedure |
| --- | --- |
| `t16-fx-ii-baseline.xy` | T16. Factory default. Save. |
| `t16-fx-ii-type-chorus.xy` | M1 → **chorus**. |
| `t16-fx-ii-type-delay.xy` | M1 → **delay**. |
| `t16-fx-ii-type-distortion.xy` | M1 → **distortion**. |
| `t16-fx-ii-type-lofi.xy` | M1 → **lofi**. |
| `t16-fx-ii-type-phaser.xy` | M1 → **phaser**. |
| `t16-fx-ii-type-reverb.xy` | M1 → **reverb**. |

## Capture procedure — M1 params (delay only)

| PC filename | Procedure |
| --- | --- |
| `t16-fx-ii-delay-p1-min.xy` | Delay: param 1 → **min**. |
| `t16-fx-ii-delay-p1-max.xy` | Delay: param 1 → **max**. |
| `t16-fx-ii-delay-p2-mid.xy` | Delay: param 2 → mid (near max). |
| `t16-fx-ii-delay-p3-mid.xy` | Delay: param 3 → mid (near max). |
| `t16-fx-ii-delay-p4-mid.xy` | Delay: param 4 → mid (near min). |

## Capture procedure — M2 (sends)

| PC filename | Procedure |
| --- | --- |
| `t16-fx-ii-send-t1-99.xy` | M2: T1 send → **99**. |

---

## Analysis Results

Device-returned captures, 2026-06-15:

### Type enum

T16 FX II type is stored at track-relative `+0x14`, using the same type bytes
as T15 FX I.

| Capture | Type byte |
| --- | ---: |
| `t16-fx-ii-type-delay.xy` | `0x00` |
| `t16-fx-ii-baseline.xy` / `t16-fx-ii-type-reverb.xy` | `0x05` |
| `t16-fx-ii-type-chorus.xy` | `0x0C` |
| `t16-fx-ii-type-phaser.xy` | `0x0D` |
| `t16-fx-ii-type-distortion.xy` | `0x0E` |
| `t16-fx-ii-type-lofi.xy` | `0x0F` |

The baseline type is reverb; selecting reverb again only produced known aux
save noise.

### Delay parameter anchors

Delay M1 params use the usual four-word parameter block after selecting delay:

| Field | Offset | Capture |
| --- | ---: | ---: |
| Delay param 1 | T16 `+0x3857` | min `0x00000000`, max `0x7FFFFFFF` |
| Delay param 2 | T16 `+0x385B` | mid/near-max `0x6E149C00` |
| Delay param 3 | T16 `+0x385F` | mid/near-max `0x68F5E000` |
| Delay param 4 | T16 `+0x3863` | mid/near-min `0x11EA3600` |

Baseline reverb values:

```text
type=0x05, p1=0x5999999A, p2=0x00000000, p3=0x26666666, p4=0x7FFFFFFF
```

These are device-authored anchors. Exact per-effect labels and bucket/display
boundaries remain open.

### M2 send

FX II sends are stored on source tracks at track-relative `+0x38B3`, not in the
T16 struct. Baseline had T4-T7 nonzero:

```text
T1 00000000  T2 00000000  T3 00000000  T4 1EB80000
T5 33330000  T6 147A0000  T7 43FE0000  T8 00000000
```

`t16-fx-ii-send-t1-99.xy` sets T1 `+0x38B3` to `0x7FFFFFFF` and zeroes the
other T1-T8 FX II send words.

Known non-semantic save noise: T9-T16 `+0x38F2/+0x38F6` (`0x00 -> 0x40`).
Edited captures also clear the edited track's `+0x11` (`0x08 -> 0x00`).
