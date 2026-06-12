# P2-A — Static mixer fixtures

> **Status:** partial (f0–f15 captured, f16–f24 pending)

**Operator capture plan (f16–f24):**
[`user_probes/2026-06-mixer-static/README.md`](../../../../user_probes/2026-06-mixer-static/README.md)

| File | Field |
| --- | --- |
| `f0-baseline-mix-default.xy` | defaults |
| `f1`/`f2` | T1 volume min/max @ `+0x38FE` |
| `f3`–`f5` | T1 pan L/R/center @ `+0x38FA` |
| `f6`–`f9` | T1 send FX1/FX2 @ `+0x38B2` / `+0x38B6` |
| `f10`–`f15` | master perc/melody/comp @ global `+0x88`/`+0x8C`/`+0x90` |
| `f16`–`f24` | *pending* — see operator README |

Log: `docs/logs/2026-06-12_mixer_static_inspection.md`  
Tests: `tests/test_mixer_static_inspection.py`  
API: `xy/mixer_static_inspection.py`
