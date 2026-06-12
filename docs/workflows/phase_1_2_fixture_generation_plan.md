# Phase 1 & 2 — Fixture generation plan

> **Purpose:** Operator-ready capture recipes for every open Phase 1 (read API)
> and Phase 2 (device probe) todo in [`docs/roadmap.md`](../roadmap.md).
>
> **Conventions:** [`device_test_naming.md`](device_test_naming.md) · raw captures
> may live in an external operator workspace · promoted copies in
> `src/app-*-probes/` · analysis logs in `docs/logs/`.

## Global rules (every capture)

| Rule | Why |
| --- | --- |
| Firmware **1.1.4** (note if different) | Matches existing corpus |
| **One variable** per variant file | Isolates decoded diff |
| **Re-open baseline** before each variant (don’t chain edits) | Avoids accidental drift |
| **No pattern notes** unless the mission needs them | Reduces event noise |
| Short on-device name → descriptive PC filename after MTP | `d0` → `d0-baseline-pp.xy` |
| Record pass/crash with `python tools/corpus_lab.py record …` | Traceability |
| README per probe folder: procedure + decoded table | Docs with fixtures |

**Promotion checklist (dev, after you say “done”):**

1. Copy `.xy` → `src/app-*-probes/<pack>/`
2. Add/update `README.md` + `docs/logs/YYYY-MM-DD_<topic>.md`
3. Add `tests/test_*.py` assertions
4. Update `parse_capability_checklist.md` + `decoded_image_map.md` +
   `image_coverage_map.md` if offsets pinned
5. Run `pytest` on new tests

---

## Summary matrix

| ID | Roadmap item | Pack | New captures? | Est. files |
| --- | --- | --- | --- | --- |
| ✅ P1-0 | Preset inference (done) | `app-preset-probes/2026-06-app-required` | No | 36 exist |
| ✅ P1-0b | Drum sample paths (done) | `app-sample-probes/2026-06-sample-paths` | No | 4 + 4 archive |
| P1-A | `project_to_json` export golden | `app-json-golden/` | **Derived** (no device) | ~8 |
| P1-B | Structural preset path `@+0x453F` | `2026-06-preset-path/` | Yes | 6 |
| P2-A | Static mixer vol/pan/send | `2026-06-mixer-static/` | Yes | 12 |
| P2-B | One-shot sampler slots | `2026-06-sampler-oneshot/` | Yes | 15 |
| P2-C | Multisampler zones | `2026-06-sampler-multi/` | Yes | 8 |
| P2-D | Scene-stored track volumes | `2026-06-scene-volumes/` | Yes | 6 |
| P2-E | Scene-stored track mutes | `2026-06-track-mutes/` | Yes | 4 + 9 |
| P2-F | Master EQ bass/mid/treble + power | `2026-06-eq/` | Yes | 9 |
| P2-G | Master saturator | `2026-06-saturator/` | Yes | 9 |
| P3-A | Auxiliary tracks T9–T16 | `2026-06-aux-tracks/` | Yes | 16 |
| P3-B | Players (arp / maestro / hold) | `2026-06-players/` | Yes | 9 |
| M1 | Drum sample paths | (done) | — | — |
| M2 | Preset on T5–P9 | `2026-06-preset-t5-p9/` | Optional | 18 |
| M3 | Drum pan vs fade | `2026-06-drum-pan-fade/` | Yes | 4 |
| M4 | A-series deepen + P8/P9 kick | `app-preset-probes/` (existing) | Maybe 2 | 2 |
| M5 | Phase B complete map | `app-preset-probes/2026-06-phase-b/` | Maybe 0 | 0–11 |
| M6 | Pad→voice non-`pp` kit | `2026-06-pad-voice-map/` | Yes | 4 |

**Suggested capture order:** M3 → P1-B → P2-D → P2-A → P2-B → P2-C → M6 → P3-B → P3-A → M4/M5 analysis → M2 if needed.

---

## Phase 1 — Done (reference only)

### P1-0 — Preset reference inference ✅

