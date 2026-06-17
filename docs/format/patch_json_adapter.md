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
| `octave` | Keyboard octave metadata. | Ignored; no confirmed project slot mapping. |
| `engine` | Engine-level settings and params. | Not written by this adapter. |
| `envelope` | Amp/filter envelope blocks. | Not written by this adapter. |
| `fx` | Preset-local FX state. | Not written by this adapter. |
| `lfo` | Preset-local LFO state. | Not written by this adapter. |
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

The adapter currently does not write these top-level engine fields. Some have
known project-image locations in other readers/writers, but this adapter only
promotes fields whose `patch.json` meaning and project slot storage are tied
together by confirmed sample-based preset behavior.

## Drum region fields

For `type: "drum"`, each region maps to one pad. The adapter uses
`voice = hikey - 53`; out-of-range regions are ignored.

| Region field | `.xy` write status |
| --- | --- |
| `sample` | Written to the drum voice sample path. If `preset_device_path` is supplied, it is prefixed as `<preset_device_path>/<sample>`. |
| `hikey` | Written as drum key assignment and used to select voice index. |
| `lokey` | Ignored; observed drum presets use `lokey == hikey`. |
| `pitch.keycenter` | Ignored; observed drum presets use `60`. |
| `playmode` | Written as drum play mode using the patch.json adapter mapping `oneshot=0`, `group=1`, `loop=2`, `gate=3`; numeric values are passed through. |
| `reverse` | Written as drum direction. |
| `transpose` | Written as drum tune when present. |
| `tune` | Written as drum tune only when `transpose` is absent. |
| `pan` | Written as signed drum pan byte. |
| `sample.start` | Written as drum sample start. |
| `sample.end` | Written as drum sample end. |
| `framecount` | Used as drum sample end only when `sample.end` is absent. |
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
| `framecount` | Used as sampler sample end u32 only when `sample.end` is absent. |
| `loop.start` | Written as sampler loop start u32. |
| `loop.end` | Written as sampler loop end u32. |
| `loop.crossfade` | Written as sampler loop crossfade frames, normalized against `framecount` into the raw u32 at track `+0x3953`; if `framecount` is absent, `sample.end` is used as a fallback denominator. |
| `loop.enabled` | `false` writes loop type `off`; otherwise loop type defaults to `infinite` unless `loop.onrelease` is true. |
| `loop.onrelease` | `true` writes loop type `until_release`. |
| `tune` | Written as sampler tune tenths. |
| `gain` | Written as sampler gain byte. |
| `reverse` | Written as sampler direction. |
| `hikey` | Ignored for one-shot sampler authoring. |
| `lokey` | Ignored for one-shot sampler authoring. |
| `pitch.keycenter` | Ignored for one-shot sampler authoring. |

## Unsupported preset types

Synth engine presets and multi-zone sampler presets require more complete
project sound-state mapping before they can be written safely from `patch.json`.
The adapter rejects unsupported `type` values instead of silently producing a
partial or incoherent project state.
