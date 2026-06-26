# midi_to_xy.py

`tools/midi_to_xy.py` imports MIDI into OP-XY authoring artifacts.

## New Project From MIDI

Use `--new-project` when there is no existing `.xy` project to edit:

```bash
python3 tools/midi_to_xy.py song.mid --new-project -o output/from-midi/song.xy
python3 tools/midi_to_xy.py song.mid --new-project --bpm 98 -o output/from-midi/song.xy
```

The tool starts from the known-good blank baseline, splits the MIDI into
4-bar windows, assigns useful source lanes to OP-XY tracks by role, creates
scene/song state, sets the MIDI tempo, and writes a decoded-image authored
`.xy`.

OP-XY has a hard limit of nine patterns per instrument track. The importer
therefore stores each distinct 4-bar window once, reuses it from later Song
scenes, and uses a spare instrument track as a muted pattern bank when a
source lane needs more than nine distinct windows. This preserves the full
timeline for songs up to 96 four-bar scenes (384 bars). It stops with a clear
error rather than silently truncating longer projects or arrangements that
cannot fit into eight instrument pattern banks.

Useful options:

- `--patterns N`: force the number of 4-bar Song scenes, up to 96.
- `--start-bar N`: start from a later bar.
- `--bpm N`: override the output project tempo when MIDI metadata is wrong.
- `--info`: print lane scoring and pattern density without writing a file.
- `--format json`: emit the intermediate JSON spec instead of `.xy`.

Single-lane polyphonic MIDI is kept on one chord track; missing secondary
slots are not auto-duplicated unless there are multiple assigned source parts.
