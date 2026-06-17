# Preset corpus

Status: partial corpus, captured alphabetically
Firmware target: OP-XY 1.1.4

This directory pairs OP-XY `.preset` folders with projects where track 1 was
assigned the corresponding preset on device.

## Layout

- `presets/<name>.preset/patch.json` — preset metadata and sample-region JSON.
- `presetprojs/<name>.xy` — project saved after loading that preset on track 1.

The project set is intentionally incomplete because each project requires a
manual on-device load/save pass. `docs/logs/2026-06-16_preset_corpus_analysis.md`
records the current inventory and coverage.

## Capture procedure

For each preset:

1. Start from the baseline project used by the corpus batch.
2. Load `<name>.preset` onto track 1.
3. Save the project on device.
4. Copy the saved project to `presetprojs/<name>.xy`.

The filename stem must match the preset folder stem exactly so
`tools/analysis/analyze_preset_corpus.py` can pair them automatically.

## Notes

- Audio files are not needed for analysis once the device-authored project has
  been captured; committed preset folders keep `patch.json` only.
- The corpus is broad but observational. It is good at finding common field
  lanes and bad at proving enum boundaries or fields that do not vary in the
  captured presets.
- Focused follow-up probes live under `src/preset-load-experiments/` when a
  corpus field needs direct A/B confirmation.
