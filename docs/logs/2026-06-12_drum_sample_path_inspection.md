# 2026-06-12 Drum sample path inspection

App-driven probe for library-manager sample reference readout: which sample
path string is assigned to each of the 24 drum-sampler voices on a track.

AI-assisted analysis and implementation; claims are fixture-backed.

## Capture procedure (Mission 1)

Firmware 1.1.4. Track 1, drum preset `pp`, no pattern notes.

1. Save baseline `c0-baseline`.
2. For each variant, reopen baseline, change **one** drum voice sample, save as
   new file (do not chain variants).

On-device names were `c0-1` … `c0-4` for MTP ergonomics; renamed on PC to the
`src/app-sample-probes/2026-06-sample-paths/` names in the fixture README.

Operator notes recorded sample labels as `nt-z-fx/unnamed-a2-3` etc. Decoded
paths include the full `/fat32/presets/.../*.wav` string at drum slot +0x08.

## Findings

- Sample paths are **not** generic `/fat32/samples/...` loose files in these
  captures; assignments reference preset-nested wav paths such as
  `/fat32/presets/drum/pp.preset/unnamed-f#2-31.wav` and
  `/fat32/presets/fx/nt-z-fx.preset/unnamed-a3-3.wav`.
- Storage matches the device-decoded drum table: 24 × 128 B at track+0x3957,
  path at slot+0x08 (`docs/format/decoded_image_map.md`).
- Single-voice edits produce isolated diffs in exactly one slot (verified for
  voices 0, 1, and 23).
- **Capture correction:** `c1-v23-fx-a2-3.xy` changed voice **23**, not voice
  0 as the original field script intended. Tests use the decoded truth.

## Implementation

- `xy/drum_sample_inspection.py` reads paths from the decoded RAM image via
  `ImageProject` track struct bases (not scaffold logical-entry bodies).
- `tools/inspect_xy.py` prints `[Drum Samples]` for drum-engine tracks.
- Tests: `tests/test_drum_sample_inspection.py`.

## Open questions

- Read path for sampler / multisampler non-drum engines (different table layout).
- Whether standalone `/fat32/samples/...` paths appear when samples are picked
  outside preset folders (needs a follow-up probe).
