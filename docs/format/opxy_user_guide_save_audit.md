# OP-XY User Guide Save Audit

> Byte-region status at a glance: [`image_coverage_map.md`](image_coverage_map.md)

> Review date: 2026-06-10. Source: Teenage Engineering OP-XY user guide
> v1.1.0, online guide
> (`https://teenage.engineering/guides/op-xy`) and printable PDF
> (`https://assets.teenage.engineering/_img/68ef8a079775f13263a349ef_original.pdf`).
>
> This is the single cross-reference from guide-visible editing functions to
> current `.xy` knowledge. "Decoded" means we know the decoded-image storage
> location well enough to parse/preserve and usually write. "Partial" means the
> storage region is known, but value labels, enum domains, scaling, or one
> subfield are not fully mapped. "Gap" means the guide describes project/device
> state that should persist, but this repo has not actually pinned where it is
> saved.

## Scope

The guide's workflow chapter is the best persistence summary: each track has
up to nine patterns; each pattern holds notes/sounds, locks, components,
bars, and preset/sound state; scenes store pattern choices plus track volumes
and mutes; songs arrange scenes; projects hold those objects. This audit follows
that model and then walks through every guide section that exposes editable
state.

Primary repo references:

- `docs/parse_capability_checklist.md` for a checkbox overview with code paths.
- `docs/format/decoded_image_map.md` for canonical decoded-image offsets.
- `docs/format/record_structure.md` for RLE/container and scene/song structs.
- `docs/engineering/authoring.md` for fields currently writeable through
  `xy/image_writer.py`.
- `docs/reference/opxy_midi_cc_map.md` for guide CC labels.

## Current Coverage Snapshot

| Guide area | Save-relevant controls | Current status |
|---|---|---|
| Project file/container | save, save-as, duplicate, history files | Decoded at `.xy` project-file level; filesystem history/backups are outside one `.xy`. |
| Project settings | global transpose, time signature, voice allocation, per-track MIDI channel | Core project settings decoded by PCFG/HDR probes. |
| Tempo | BPM, groove type/amount, metronome level/on-off | BPM, groove type/amount, time signature, click volume, and metronome persistence decoded. |
| Patterns/sequencer | notes, chords, gate, microtiming, bars, track scale, p-locks, step components | Decoded. |
| Bar page | quantization, default length, per-track groove, lock smoothing, final-bar length | Quantization, final-bar length, default step length, per-track groove, and p-lock shape decoded. |
| Players | arpeggio, maestro, hold | Gap. |
| Instrument | engine, preset, M1 params, envelopes, filter, LFO, preset settings | Main regions decoded; several shift/subfunction values are partial. |
| Auxiliary tracks | Brain, Punch-in FX, External MIDI/CV/Audio, Tape, FX I/II | Track structs exist; many aux-specific parameter labels/enums are gaps. |
| Arrange | pattern switching/copying, scenes, mutes, song chains, loop | Core scenes/songs decoded; scene-stored volume bytes mapped, playback semantics need retest. |
| Mix | track levels, pans, sends, EQ, saturator, master/compressor | Static mixer, master volume/compressor, master EQ, and master saturator decoded by P2 probes; some aux labels remain partial. |
| Sample | one-shot, drum sampler, multisampler, sample folder assignments | Drum and one-shot sampler state mostly decoded; multisampler zones and slicing internals remain gaps. |
| COM/system | multi-out, Bluetooth MIDI, system settings, devices, controller mode | Mostly outside `.xy`; any project-specific MIDI channel overlaps project settings. |
| MIDI CC | CC 7/9/10/12-47/80-86/90 | Reference labels documented; storage coverage varies by target. |

## Point-by-Point Audit

### Project and Project Settings

Guide refs: section 10.1 p.36; section 10.2 p.36; section 10.3 p.37; section 22.10 p.119.

| Function | What should save | Current decode |
|---|---|---|
| Save / save-as / duplicate | Current project image and filesystem copy/history. | Decoded as whole `.xy`: 8-byte header + one RLE stream over the decoded RAM image. History/backups are filesystem policy, not an internal field. |
| Rename | Project name / filename. | Gap for any internal display-name field. The MTP instructions also allow direct filename rename, so the name may be external to the `.xy` body. |
| Project general transpose | Global transposition including drums. | Decoded: signed i8 at global `0x1B`, range −24..+24 (PCFG). |
| Project tempo/time signature | Time signatures 3/4, 4/4, 5/4, 6/8, 7/8, 12/8 plus groove type view/edit. | Decoded: tempo at global `0x00`, groove type/amount at `0x03`/`0x02`, time-signature enum at global `0x1C` (`0x10`–`0x15`). |
| Project voices | Per-track voice allocation/priority within 24-voice total. | Decoded: global `0x4D-0x54` for T1-T8, `0` auto / `1`-`8` fixed (PCFG). |
| Project MIDI | MIDI channel for each of 16 tracks. | Decoded: global header `0x55-0x64`, one byte per track. |

