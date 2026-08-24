# Roadmap

> Refreshed 2026-08-24 for OP-XY OS 1.1.25. Structural authoring is solved;
> this roadmap now separates shipped software work from fields that still need
> a device-authored A/B capture. The dated belief ledger remains
> [`state_of_understanding.md`](state_of_understanding.md).

## Current release target — OS 1.1.25 + XYBuddy

- [x] Merge the antiero and kmorrill histories without losing 16-pattern and
  96-scene long-song support.
- [x] Verify the connected OP-XY reports firmware 1.1.25 over MTP.
- [x] Add Python, inspector, browser-timing, editor, and UI coverage for the
  full 1/2, 1, 2, 3, 4, 5, 6, 7, 8, 16 track-scale enum.
- [x] Add coherent pattern rotation: triggers, p-lock rows, p-lock activation
  rows, and step-component rows move together in Python and XYBuddy.
- [x] Preserve the complete track state when constructing pattern clones, so
  OS 1.1.25's inherited player type and still-opaque player bytes are retained.
- [x] Restore the Pattern workspace to XYBuddy's current project navigation so
  note editing, odd-scale selection, and coherent rotation are reachable.
- [x] Add generated-project preflight for layout, note/pattern limits, engine
  and preset identity, scene references, sample paths/windows, mapped drum
  slots, known scale bytes, all 14 song footers, and metronome-off output.
- [x] Rebuild XYBuddy with the current web bundle, run its full Swift tests and
  universal Release build, then repeat a live MTP upload/download/delete test.
- [x] Parse and rewrite all 14 serialized song slots in XYBuddy, with compact
  Song workspace navigation and device-authored Song 2 regression coverage.
- [x] Correct the decoded song loop field to one byte plus reserved zero;
  expose all 14 slots through the Python image API as well as XYBuddy.
- [x] Correct generated Scene N storage to device-authored slot N−1 semantics.
- [x] Bound direct preset-path writes to the actual 48-byte field so long
  identities cannot overwrite the note vector.
- [x] Add deterministic, preflighted limit probes for 99 scenes, a 96-entry
  song chain, 16 patterns, and 120 notes; reject note 121 off-device.
- [ ] Add one device-saved odd-scale capture to promote the contiguous
  0x06/0x08/0x09/0x0A mapping from E0 to E2.

The last unchecked item cannot be manufactured by an off-device writer: it
needs the OP-XY UI to select an odd scale and save the project. The exact
ordered capture recipe is in
[`workflows/next_device_captures.md`](workflows/next_device_captures.md).

## Format closure — device captures required

Ordered by the amount of authoring capability each capture unlocks:

1. **Player state** — locate enable/type and the arpeggio, maestro, and hold
   parameter blocks. OS 1.1.25 changes hold-player note-off behavior and makes
   new patterns inherit the current player type, so pre-1.1.25 assumptions must
   not be promoted without fresh captures.
2. **Multisampler zones** — map slot enable, low/high key, root key, window,
   and zone count. Retest global transpose because OS 1.1.25 changed its
   interaction with multisamples.
3. **Instrument labels/enums** — complete LFO subfunctions, mod-routing target
   IDs and signed scaling, play-mode/portamento/bend labels, plus preset
   transpose and the 12-note user-tuning table. Tuning slot/root/width and the
   raw modulation lanes are already readable and writable.
4. **Auxiliary details** — finish External MIDI CC slot enable/number/value,
   Punch-in key map, FX schemas, and the remaining Brain/Tape/External Audio
   labels. Raw locations and safe setters already cover the confirmed fields.
5. **Sampling details** — drum slicing metadata/choke groups and sparse or
   rotated kit placement. One-shot sampler and clean 24-pad kit authoring are
   already implemented.
6. **Scene-volume playback** — repeat the chained audible A/B on 1.1.25; bytes
   are mapped, but the prior 1.1.4 listen test behaved globally.

## Limits certification — device acceptance

- [ ] 99 scene rows load and select correctly.
- [ ] All 14 serialized song slots reconcile with the currently visible song
  slots in the device UI.
- [ ] Full 16-pattern topology passes on 1.1.25.
- [ ] A 120-note pattern passes; note 121 is rejected off-device.

The writer already enforces the structural limits. These checks certify the UI
and playback edges rather than discovering new byte layouts. Generate the
ordered artifacts with [`workflows/limit_certification.md`](workflows/limit_certification.md).
The current set is staged byte-identically in the connected OS 1.1.25 device's
Templates folder; see
[`logs/2026-08-24_os_1_1_25_limit_probe_staging.md`](logs/2026-08-24_os_1_1_25_limit_probe_staging.md).

## Completed format/tooling work

- [x] Byte-level RLE container; 245/246 corpus files round-trip byte-exact.
- [x] Decoded global header, 16 track structs, clone patterns, scenes, song
  footer, note vectors, p-lock table, step-component slots, and drum voices.
- [x] P-lock parameter columns and all 14 component slot positions.
- [x] Engine ID, preset path, sound-state blocks, direct preset-path writer,
  drum sample-path writer, and one-shot sampler writer.
- [x] Sampler project-state capture batch and patch.json adapter for tonal
  sampler plus clean full drum kits.
- [x] Static mixer, master EQ/saturator/mix cluster, project config, Bar menu,
  and confirmed auxiliary raw fields.
- [x] Reusable decoded-space variance index:
  `tools/analyze_spatial_variance.py` with Markdown and JSON output.
- [x] Machine-readable and human-readable spatial maps:
  `docs/format/spatial_coverage_ledger.md` and
  `docs/format/image_coverage_map.md`.
- [x] `midi_to_xy` direct image authoring with 16-pattern banks, 96-scene song
  routing, coherent sparse tracks, and generated-project validation.
- [x] Short, sortable next-capture queue with exact comparisons and evidence
  recording commands.

## Exit criteria

The project-format roadmap is complete when:

1. Every unchecked device-capture item above has an E2 fixture and test, or is
   explicitly classified as runtime/device-global and outside `.xy`.
2. Every generated project passes `xy.project_validation` before being written.
3. XYBuddy passes Swift tests, web tests/check/build, universal Release build,
   code-sign verification, and a byte-identical live MTP round-trip on the
   latest firmware.
4. Device crashes, if any, follow `docs/workflows/crash_capture.md` and have a
   passing follow-up artifact before an item is closed.

Per-field evidence remains in
[`parse_capability_checklist.md`](parse_capability_checklist.md); this roadmap
does not inflate partial device evidence into a completed field.