| | |
| --- | --- |
| **Fixtures** | `src/app-preset-probes/2026-06-app-required/` (36), `2026-06-phase-b/` (40) |
| **Tests** | `tests/test_project_inspection.py` |
| **No new captures** | Unless M4/M5 gaps below |

### P1-0b — Drum sample paths ✅

| | |
| --- | --- |
| **Fixtures** | `src/app-sample-probes/2026-06-sample-paths/` (4), `archive-round0-nt-z-fx/` (4) |
| **Tests** | `tests/test_drum_sample_inspection.py`, `test_drum_sample_inspection_round0.py` |
| **Doc** | `docs/format/drum_sample_paths.md` |

---

## Phase 1 — Remaining todos

### P1-A — `project_to_json` includes preset refs + drum paths

| | |
| --- | --- |
| **Type** | **Software golden files** (no new device work) |
| **Pack** | `src/app-json-golden/` |
| **Goal** | Lock JSON export shape for inspection fields |

**Procedure (dev machine):**

1. Pick representative `.xy` inputs (already in repo):

   | Source file | Why |
   | --- | --- |
   | `app-preset-probes/.../a1-t1-p9.xy` | 9 drum presets, multi-pattern |
   | `app-preset-probes/.../b1-t1eng3bar1.xy` | Non-drum preset fragment |
   | `app-sample-probes/.../c1-pad01-lowf-v23-chi-box.xy` | Family C drum path |
   | `app-sample-probes/archive-round0-nt-z-fx/c0-pad01-….xy` | Family B path |
   | `src/one-off-changes-from-default/unnamed 1.xy` | Minimal baseline |

2. Run export (once implemented): `project_to_json` → save as
   `<stem>.expected.json` beside a `manifest.yaml` listing source `.xy`.

3. Test: `tests/test_project_to_json_inspection_export.py` — byte-stable JSON
   compare (or semantic diff).

**Deliverables:** 5–8 `.expected.json` + manifest; fixtures live under `src/app-*-probes/`.

---

### P1-B — Structural preset path @ track `+0x453F`

| | |
| --- | --- |
| **Pack** | `src/app-preset-probes/2026-06-preset-path/` |
| **Goal** | Pin exact null-padded string at `+0x453F` vs heuristic `0xF7` fragments |
| **Track** | T1 only, pattern P1, no notes |

**Baseline**

| On-device | PC filename | Setup |
| --- | --- | --- |
| `e0` | `e0-baseline-empty.xy` | New project, T1 default, save |

**Variants** (re-open `e0` baseline each time; change **only** preset):

| On-device | PC filename | Action | Expected `@+0x453F` (verify) |
| --- | --- | --- | --- |
| `e1` | `e1-t1-drum-pp.xy` | T1 engine Drum, preset **`pp`** | `drum/pp` or `/fat32/presets/drum/pp.preset` (record actual) |
| `e2` | `e2-t1-drum-aeroplane.xy` | Drum, user kit **`nt-aeroplane`** | `drum/nt-aeroplane` shape |
| `e3` | `e3-t1-sampler-106bass.xy` | Sampler, **`nt-106 bass`** | `sampler/…` or fragment pattern |
| `e4` | `e4-t1-axis-accord.xy` | Axis, **`nt-accord`** | `synth/…` or `wind/…` |
| `e5` | `e5-t1-engine-only-no-preset.xy` | Change engine (e.g. Prism) **without** picking preset | Bare `/` or empty (per map note) |

**Operator steps (each variant):**

1. Open baseline `e0` from device project list (not previous variant).
2. T1 → select engine type → select preset (steps 3–4 as table).
3. Do **not** add notes or change other tracks.
4. Save As → short name → MTP to PC → rename.

**Analysis:** decoded diff `e0` vs `e1`…`e5` at `track_start(1)+0x453F`; compare to
`project_inspection` heuristic output.

**Tests:** `tests/test_preset_path_structural.py` — exact string per file at offset.

---

### P2-A — Static mixer values (vol / pan / send)