### Tempo

Guide refs: section 11.1 p.39; section 11.2 p.40.

| Function | What should save | Current decode |
|---|---|---|
| Tempo | BPM/tap tempo. | Decoded: global `0x00`, u16 LE tenths of BPM in decoded image. |
| Groove type | Shuffle/half-shuffle/danish/bombora/wobbly/gaussian/accents/island nod/disfunk/roll over/prophetic. | Decoded location: global `0x03`; only some enum values are named from captures. |
| Groove amount | Amount of selected groove. | Decoded: signed global `0x02`; writer: `ImageProject.set_groove_amount()`. |
| Metronome volume/toggle | Click level and enabled state. | Click volume decoded at global `0x04`; off and minimum volume both persist as `0x00`, and probes did not reveal a separate toggle byte. |

### Sequencer, Pattern, and Bar State

Guide refs: section 7.1 p.22-23; section 7.2 p.24; section 7.3 p.25; section 7.4 p.26-27; section 12.1 p.41.

| Function | What should save | Current decode |
|---|---|---|
| Step sequencing / live recording / step recording | Notes, chords, velocity, timing, and gate. | Decoded: note vector near track `+0x456F`: `[count] + 12-byte {tick, gate, note, velocity, flags[2]}`. Tick carries microtiming/nudge; gate carries note length. |
| Chords | Multiple note records at same tick. | Decoded as repeated 12-byte records. 120-note pattern cap is enforced by writer. |
| Extend note | Gate length. | Decoded as `u32 gate` in each note record. |
| Nudge step | Off-grid tick value. | Decoded as non-grid `u32 tick`. |
| Clear notes / clear all | Delete note vector rows, optionally p-locks. | Operation derived from decoded vectors/tables; no separate field. |
| Copy step | Notes + locks + step components copied between step slots. | Operation over decoded note rows, p-lock row, and component slot; no separate field. |
| Change sequence octave/semitone | Mass note transposition. | Operation over note values, not a separate field unless project transpose is used. |
| Parameter lock | Per-step parameter value. | Decoded: p-lock table at track `+0x2A0`, 64 rows x 84 bytes, 42 u16 columns. |
| Track scale | One step duration: 1, 2, 3, 4, 6, 8, 16, 1/2 per guide. | Partial. Location decoded at track `+0x06`; observed values include 1, 2, 16, and 1/2. Missing confirmed enum bytes for 3, 4, 6, 8. |
| Add/remove bars | 1-4 bars per pattern. | Decoded at track `+0x01` as total active steps. Full bars are `16`, `32`, `48`, `64`; partial final bars use `(bar_count - 1) * 16 + final_bar_steps`. |
| Duplicate bar | Copy notes/locks/components between step ranges. | Operation over decoded structures; no separate field. |
| Sequence length / final-bar length | Number of active steps when last bar is shortened. | Decoded (BAR-LEN). Track `+0x01` stores total active steps: `(bar_count - 1) * 16 + final_bar_steps`. |
| Track quantization | Recording quantize amount; affects whether nudge is allowed at 100. | Decoded (BAR). Raw byte at track `+0x07`; displayed UI is `floor(raw * 100 / 255)`. Generated PC-to-device probes confirmed top-end boundaries, including `0xFD -> 99`. |
| Default step length | Length of newly step-sequenced notes. | Decoded (BAR). U16 ticks at track `+0x02`; default `240`, max `480`, one detent near center = 4 ticks. |
| Per-track groove override | Bar-page groove overriding tempo swing. | Decoded (BAR). Raw index byte at track `+0x08`; storage is `3 * index` into the displayed UI sequence, saturated at ±99. |
| P-lock smoothing/shape | Interpolation/smoothing between p-locks. | Decoded raw storage (BAR) at track `+0x3056`; UI curve names/icons still not mapped. |

### Step Components

