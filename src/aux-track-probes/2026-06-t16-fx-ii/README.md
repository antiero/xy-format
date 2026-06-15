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
| `t16-fx-ii-delay-p2-mid.xy` | Delay: param 2 → mid. |
| `t16-fx-ii-delay-p3-mid.xy` | Delay: param 3 → mid. |
| `t16-fx-ii-delay-p4-mid.xy` | Delay: param 4 → mid. |

## Capture procedure — M2 (sends)

| PC filename | Procedure |
| --- | --- |
| `t16-fx-ii-send-t1-99.xy` | M2: T1 send → **99**. |

---

## Analysis Results

_(append after MTP back)_
