# 2026-06 T14 Tape Probe Plan

> **Status:** todo · Firmware **1.1.4**
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
| `t14-tape-pitch-x01.xy` | M1 param 1 → pitch **×1**. |
| `t14-tape-pitch-x10.xy` | M1 param 1 → pitch **×10**. |
| `t14-tape-speed-050.xy` | M1 param 2 → speed **50%**. |
| `t14-tape-speed-200.xy` | M1 param 2 → speed **200%**. |
| `t14-tape-length-01.xy` | M1 param 3 → length **1**. |
| `t14-tape-length-10.xy` | M1 param 3 → length **10**. |
| `t14-tape-mix-00.xy` | M1 param 4 → mix **0**. |
| `t14-tape-mix-99.xy` | M1 param 4 → mix **99**. |

## Capture procedure — M2 (sends)

| PC filename | Procedure |
| --- | --- |
| `t14-tape-send-t1-99.xy` | M2: T1 send → **99**. |
| `t14-tape-send-t2-99.xy` | M2: T2 send → **99**. |
| `t14-tape-send-t3-99.xy` | M2: T3 send → **99**. |
| `t14-tape-send-t4-99.xy` | M2: T4 send → **99**. |
| `t14-tape-send-t5-99.xy` | M2: T5 send → **99**. |
| `t14-tape-send-t6-99.xy` | M2: T6 send → **99**. |
| `t14-tape-send-t7-99.xy` | M2: T7 send → **99**. |
| `t14-tape-send-t8-99.xy` | M2: T8 send → **99**. |

---

## Analysis Results

_(append after MTP back)_
