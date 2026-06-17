# Patch.json field preset-load experiment

Firmware: OP-XY 1.1.4  
Fixtures: `src/preset-load-experiments/2026-06-patch-json-fields`

This experiment used generated `.preset/patch.json` folders plus matching
baseline projects. Each project was opened on device, the matching preset was
loaded onto T1, and the saved `.xy` was copied back for decoded-image analysis.

## Drum playmode

The string labels are now pinned for patch.json preset loading:

| patch.json `regions[0].playmode` | stored drum slot byte |
| --- | --- |
| `gate` | `0x00` |
| `key` | `0x01` |
| `oneshot` | `0x01` |
| `group` | `0x02` |
| `loop` | `0x03` |

Numeric playmode values are not raw passthrough for device preset loading:
`1`, `2`, `3`, and `4` all loaded as byte `0x01`. `dpm-num-0.xy` is excluded
because its saved preset label was `presets/dpm-num-2`.

## Sampler loop flags

Patch.json preset loading composes the sampler slot `+0x03` byte from fields:

| fields | stored byte |
| --- | --- |
| `loop.enabled` missing, `loop.onrelease` missing | `0x00` |
| `loop.onrelease=true` | `0x80` |
| `loop.enabled=false`, `loop.onrelease=true` | `0xC0` |

This should be treated as patch-load bit behavior. It is related to, but not
identical in meaning to, the direct sampler edit labels exposed by
`read_sampler_sample_edit()`.

## Sampler crossfade

The raw u32 at `track+0x3953` matches single-precision normalization:

```text
int(float32(loop.crossfade * 0x80000000 / framecount))
```

The max case clamps to `0x7FFFFFFF`. This matched all captured crossfade cases:
0, 1, 2048, 24702, 49404, 74105, 98806, and 98807 frames for a 98807-frame
sample.

## Sampler root, tune, gain, direction

Conflict probes show sampler `pitch.keycenter` drives slot `+0x00`; `hikey`
and `lokey` did not affect that byte when they disagreed with
`pitch.keycenter`.

Patch `tune` is cents and writes the slot `+0x04` byte as signed storage:
`4 -> +0.04` (`0x04`), `-5 -> -0.05` (`0xFB`). This is distinct from the
direct sampler edit tune UI encoder, which uses the paired `+0x00/+0x04`
representation.

Sampler `gain` and `reverse` match direct slot bytes: `gain` at `+0x05`,
direction at `+0x07` (`0=forward`, `1=backward`).

## Code changes

- `encode_sampler_loop_crossfade_frames()` now uses the captured float32
  calculation.
- `xy.patch_json` maps confirmed drum playmode strings and rejects numeric
  playmode values.
- `xy.patch_json` writes sampler `pitch.keycenter`, patch tune cents, loop flag
  bits, gain, and reverse using the confirmed preset-load mapping.
- `tests/test_patch_json_field_experiment.py` guards the conclusions directly
  against the device-captured fixtures.
