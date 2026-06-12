# 2026-06-12 P2-A — Static mixer fields (f0–f15)

Fixtures: `src/app-mixer-probes/2026-06-static/` (partial; f16–f24 pending)  
Operator notes: `user_probes/2026-06-mixer-static/README.md`

Firmware 1.1.4. New project, T1 default engine, no p-locks, no pattern notes.

## Encoding pattern

Most mix knobs use a **4-byte LE u32** with the **high byte** (`u32_start+3`)
holding the level (`0x00` min … default … `0x7F` max). Max often sets the
preceding three bytes to `0xFF` (`u32 = 0x7FFFFFFF`).

## T1 track mix (track struct)

| Control | u32 @ | byte @ | f0 default | min capture | max capture |
| --- | --- | --- | --- | --- | --- |
| Volume | `+0x38FB` | `+0x38FE` | `0x60` | `f1` → `0x00` | `f2` → `0x7F` |
| Pan | `+0x38F7` | `+0x38FA` | `0x40` center | `f3` → `0x00` L | `f4` → `0x7F` R |
| Send FX I | `+0x38AF` | `+0x38B2` | `0x00` | `f7` (unchanged) | `f6` → `0x7F` |
| Send FX II | `+0x38B3` | `+0x38B6` | `0x00` | `f9` (unchanged) | `f8` → `0x7F` |

`f5` pan center: no change at pan bytes vs `f0`.

Volume field matches P2-D / scene probe offsets.

## Master (global header)

| Control | u32 @ | byte @ | f0 default | min | max |
| --- | --- | --- | --- | --- | --- |
| Percussion group | `0x85` | `0x88` | `0x40` | `f10` → `0x00` | `f11` → `0x7F` |
| Melody group | `0x89` | `0x8C` | `0x40` | `f12` → `0x00` | `f13` → `0x7F` |
| Compressor | `0x8D` | `0x90` | `0x0C` | `f14` → `0x00` | `f15` → `0x7F` |
| Master volume | `0x91` | `0x94` | `0x40` | *f16 pending* | *f17 pending* |

## Side effects (ignore for decode)

- `T1+0x11` pristine u16 `0x08` → `0x00` on most T1 mix edits.
- Visiting master/mix (M4) pages sets `T9..T16` `+0x38F2` and `+0x38F6` to
  `0x40` in many captures — UI-session bytes, not the knob under test.

## API

`xy/mixer_static_inspection.py` — `inspect_static_mixer_bytes`, per-track
`volume` / `pan` / `send_fx1` / `send_fx2`, plus master group fields.

Tests: `tests/test_mixer_static_inspection.py`

## Open (f16–f24)

- Master master volume `global+0x94` endpoints (`f16`/`f17`).
- Per-track confirmation on T2–T8 (`f18`–`f24`).
- Write API.
