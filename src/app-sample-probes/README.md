# App sample probe fixtures

Device-authored `.xy` captures for read-only drum sample path inspection.

## `2026-06-sample-paths/`

Firmware 1.1.4. Track 1 drum kit preset `pp`. One voice sample assignment
changed per file from `c0-baseline.xy`.

| File | Changed voice | Sample path in struct |
| --- | --- | --- |
| `c0-baseline.xy` | — | factory `pp` kit defaults |
| `c1-v23-fx-a2-3.xy` | 23 | `/fat32/presets/fx/nt-z-fx.preset/unnamed-a2-3.wav` |
| `c2-v00-fx-a3-3.xy` | 0 | `/fat32/presets/fx/nt-z-fx.preset/unnamed-a3-3.wav` |
| `c3-v01-fx-b2-4.xy` | 1 | `/fat32/presets/fx/nt-z-fx.preset/unnamed-b2-4.wav` |

Capture procedure: `docs/logs/2026-06-12_drum_sample_path_inspection.md`.

**Note:** On-device filenames were `c0-1` … `c0-4`; voice 23 in `c1` was an
accidental pad selection during capture, not voice 0 as originally intended.
Tests lock the decoded paths above.