| | |
| --- | --- |
| **Pack** | `src/app-mixer-probes/2026-06-static/` |
| **Goal** | Find **current-value** bytes (not p-lock table) for T1 mix knobs |
| **Prereq** | Initialized project; T1 with any engine; **no p-locks** |

**Baseline:** `f0-baseline-mix-default.xy` — new project, don’t touch mix.

**One knob per file** (T1 mix page; shift page for sends). Re-open `f0` each time.

| On-device | PC filename | UI change (T1) | Record UI value |
| --- | --- | --- | --- |
| `f1` | `f1-t1-vol-min.xy` | Track volume → minimum | 0 or lowest |
| `f2` | `f2-t1-vol-max.xy` | Track volume → maximum | |
| `f3` | `f3-t1-pan-hard-left.xy` | Pan → hard left | |
| `f4` | `f4-t1-pan-hard-right.xy` | Pan → hard right | |
| `f5` | `f5-t1-pan-center.xy` | Pan → center (after f3/f4) | |
| `f6` | `f6-t1-send-a-max.xy` | Shift → Send A max | |
| `f7` | `f7-t1-send-b-max.xy` | Send B max | |
| `f8` | `f8-t1-send-c-max.xy` | Send C max | |
| `f9` | `f9-t1-send-d-max.xy` | Send D max | |
| `f10` | `f10-master-vol-min.xy` | **Master** volume min (if separate) | |
| `f11` | `f11-master-vol-max.xy` | Master volume max | |

**Optional second track** (`f12-t2-vol-max.xy`) — confirm static offset is per-track struct.

**Analysis:** `tools/analysis/decoded_diff.py` f0 vs fN; cross-check p-lock columns
aren’t the only storage (compare to `unnamed 14/16` corpus if needed).

**Tests:** structural offsets + decoded values once mapped.

---

### P2-B — One-shot sampler slot internals ✅

| | |
| --- | --- |
| **Pack** | `src/app-sampler-probes/2026-06-oneshot/` |
| **Engine** | T1 = **Sampler** (`0x02`); preset **`nt-acidic`** |
| **Goal** | Map path, start, loop, end, direction, tune, gain, loop type, crossfade |

**Baseline:** `g0.xy`. Device files `g0`…`g14` (15 captures). Operator README lists each edit.

**Analysis:** Sampler start/end/loop @ `track+0x3943`…`+0x3956` (not drum `slot+0x68`).
Log: `docs/logs/2026-06-12_sampler_oneshot_inspection.md`. **Status:** captured ✅

---

### P2-C — Multisampler zones

| | |
| --- | --- |
| **Pack** | `src/app-sampler-probes/2026-06-multisampler/` |
| **Engine** | T1 = **Multisampler** (engine 6); factory **`bandpasser`** OK |
| **Goal** | Zone boundaries, root key, second zone sample path |

| On-device | PC filename | Action |
| --- | --- | --- |
| `h0` | `h0-baseline-multi.xy` | Load multisampler preset only |
| `h1` | `h1-zone1-sample.xy` | Zone 1: assign known built-in sample (note name) |
| `h2` | `h2-zone2-sample.xy` | Zone 2: different sample (enable 2-zone if needed) |
| `h3` | `h3-zone1-root-c3.xy` | Zone 1 root key → C3 (record MIDI) |
| `h4` | `h4-zone2-root-g3.xy` | Zone 2 root key → G3 |
| `h5` | `h5-zone1-start.xy` | Zone 1 start point only |
| `h6` | `h6-fill-down-on.xy` | Zone fill-down enabled (if UI exists) |
| `h7` | `h7-zone2-tune.xy` | Zone 2 tune only |

**If only factory preset available:** h1–h2 may swap samples within factory zones
first; document limitation in README.

---

### P2-D — Scene-stored track volumes

| | |
| --- | --- |
| **Pack** | `src/app-scene-probes/2026-06-volumes/` |
| **Goal** | Prove guide claim: scenes store per-track volumes separate from pattern |
| **Setup** | 2 scenes, 1 pattern, T1 audible |

