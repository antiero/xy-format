# Parse & Author Capability Checklist

Living checklist of what this repo can **read**, **write**, and **inspect** in
OP-XY `.xy` project files. Update when a field moves from guessed → decoded →
device-validated.

**Legend**

| Mark | Meaning |
| --- | --- |
| `[x]` | Implemented with tests or corpus/device validation |
| `[~]` | Partial — location or heuristic known; enums/scaling/edge cases open |
| `[ ]` | Not implemented or not pinned to stable offsets |

**Evidence tiers** (use in logs and when marking `[~]`)

| Tier | Meaning | Required citation |
| --- | --- | --- |
| **E0** | Code path only — no fixture | module + unit test or corpus-only diff |
| **E1** | Corpus diff | `src/one-off-changes-from-default/` or change log |
| **E2** | Device probe + in-repo fixture | `src/*-probes/` + `tests/test_*` + dated log |
| **E3** | Device load validated | E2 + operator pass note or `corpus_lab record` |

Every `[x]` row below should cite at least **E1**; prefer **E2** for guide-visible
fields. Heuristic reads must say so and stay `[~]` until structural decode exists.

**Citation format** (inline): `evidence: tests/foo.py · log · fixtures/pack`

**Inspection module index** (2026-06 read APIs)

| Module | Tests | Primary log | Fixtures |
| --- | --- | --- | --- |
| `xy/project_inspection.py` | `test_project_inspection.py` | `2026-06-09_app_preset_probe_inspection.md` | `preset-probes/` (heuristic preset refs) |
| `xy/preset_path_inspection.py` | `test_preset_path_structural.py` | `2026-06-12_preset_path_structural.md` | `2026-06-preset-path/` |
| `xy/drum_sample_inspection.py` | `test_drum_sample_inspection*.py`, `test_drum_pan_fade_inspection.py`, `test_drum_voice_params_inspection.py` | `2026-06-12_drum_sample_path_inspection.md` | `2026-06-sample-paths/`, `2026-06-drum-pan-fade/` |
| `xy/mixer_static_inspection.py` | `test_mixer_static_inspection.py` | `2026-06-12_mixer_static_inspection.md` | `2026-06-static/` |
| `xy/scene_volume_inspection.py` | `test_scene_volume_inspection.py` | `2026-06-12_scene_volume_inspection.md` | `2026-06-volumes/` |
| scene mutes (same module) | `test_scene_track_mute_inspection.py` | `2026-06-12_scene_track_mute_inspection.md` | `2026-06-track-mutes/` |
| `xy/master_eq_inspection.py` | `test_master_eq_inspection.py` | `2026-06-12_master_eq_inspection.md` | `2026-06-eq/` |
| `xy/master_saturator_inspection.py` | `test_master_saturator_inspection.py` | `2026-06-12_master_saturator_inspection.md` | `2026-06-saturator/` |
| `xy/sampler_sample_inspection.py` | `test_sampler_sample_inspection.py` | `2026-06-12_sampler_oneshot_inspection.md` | `2026-06-oneshot/` |
| `xy/project_config_inspection.py` | `test_project_config_inspection.py` | `2026-06-13_project_config_inspection.md`, `2026-06-13_global_header_inspection.md` | `2026-06-project-config/`, `2026-06-global-header/` |
| `xy/bar_menu_inspection.py` | `test_bar_menu_inspection.py` | `2026-06-13_bar_menu_inspection.md`, `2026-06-14_bar_length_inspection.md` | `2026-06-bar-menu/`, `2026-06-bar-length/` |

Contributor workflow: `docs/workflows/contributor_inspection_workflow.md`.

**Primary code paths**

