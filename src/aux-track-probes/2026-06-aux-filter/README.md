# 2026-06 Aux Filter Probe Plan (M3, T13–T16)

> **Status:** todo · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`
> **Probe vehicle:** Track **13** (External Audio) — same M3 filter on T14–T16.

## What this is

Filter on **M3** is **identical** on aux tracks **5–8** (T13 External Audio,
T14 Tape, T15 FX I, T16 FX II). Probe once; encoding should match at the same
track-relative offsets on all four tracks.

| Param | Function |
| --- | --- |
| **Param 1** | **High pass** — active control. |
| **Param 2** | No effect (ignore). |
| **Param 3** | No effect (ignore). |
| **Param 4** | **Low pass** — active control. |

**Goal:** locate HPF (param 1) and LPF (param 4) storage; confirm params 2/3
are inert.

## Scope

Scene **1**, Track **13** unless cross-checking T15/T16 after decode.

## Rules

1. Re-copy baseline before each row; one M3 control change → **Save**.
2. Do not touch M4 (LFO pack) or unrelated M1/M2 fields.

---

## Capture procedure

| PC filename | Procedure |
| --- | --- |
| `aux-filter-baseline.xy` | T13. M3 filter at factory default. Save. |
| `aux-filter-hpf-min.xy` | M3 param 1 (HPF) → **minimum**. |
| `aux-filter-hpf-max.xy` | M3 param 1 (HPF) → **maximum**. |
| `aux-filter-lpf-min.xy` | M3 param 4 (LPF) → **minimum**. |
| `aux-filter-lpf-max.xy` | M3 param 4 (LPF) → **maximum**. |
| `aux-filter-p2-mid.xy` | M3 param 2 → mid (expect **no** meaningful filter change vs baseline). |
| `aux-filter-p3-mid.xy` | M3 param 3 → mid (expect **no** meaningful filter change). |

Optional cross-check after decode: repeat `aux-filter-hpf-max.xy` capture on
**T15** or **T16** to confirm same offset layout.

---

## Analysis Results

Decoded against `aux-filter-baseline.xy` with firmware 1.1.4 captures.

### Common write side effects

Every edited capture sets the current track's edited-state byte at `+0x0011`
from `0x08` to `0x00`, turns on the filter block at `+0x0025`
(`0x00000000` -> `0x00000001`), and shows the usual aux save side effects at
`+0x38F2` and `+0x38F6` (`0x00000040`).

### T13 M3 filter fields

These are track-relative offsets. T13 was used as the vehicle track; the same
M3 layout is expected on T14–T16.

| UI field | Offset | Baseline/default | Observed captures |
| --- | ---: | ---: | --- |
| Param 1 / HPF | `+0x3897` | `0x00000000` | min/default `0x00000000`, max `0x7FFFFFFF` |
| Param 2 | `+0x389B` | `0x00000000` | mid `0x7C28F2FF` |
| Param 3 | `+0x389F` | `0x00000000` | mid `0x3570CA40` |
| Param 4 / LPF | `+0x38A3` | `0x7FFFFFFF` | min `0x00000000`, max/default `0x7FFFFFFF` |

Param 2 and Param 3 were expected to be inert from the UI description, but the
device does persist raw words for them. Their audio/semantic effect remains
unknown.

`aux-filter-lpf-min.xy` also changed Param 2 (`+0x389B`) to `0x0147AF00`.
Treat that as a capture co-change until a follow-up isolates LPF-min from
nearby encoder movement.
