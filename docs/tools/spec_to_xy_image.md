# spec_to_xy_image.py

`tools/spec_to_xy_image.py` compiles a MIDI/arrangement JSON spec into a
device-loadable `.xy` file through the decoded-image writer.

It uses the canonical path:

```text
baseline .xy -> xy.rle.decode_project -> xy.image_writer.build_arrangement -> xy.rle.encode_project
```

## Usage

```bash
python tools/spec_to_xy_image.py specs/midi-to-xy/song.json -o output/song.xy
python tools/spec_to_xy_image.py specs/midi-to-xy/song.json -o output/song.xy --baseline "src/one-off-changes-from-default/unnamed 1.xy"
```

Useful options:

- `--no-scenes`: write pattern clones without scene rows.
- `--no-song`: write scenes but skip the Song 1 chain.
- `--keep-empty-tracks`: preserve explicit empty pattern clones.
- `--min-velocity N`: drop notes below velocity `N` before writing.

## Spec Shape

```json
{
  "version": 1,
  "template": "src/one-off-changes-from-default/unnamed 1.xy",
  "output": "output/from-midi/song.xy",
  "tracks": [
    {
      "track": 1,
      "patterns": [
        [{"step": 1, "note": 60, "velocity": 100, "gate_ticks": 480}],
        null
      ]
    }
  ]
}
```

Each note may use `step` or explicit `tick`, plus optional `velocity`,
`tick_offset`, and `gate_ticks`.

This replaces the removed legacy JSON compiler. Do not add descriptor,
preamble, scaffold, event-type, or profile fields to new specs.
