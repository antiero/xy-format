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
| `sample.start` | Corpus-confirmed as a u32 sampler sample-start word at `track+0x3943` when present. |
| `sample.end` | Corpus-confirmed as a u32 sampler sample-end word at `track+0x3947`. |
| `framecount` | Corpus-confirmed as a u32 framecount word at `track+0x393F`; also used as sample end when `sample.end` is absent. |
| `loop.start` | Corpus-confirmed as a u32 sampler loop-start word at `track+0x394B`. |
| `loop.end` | Corpus-confirmed as a u32 sampler loop-end word at `track+0x394F`. |
| `loop.crossfade` | Corpus-confirmed as normalized byte `floor(loop.crossfade * 128 / framecount)` at `track+0x3956`; the adapter writes this normalized storage value when `framecount` is available. |
| `loop.enabled` | Adapter currently writes loop type from this boolean, but preset-corpus validation is still incomplete. |
| `loop.onrelease` | Unresolved for preset loads: current corpus has `loop.onrelease=true` while the project slot stores the same loop-type byte as ordinary infinite looping. |
| `tune` | Unresolved for preset loads: current sampler corpus has only `0`, while slot `+0x00` is confirmed to store keycenter/root instead. |
| `gain` | Observed nonzero values map directly to byte `track+0x395C`. |
| `reverse` | `false` maps to direction byte `0` at `track+0x395E`; no `true` sampler preset is in the paired corpus yet. |
| `hikey` | Corpus-confirmed to match the root/keycenter byte at `track+0x3957` for one-shot sampler presets. |
| `lokey` | Ignored for one-shot sampler authoring. |
| `pitch.keycenter` | Corpus-confirmed to match the root/keycenter byte at `track+0x3957` for one-shot sampler presets. |

## Unsupported preset types

Synth engine presets and multi-zone sampler presets require more complete
project sound-state mapping before they can be written safely from `patch.json`.
The adapter rejects unsupported `type` values instead of silently producing a
partial or incoherent project state.
