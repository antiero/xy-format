# Preset corpus analysis

Probe source: `src/presets`

The corpus pairs `.preset` folders with device-authored projects where track 1
was assigned the corresponding preset. Current inventory:

| Set | Count |
| --- | ---: |
| Preset folders | 322 |
| Project captures | 139 |
| Paired captures | 139 |
| Presets without project capture | 183 |
| Projects without preset folder | 0 |

Paired project types:

| Type | Count |
| --- | ---: |
| sampler | 109 |
| drum | 12 |
| epiano | 5 |
| axis | 4 |
| prism | 3 |
| organ | 2 |
| dissolve | 2 |
| hardsync | 1 |
| simple | 1 |

All preset types:

| Type | Count |
| --- | ---: |
| sampler | 227 |
| drum | 43 |
| axis | 10 |
| epiano | 10 |
| organ | 9 |
| prism | 8 |
| dissolve | 6 |
| simple | 6 |
| hardsync | 2 |
| wavetable | 1 |

## Confirmed direct mappings

`patch.json` to project-image mappings confirmed across the 139 paired captures:

| `patch.json` field | Project image mapping |
| --- | --- |
| `type` | Track engine byte at `track+0x14`. |
| `octave` | Signed byte at decoded-image `0x003D` for T1 in this corpus. Manual device testing confirms octave is track-global, not pattern-local; T2-T16 table offsets still need a multi-track fixture. |
| preset folder name | Short preset label at `track+0x453F`, encoded as `1/<preset folder name>`. |
| `engine.params[0..7]` | q16 values at `track+0x3857..0x3873`. |
| `engine.playmode` | Raw word at `track+0x3887`: `poly=0x15555555`, `mono=0x3FFFFFFF`. |
| `envelope.amp.attack/decay/sustain/release` | q16 values at `track+0x3877/0x387B/0x387F/0x3883`. |
| `engine.portamento.amount` | q16 value at `track+0x388B`. |
| `engine.bendrange` | q16 value at `track+0x388F`. |
| `engine.volume` | q16 value at `track+0x3893`. |
| `engine.velocity.sensitivity` | q16 value at `track+0x3917`. |
| `engine.portamento.type` | q16 value at `track+0x391B`. |
| `engine.tuning.scale` | q16 value at `track+0x391F`. |
| `engine.width` | q16 value at `track+0x3923`. |
| `engine.tuning.root` | q16 value at `track+0x392B`. |
| `engine.highpass` | q16 value at `track+0x392F`. |
| `fx.params[0..7]` | q16 values at `track+0x3897..0x38B3`, except the `fx.params[5]` exception below. |
| `lfo.params[0..7]` | q16 values at `track+0x38B7..0x38D3`. |
| `envelope.filter.attack/decay/sustain/release` | q16 values at `track+0x38D7/0x38DB/0x38DF/0x38E3`. |
| modulation target/amount lanes | q16 values at `track+0x38FF..0x3937`, matching the known sampler project-state map. |
| `lfo.type` | Byte at `track+0x1C`: `tremolo=0`, `value=1`, `random=2`, `element=3`. |
| `lfo.active` | Boolean byte at `track+0x20`. |
| `fx.type` | Byte at `track+0x21`: `z lowpass=9`, `svf=10`, `ladder=16`, `z hipass=17`. |
| `fx.active` | Boolean byte at `track+0x25`. |
| sampler sample path | C string at `track+0x395F`, usually `/fat32/presets/1/<preset>.preset/<sample>`. |
| sampler `hikey` / `pitch.keycenter` | Root/keycenter byte at `track+0x3957`. These two JSON fields match each other in the current sampler corpus. |
| sampler sample windows | Full u32 values at `track+0x393F/0x3943/0x3947/0x394B/0x394F`. |
| sampler `loop.crossfade` | Normalized byte at `track+0x3956`: `floor(loop.crossfade * 128 / framecount)`. |

The sampler sample-window finding matters for writer coverage: these must be
read and written as u32 fields. Many captured `framecount`, `sample.end`,
`loop.start`, and `loop.end` values exceed 65535.

The analyzer now checks the LFO/FX header bytes directly, not just by prose:
all 139 paired captures match the `lfo.type`, `lfo.active`, `fx.type`, and
`fx.active` maps above.

## Field coverage ledger

