# patch.json adapter coverage

OP-XY `.preset` folders store a `patch.json` file next to their audio files.
This document lists the fields currently known from device presets and
OP-PatchStudio-style generated presets, and whether `xy.patch_json` can write
them into a decoded `.xy` project image.

## Top-level fields

| Field | Meaning | `.xy` write status |
| --- | --- | --- |
| `platform` | Preset platform marker, observed as `OP-XY`. | Ignored; not project sound state. |
| `version` | patch schema version, observed as `4`. | Ignored; not project sound state. |
| `name` | Preset display/export name. | Ignored; project stores short preset identity separately. |
| `type` | Preset engine family such as `drum`, `sampler`, `axis`, etc. | `drum` and `sampler` are writable; other types are rejected. |
| `octave` | Track keyboard octave. | Confirmed readable for T1 at decoded-image `0x003D` as a signed byte; manual device testing shows this is track-global, not pattern-local. The adapter does not write it yet. |
| `engine` | Engine-level settings and params. | Confirmed common lanes are written for supported sound patches; see below. |
| `envelope` | Amp/filter envelope blocks. | Confirmed amp/filter ADSR lanes are written for supported sound patches. |
| `fx` | Preset-local FX state. | Confirmed type/active/params lanes are written for supported sound patches; `params[5]` serializes as max. |
| `lfo` | Preset-local LFO state. | Confirmed type/active/params lanes are written for supported sound patches. |
| `regions` | Sample-region list. | Source for writable drum and one-shot sampler fields. |

## Common engine fields

Known `engine` keys include:

```text
bendrange
highpass
playmode
transpose
volume
width
velocity.sensitivity
portamento.amount
portamento.type
tuning.root
tuning.scale
params
modulation.aftertouch.amount
modulation.aftertouch.target
modulation.modwheel.amount
modulation.modwheel.target
modulation.pitchbend.amount
modulation.pitchbend.target
modulation.velocity.amount
modulation.velocity.target
```

The adapter writes the confirmed common project-image lanes when applying a
supported drum or sampler patch. This does **not** make synth-engine preset
loading complete: unsupported preset types still need opaque engine tails and
engine-specific state that are not safely synthesized from `patch.json`.

| Field | `.xy` write status |
| --- | --- |
| `type` | Written as the engine byte at `track+0x14` for known engine families. |
| `engine.params[0..7]` | Written as q16 words at `track+0x3857..0x3873`. |
| `engine.playmode` | `poly` and `mono` are written as the confirmed raw words at `track+0x3887`. |
| `engine.portamento.amount` | Written as q16 at `track+0x388B`. |
| `engine.bendrange` | Written as q16 at `track+0x388F`. |
| `engine.volume` | Written as q16 at `track+0x3893`. |
| `engine.modulation.*.target/amount` | Written as q16 words at `track+0x38FF..0x3937`. |
| `engine.velocity.sensitivity` | Written as q16 at `track+0x3917`. |
| `engine.portamento.type` | Written as q16 at `track+0x391B`. |
| `engine.tuning.scale` | Written as q16 at `track+0x391F`. |
| `engine.width` | Written as q16 at `track+0x3923`. |
| `engine.transpose` | Not written; current paired corpus only constrains two raw values, not a general encoding. |
| `engine.tuning.root` | Written as q16 at `track+0x392B`. |
| `engine.highpass` | Written as q16 at `track+0x392F`. |
| `engine.tuning[]` | Not written; the current corpus did not find this 12-value table in project bytes. |
| `envelope.amp.*` | Written as q16 words at `track+0x3877..0x3883`. |
| `envelope.filter.*` | Written as q16 words at `track+0x38D7..0x38E3`. |
| `fx.type` | `z lowpass`, `svf`, `ladder`, and `z hipass` are written to `track+0x21`. |
| `fx.active` | Written as boolean byte at `track+0x25`. |
| `fx.params[0..7]` | Written as q16 words at `track+0x3897..0x38B3`, except `params[5]`, which serializes as raw `0x7FFFFFFF` in every paired capture. |
| `lfo.type` | `tremolo`, `value`, `random`, and `element` are written to `track+0x1C`. |
| `lfo.active` | Written as boolean byte at `track+0x20`. |
| `lfo.params[0..7]` | Written as q16 words at `track+0x38B7..0x38D3`. |