Guide refs: section 8.2 p.29; section 8.3 p.30; section 8.4 p.31.

Storage is decoded: each step has a 16-byte slot at track
`+0x3057 + 16 * step_index`, with a u16 enabled mask and 14 value bytes.

| Component | Current decode |
|---|---|
| Pulse, hold, multiply, velocity, ramp up, ramp down, random, portamento, bend, tonality, jump, skip parameter lock, skip component, skip trigger | Decoded as bit positions 0-13 with one value byte each. Corpus examples cover many guide values. Exact byte labels for every guide table column, especially random/max variants, should still be promoted into a complete enum table before claiming user-facing write coverage for every value. |

### Players

Guide refs: section 9.1 p.33; section 9.2 p.33; section 9.3 p.34.

| Function | What should save | Current decode |
|---|---|---|
| Player enable/type | Off/arpeggio/maestro/hold selection per track. | Gap. No canonical offset. |
| Arpeggio | Speed, pattern, range, hold, note length, style/play order, glide, stereo. | Gap. |
| Maestro | Recorded chord notes, roll, pattern, hold. | Gap. Maestro note buffer storage is unknown. |
| Hold player | Enable state and held-note behavior. | Gap. |

### Instrument Tracks

Guide refs: section 14.1 p.42; section 14.2 p.43; section 14.3 p.44; section 14.4 p.45-50; section 14.5 p.51; section 14.6 p.52; section 20.1-20.9 p.93-101.

| Function | What should save | Current decode |
|---|---|---|
| Engine selection | Synth/drum/sampler engine ID. | Decoded: engine ID at track `+0x14`; preset identity can be copied by `ImageProject.set_preset()`. |
| Preset selection/copy/paste/scramble | Engine, params, sample table/path, preset path/name. | Decoded enough for donor-copy authoring: preset path at ~track `+0x453F`; preset identity regions copied by writer. User preset file format outside `.xy` is not decoded here. |
| Engine M1 params | Four current engine-specific parameters for Axis/Dissolve/EPiano/etc. | Decoded as 4-byte values starting at track `+0x3857`; labels are guide/engine-specific and not all value scaling is documented. |
| Amp envelope | Attack/decay/sustain/release. | Decoded at track `+0x3877`, 16-byte ADSR block. |
| Filter envelope | Attack/decay/sustain/release. | Decoded at track `+0x38D7`, 16-byte ADSR block. |
| Play mode | Poly/mono/legato. | Partial. P-lock/current lane pinned at track `+0x3887` from `unnamed 122` CC28; exact enum labels still need a direct UI capture. |
| Portamento amount/type | Glide amount and preset-settings type. | Partial. Current lane pinned at track `+0x388B` from `unnamed 122` CC29; portamento type remains unmapped. |
| Bend range | Pitch-bend range. | Partial. Current lane pinned at track `+0x388F` from `unnamed 122` CC30; scaling/enum still needs UI confirmation. |
| Preset volume / engine volume | Per-preset volume separate from track volume. | Partial. Current lane pinned at track `+0x3893` from `unnamed 122` CC31; scale follows the 0..0x7FFFFFFF fixed-point family. |
| Filter type/on-off | SVF/ladder and filter enabled. | Decoded at track `+0x21` and `+0x25`; complete type enum still needs names beyond observed values. |
| Filter knobs | Cutoff, resonance, envelope amount, key tracking. | Decoded at track `+0x3897`; p-lock columns also known. |
| Track sends | Aux out, tape, FX I, FX II. | Partial. Current lanes pinned at track `+0x38A7/+0x38AB/+0x38AF/+0x38B3` from `unnamed 123` CC36-39; send tape is inferred by lane order because the baseline already matched the recorded max value. |
| LFO type | Element/random/tremolo/value and prior M4 selectors. | Partial. M4/LFO type selector region starts at track `+0x1C`; exact enum and all subfunction storage is not complete. |
| LFO params | Source/rate, amount, destination, parameter, shape/envelope/subfunctions. | Partial. M4 values live at track `+0x38B7`; CC40/CC41 lanes are pinned at `+0x38B7/+0x38BB` from `unnamed 124`. Shape/type-specific state is likely near `+0x38D3..+0x38D6`, but enum labels remain incomplete. |
| Preset settings: high pass | Basic high-pass. | Decoded at track `+0x392F`. |
| Preset settings: velocity sensitivity | Velocity sensitivity. | Decoded at track `+0x3917`. |
| Preset settings: tuning, tuning root, transpose, width | Microtonal/user tuning slot, root, transpose, stereo width. | Gap/partial. These settings are guide-visible but not mapped to stable fields. |
| Preset modulation settings | Modwheel/aftertouch/pitchbend/velocity target and amount. | Partial. Region decoded at track `+0x38FF-0x393B`; exact destination IDs and scaling still in progress. |
| User preset rename/save/delete | `.preset`/preset library changes. | Outside the project `.xy` unless loaded/copied into a track. User preset file format is not decoded in this audit. |