| On-device | PC filename | Procedure |
| --- | --- | --- |
| `s0` | `s0-baseline-2scenes.xy` | Scene 1 & 2 exist; same pattern; default volumes |
| `s1` | `s1-scene1-t1-vol-low.xy` | Scene **1** active → T1 volume low → save |
| `s2` | `s2-scene2-t1-vol-high.xy` | Re-open s0 → Scene **2** → T1 volume high → save |
| `s3` | `s3-scene1-t2-vol-low.xy` | Scene 1 → T2 volume low only |
| `s4` | `s4-switch-scene-compare.xy` | After s1+s2: toggle Scene 1/2 on device, **don’t** resave — optional sanity |
| `s5` | `s5-scene1-master-vol.xy` | Scene 1 → master volume change only |

**Critical:** When editing Scene 2, re-open `s0` baseline so Scene 1 volume isn’t
carried unintentionally.

**Analysis:** diff scene struct regions (`docs/format/scenes_songs.md`); look for
16× track volume bytes per scene slot.

---

### P2-E — Scene-stored track mutes

| | |
| --- | --- |
| **Pack** | `src/app-scene-probes/2026-06-track-mutes/` |
| **Goal** | Device-validate per-scene mute bytes (separate from volumes) |
| **Setup** | Scene 1: single-scene project; Scene 2+: two-scene `s0b`-style baseline |

**Naming:** `mute<N>-<t1>-<t2>-<t3>-<t4>.xy` — scene **N**, muted tracks
**1–8**; `#` = unused name slot.

#### Scene 1 (single-scene)

| On-device | PC filename | Procedure |
| --- | --- | --- |
| `mute-#-#-#-#` | `mute-#-#-#-#.xy` | No mutes → baseline |
| `mute-1-3-6-7` | `mute-1-3-6-7.xy` | Re-open baseline → mute T1,T3,T6,T7 |
| `mute-2-7-8-#` | `mute-2-7-8-#.xy` | Re-open baseline → mute T2,T7,T8 |
| `mute-3-4-5-6` | `mute-3-4-5-6.xy` | Re-open baseline → mute T3–T6 |

**Status:** captured ✅

#### Scene 2+ (8-scene / 8-pattern T1 baseline)

Operator procedure: `src/app-scene-probes/2026-06-track-mutes/README.md` § Scene 2+.

| On-device | PC filename | Scene | Muted tracks |
| --- | --- | --- | --- |
| `mute#-#-#-#-#` | `mute#-#-#-#-#.xy` | — | none (baseline) |
| `mute2-1-7-8-#` | `mute2-1-7-8-#.xy` | 2 | T1, T7, T8 |
| `mute3-1-7-8-#` | `mute3-1-7-8-#.xy` | 3 | T1, T7, T8 |
| `mute3-2-3-6-7` | `mute3-2-3-6-7.xy` | 3 | T2, T3, T6, T7 |
| `mute4-6-7-8-#` | `mute4-6-7-8-#.xy` | 4 | T6–T8 |
| `mute5-2-4-6-7` | `mute5-2-4-6-7.xy` | 5 | T2, T4, T6, T7 |
| `mute6-1-7-8-#` | `mute6-1-7-8-#.xy` | 6 | T1, T7, T8 |
| `mute7-2-3-6-7` | `mute7-2-3-6-7.xy` | 7 | T2, T3, T6, T7 |
| `mute8-6-7-8-#` | `mute8-6-7-8-#.xy` | 8 | T6–T8 |

**Analysis:** scene **N** → slot **N − 1**; mute byte `0x02`. Arrange-view mutes
match mixer-view storage. Log: `docs/logs/2026-06-12_scene_track_mute_inspection.md`.

**Status:** captured ✅

---

### P2-F — Master EQ (bass / mid / treble)

| | |
| --- | --- |
| **Pack** | `src/app-mixer-probes/2026-06-eq/` |
| **Goal** | Device-validate global master EQ bytes |
| **Setup** | Fresh project; Master → EQ; one band per file |

