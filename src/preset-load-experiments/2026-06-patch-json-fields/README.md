# 2026-06 patch.json field preset-load experiment

Status: ready for device capture
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

## Current gaps

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

What closes:

- The loaded project byte at track 1 drum slot `+0x03` will tell us which string
  labels the firmware accepts, and which byte each accepted label stores.
- Numeric cases show whether numeric JSON passes through, is rejected, or is
  normalized by the device.

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

What closes:

- The loaded sampler slot `+0x03` byte will confirm whether the patch adapter's
  loop-type mapping matches device preset loading.

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

What closes:

- These cases test whether `loop.crossfade` is ceiling-normalized against
  `framecount`, and what happens at zero, tiny values, near-end, and full
  sample length.

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

What closes:

- These cases tell us whether `hikey`, `pitch.keycenter`, both, or neither
  drive the loaded sampler root/key byte.

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

What closes:

- The loaded sampler slot bytes should confirm whether the patch adapter can
  safely write these fields through the existing direct-edit writer.

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