### Auxiliary Tracks

Guide refs: section 15.1 p.54 through section 15.7 p.63.

All aux tracks are present as track structs (T9-T16). T15 is FX I and T16 is
FX II; FX type changes use the same engine/parameter regions. Beyond that,
guide-visible aux semantics are still the largest project-format gap.

| Aux track/function | What should save | Current decode |
|---|---|---|
| T9 Brain | Manual/auto, key, scale, linked tracks, routing, recorded Brain sequence. | Gap/partial. Track struct exists; no promoted field map for Brain settings/routing. |
| T10 Punch-in FX | Percussion/melodic mode, punch effect assignments/recorded triggers. | Partial. Recorded punch triggers use the generic note vector at T10 `+0x456F`; full punch key/effect map and modulation behavior remain gaps. |
| T11 External MIDI | MIDI channel, bank, program, eight assignable CC controls. | Partial. Channel/bank/program words are located at T11 `+0x3857/+0x385B/+0x385F`; CC assignment table localizes to `+0x3877..+0x3896`, but exact number/message ownership remains partial. T11 note-vector confirmation fixture was not captured yet. |
| T12 External CV | CV/gate behavior and track params. | Gap/partial. |
| T13 External Audio | Input level/drive/filters/sends. | Gap/partial. `unnamed 126` captures CC12 input on T13; there is no source-corpus CC13 drive capture yet. |
| T14 Tape | Tape parameters and sends. | Gap/partial. |
| T15/T16 FX I/II | FX type and parameters. | Partial. Aux track identity and params are structurally decoded; exact type enums/parameter scaling for chorus/delay/distortion/lofi/phaser/reverb need full tables. |

### Arrange, Scenes, and Songs

Guide refs: section 16.1 p.66; section 16.2 p.66; section 16.3 p.67; section 16.4 p.68; section 12.1 p.41.

| Function | What should save | Current decode |
|---|---|---|
| Pattern switching/copy/create | Up to nine pattern structs per track. | Decoded: adding a pattern inserts a 17,876-byte pattern struct; leader count byte gives pattern count. |
| Scene pattern selections | Pattern choice for each track in each scene. | Decoded in current RLE-image model as 33-byte scene slots: `selected_pattern[16] + mute[16] + flags`. Legacy pretrack token docs are superseded for canonical writing. |
| Scene mutes | Per-track mute state per scene. | Decoded: mute bytes in scene slot; device-confirmed nonzero boolean, writer uses value `2`. |
| Scene volumes | Guide explicitly says scenes store track volumes. | **Partial (P2-D).** Bytes on track struct `+0x38FE` (and master `global+0x94`) differ per scene; storage routing `T+S−1` on two-scene captures. Playback on 1.1.4 heard global mix — semantics open. |
| Song arrangement | Scene chain per song. | Decoded: footer song table slots `[scene_count][scene_ids...][loop_word]`. |
| Song loop | Loop on/off per song. | Decoded: loop word in footer, device-validated. |
| Number of songs | Guide says 9 songs. | Partial/mismatch. Footer has 14 four-byte slots in decoded image; need reconcile which slots are user-visible vs reserved/other state. |
| Active song/scene selection | Current selected song/scene. | Decoded (HDR). Global `0x06` is active scene slot, zero-based; global `0x07` is active song slot, with `0x10` as fresh/default Song 1 sentinel. |

### Mix, EQ, Saturator, and Master

Guide refs: section 17.1 p.70; section 17.2 p.71; section 17.3 p.72; section 17.4 p.73.

