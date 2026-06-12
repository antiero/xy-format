# 2026-06-12 Mission 3 — Drum pan vs fade

Fixtures: `src/app-sample-probes/2026-06-drum-pan-fade/`  
Operator notes: `user_probes/2026-06-drum-pan-fade/README.md`

## Setup

- Firmware 1.1.4, T1 drum kit **`pp`**, no pattern notes.
- Pad edited: **leftmost low F / kick** → struct **voice 23**, MIDI key **53**.

## Pan (decoded)

| File | UI | Voice | Slot offset | Value |
| --- | --- | --- | --- | --- |
| `d0-baseline-pp.xy` | default | 23 | `+0x06` | 0 |
| `d1-v23-pan-hard-left.xy` | pan L | 23 | `+0x06` | **−100** (u8 `0x9C`) |
| `d2-v23-pan-hard-right.xy` | pan R | 23 | `+0x06` | **+100** (u8 `0x64`) |

Only voice 23 slot `+0x06` changes vs baseline. Slot `+0x05` stays 0.

`ImageProject.set_drum_voice(..., pan=±100)` reproduces the device byte at `+0x06`.

## Fade / loop-crossfade (decoded)

Fade UI edits on the **same pad (v23)** did **not** change bytes in the voice 23
slot. Each fade capture differs from baseline in **four bytes** at image
`0x524C..0x524F` = track `+0x44D3` = **voice 22 slot `+0x7C`** (u32).

| File | UI fade | u32 @ v22 `+0x7C` |
| --- | --- | --- |
| `d3-v23-fade-99.xy` | 99 (max) | `0x7FFFFFFF` |
| `d3-v23-fade-27.xy` | 27 | `0x23D6C7FF` |
| `d3-v23-fade-63.xy` | 63 | `0x51EB63FF` |

Encoding vs UI value is **not** a simple linear map yet. The field shares the
documented gain / loop-crossfade u32 offset (`+0x7C`) but the **voice index
pairing** (UI on v23 → storage on v22) needs more probes before write API.

## API updates

- `DrumVoiceSample.pan` — signed read @ `+0x06`
- `DrumVoiceSample.slot_gain_u32` — u32 @ `+0x7C`
- `set_drum_voice(..., pan=)` — write @ `+0x06`
- Tests: `tests/test_drum_pan_fade_inspection.py`

## Open

- Fade write path and voice-index rule (v23 UI → v22 `+0x7C`?).
- Whether `+0x05` is used on other kits / engines.
