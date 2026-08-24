# 2026-08-24 — OP-XY OS 1.1.25 compatibility

Official release date: 2026-08-19. The
[OP-XY downloads page](https://teenage.engineering/downloads/op-xy) still lists
1.1.25 as the newest release, and connected-device MTP discovery reports
firmware `1.1.25`.

Official changes with project/tooling impact:

- New quantization grids for track scales x3, x5, x6, and x7.
- Improved multisample behavior with global transpose.
- Normal note-off/release when stopping Hold player.
- New patterns inherit the current player type.

## Complete release-note audit

Every official 1.1.25 item was classified so a runtime fix is not mistaken for
a new serialized field:

| Official change | XYBuddy / `.xy` consequence |
| --- | --- |
| Odd x3/x5/x6/x7 quantization grids | Read/write/timing/UI implemented; raw enum remains E0 pending one controlled odd-scale save. |
| Multisamples with global transpose | Existing opaque zone/player bytes are preserved; fresh paired captures remain required before zone authoring is claimed. |
| Hold player now sends normal note-off/release | Runtime playback change. Player state is preserved, but its enable/type/parameter block still needs a 1.1.25 capture. |
| New patterns inherit current player type | Clone construction now preserves the complete source pattern state instead of rebuilding only known fields. |
| Same-named user/factory preset folders | Device preset-browser UX; no new project field. XYBuddy's captured factory presets copy donor state without reconstructing device paths; user-preset browsing is not claimed. |
| Voice-stealing indicator rework | Device UI/runtime only. |
| Delay no longer reacts to jittery external tempo | DSP/clock runtime only. |
| Notes near pattern end quantize correctly | Sequencer runtime fix; event tick storage and signed pickup ticks are unchanged. Do not add a writer-side compensating nudge. |
| Overlapping notes no longer confuse arpeggio | Player runtime fix; overlapping note records remain valid serialized input. |
| User tunings load consistently into user slots | Device loading fix. Known tuning slot/root/width and raw tuning lanes remain preserved; the 12-note table still needs controlled captures. |
| Same note two octaves apart can be added to a step | Input UI fix; the note vector already permits both records. |
| Audio-only USB no longer appears disconnected | Device USB/system behavior, outside `.xy` and MTP project transfer. |
| EPiano parameter names corrected | Device label fix; it does not change stored engine ID or raw parameter lanes. |
| Muted arpeggio tracks no longer replay stale held notes | Runtime player fix; no format change. |
| Maestro input blocked while Bar screen is shown | Device UI/input routing only. |
| Project duplication includes unsaved changes | Device workspace/copy behavior; no new serialized field. XYBuddy still operates only on the bytes it downloads. |
| TRS MIDI notes restored when externally clocked over TRS | Runtime MIDI routing fix, outside `.xy`. |

The only new authoring surfaces are therefore odd scales and inherited player
state. Multisampler/transpose and Hold behavior change how existing state is
interpreted at runtime and justify fresh captures, but not guessed writers.

Implemented off-device:

- Full scale enum in Python and browser read/write/timing/UI.
- Coherent trigger + p-lock + step-component rotation in Python and XYBuddy,
  matching the device's current sequencer behavior.
- Restored the Pattern workspace to the current post-import navigation; the
  scale and rotation controls were implemented but unreachable from the newer
  Arrange/Song-only project surface.
- Generated-project preflight and metronome-off direct output.
- Fresh capture queue for the device-dependent scale, multisampler, and player
  fields.

Evidence boundary: existing corpus anchors prove 1/2, 1, 2, 4, 8, and 16.
The x3/x5/x6/x7 raw values follow the contiguous enum between those anchors and
are covered by writer/browser tests, but remain E0 until the ordered
device-saved captures are returned.

## Verification

- Python: 1,562 tests passed and 25 skipped, including validation of a freshly
  decoded image with no cached track indexes.
- Browser: 126 tests passed and 3 skipped; Svelte/type checks reported no
  errors or warnings; the production build completed.
- Hosted app: GitHub Pages deployment `32763615823` completed successfully and
  the macOS host loaded the restored Pattern/Arrange/Song navigation.
- macOS: all 35 Swift tests passed. The Release app, MTP helper, libmtp, and
  libusb are universal arm64/x86_64 binaries with minimum macOS 14.6; deep
  code-sign and bundled-web verification passed.
- Live OP-XY: firmware 1.1.25, serial `XXYVP11X`. XYBuddy exported track 1 at
  scale x5 (`0x08`), uploaded `z_fw125_e2e.xy` to Templates, and read it back
  byte-identically (SHA-256
  `3ee643b276092a35ef8e59b6c642fc3c5de0b47e34f081b70351658db0644748`).
  Exact remote object 310 was deleted afterward; a final snapshot contained
  only the pre-existing `amen2.xy` template.

## Read-only connected corpus audit

A temporary export inspected 203 existing project/current-backup files without
changing the OP-XY. The current 1.1.25 `workspace.xy` decoded as 16 tracks and
passed structural validation. An older device-saved `sevend.xy` (2026-04-28)
contains credible x3 (`0x06`) and x6 (`0x09`) values in a coherent 16-track
layout. It is useful private corroboration, but it was not copied into this
public repository and therefore does not promote the odd-scale rule to E2.

One apparent x5 value came from an older file whose decoded layout resolves to
only 15 tracks and whose surrounding fields are incoherent, so it was rejected
as evidence. No controlled x5 or x7 device-save pair was present. The temporary
device export was removed after this audit.

A later read-only MTP inventory found no additional user-preset corpus to mine:
`/presets` contained only an empty `/presets/snapshot` folder. The remaining
user `.preset` variants therefore still require deliberate captures rather
than inference from unrelated projects or sample filenames.
