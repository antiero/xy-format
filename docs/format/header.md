# Header / Global Region

This page documents decoded-image global offsets. Older raw-header scans used
different offsets because they read compressed bytes; those notes are historical
only and should not guide authoring.

Coverage overview: [`image_coverage_map.md`](image_coverage_map.md).

## Decoded Project-Config Bytes

Firmware 1.1.4 project-config probes (`src/project-config-probes/2026-06-project-config/`)
pin guide-visible decoded-image bytes. Use these offsets, not historical
raw/header scans, for image-space inspection and authoring:

- `0x00-0x01` tempo in tenths of BPM, u16 LE.
- `0x02` signed groove amount.
- `0x03` groove type enum.
- `0x04` metronome/click volume. HDR toggle probes did not reveal a separate
  on/off byte; off and volume-min both persist as `0x00`.
- `0x06` active scene slot.
- `0x07` active song slot.
- `0x08` scene length mode.
- `0x1B` signed global transpose.
- `0x1C` time signature enum.
- `0x4D–0x54` T1–T8 voice allocation.
- `0x55–0x64` T1–T16 MIDI channel map.

Use `xy/project_config_inspection.py` and `docs/format/decoded_image_map.md`
as the authoritative map for these fields.

## Global Mix / Master Bytes

Other decoded global fields are mapped in `docs/format/image_coverage_map.md`:

- Master EQ band values: `0x68`, `0x6C`, `0x70`.
- Master saturator gain/clip/tone/mix: level bytes at `0x78`, `0x7C`,
  `0x80`, `0x84`.
- Master percussion/melody/compressor/output bytes: `0x88`, `0x8C`,
  `0x90`, `0x94`.

## Tooling

- Header reader utility: `docs/tools/read_xy_header.md`
- Project config inspection: `xy/project_config_inspection.py`
- Inspector workflow: `docs/workflows/inspector_sweep.md`