| Function | What should save | Current decode |
|---|---|---|
| Track volume | Per-track level. | **Decoded (P2-A).** Static byte @ `track+0x38FE` (u32 @ `+0x38FB`); p-lock col 0 / CC7 also. |
| Track pan | Per-track pan. | **Decoded (P2-A).** Static byte @ `track+0x38FA`; p-lock col 41 / CC10 also. |
| Track mute | Per-track mute/live mix state. | **Decoded:** scene mute in 33-byte slots (P2-E scenes 1–8, slot `N−1`, value `0x02`); CC9 not p-lock. Live mixer mute not separate from scene mute. |
| Sends | Ext/tape/FX I/FX II sends. | **Partial (P2-A).** Static FX1/FX2 @ `+0x38B2`/`+0x38B6`; tape/ext p-lock cols known. |
| Master EQ | Low/mid/high. | **Device-validated (P2-F).** Global `0x68`/`0x6C`/`0x70`; blend @ `0x74` unprobed. |
| Saturator | Gain/clip/tone/mix. | **Device-validated (P2-G).** Global `0x78`/`0x7C`/`0x80`/`0x84`. |
| Master compressor/output | Compressor amount and master/output level. | **Decoded (P2-A/P2-D).** Compressor @ `global+0x90`; master vol @ `global+0x94`; perc/melody @ `+0x88`/`+0x8C`. |

### Sample Mode

Guide refs: section 18.1 p.77-78; section 18.2 p.79-82; section 18.3 p.83-84; section 18.4 p.85; section 22.11 p.120.

| Function | What should save | Current decode |
|---|---|---|
| Sample folder | External WAV/AIFF files and folders. | Outside `.xy` except project sample-path references. |
| One-shot synth sampler | Sample path, start, loop start/end, end, direction, tune, loop crossfade, gain, loop type. | **Decoded (P2-B):** header @ `track+0x3943`…`+0x3956`; path/tune/gain/direction/loop-type @ voice-0 `+0x3957`. Tune UI scaling partial. |
| Drum sampler sample assignment | 24 key slots with path strings. | Decoded: 24 x 128-byte slots at track `+0x3957`; sample path at slot `+0x08`. |
| Drum sampler edit controls | Tune, start, end, play mode, direction, pan, fade, gain. | **Decoded:** tune `+0x00`, play mode `+0x03`, direction `+0x07`, pan `+0x06` (M3 ±100), start `+0x68`, end `+0x70`, gain/fade `+0x7C` (fade on preceding slot for pad voices, M3). |
| Drum clear/copy/paste/select multiple | Assignment/table operations. | Operation over decoded slot table; multi-select UI state itself is not relevant unless saved as UI state. |
| Drum slicing | Slice mode, slice boundaries, generated choke/mute-group assignments. | Gap/partial. Result likely writes drum slots, but transient/even/tap slice metadata and generated assignment rules are not decoded. |
| Multisampler zones | Up to 24 zones, key assignment, sample path, zone fill-down behavior. | Gap/partial. The 24-slot table model likely applies, but multisampler zone boundaries/root-key fields are not decoded. |
| Multisampler edit controls | Start, loop start/end, end, direction, tune, loop crossfade, gain, loop type. | Gap/partial. Not promoted separately from drum table. |

### COM, Devices, and System Settings

Guide refs: section 19.1 p.87; section 19.2 p.88; section 19.3 p.89; section 19.4 p.90; section 19.5 p.91.

Most COM settings are device-global, not project `.xy` data. They should not
be assumed to live in project files without a capture proving it.

| Function | What should save | Current decode |
|---|---|---|
| Multi-out mode | MIDI/CV-gate/sync/audio output selection. | Not decoded in `.xy`; likely device-global system setting. |
| Bluetooth MIDI advertise | Bluetooth connection state. | Not project `.xy`. |
| System settings | Screen/LED brightness, country, power-off, keyboard velocity/detune, MIDI preferences, clock, pitchbend calibration, battery. | Not decoded in `.xy`; likely device-global. |
| MIDI controller mode | Controller channel, knob mode, octave buttons. | Not project `.xy`. |
| Devices page | Per-device clock/notes/CC/timestamp/velocity routing. | Not project `.xy`; likely device-global. |
| MTP | File transfer mode/eject. | Not project `.xy`. |

### MIDI CC Reference

Guide refs: section 23 p.122.