| Field | Status | Notes |
| --- | --- | --- |
| `platform` | metadata | Preset file marker; not expected to be stored as track sound state. |
| `version` | metadata | Preset schema version; not expected to be stored as track sound state. |
| `type` | confirmed | Engine byte at `track+0x14`. |
| `octave` | confirmed-for-track-1 | Signed byte at decoded-image `0x003D` for T1 in this corpus. Manual testing confirms octave is track-global, not pattern-local; T2-T16 table offsets still need a multi-track fixture. |
| `engine.params[0..7]` | confirmed | q16 words at `track+0x3857..0x3873`. |
| `engine.playmode` | confirmed | Raw word at `track+0x3887`. |
| `engine.portamento.amount`, `engine.bendrange`, `engine.volume` | confirmed | q16 words at `track+0x388B/0x388F/0x3893`. |
| `engine.velocity.sensitivity`, `engine.portamento.type`, `engine.tuning.scale`, `engine.width`, `engine.tuning.root`, `engine.highpass` | confirmed | q16 words in the `track+0x3917..0x392F` block. |
| `engine.transpose` | candidate | Raw word at `track+0x3927`; observed `0 -> 0x3FFFFFF8`, `12 -> 0x550A8538`. Encoding not generalized. |
| `engine.modulation.*.target/amount` | confirmed | q16 words at `track+0x38FF..0x3937`. |
| `engine.tuning[]` | unresolved | Observed on some organ/epiano/drum/wavetable presets. The paired captures all use the same 12-value table, and no direct float/int/q16 byte table has been found yet. |
| `envelope.amp.*`, `envelope.filter.*` | confirmed | q16 ADSR words in the known envelope blocks. |
| `fx.type`, `fx.active` | confirmed | Header bytes at `track+0x21` and `track+0x25`. |
| `fx.params[0..7]` | confirmed-with-exception | q16 words at `track+0x3897..0x38B3`; `params[5]` can serialize as max for some FX/type combinations. |
| `lfo.type`, `lfo.active` | confirmed | Header bytes at `track+0x1C` and `track+0x20`. |
| `lfo.params[0..7]` | confirmed | q16 words at `track+0x38B7..0x38D3`. |
| sampler `regions[0].sample`, `hikey`, `pitch.keycenter`, `framecount`, `sample.end`, `loop.start`, `loop.end`, `loop.crossfade` | confirmed | Sample path string, root/keycenter byte, u32 sample-window fields, and normalized crossfade byte. |
| sampler `regions[0].sample.start`, `reverse`, `gain` | confirmed-for-observed-values | `sample.start` maps to the u32 word when present; `reverse=false` maps to direction byte `0`; observed `gain` values map directly to byte `track+0x395C`. |
| sampler `regions[0].loop.onrelease`, `tune` | unresolved | `loop.onrelease=true` does not match the previous loop-type assumption in this corpus. `tune` is always zero; slot `+0x00` is keycenter/root instead. |
| drum `regions[].sample`, `hikey`, `reverse`, `pan`, `transpose`, `tune`, `playmode` | partial | Ten clean 24-region kits align with `track+0x3957 + (hikey - 53) * 0x80`; current paired captures only show `oneshot` as byte `1`. |
| drum `regions[].sample.end`, `framecount` | confirmed-for-clean-full-kits | Ten clean 24-region kits store voice 0 in the pre-table header (`+0x393F/+0x3947`) and voices 1-23 in the previous slot's `+0x68/+0x70`. Sparse/rotated kits remain unresolved. |
| drum `regions[].fade.*` | constant-in-corpus | `fade.in` and `fade.out` are zero in every current drum preset, so this corpus cannot independently map them. |
| `regions[].lokey`, `regions[].pitch.keycenter` | ignored-or-unresolved | Often redundant with `hikey`/default keycenter, but no independent project field is confirmed. |

## Exceptions

`nt-dx analog.xy` appears to contain the `nt-dx legend` preset load:

| Field | Expected from `nt-dx analog.preset` | Found in project |
| --- | --- | --- |
| Preset label | `1/nt-dx analog` | `1/nt-dx legend` |
| Sample path | `/fat32/presets/1/nt-dx analog.preset/unnamed-c3-61.wav` | `/fat32/presets/1/nt-dx legend.preset/unnamed-c3-60.wav` |
| `regions[0].framecount` | `423043` | `327223` |

Ten synth-ish presets have `fx.params[5] == 21954` in `patch.json`, while the
project stores `0x7FFFFFFF` at the corresponding lane:

```text
nt-bellodic
nt-blip tips
nt-cabin pressure
nt-castle vania
nt-circus ring
nt-cold brew
nt-digital signals
nt-equinox
nt-faded
nt-fly kites
```

This looks like an engine/FX-specific saturation or fixed default lane rather
than random drift, because all ten project values are exactly `0x7FFFFFFF`.

Drum kit alignment:

- Ten clean 24-region kits align path, key assignment, transpose/tune center,
  pan, reverse/direction, and `patch.json` `oneshot` play mode byte `1` at
  `track+0x3957 + (hikey - 53) * 0x80`.
- In those clean kits, voice 0 `framecount`, `sample.start`, `sample.end`,
  `loop.start`, and `loop.end` use the pre-table header at
  `track+0x393F/+0x3943/+0x3947/+0x394B/+0x394F` (`loop.end` is
  `0xFFFFFFFF` in the current full-kit captures).
- Voices 1-23 store `sample.end` / `framecount` in the previous slot at both
  `+0x68` and `+0x70`, matching the earlier shifted-storage pattern.
- This means the generic direct drum voice writer is not yet a faithful
  preset-load serializer for drum `sample.end` / `framecount`. It remains useful
  for direct edit-field authoring, but patch.json drum preset loading needs a
  separate shifted-storage path.

Drum kit caveats:

- `nt-hard spunch.xy` appears rotated relative to its `patch.json` region order.
- `nt-cherry.xy` has a missing/empty voice in the middle of the 24-slot table,
  after which path and end alignment no longer match a simple `hikey - 53`
  mapping.

## Tooling

`tools/analysis/analyze_preset_corpus.py` generates a Markdown report from the
current corpus and should be rerun after adding new project captures. It flags
missing pairs, mapping mismatches, and likely bad fixture pairings.