| Layer | Read / inspect | Write |
| --- | --- | --- |
| Container + RLE | `xy/rle.py` (`decode_project`) | `xy/rle.py` (`encode_project`) |
| RAM image edits | `xy/image_writer.py` (`ImageProject`) | same |
| Arrangement assembly | `xy/image_writer.py` (`build_arrangement`) | same |
| Notes | decoded note vector (`tools/inspect_xy.py`, `xy/image_writer.py`) | `ImageProject.add_note` |
| P-locks | `xy/plocks.py` | `ImageProject.set_plock` |
| Step components | `xy/step_components.py` | `ImageProject.set_step_component` |
| Preset reference inference | `xy/project_inspection.py` (heuristic) | `ImageProject.set_preset` (donor copy) |
| Track preset path @ `+0x453F` | `xy/preset_path_inspection.py` | gap — donor `set_preset` only |
| Drum sample path read | `xy/drum_sample_inspection.py` | indirect via `set_preset`; no per-slot path API |
| Static mixer / master bus read | `xy/mixer_static_inspection.py` | gap |
| Scene volumes + mutes read | `xy/scene_volume_inspection.py` | partial write via `build_arrangement` |
| Master EQ / saturator read | `xy/master_eq_inspection.py`, `xy/master_saturator_inspection.py` | partial (`set_master_eq`) |
| Sampler one-shot read | `xy/sampler_sample_inspection.py` | gap |
| Project config/global header read | `xy/project_config_inspection.py` | `set_groove`, `set_groove_amount`, `set_click_volume`, `set_scene_length_mode`, `set_project_transpose`, `set_time_signature`, `set_voice_allocation`, `set_midi_channel`, `set_active_scene`, `set_active_song` |
| Bar menu read | `xy/bar_menu_inspection.py` | `set_pattern_steps`, `set_default_step_length_ticks`, `set_track_quantization_raw`, `set_track_quantization_ui`, `set_track_groove_ui`, `set_plock_shape_raw` |
| Human report | `tools/inspect_xy.py` | — |

Detailed guide cross-reference: `docs/format/opxy_user_guide_save_audit.md`.
Field offsets: `docs/format/decoded_image_map.md`.
**Byte-region overview:** `docs/format/image_coverage_map.md`.

---

## 1. Container & file format

- [x] 8-byte file header (magic, payload length) — `xy/container.py`
- [x] Whole-file RLE decode/encode (245/246 corpus byte-exact) — `xy/rle.py`, `tests/test_rle.py`
- [x] Decoded RAM image as primary edit surface — `docs/format/record_structure.md`
- [~] Non-greedy RLE specimens (e.g. `bleez.xy`) — decode OK, re-encode may shrink — `docs/state_of_understanding.md`

## 2. Global / project header

- [x] Tempo (BPM, u16 tenths) — read: `tools/inspect_xy.py`; write: `ImageProject.set_tempo`
- [x] Groove type enum — read/write: `xy/project_config_inspection.py`, `set_groove`,
  global `0x03`, PCFG `prjconf-t-grv-*`
- [x] Groove amount — signed i8 at global `0x02`, `set_groove_amount`,
  HDR `hdr-grv-*`
- [x] Metronome click volume — `set_click_volume`
- [x] Metronome on/off persistence — HDR probes show no independent toggle byte;
  off and volume-min both persist as click volume `0x00` at global `0x04`
- [x] Per-track MIDI channel (T1–T16) — `set_midi_channel`,
  `xy/project_config_inspection.py`, global `0x55–0x64`, PCFG `prjconf-m-*`
- [x] Master EQ low/mid/high — device-validated min/default/max with exact u32 spill
  lanes — `read_master_eq`, global `0x68/0x6C/0x70`, P2-F `eq0`–`eq8`
- [x] Active scene/song selection — scene slot at global `0x06`, song slot at
  global `0x07` (`0x10` fresh Song 1 sentinel), HDR `hdr-arr-*`
- [x] Project-config scene length mode — `xy/project_config_inspection.py`,
  global `0x08`, PCFG `prjconf-g-slen-*`
- [x] Project transpose — signed i8 at global `0x1B`, range −24..+24,
  `set_project_transpose`, PCFG `prjconf-g-x*`
- [x] Time signature enum — global `0x1C`, `0x10` 3/4 through `0x15` 12/8,
  `set_time_signature`, PCFG `prjconf-t-sig-*`
