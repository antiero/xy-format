# midi_to_xy.py

`tools/midi_to_xy.py` imports MIDI into OP-XY authoring artifacts.

## New Project From MIDI

Use `--new-project` when there is no existing `.xy` project to edit:

```bash
python3 tools/midi_to_xy.py song.mid --new-project -o output/from-midi/song.xy
python3 tools/midi_to_xy.py song.mid --new-project --bpm 98 -o output/from-midi/song.xy
```

The tool starts from the known-good blank baseline, splits the MIDI into
4-bar OP-XY patterns, assigns useful source lanes to OP-XY tracks by role,
creates scene/song state, sets the MIDI tempo, and writes a decoded-image
authored `.xy`.

Useful options:

- `--patterns N`: force the number of 4-bar patterns, up to 9.
- `--start-bar N`: start from a later bar.
- `--bpm N`: override the output project tempo when MIDI metadata is wrong.
- `--info`: print lane scoring and pattern density without writing a file.
- `--format json`: emit the intermediate JSON spec instead of `.xy`.

Single-lane polyphonic MIDI is kept on one chord track; missing secondary
slots are not auto-duplicated unless there are multiple assigned source parts.
