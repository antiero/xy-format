# 2026-06 T10 Punch-in FX Probe Plan

> **Status:** todo · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`

## What T10 actually is

Track 10 (Punch-in FX) is a **sequencer track for punch triggers** — nothing
more. There are no punch-specific parameters to save.

- **M1 / M2 / M3** — visual-only screens (not stored settings).
- **M4** — standard LFO, encoded like every other track (out of scope here).
- **Octave** — locked at **+0**; the keyboard exposes two octaves of punch
  keys (lower row targets percussion tracks, upper row targets melodic tracks).
  That split is not a separate “mode” field.

**Goal:** confirm sequenced punch triggers use the generic note vector at T10
`track+0x456F`, same 12-byte note records as T1–T8 and Brain
(`t09-brain-seq-two-notes.xy`).

## Scope

Scene **1**, Track **10**, Pattern **1** only. Blank pattern on baseline.

## Rules

1. All three `.xy` files are identical copies of **`bar0.xy`** — ready for MTP
   as-is; re-copy from `bar0.xy` on PC before each capture row if you need a
   fresh baseline mid-session.
2. On device: open → change **one** thing → **Save** (overwrite).
3. Do the trigger captures from a fresh `bar0` copy each time (not from the
   already-saved baseline file).
4. Do not touch M4, bar menu, tempo, or other tracks.

---

## Capture procedure

| PC filename | Procedure |
| --- | --- |
| `t10-punch-in-fx-baseline.xy` | Select T10 / P1. Leave pattern **empty**. Save. |
| `t10-punch-trigger-step1.xy` | From baseline: enter step **1**, trigger **one** punch key from the **lower** octave (leftmost key is fine). Save. |
| `t10-punch-trigger-step9.xy` | From baseline: enter step **9**, trigger **one** punch key from the **upper** octave (leftmost key is fine). Save. |

Record the exact punch keys pressed in **Results** (for note-byte lookup after
decode).

---

## Analysis Results

Confirmed: Punch-in FX triggers are generic note-vector entries at T10
track-relative `+0x456F`.

| File | Count | Tick | Step | Gate | Note byte | Velocity | Flags |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `t10-punch-in-fx-baseline.xy` | 0 | - | - | - | - | - | - |
| `t10-punch-trigger-step1.xy` | 1 | 0 | 1 | 240 | 101 | 100 | `00 00` |
| `t10-punch-trigger-step9.xy` | 1 | 3840 | 9 | 240 | 101 | 100 | `00 00` |

This closes the basic T10 event-record format: punch triggers use the same
12-byte note record shape as generic track notes and T9 Brain notes. The
current captures do not yet map the full punch key range; both trigger captures
landed on note byte `101`.