## Drum region fields

For `type: "drum"`, the adapter authors the clean full-kit mapping validated by
the preset corpus: `voice = hikey - 53`; out-of-range regions are ignored.
Sparse or rotated kit ordering is not fully decoded yet (`nt-cherry` and
`nt-hard spunch` are current caveats), so this adapter does not attempt a more
general region-placement algorithm.

| Region field | `.xy` write status |
| --- | --- |
| `sample` | Written to the drum voice sample path. If `preset_device_path` is supplied, it is prefixed as `<preset_device_path>/<sample>`. |
| `hikey` | Written as drum key assignment and used to select voice index. |
| `lokey` | Ignored; observed drum presets use `lokey == hikey`. |
| `pitch.keycenter` | Ignored; observed drum presets use `60`. |
| `playmode` | `oneshot` is corpus-confirmed and written as byte `1`; numeric values pass through. Other strings are rejected until mapped from device evidence. |
| `reverse` | Written as drum direction. |
| `transpose` | Written as drum tune when present. |
| `tune` | Written as drum tune only when `transpose` is absent. |
| `pan` | Written as signed drum pan byte. |
| `sample.start` | Written as drum sample start. |
| `sample.end` | Written as drum sample end for the selected voice. Corpus analysis shows device-loaded clean kits use the pre-table header for voice 0 and previous slot `+0x68/+0x70` for voices 1-23; writer support still uses the direct voice edit field. |
| `framecount` | Used as drum sample end only when `sample.end` is absent; same caveat as `sample.end`. |
| `gain` | Written as drum gain. |
| `fade.out` | Written through the confirmed drum fade storage rule. |
| `fade.in` | Ignored; no confirmed project slot mapping. |

## Sampler region fields

For `type: "sampler"`, this adapter writes one-shot sampler state from the
first region. Multi-zone behavior is intentionally not claimed here.

| Region field | `.xy` write status |
| --- | --- |
| `sample` | Written to the sampler slot path. If `preset_device_path` is supplied, it is prefixed as `<preset_device_path>/<sample>`. |
| `sample.start` | Written as sampler sample start u32. |
| `sample.end` | Written as sampler sample end u32. |
| `framecount` | Written as sampler framecount u32 at `track+0x393F`; also used as sample end when `sample.end` is absent. |
| `loop.start` | Written as sampler loop start u32. |
| `loop.end` | Written as sampler loop end u32. |
| `loop.crossfade` | Written as sampler loop crossfade frames, normalized against `framecount` into the raw u32 at track `+0x3953`; if `framecount` is absent, `sample.end` is used as a fallback denominator. |
| `loop.enabled` | `false` writes loop type `off`; otherwise loop type defaults to `infinite` unless `loop.onrelease` is true. |
| `loop.onrelease` | `true` writes loop type `until_release`. |
| `tune` | Written as sampler tune tenths. |
| `gain` | Written as sampler gain byte. |
| `reverse` | Written as sampler direction. |
| `hikey` | Corpus-confirmed to match the root/keycenter byte at `track+0x3957` for one-shot sampler presets; ignored for one-shot sampler authoring. |
| `lokey` | Ignored for one-shot sampler authoring. |
| `pitch.keycenter` | Corpus-confirmed to match the root/keycenter byte at `track+0x3957` for one-shot sampler presets. |

## Unsupported preset types

Synth engine presets and multi-zone sampler presets require more complete
project sound-state mapping before they can be written safely from `patch.json`.
The adapter rejects unsupported `type` values instead of silently producing a
partial or incoherent project state.
