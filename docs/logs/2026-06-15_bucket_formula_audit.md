# 2026-06-15 Bucket Formula Audit

This pass separates three different levels of confidence:

1. **Boundary-confirmed** — PC-authored boundary/near-boundary files were
   loaded on device and matched the expected UI display.
2. **Detent-confirmed hypothesis** — device-authored knob detents decode with a
   simple formula, but PC-generated boundary files have not confirmed the true
   bucket edges.
3. **Display/scale approximation** — a byte or u32 is converted to a readable UI
   number, but the exact device boundary/display rounding is not proven.

## Boundary-confirmed

| Area | Formula | Evidence |
| --- | --- | --- |
| Bar quantization, track `+0x07` | `ui = floor(raw * 100 / 255)` | `src/bar-menu-probes/2026-06-quant-generated/` loaded on device; all listed raw files matched expected UI, including top-end boundary probes `0xFD -> 99`, `0xFE -> 99`, `0xFF -> 100`. |

Bar groove is also now decoded, but it is **not** a bucket formula: it uses the
handwritten UI sequence from device observations and stores adjacent sequence
indices as adjacent raw steps (`±3` raw increments, with endpoint behavior).

## Detent-confirmed hypotheses only

| Area | Current evidence | Status |
| --- | --- | --- |
| T9 Brain key (`+0x385B`) | Device-authored key detents fit a 12-bucket candidate mapping at mid-bucket values. | Provisional. Phase-A PC-generated edge probes falsified the naive `floor(raw*N/0x80000000)` boundary table; true boundaries remain in progress. |
| T9 Brain scale (`+0x385F`) | Device-authored scale detents fit a 7-bucket candidate mapping at mid-bucket values. | Provisional. Phase-A edge probes falsified naive boundaries; later phases are still validation data, not a closed writer rule. |
| T9 Brain link (`+0x3863`) | Field located from device-authored link captures. | Provisional. Treat as raw until boundary and enum ownership are isolated. |
| T11 External MIDI channel/bank/program (`+0x3857/+0x385B/+0x385F`) | Returned detents fit 16/129/129 bucket hypotheses. | Provisional. Needs PC-generated boundary probes before using as a boundary-safe decoder or writer rule. |
| T11 External MIDI CC table (`+0x3877..+0x3896`) | Table localized; returned words bucket-decode to named capture values. | Provisional. Exact word ownership and all bucket boundaries need cleaner captures/PC-gen validation. |

## Display/scale approximations, not discrete bucket proofs

These readers expose useful UI-ish numbers, but should not be described as
closed bucket-boundary decoders unless future PC-generated probes verify the
edges:

| Area | Current mapping | Notes |
| --- | --- | --- |
| Mixer/static and scene volume fields | high byte `0..0x7F`, UI via `round(byte * 100 / 0x7F)` | Device min/default/max anchors are known; exact display rounding for every boundary is not exhaustively proven. |
| Master saturator fields | same high-byte family, UI via `round(byte * 100 / 0x7F)` | Static reader approximation; not a discrete enum/bucket proof. |
| Master EQ bands | byte `0..0x7F`, UI via `round(byte * 100 / 0x7F)` | EQ max has known spill behavior into adjacent bytes; keep byte/u32 evidence explicit. |
| Drum sampler loop crossfade/fade | `0`, `0x7FFFFFFF`, otherwise `(u32 >> 8) // 0x0147AF` | Matches current M3 fade probes; boundary behavior between UI values is not PC-generated verified. |

## Future probe rule

For any u32 field that looks like a discrete encoder bucket, device-authored
detents are enough to label offsets and mid-bucket values, but not enough to
claim exact boundaries. Close those formulas with small PC-generated
near-boundary packs, named with expected UI values, before promoting them to
writer-safe rules.