| On-device | PC filename | Procedure |
| --- | --- | --- |
| `eq0` | `eq0-baseline.xy` | Fresh project, default EQ |
| `eq1` | `eq1-bass-min.xy` | Re-open eq0 → bass min |
| `eq2` | `eq2-bass-max.xy` | Re-open eq0 → bass max |
| `eq3` | `eq3-mid-min.xy` | Re-open eq0 → mid min |
| `eq4` | `eq4-mid-max.xy` | Re-open eq0 → mid max |
| `eq5` | `eq5-treble-min.xy` | Re-open eq0 → treble min |
| `eq6` | `eq6-treble-max.xy` | Re-open eq0 → treble max |
| `eq7` | `eq7-blend-min.xy` | Re-open eq0 → blend min |
| `eq8` | `eq8-blend-max.xy` | Re-open eq0 → blend max |

**Analysis:** level byte @ `0x68` / `0x6C` / `0x70` (field start); default
`0x40`, min `0x00`, max `0x7F`. Max also sets `0xFF` on prior field tail bytes.
Blend min = byte-identical to baseline; blend max = all three bands `0x7F`.

**Status:** captured ✅ (incl. blend)

---

### P2-G — Master saturator (gain / clip / tone / mix)

| | |
| --- | --- |
| **Pack** | `src/app-mixer-probes/2026-06-saturator/` |
| **Goal** | Device-validate global saturator bytes |
| **Setup** | Fresh project; Master → Saturator; one knob per file |

| On-device | PC filename | Procedure |
| --- | --- | --- |
| `sat0` | `sat0-baseline.xy` | Fresh project |
| `sat1` | `sat1-gain-min.xy` | Re-open sat0 → gain min |
| `sat2` | `sat2-gain-max.xy` | gain max |
| `sat3` | `sat3-clip-min.xy` | clip min |
| `sat4` | `sat4-clip-max.xy` | clip max |
| `sat5` | `sat5-tone-min.xy` | tone min |
| `sat6` | `sat6-tone-max.xy` | tone max |
| `sat7` | `sat7-mix-min.xy` | mix min (= baseline) |
| `sat8` | `sat8-mix-max.xy` | mix max |

**Analysis:** u32 groups @ `0x75`/`0x79`/`0x7D`/`0x81`; level bytes
`0x78`/`0x7C`/`0x80`/`0x84` (mixer-style `u32+3`).

**Status:** captured ✅

---

### P3-A — Auxiliary tracks T9–T16

| | |
| --- | --- |
| **Pack** | `src/app-aux-probes/2026-06-t9-t16/` |
| **Goal** | One capture per aux track with **identifiable** knob moves |
| **Pattern** | Single pattern P1; one bar; optional one note on aux track if it sequences |

**Generic template per track** (prefix = track number):

| Track | Name | On-device | PC example | Min action |
| --- | --- | --- | --- | --- |
| T9 | Brain | `i9-0` | `i9-brain-baseline.xy` | Select Brain track, save |
| T9 | | `i9-1` | `i9-brain-knob1-max.xy` | Turn **knob 1** (manual/auto) to extreme |
| T10 | Punch-in FX | `i10-0`…`i10-1` | `i10-punchin-*.xy` | FX type + one param |
| T11 | External MIDI | `i11-0`…`i11-2` | `i11-midi-*.xy` | Channel, bank, program each file |
| T12 | External CV | `i12-0`…`i12-1` | `i12-cv-*.xy` | CV param |
| T13 | Audio in | `i13-0`…`i13-1` | `i13-audio-*.xy` | Input gain/threshold |
| T14 | Tape | `i14-0`…`i14-1` | `i14-tape-*.xy` | Tape param |
| T15 | FX I | `i15-0`…`i15-2` | `i15-fx1-*.xy` | FX type + 2 params |
| T16 | FX II | `i16-0`…`i16-2` | `i16-fx2-*.xy` | Same |

**Total:** ~16–20 files. Can split across sessions.

