# App preset probe fixtures

Device-authored `.xy` captures used to validate read-only project preset
inspection (`xy/project_inspection.py`, `tests/test_project_inspection.py`).

## Families

### `2026-06-app-required/` (36 files)

Tracks 1–4 with nine active patterns each. Patterns P1–P9 use drum preset
folders `pp` through `xx` (one note on step 1 per pattern). Firmware 1.1.4.

Capture procedure: see `docs/logs/2026-06-09_app_preset_probe_inspection.md`.

### `2026-06-phase-b/` (40 files)

Engine sweep on track 1: Axis, Dissolve, Drum, EPiano, Hardsync,
Multisampler, Organ, Prism, Sampler, Simple, Wavetable — each with a
known factory preset and one or more bars of notes.

Bar-length variants exist for several engines; tests use the canonical
one-bar (or noted) filenames listed in `tests/test_project_inspection.py`.

## Related captures

Companion drum preset folders (`pp` … `xx`) and extended capture notes live
in the OP-XY MTP Manager repo under `reference_material/user_probes/`.
