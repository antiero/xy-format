# 2026-06 T12 External CV Probe Plan

> **Status:** todo · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`

## What T12 actually is

Track 12 (External CV) is a **sequencer track for CV/gate notes** — same idea
as Punch-in FX (T10), but **octave is not locked**.

- **M1 / M2 / M3** — visual-only (M3 shows current CV level from the **last
  played note**, independent of note length). Nothing stored beyond the sequence.
- **No** CV mode, gate polarity, or calibration parameters in the project file.
- **M4** — shared aux LFO — see `../2026-06-aux-lfo/`.

**Goal:** confirm CV notes encode like a regular sequencer track at T12
`track+0x456F` (compare T10 punch triggers and Brain sequence).

## Scope

Scene **1**, Track **12**, Pattern **1**. Blank pattern on baseline.

## Rules

1. Re-copy **`bar0.xy`** before each capture row.
2. One edit per file → **Save**.
3. Do not touch M4, bar menu, or other tracks.

---

## Capture procedure

| PC filename | Procedure |
| --- | --- |
| `t12-external-cv-baseline.xy` | T12 / P1. Leave pattern **empty**. Save. |
| `t12-cv-note-step1.xy` | Step **1**: one note (octave -2, lower F). Save. |
| `t12-cv-note-step9.xy` | Step **9**: one note (octave +0, lower F). Save. |

Record exact notes/octaves in **Results**.

---

## Analysis Results

Device-returned captures, 2026-06-15:

| Capture | Count | Tick | Step | Gate | Note | Velocity | Flags |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `t12-external-cv-baseline.xy` | 0 | — | — | — | — | — | — |
| `t12-cv-note-step1.xy` | 1 | 0 | 1 | 240 | 29 | 100 | `00 00` |
| `t12-cv-note-step9.xy` | 1 | 3840 | 9 | 240 | 53 | 100 | `00 00` |

Confirmed: T12 External CV uses the generic note vector at track-relative
`+0x456F`. The two octaves are stored as ordinary note bytes (`29` and `53`);
no CV-specific pitch side field changed before the note vector.

Known non-semantic save noise: T9-T16 `+0x38F2/+0x38F6` (`0x00 -> 0x40`).
T12 edited captures also clear T12 `+0x11` (`0x08 -> 0x00`).
