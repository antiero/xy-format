# M3 — Drum pan vs fade fixtures

> **Status:** captured

6 files. T1 drum `pp`, voice **23** (low F kick, key 53).

| File | Change |
| --- | --- |
| `d0-baseline-pp.xy` | baseline |
| `d1-v23-pan-hard-left.xy` | pan −100 @ v23 `+0x06` |
| `d2-v23-pan-hard-right.xy` | pan +100 @ v23 `+0x06` |
| `d3-v23-fade-99.xy` | fade UI 99 → v22 `+0x7C` |
| `d3-v23-fade-27.xy` | fade UI 27 |
| `d3-v23-fade-63.xy` | fade UI 63 |

Log: `docs/logs/2026-06-12_drum_pan_fade_inspection.md`  
Tests: `tests/test_drum_pan_fade_inspection.py`
