# 2026-06 T15 FX I Probe Plan

> **Status:** todo · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`

## What T15 actually is

Track 15 (FX I) is a **send effect bus** with effect-type-specific M1 params.

| Page | Controls |
| --- | --- |
| **M1** | Effect **type** + **4 params** (often 0–99; some effects bucketize differently — per-effect sweeps deferred). |
| **M2** | T1–T8 send levels, each 0–99. |
| **M3** | Filter — see `../2026-06-aux-filter/`. |
| **M4** | LFO — see `../2026-06-aux-lfo/`. |

**Goal (this pass):** pin the **effect type enum** and confirm param storage
layout for **one reference type** (delay). Full per-effect parameter LUTs come
later.

## Scope

Scene **1**, Track **15**. Re-copy baseline before each row.

## Rules

1. One change per capture → **Save**.
2. Param sweeps below use **delay** only — note the fixed type in Results.
3. Do not touch M3/M4.

---

## Capture procedure — M1 type enum

| PC filename | Procedure |
| --- | --- |
| `t15-fx-i-baseline.xy` | T15. Factory default effect. Save. |
| `t15-fx-i-type-chorus.xy` | M1 → effect **chorus**. |
| `t15-fx-i-type-delay.xy` | M1 → effect **delay**. |
| `t15-fx-i-type-distortion.xy` | M1 → effect **distortion**. |
| `t15-fx-i-type-lofi.xy` | M1 → effect **lofi**. |
| `t15-fx-i-type-phaser.xy` | M1 → effect **phaser**. |
| `t15-fx-i-type-reverb.xy` | M1 → effect **reverb**. |

## Capture procedure — M1 params (delay only)

Re-copy baseline, select **delay**, then change one param.

| PC filename | Procedure |
| --- | --- |
| `t15-fx-i-delay-p1-min.xy` | Delay: param 1 → **minimum**. |
| `t15-fx-i-delay-p1-max.xy` | Delay: param 1 → **maximum**. |
| `t15-fx-i-delay-p2-mid.xy` | Delay: param 2 → mid (near maximum). |
| `t15-fx-i-delay-p3-mid.xy` | Delay: param 3 → mid (near maximum). |
| `t15-fx-i-delay-p4-mid.xy` | Delay: param 4 → mid (near minimum). |

## Capture procedure — M2 (sends)

| PC filename | Procedure |
| --- | --- |
| `t15-fx-i-send-t1-99.xy` | M2: T1 send → **99** (others 0). |

_(Add `send-t2` … `send-t8` if the first send diff is ambiguous.)_

---

## Analysis Results

Device-returned captures, 2026-06-15:

### Type enum

T15 FX I type is stored at track-relative `+0x14`.

| Capture | Type byte |
| --- | ---: |
| `t15-fx-i-baseline.xy` / `t15-fx-i-type-delay.xy` | `0x00` |
| `t15-fx-i-type-reverb.xy` | `0x05` |
| `t15-fx-i-type-chorus.xy` | `0x0C` |
| `t15-fx-i-type-phaser.xy` | `0x0D` |
| `t15-fx-i-type-distortion.xy` | `0x0E` |
| `t15-fx-i-type-lofi.xy` | `0x0F` |

The baseline type is delay; selecting delay again only produced known aux save
noise.

### Delay parameter anchors

| Field | Offset | Baseline | Capture |
| --- | ---: | ---: | --- |
| Delay param 1 | T15 `+0x3857` | `0x53F7CED9` | min `0x00000000`, max `0x7FFFFFFF` |
| Delay param 2 | T15 `+0x385B` | `0x40000000` | mid/near-max `0x6CCCED00` |
| Delay param 3 | T15 `+0x385F` | `0x40000000` | mid/near-max `0x63D72400` |
| Delay param 4 | T15 `+0x3863` | `0x7FFFFFFF` | `t15-fx-i-delay-p4-mid.xy` was byte-identical to baseline |

These are device-authored anchors. Exact per-effect labels and bucket/display
boundaries remain open.

### M2 send

FX I sends are stored on source tracks at track-relative `+0x38AF`, not in the
T15 struct. Baseline had T5 and T7 nonzero:

```text
T1 00000000  T2 00000000  T3 00000000  T4 00000000
T5 0F5C0000  T6 00000000  T7 57FF0000  T8 00000000
```

`t15-fx-i-send-t1-99.xy` sets T1 `+0x38AF` to `0x7FFFFFFF` and zeroes the
other T1-T8 FX I send words.

Known non-semantic save noise: T9-T16 `+0x38F2/+0x38F6` (`0x00 -> 0x40`).
Edited captures also clear the edited track's `+0x11` (`0x08 -> 0x00`).