- [x] Voice allocation / 24-voice priority — T1–T8 at global `0x4D–0x54`,
  `0` auto / `1`–`8` fixed, `set_voice_allocation`, PCFG `prjconf-v-*`
- [x] Internal project display name — no decoded-image name field found; project
  list name is external `.xy` filename, HDR decode search

## 3. Pattern topology

- [x] Leader vs clone pattern structs (17,876 B base) — `docs/format/decoded_image_map.md`, `xy/image_writer.py`
- [x] Pattern count and clone walking in decoded image — `pattern_starts_from_image`, `build_arrangement`
- [x] Scene/song selection rows over pattern indices — `docs/format/scenes_songs.md`

## 4. Sequencer: notes, timing, bars

- [x] Quantized note records (tick, gate, note, velocity, flags) —
  decoded vector at track+`0x456F`, `ImageProject.add_note`
- [x] 120-note pattern cap enforced on write — `ImageProject.add_note`
- [x] Bars per pattern / active steps (full bars: `16`, `32`, `48`, `64` at track+`0x01`) — `set_bars`, `set_pattern_steps`
- [x] Track scale byte (subset: 1/2, 1, 2, 16 observed) — `set_track_scale`
- [~] Track scale full enum (3, 4, 6, 8) — partial — `opxy_user_guide_save_audit.md`
- [x] Final-bar / partial-bar length — total active steps at track+`0x01`;
  `steps = (bars - 1) * 16 + final_bar_steps` — BAR-LEN fixtures
- [x] Per-track quantization amount — raw byte at track+`0x07`;
  UI display `floor(raw * 100 / 255)` — BAR fixtures + generated quant probes
- [x] Default step length (persistent) — u16 ticks at track+`0x02`;
  `240` default, `480` max — `xy/bar_menu_inspection.py`
- [x] Per-track groove override — index byte at track+`0x08`;
  storage is `3 * index` into the displayed UI sequence, saturated at ±99 — BAR fixtures
- [x] P-lock smoothing/shape — raw byte at track+`0x3056`;
  UI labels/icons still open — `xy/bar_menu_inspection.py`

## 5. Step components (14 types)

- [x] 16-byte slots, enabled mask, 14 value bytes — `xy/step_components.py`
- [x] Read/write pulse, hold, velocity, portamento, etc. — `set_step_component`, `STEP_COMPONENTS`
- [~] Complete user-facing value enum for every guide table column — partial — `docs/format/step_components.md`

## 6. Parameter locks

- [x] 64×84-byte table, 42 u16 columns — `xy/plocks.py`
- [x] Param name → column mapping (vol, params, ADSR, sends, LFO, pan, …) — `PLOCK_PARAMS`, `ImageProject.set_plock`
- [x] Automation across steps — `ImageProject.automate_param`
- [~] Static current-value offsets for mix params (vs p-lock-only) — partial — `docs/format/opxy_user_guide_save_audit.md` § Mix

## 7. Instrument, engine, preset

- [x] Engine ID @ track+`0x14` — `set_engine`, `inspect_xy`
- [x] Engine M1 params (4× u32 @ `+0x3857`) — `set_engine_param`
- [x] Amp/filter envelope blocks — `set_track_block`, decoded map
- [x] Filter type/on @ `+0x21`, `+0x25` — `set_filter`
- [x] Filter knobs @ `+0x3897` — decoded map
- [x] Preset identity **write** via donor region copy — `ImageProject.set_preset`, `tests/test_image_writer.py`
- [~] Preset reference **read** (heuristic) per active pattern — fixture-backed inference in
  `xy/project_inspection.py` / `tests/test_project_inspection.py`; stays partial until the
  `0xF7` preset-fragment region is structurally decoded
- [x] Preset path structural **read** @ track `+0x453F` — `xy/preset_path_inspection.py`,
  `tests/test_preset_path_structural.py`, `src/preset-probes/2026-06-preset-path/`
