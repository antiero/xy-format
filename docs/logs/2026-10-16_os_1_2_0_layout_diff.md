# OS 1.2.0 decoded-layout diff and write-validation plan

Date: 2026-10-16

Goal: decide what evidence is needed to unlock project writes for OS 1.2.0
(container header `ddccbbaa09140786`), starting from the fixtures already in
the corpus.

## Fixtures compared

| key | file | header | decoded |
|---|---|---|---:|
| old | `src/one-off-changes-from-default/unnamed 1.xy` | `09130386` | 289,521 |
| 1.1.21 | `src/factory-preset-captures/firmware-1.1.21/batches/fp01.xy`, `fp02.xy` | `09130686` | 289,521 |
| 1.2.0 | `src/factory-preset-captures/firmware-1.2.0/batches/drumline01.xy`, `drumline02.xy` | `09140786` | 289,521 |

There is no blank 1.2.0 project in the corpus yet. The Drumline captures are
the best substitute. Each was saved once from a fresh blank project with only
Tracks 1–8 reassigned, so the global header, Tracks 9–16 and the footer are
effectively blank-project state.

All five files re-encode byte-exact with `xy/rle.py`.

## Results

Controls: two captures from the same firmware differ only in Tracks 1–8,
where the presets differ. There are no global, Track 9–16 or footer
differences within either firmware.

1.1.21 → 1.2.0, outside the reassigned tracks:

| region | 1.1.21 | 1.2.0 | `09130386` | notes |
|---|---|---|---|---|
| global `0x3D..0x44` (8 B) | `fe fe fe fe fe fe fe fe` | `00 × 8` | `00 00 ff 01 00 ff 00 00` | **New finding.** Sits inside opaque `global.pre_scene_cluster` (`0x08..0x54`), just before T1–T8 voice allocation at `0x4D`. Eight bytes suggests a per-track array for T1–T8. Its meaning is unknown (E0). It may relate to the 1.2.0 per-track USB audio routing, but that is a hypothesis. |
| T9–T16 `+0x38F2`, `+0x38F6` | `0x40` | `0x00` | `0x00` | Already documented as a project-config save side effect (`decoded_image_map.md`). 1.2.0 fresh projects match the old fresh baseline. Not a 1.2.0 change. |

No other byte differs. In particular:

- Track 1 still starts at 3,449, with the same 17,876-byte track stride and
  16 leaders.
- The footer is still the 56-byte, 14-slot song table.
- The Drumline engine is a size-preserving in-place substitution in the
  track struct, like every earlier engine swap.

Conclusion: on blank-project evidence, family `0x14` (minor `0x07`) uses the
`0x13` decoded topology. The only unexplained global delta is
`0x3D..0x44`. The likely new per-track fields for filter drive and detune
cannot show up in these fixtures, because neither was edited. They probably
sit in currently-zero opaque track bytes, which the image writer already
preserves by editing in place.

## Code gaps found

Status: gaps 1 and 2 were fixed on 2026-10-16.

- `0x14` is now an explicit `TRACK_BASE_BY_FIRMWARE` entry, covered by
  `test_os_1_2_0_header_family_maps_to_0x13_topology`.
- Donors whose header byte 5 is newer than the target project are withheld:
  - MIDI import falls back to the category default.
  - The piano-roll picker shows them as needing a newer OS.
  - `trackStructForPreset` throws `PresetFirmwareError`.

  See `donorFitsTarget` in `web/src/lib/xy/opXyPresets.ts`. Remove the gate
  only if `j_` passes.

1. **`xy/image_writer.py` `TRACK_BASE_BY_FIRMWARE` has no `0x14` entry.** It
   falls back to `TRACK_BASE0`, which happens to be 3,449, so it is correct
   only by accident. Add `0x14: 3449` explicitly, with a test using
   `drumline01.xy`.
2. **Web MIDI import authors on `public/baselines/blank.xy` (`09130386`), but
   the preset chooser now offers Drumline donors.** A MIDI import that picks a
   Drumline preset produces an old-header file that contains a 1.2.0-only
   engine:
   - On OS ≤ 1.1.x that is an engine the firmware does not know, so expect a
     crash.
   - On 1.2.0 it is untested.

   Until hardware test `j_` below passes, gate Drumline donors to authoring on
   a 1.2.0 baseline. Failing that, label the export "OS 1.2.0+ only" and block
   it when the target is known to be older.
