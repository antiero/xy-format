# 2026-06-13 — Bar menu inspection

Fixture pack: `src/bar-menu-probes/2026-06-bar-menu/`

Firmware 1.1.4 probe pack targeting checklist §4 bar-menu gaps for Scene 1,
Track 1, Pattern 1.

## Decoded fields

| Field | Track offset | Encoding | Fixtures |
| --- | --- | --- | --- |
| Default step length | `+0x02` | u16 LE ticks; baseline `240` (UI 50), min capture `4`, max `480`; one detent near center = 4 ticks | `bar-l-*` |
| Quantization | `+0x07` | raw byte; baseline/max `0xFF`, min `0x00`, near-min `0x04`/`0x07`, near-max `0xFE`/`0xFC`; full UI scaling partial | `bar-q-*` |
| Per-track groove override | `+0x08` | raw signed/LUT byte; baseline `0`, limited sweep only | `bar-g*` |
| P-lock interpolation/shape | `+0x3056` | raw byte; default/min `0x00`, min+1/+2 `0x04`/`0x08`, max-side `0xF7`/`0xFB`/`0xFF` | `bar-s-*` |

Most quantization, length, and groove edits also clear the T1 pristine flag at
`+0x11` (`08 00 -> 00 00`). Shape edits do not in this pack.

## Notes

`bar-q-max.xy` is anomalous: quantization is already max/default in `bar0`, and
the capture changes length to `244` ticks while leaving quantization `0xFF`.
Tests keep this as an explicit anomaly.

`bar-gp002.xy` is also suspicious: it stores `0x09`, same as `bar-gp007.xy`,
while `bar-gp004.xy` stores `0x06`. Treat the groove UI-to-raw table as partial
until a full or repeated LUT pass lands.

These fields overlap the old track-signature bytes used by the historical
scanner. `xy/bar_menu_inspection.py` reads the baseline-shape BAR pack by
canonical decoded-image base/stride instead of signature scanning.

## Code

- Read API: `xy/bar_menu_inspection.py`
- Writer raw setters: `ImageProject.set_default_step_length_ticks`,
  `set_track_quantization_raw`, `set_track_groove_raw`, `set_plock_shape_raw`
- Human report: `[Bar Menu]` in `tools/inspect_xy.py`
- Tests: `tests/test_bar_menu_inspection.py`