- [~] Preset path **write** @ `+0x453F` — no dedicated writer yet
- [~] Play mode poly/mono/legato current value — partial
- [~] Portamento amount/type, bend range — partial
- [~] Preset volume / engine volume current value — partial
- [~] LFO type and M4 subfunctions — partial, `+0x38B7`, mod matrix `+0x38FF`
- [x] Preset settings: high-pass, velocity sensitivity — decoded map
- [ ] Preset settings: tuning, root, transpose, width — gap
- [ ] Mod-routing destination enum + signed scaling — gap
- [ ] User `.preset` file format (filesystem) — outside `.xy`

## 8. Drum sampler (24 voices)

- [x] 24×128 B voice table @ track+`0x3957` — `set_drum_voice`, `tests/test_image_writer.py`
- [x] Sample path **read** @ slot+`0x08` — `xy/drum_sample_inspection.py`, device fixtures
  `src/drum-sample-probes/2026-06-sample-paths/` + `archive-round0-nt-z-fx/`,
  `tests/test_drum_sample_inspection.py`, `tests/test_drum_sample_inspection_round0.py`
- [~] Sample path **write** — only as part of donor `set_preset` region copy; no
  `set_drum_voice_path()` yet — `docs/format/drum_sample_paths.md`
- [x] Tune, play mode, direction, start, loop-start candidate, end, gain — `set_drum_voice` (tune device-validated);
  **read** via `DrumVoiceSample` (`tune_semitones`, `direction`, `start`, `end`, `gain_u32`) —
  `tests/test_drum_voice_params_inspection.py` (`cap_drum_params.xy`)
- [x] Pan read/write @ slot `+0x06` — device ±100, `tests/test_drum_pan_fade_inspection.py`
- [x] Fade / loop-crossfade @ preceding voice `+0x7C` — `fade_ui`, `encode_drum_fade_ui`,
  `set_drum_voice(..., fade=)`; v23 UI → v22 storage; 21 fade fixtures in
  `tests/test_drum_pan_fade_inspection.py`
- [ ] Drum slicing metadata / choke groups — gap

## 9. One-shot / multisampler slots

- [~] High-level sample table structure — partial — `docs/format/decoded_image_map.md`
- [x] One-shot loop/crossfade/tune/gain/direction per slot — P2-B `g0`–`g14` +
  `g-tune-*`, `decode_sampler_tune_tenths`, `.tune_ui` (header @ `+0x3943`) — gap
- [ ] Multisampler zone boundaries / root key — gap

## 10. Scenes, songs, arrangement

- [x] Scene slots: pattern sel[16] + mute[16] + row-present flag — `build_arrangement`,
  `read_scene_slot_flag`, `read_present_scene_slots`, `docs/format/scenes_songs.md`
- [x] Scene mute (device value 2) — scenes 1–8, slot `N−1` — `tests/test_scene_track_mute_inspection.py`, `scene_mute_storage_slot`, `read_scene_muted_tracks`
- [x] Song footer chain + loop word — `build_arrangement`
- [x] Multi-pattern clone assembly — `build_arrangement`
- [~] 14 song slots vs guide “9 songs” — partial reconciliation — `docs/format/opxy_user_guide_save_audit.md`
- [x] Track mix volume **read** @ track+`0x38FE` (u32 @ `+0x38FB`) —
  `xy/scene_volume_inspection.py`, P2-D `s0b` fixtures; scene routing partial
- [x] Master mix volume **read** @ global+`0x94` — same module (`s5b`)
- [~] Scene-stored volumes **playback** — bytes differ per scene; operator
  heard global mix on 1.1.4 — needs chained capture retest

## 11. Mix, saturator, master

- [x] Master EQ — `xy/master_eq_inspection.py`, P2-F
- [x] Track static volume/pan/send FX1/FX2 **read** @ `+0x38FE`/`+0x38FA`/`+0x38B2`/`+0x38B6`
  — `xy/mixer_static_inspection.py`, P2-A f0–f24 (T1–T8 confirmed)
