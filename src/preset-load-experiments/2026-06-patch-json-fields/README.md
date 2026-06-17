# 2026-06 patch.json field preset-load experiment

Status: captured and analyzed
Firmware target: OP-XY 1.1.4

## Goal

These fixtures test fields where direct project editing, device-authored preset
loads, and current docs do not fully agree yet. Each case has:

- `presets/<case>.preset/patch.json`
- `presetprojs/<case>.xy`

The `.preset` folders are intentionally committed without duplicate WAV files.
The shared sample asset lives at `src/preset-load-experiments/assets/probe.wav`.
Before copying this experiment to the OP-XY, populate the preset folders:

```powershell
python tools/populate_preset_wavs.py src/preset-load-experiments/2026-06-patch-json-fields/presets
```

The `.xy` files are baseline project copies. On device, open the matching
project, load the matching preset onto track 1, save, then copy the saved
project back over `presetprojs/<case>.xy`.

## Analysis summary

Run the analyzer with:

```powershell
python tools/analysis/analyze_patch_json_field_experiment.py
```

Captured projects are in `presetprojs/`. Three baseline-identical captures were
removed because they did not contain useful preset-load evidence:

- `sfld-gain64-revtrue-tune4.xy`
- `slt-enabled-true-onrelease-false.xy`
- `slt-enabled-true-onrelease-true.xy`

`dpm-num-0.xy` is also excluded from conclusions because the saved preset label
inside the project is `presets/dpm-num-2`, not `presets/dpm-num-0`.

Confirmed findings:

- Drum `regions[].playmode` string labels load as `gate=0`, `key=1`,
  `oneshot=1`, `group=2`, `loop=3`.
- Drum numeric `playmode` values `1..4` did not pass through as raw slot bytes;
  they all loaded as byte `1`.
- Sampler `loop.crossfade` uses single-precision float normalization:
  `int(float32(loop.crossfade * 0x80000000 / framecount))`, clamped to
  `0x7FFFFFFF`.
- Sampler `pitch.keycenter` drives slot `+0x00`; `hikey` and `lokey` did not
  drive that byte in conflict probes.
- Sampler patch `tune` is cents and writes slot `+0x04` as a signed byte
  (`4 -> +0.04`, `-5 -> -0.05`), distinct from the direct sample-edit tune UI
  encoding.
- Sampler patch `loop.enabled=false` sets bit `0x40`; `loop.onrelease=true`
  sets bit `0x80`. These are patch-load bits, not direct sampler-edit labels.
- Sampler `gain` and `reverse` write slot `+0x05` and `+0x07`.

## Original gaps

### Drum region `playmode`

Known:

- The preset corpus confirms `patch.json` `regions[].playmode = "oneshot"`
  stores byte `1` at drum slot `+0x03`.
- `cap_drum_params.xy` confirms byte `3` is writable at the same slot, but
  does not pin its UI label.

Gap:

- The labels for bytes `0`, `2`, `3`, and `4` are not confirmed by preset-load
  evidence.
- A previous doc table claimed `oneshot=0`, `group=1`, `loop=2`, `gate=3`, but
  that conflicts with current corpus evidence and adapter code.

Cases:

- `dpm-str-oneshot`
- `dpm-str-key`
- `dpm-str-group`
- `dpm-str-loop`
- `dpm-str-gate`
- `dpm-num-0` through `dpm-num-4`

Result:

- String labels are confirmed as above.
- Numeric values are not preserved as raw project bytes by device preset
  loading, so the patch.json adapter rejects them rather than presenting a
  misleading raw passthrough.

### Sampler loop type

Known:

- Direct sampler edit probes map loop type bytes in the slot.
- Existing preset corpus has weak variation around `loop.enabled` and
  `loop.onrelease`.

Gap:

- The patch.json preset-load mapping for `loop.enabled` and `loop.onrelease`
  is not fully confirmed.

Cases:

- `slt-enabled-false`
- `slt-enabled-true-onrelease-true`
- `slt-enabled-true-onrelease-false`
- `slt-missing-enabled`
- `slt-missing-onrelease`

Result:

- Device preset loading composes bits: `0x40` for `loop.enabled=false` and
  `0x80` for `loop.onrelease=true`. Existing direct edit labels remain useful
  for the sampler edit screen, but they should not be treated as patch.json
  field names.

### Sampler loop crossfade

Known:

- Upstream and project-state probes show raw u32 crossfade at `track+0x3953`.
- One strong point exists: `loop.crossfade=2048`, `framecount=98807` loads as
  raw `0x02A73100`.

Gap:

- More points are needed to confirm rounding and boundary behavior.

Cases:

- `scf-00000`
- `scf-00001`
- `scf-02048`
- `scf-24702`
- `scf-49404`
- `scf-74105`
- `scf-98806`
- `scf-98807`

Result:

- Ceiling/floor integer math was wrong. The captured raw u32 values match a
  single-precision float calculation followed by integer truncation and max
  clamp.

### Sampler root/key fields

Known:

- The preset corpus usually has `hikey == pitch.keycenter`.
- The loaded sampler root/key byte is at sampler slot `+0x00`.
- `lokey` is constant or ignored in current corpus.

Gap:

- Which JSON key controls slot `+0x00` when `hikey` and `pitch.keycenter`
  disagree.

Cases:

- `skey-hikey-64`
- `skey-pitch-64`
- `skey-both-64`
- `skey-lokey-12`
- `skey-conflict-h72-p48`
- `skey-conflict-h48-p72`

Result:

- `pitch.keycenter` drives the root/key byte. `hikey` and `lokey` did not affect
  it in conflict probes.

### Sampler tune/gain/reverse

Known:

- Direct sampler edit probes map tune, gain, and direction bytes.
- Current preset corpus has weak variation: especially `tune=0` and
  `reverse=false`.

Gap:

- Whether patch.json preset loading uses the same storage bytes as direct
  sampler edits for these fields.

Cases:

- `sfld-tune-neg5`
- `sfld-tune-pos4`
- `sfld-gain-001`
- `sfld-gain-064`
- `sfld-gain-127`
- `sfld-reverse-false`
- `sfld-reverse-true`
- `sfld-gain64-revtrue-tune4`

Result:

- `gain` and `reverse` match the direct slot bytes.
- Patch `tune` does not use the direct sample-edit tune-tenths encoder; it is
  stored as signed cents at slot `+0x04`.

## Capture procedure

For each case:

1. Run `tools/populate_preset_wavs.py` if the preset folders do not contain
   `probe.wav` yet.
2. Copy or sync this experiment folder to the OP-XY storage.
3. Open `presetprojs/<case>.xy`.
4. On track 1, load `presets/<case>.preset`.
5. Save the project.
6. Copy the saved project back over `presetprojs/<case>.xy`.

If a preset fails to load, leave the project unchanged and note the case name.
That is useful evidence too.

## Generated manifest

`manifest.json` lists every case with its short question. It is intended for
the follow-up analyzer after device captures are copied back.