| CC area | Current decode |
|---|---|
| CC7 volume, CC10 pan, CC12-47 track parameters | P-lock table maps many recorded CCs to parameter columns/IDs. Static current-value offsets for several mix/aux controls still need promotion. |
| CC9 mute | Scene mute decoded separately; MIDI CC9 did not produce p-lock data in captures. Static/mixer mute field remains open. |
| CC80 tempo, CC81 groove | Global tempo/groove fields partially decoded. |
| CC82 delay scene, CC83 previous scene, CC84 next scene, CC85 scene, CC86 project | These are control actions/selectors, not necessarily persistent fields. Active scene/song/project selection bytes are only partially mapped. |
| CC90 EQ | Master EQ decoded globally; complete CC90 channel-to-EQ mapping should be checked against the current image map before writing. |

## Consolidated Gap Ledger

These are the guide-visible features that should be prioritized if the goal is
"everything in the manual that saves has a named `.xy` field."

| Priority | Gap | Guide reference | Why it matters | Suggested capture |
|---|---|---|---|---|
| P0 | Scene-stored track volume playback semantics | section 12.1 p.41, section 16.3 p.67 | Storage bytes are mapped from P2-D captures, but operator playback on firmware 1.1.4 sounded global. | Retest one two-scene project on device: scene 2 T1 volume only, then A/B scene playback without rebuilding the file. |
| P1 | Players: arpeggio/maestro/hold | section 9.1-section 9.3 p.33-34 | Entire guide chapter with persistent per-track behavior; no canonical offsets. | Three captures: enable Hold; Arp with non-default all knobs; Maestro with a two-note recorded chord. |
| P1 | Aux-specific parameter maps for T9-T14 and exact FX I/II enums | section 15.1-section 15.7 p.54-63 | Aux tracks are first-class sequenceable tracks; current struct map is generic. | One capture per aux track with all four visible knobs moved; one per shift page. |
| P1 | Multisampler zone internals | section 18.3 p.83-84 | One-shot sampler fields and drum slot paths/params are mapped, but multisampler zone/root/fill-down behavior is not. | Assign two zones; change one edit-screen field at a time; include root/key-boundary captures. |
| P1 | Preset settings tuning/root/transpose/width/portamento type | section 14.5 p.51 | Visible preset settings not fully mapped. | Same track/preset, one setting per save. |
| P1 | Mod-routing destination enum and signed scaling | section 14.5 p.51, section 22.9 p.118 | Region known, but target IDs/amount scaling incomplete. | Pitchbend/modwheel/aftertouch/velocity target+amount matrix with fixed nonzero amounts. |
| P2 | Aux/static mix labels beyond P2-A fields | section 17.1-section 17.4 p.70-73 | Main static mixer, master compressor/output, EQ, and saturator are mapped; aux-specific labels and some send semantics remain partial. | One save per aux-visible control from initialized project; use decoded diff against baseline. |
| P2 | LFO type/subfunction enum table | section 14.4 p.45-50 | Region known; user-facing labels incomplete. | LFO type sweep and one capture per shift/click subfunction. |
| P2 | External MIDI CC assignment ownership and boundary-safe writer values | section 20.4 p.96, section 15.3 p.56 | M1 channel/bank/program offsets are located, and the CC table range is located; exact CC number/message word ownership and PC-generated boundary behavior remain open. | One clean capture per CC word from a reset baseline, plus PC-generated boundary checks for channel/bank/program buckets. |
| P2 | Active song/scene/project selector and guide 9-song vs decoded 14-slot footer reconciliation | section 12.1 p.41, section 16.4 p.68, section 23 p.122 | Core model works for Song 1 chains, but selector/count semantics and unused footer slots need cleanup. | Create songs 1-9 with unique one-scene chains; save after selecting each. |
| P3 | User preset file format and internal project display name | section 10.1 p.36, section 14.6 p.52 | Useful for library tooling, less critical for `.xy` musical playback. | Save/rename user preset and project; compare filesystem artifacts plus project body. |
| P3 | Device-global COM/system settings | section 19.1-section 19.5 p.87-91 | Probably not `.xy`, but should be proven to avoid false expectations. | Change COM/system settings and resave same project; confirm no project-body delta. |

## Notes for Future Updates

- Do not demote the RLE/container result: structure is solved. Most gaps above
  are named field semantics, enum tables, or project-vs-device-global
  attribution.
- When a gap is closed, promote the stable offset/value rule into the relevant
  canonical doc (`decoded_image_map.md`, `header.md`, `scenes_songs.md`,
  or a new subsystem file) and leave this audit as the checklist.
- Generated test filenames should follow the repo naming rule, e.g.
  `01_scene_vol_t3.xy`, `02_project_sig_7_8.xy`, matching intended test order.