3. `projectCompatibility.ts` `KNOWN_EDITABLE_HEADER_VERSIONS` correctly
   excludes `09140786` today. Keep it that way until the gate below passes.

## Hardware validation plan

Device: OP-XY on OS 1.2.0. Use the default USB audio mode unless a step says
otherwise. Filenames sort in test order (AGENTS.md). Record every result with
`python tools/corpus_lab.py record <file> <pass|crash|untested> --note "..."`
and follow `docs/workflows/crash_capture.md` for any crash.

### Phase 1: device-authored captures

Each capture starts from **New project**, makes only the listed change, and
saves once. Copy the files into
`src/one-off-changes-from-default/firmware-1.2.0/`.

| file | change | what it answers |
|---|---|---|
| `a_blank.xy` | nothing | True 1.2.0 blank baseline. Is `0x3D..0x44` zero, and are T1–T8 identical to the 1.1.21 blank? |
| `b_t1_note.xy` | T1, step 1, one C4 note, default velocity | Note vector unchanged? Target for byte-exact writer replication. |
| `c_t1_2pat.xy` | add pattern 2 on T1 | Pattern struct growth is still 17,876 B. |
| `d_song.xy` | create scene 2 and chain song 1 = scenes 1,2 | Footer and scene slab unchanged. |
| `e_plock.xy` | T1, one p-lock on step 1 (filter cutoff) | P-lock lane layout unchanged. |
| `f_usb8ch.xy` | switch USB audio to `8 ch`, save | Is the USB mode project-scoped? Does `0x3D..0x44` move? |
| `g_drive.xy` | T1 filter drive: one detent | Locates the filter-drive field (mapping, not gating). |
| `h_detune.xy` | T1 preset detune: one detent | Locates the detune field (mapping, not gating). |
| `i_resave_old.xy` | load a 1.1.21 project (`fp01.xy`), save unchanged | **Key test.** How does the firmware migrate old files? Header rewrite, `0x3D..0x44` normalisation, other fixups. |

Desk work after Phase 1:

- `decoded_diff.py a_blank.xy <each>` and `decoded_diff.py fp01.xy i_resave_old.xy`.
- Update `decoded_image_map.md` and `spatial_coverage_ledger.md`.
- **Gate 1 (desk):** `xy/image_writer.py` and the TS writer, starting from
  `a_blank.xy`, reproduce `b_`, `c_`, `d_` and `e_` **byte-exact**.

### Phase 2: authored files loaded on the device

These are generated from `a_blank.xy`, keeping header `09140786`. Do not up- or
down-convert headers.

| file | content |
|---|---|
| `01_note.xy` | Writer replica of `b_t1_note.xy`. Must be byte-identical before loading. |
| `02_arrange.xy` | `spec_to_xy_image.py` multi-track, multi-pattern, scenes and song chain, with p-locks |
| `03_drumline.xy` | Drumline donor (`atom`) on T1 with a 16-step pattern, plus `we will c` on T2 |
| `04_midi.xy` | Web MIDI import on a 1.2.0 baseline with mixed presets, including Drumline |
| `j_old_hdr_drumline.xy` | Today's web output: `09130386` baseline plus Drumline donor. Tests gap 2. |

Pass criteria for each file:

1. It loads without an assert.
2. It plays the expected notes and sounds.
3. Save it on the device and pull it back. The decoded diff against the
   authored file shows only known UI and pristine-flag churn.

This is evidence tier **E3**.

### Gate 2: enable writes

All of the following must hold:

- Gate 1 passes.
- `01_`–`04_` pass E3.
- `i_resave_old.xy` is understood.

Then:

- Add `0x14` to `TRACK_BASE_BY_FIRMWARE` (Python and TS).
- Add `09140786` to `KNOWN_EDITABLE_HEADER_VERSIONS`.
- Ship a 1.2.0 blank baseline beside the old one, and choose the baseline by
  target firmware. Drumline donors require the 1.2.0 baseline.
- Treat `0x3D..0x44` and any newly found drive/detune bytes as opaque, copied
  from the source project, never defaulted.
- Add regression tests over all Phase 1 and Phase 2 fixtures.

If `j_old_hdr_drumline.xy` crashes, keep the old-header + Drumline combination
blocked permanently.