**Shortcut (P3):** If time-boxed, capture **T9 Brain + T11 MIDI + T15 FX I** only
(three tracks) → mark others “deferred” in checklist.

---

### P3-B — Players (arpeggio / maestro / hold)

| | |
| --- | --- |
| **Pack** | `src/app-player-probes/2026-06/` |
| **Engine** | T1 = Simple or EPiano (easy to hear) |
| **Goal** | Player enable byte + param block per player type |

| On-device | PC filename | Setup |
| --- | --- | --- |
| `j0` | `j0-baseline-no-player.xy` | T1 preset, player off |
| `j1` | `j1-hold-on.xy` | Enable **Hold** only |
| `j2` | `j2-arp-on-default.xy` | **Arpeggio** on, defaults |
| `j3` | `j3-arp-rate-fast.xy` | Arp on, rate → fastest |
| `j4` | `j4-arp-octave-2.xy` | Arp octave range → 2 |
| `j5` | `j5-maestro-on.xy` | **Maestro** on |
| `j6` | `j6-maestro-2note-chord.xy` | Record 2-note chord in Maestro buffer |
| `j7` | `j7-hold-plus-arp.xy` | Hold + Arp (if combinable — record UI) |
| `j8` | `j8-player-off-after-arp.xy` | Arp on → save → re-open → turn off (optional) |

**Play test:** Hold one key 2s before save on j1; verify LED/state in README note.

---

## Phase 2 — Mission queue (detailed)

### M1 — Drum sample paths ✅

See `src/app-sample-probes/2026-06-sample-paths/README.md`. No further captures unless
Mission **M6** (different kit).

---

### M2 — Preset on T5–P9 (optional / skipped)

| | |
| --- | --- |
| **When** | App needs per-pattern preset on tracks 5–8 |
| **Pack** | `src/app-*-probes/2026-06-preset-t5-p9/` (planned) |
| **Clone of** | A-series but tracks **5–8**, patterns P1–P9 |

**Procedure:** Mirror `2026-06-app-required` using presets `pp`…`xx` on **T5** first
(full P1–P9), then T6–T8.

| Files | Count |
| --- | --- |
| `a5-t5-p1.xy` … `a5-t5-p9.xy` | 9 |
| Repeat for T6, T7, T8 | 27 |
| **Total** | 36 (same shape as app-required) |

**On-device shortcut:** name `u5-1`…`u5-9` then expand on PC to `a5-t5-p1.xy` etc.

---

### M3 — Drum pan vs fade (`+0x05` / `+0x06`) 🔄 NEXT