- [x] Master perc/melody/compressor/master **read** @ global `+0x88`/`+0x8C`/`+0x90`/`+0x94`
  — same module
- [x] Master saturator gain/clip/tone/mix — `read_master_saturator`, global
  `0x78`/`0x7C`/`0x80`/`0x84`, P2-G `sat0`–`sat8`

## 12. Auxiliary tracks (T9–T16)

- [~] Generic track struct, notes, p-locks — same as instrument tracks
- [ ] Brain (T9) settings / routing — gap
- [ ] Punch-in FX (T10) — gap
- [ ] External MIDI channel/bank/program/CC (T11) — gap
- [ ] External CV (T12), audio (T13), tape (T14) — gap
- [~] FX I/II (T15/T16) type enums and params — partial

## 13. Players (arpeggio / maestro / hold)

- [ ] Player enable/type per track — gap
- [ ] Arpeggio parameters — gap
- [ ] Maestro chord buffer — gap
- [ ] Hold player state — gap

## 14. JSON / tooling bridges

- [x] Spec → image compiler — `tools/spec_to_xy_image.py`, `tests/test_midi_to_xy_json_selection.py`
- [x] Corpus index/lab — `tools/corpus_lab.py`
- [x] Round-trip verify — `tools/roundtrip_xy.py`
- [x] Inspector CLI — presets, paths, drums, sampler, mixer, scenes, EQ, saturator, p-lock lanes, project config —
  `tools/inspect_xy.py`, `docs/tools/inspect_xy.md`

## 15. Outside project `.xy`

- [ ] COM / system / Bluetooth / MTP settings — device-global, not in `.xy` — `docs/format/opxy_user_guide_save_audit.md` § COM
- [ ] Sample folder WAV/AIFF on disk — filesystem; only paths referenced in project

---

## How to close a gap

1. Capture one-variable device diff → add fixture under `src/`.
2. Promote offset/rule to `docs/format/decoded_image_map.md` and
   `docs/format/image_coverage_map.md`.
3. Add read path (`inspect_xy`) and/or write path (`ImageProject`).
4. Check the box here and link the test file.
5. Update `docs/format/opxy_user_guide_save_audit.md` if guide-visible.

## Device roundtrip workflow (author → OP-XY → confirm)

Use this when promoting a field from decoded → **device-validated**:

1. **Author** — build or edit with `ImageProject` / `tools/spec_to_xy_image.py` /
   decoded-image spec compiler; save `.xy` under `output/` or `src/`.
2. **Expect** — write a short expectation file (YAML/JSON/markdown) listing what
   you believe the device should show: preset name, drum path per voice, tempo,
   etc. Keep one variable per probe file when possible.
3. **Transfer** — MTP upload to OP-XY (`tools/mtp_upload.py` or app).
4. **Load** — open on hardware; note pass/fail per expectation line.
5. **Capture** — Save As on device; pull `.xy` back; add as fixture under
   `src/*-probes/`.
6. **Verify** — `inspect_xy` + targeted tests; compare author bytes to capture
   where byte-exact writer tests exist (`tests/test_image_writer.py` pattern).

In-repo **software** roundtrip (no device): `tools/roundtrip_xy.py` checks RLE
re-encode; `tests/test_container_roundtrip.py` and corpus parametrized tests
check decode→encode on fixtures. That does **not** prove the device accepts an
authored edit — only that our container layer round-trips.

## Related logs

- App preset probe inspection: `docs/logs/2026-06-09_app_preset_probe_inspection.md`
- Drum sample path inspection: `docs/logs/2026-06-12_drum_sample_path_inspection.md`
- Round 0 `nt-z-fx` paths: `docs/logs/2026-06-12_round0_nt-z-fx_sample_paths.md`
- Drum path format reference: `docs/format/drum_sample_paths.md`
- State-of-understanding ledger: `docs/state_of_understanding.md`
- OP-XY user guide save audit (detailed tables): `docs/format/opxy_user_guide_save_audit.md`
