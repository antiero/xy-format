# 2026-06 Aux LFO Probe Plan (M4, T9–T16)

> **Status:** todo · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`

## What this is

LFO on **M4** uses the **value LFO engine** with aux-specific destination
options. Layout is shared across **all eight aux tracks** (T9–T16) at the same
track-relative M4 offsets — probe on **T13** for generic fields; **T11** for
MIDI-only destinations.

| Param | Function |
| --- | --- |
| **Param 1** | **Speed** — first 8 discrete steps, then a continuous-looking range (encoder buckets). |
| **Param 2** | **Amount** — −max … **0** … +max (default 0). |
| **Param 3** | **Destination** — see table below. |
| **Param 4** | **Param-dest** — which M1 param (1–4) the LFO modulates. |

### Param 3 destinations by track

| Tracks | Destinations shown (many are UI-dead on that track) |
| --- | --- |
| T9 Brain, T10 Punch, T12 CV | syn, filter, amp (mostly useless here) |
| **T11 External MIDI** | **off, cc1, cc2** — only useful set; probe on T11 |
| T13–T16 | syn, filter, amp |

**Goal:** speed/amount/dest/param-dest encoding on T13; T11 cc1/cc2 dest enum.

## Scope

- **Generic LFO:** Track **13**, Scene 1.
- **MIDI LFO dest:** Track **11**, Scene 1.

## Rules

1. One M4 param change per capture → **Save**.
2. Re-copy baseline before each row.
3. Leave M1–M3 untouched during LFO captures.

---

## Capture procedure — generic (T13)

| PC filename | Procedure |
| --- | --- |
| `aux-lfo-baseline.xy` | T13. M4 LFO factory default (amount **0**). Save. |
| `aux-lfo-speed-min.xy` | M4 param 1 → **slowest** speed. |
| `aux-lfo-speed-max.xy` | M4 param 1 → **fastest** speed. |
| `aux-lfo-speed-discrete-3.xy` | M4 param 1 → **3rd** discrete speed step (if distinct from min). |
| `aux-lfo-amount-min.xy` | M4 param 2 → **−max**. |
| `aux-lfo-amount-zero.xy` | M4 param 2 → **0** (explicit center). |
| `aux-lfo-amount-max.xy` | M4 param 2 → **+max**. |
| `aux-lfo-dest-syn.xy` | M4 param 3 → **syn** (encoding only). |
| `aux-lfo-dest-filter.xy` | M4 param 3 → **filter**. |
| `aux-lfo-dest-amp.xy` | M4 param 3 → **amp**. |
| `aux-lfo-param-dest-1.xy` | M4 param 4 → mod target **1**. |
| `aux-lfo-param-dest-2.xy` | M4 param 4 → mod target **2**. |
| `aux-lfo-param-dest-3.xy` | M4 param 4 → mod target **3**. |
| `aux-lfo-param-dest-4.xy` | M4 param 4 → mod target **4**. |

## Capture procedure — T11 MIDI destinations

Use `../2026-06-t11-external-midi/t11-external-midi-baseline.xy` as starting
copy; save into **this** folder with names below.

| PC filename | Procedure |
| --- | --- |
| `aux-lfo-t11-dest-off.xy` | T11 M4 param 3 → **off**. |
| `aux-lfo-t11-dest-cc1.xy` | T11 M4 param 3 → **cc1**. |
| `aux-lfo-t11-dest-cc2.xy` | T11 M4 param 3 → **cc2**. |

---

## Analysis Results

Decoded against `aux-lfo-baseline.xy` with firmware 1.1.4 captures.

### Common write side effects

Edited LFO captures set the current track's edited-state byte at `+0x0011`
from `0x08` to `0x00`, enable the LFO block at `+0x0020` (`0x00` -> `0x01`
in the first byte of the word), and show the usual aux save side effects at
`+0x38F2` and `+0x38F6` (`0x00000040`).

`aux-lfo-speed-discrete-3.xy` is byte-identical to `aux-lfo-baseline.xy`; no
returned capture was produced for that detent.

### Generic T13 LFO fields

These words are track-relative and should apply to all aux tracks that expose
the generic `syn`/`filter`/`amp` LFO destination set.

| UI field | Offset | Baseline/default | Observed captures |
| --- | ---: | ---: | --- |
| Speed | `+0x38B7` | `0x40000000` | min/default `0x40000000`, max `0x7FFFFFFF` |
| Amount | `+0x38BB` | `0x40000000` | min `0x00000000`, zero `0x40000000`, max `0x7FFFFFFF` |
| Destination | `+0x38BF` | `0x00000000` | syn `0x00000000`, filter `0x4AAAAAA9`, amp `0x75555553` |
| Param-dest | `+0x38C3` | `0x00000000` | param 1 `0x07FFFFFF`, param 2 `0x27FFFFFD`, param 3 `0x47FFFFFB`, param 4 `0x77FFFFF8` |

The destination and param-dest values are confirmed for these device-authored
detents only. Treat any bucket/boundary formula as hypothesized until
PC-generated boundary probes have been verified on-device.

`aux-lfo-param-dest-3.xy` also changed destination `+0x38BF` to `0x0AAAAAAA`.
That is recorded as capture co-change/jitter rather than evidence for a fourth
generic destination.

### T11 External MIDI destination variant

T11 uses the same destination word (`+0x38BF`) for its MIDI-only destination
set:

| UI value | Offset | Raw |
| --- | ---: | ---: |
| off | `+0x38BF` | `0x00000000` |
| cc1 | `+0x38BF` | `0x3AAAAAA7` |
| cc2 | `+0x38BF` | `0x7AAAAAA3` |

The `cc1` capture also changed the neighboring amount-like word at `+0x38BB`
to `0x028F5E00`; keep that as a capture note until isolated by a one-control
follow-up.