| | |
| --- | --- |
| **Pack** | `src/app-sample-probes/2026-06-drum-pan-fade/` |
| **Kit** | T1 drum **`pp`** (same as Mission 1) |
| **Voice** | **v03** (pad 4 on `pp` map — confirm on keyboard: G#3 area) OR pick pad you can find reliably; **use same voice in all files** |

| On-device | PC filename | Action |
| --- | --- | --- |
| `d0` | `d0-baseline-pp.xy` | T1 drum `pp`, all defaults |
| `d1` | `d1-v03-pan-hard-left.xy` | Select **voice 3 pad** → shift → **pan** hard left |
| `d2` | `d2-v03-pan-hard-right.xy` | Re-open d0 → same pad → pan hard right |
| `d3` | `d3-v03-fade-max.xy` | Re-open d0 → same pad → **fade** max |

**Optional disambiguation** (if d1–d3 ambiguous):

| `d4` | `d4-v03-pan-center.xy` | Pan center |
| `d5` | `d5-v03-fade-min.xy` | Fade min |

**README must record:** pad number, keyboard note, struct voice index, UI values.

**Expected analysis:** Only slot `+0x05` OR `+0x06` changes per file vs d0 at
`track+0x3957+0x80*voice`.

---

### M4 — A-series: deepen tests + P8/P9 kick silence

| | |
| --- | --- |
| **Fixtures** | Existing 36 files — **analysis-first** |
| **Bug** | P8/P9 sometimes kick silent on `ww`/`xx` presets |

**Dev tasks (no capture required initially):**

1. Extend `test_project_inspection.py` to parametrize **all** `a*-t*-p1.xy`…`p8.xy`
   (not only p9).
2. Diff `a1-t1-p7.xy` vs `a1-t1-p8.xy` vs `a1-t1-p9.xy` — drum paths, preset
   strings, event counts.
3. Compare on-device preset folders `ww.preset` / `xx.preset` patch.json under
   companion preset folders alongside app-required fixtures.

**Optional new captures** (if diff inconclusive):

| PC filename | Purpose |
| --- | --- |
| `a1-t1-p8-kickonly.xy` | P8, remove all notes except one kick step |
| `a1-t1-p9-kickonly.xy` | P9 same |

---

### M5 — Phase B: complete engine/preset byte map

| | |
| --- | --- |
| **Fixtures** | 40 files exist |
| **Issues** | Bar-removal artifact (README); eng9 octave; incomplete eng sweep |

**Dev tasks:**

1. Document **canonical one file per engine** in `2026-06-phase-b/README.md`
   (already partially in tests).
2. Run decoded diff matrix: all `b1-t1eng{N}bar1` vs baseline `b1-t1eng1bar1`.
3. Flag engines missing `bar1` upward capture — **optional recapture:**

| Missing | Suggested file | Action |
| --- | --- | --- |
| eng6 bar1–2 | `b1-t1eng6bar1.xy`, `bar2` | Recreate incrementally from bar1 |
| eng9 bar4 | `b1-t1eng9bar4.xy` | Incremental only |

**Alt captures (note parsing):** Phase B README mentions `*a` suffix projects
(F vs F# note) — if not in repo, add 2 files: `b1-t1eng1bar1a.xy`, `b1-t1eng1bar2a.xy`.

---

### M6 — Pad → voice map (non-`pp` kit)

| | |
| --- | --- |
| **Pack** | `src/app-sample-probes/2026-06-pad-voice-map/` |
| **Clone of** | Mission 1 procedure, different kit |

| On-device | PC filename | Kit | Pad change |
| --- | --- | --- | --- |
| `k0` | `k0-baseline-aeroplane.xy` | Drum **`nt-aeroplane`** | — |
| `k1` | `k1-pad01-lowf-sample.xy` | same | Pad 1 (leftmost low F) → built-in sample |
| `k2` | `k2-pad02-sample.xy` | same | Pad 2 → different sample |
| `k3` | `k3-pad03-sample.xy` | same | Pad 3 → different sample |

**Record:** MIDI key + voice index per pad; compare to `pp` map (v23, v0, v1).

---

## Folder layout template

```text
src/app-<domain>-probes/2026-06-<topic>/
  README.md                 # capture procedure + decode summary + log link
  projects/                 # optional: raw MTP names before rename
  <pc-renamed>.xy
```

**Reproducibility:** keep capture procedures in each fixture-pack README;
when analysis completes, append **Results** and link the dated log under
`docs/logs/`. Generation recipes for open packs live in this file.

---

## Effort estimate (operator time)

| Pack | Session time | Priority |
| --- | --- | --- |
| M3 pan/fade | 15–20 min | **Now** |
| P1-B preset path | 20 min | High |
| P2-D scene volumes | 25 min | High |
| P2-A mixer static | 45 min | Medium |
| M6 pad voice map | 15 min | Medium |
| P2-B oneshot | 40 min | Medium |
| P2-C multisampler | 35 min | Medium |
| P3-B players | 30 min | Lower |
| P3-A aux tracks | 2–3 hrs (or split) | Lower |
| M2 T5–P9 | 2+ hrs | Defer |

---

## Related

- Roadmap: [`docs/roadmap.md`](../roadmap.md)
- Checklist: [`docs/parse_capability_checklist.md`](../parse_capability_checklist.md)
- User guide gaps (priorities): [`docs/format/opxy_user_guide_save_audit.md`](../format/opxy_user_guide_save_audit.md) § Remaining gaps
- Fixture pack READMEs: `src/app-*-probes/*/README.md`
