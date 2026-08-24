# 2026-08-24 — OP-XY OS 1.1.25 compatibility

Official release date: 2026-08-19. Connected-device MTP discovery reports
firmware `1.1.25`.

Official changes with project/tooling impact:

- New quantization grids for track scales x3, x5, x6, and x7.
- Improved multisample behavior with global transpose.
- Normal note-off/release when stopping Hold player.
- New patterns inherit the current player type.

Other release notes (delay response to jittery external tempo, duplicate
factory/user folder-name UX, and voice-stealing indication) are runtime/UI
behavior and do not imply a `.xy` layout change.

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
