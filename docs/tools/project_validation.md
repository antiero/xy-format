# Generated Project Validation

`xy/project_validation.py` checks generated or edited decoded-image projects
before they reach an OP-XY. It preserves unknown bytes and reports only
invariants that can be established off-device.

```python
from xy.project_validation import validate_project_bytes

report = validate_project_bytes(data, generated=True)
if report.errors:
    raise ValueError(report.describe())
```

Checks include:

- 16-track and 1–16-pattern topology;
- 1–64 active steps and 120-note maximum;
- known track-scale and instrument-engine bytes;
- fixed-field NUL termination for preset/sample paths;
- sampler path, framecount, window, and gain preflight;
- non-empty clean drum mappings and duplicate key warnings;
- scene selections referencing available patterns;
- metronome-off expectation for generated files.

Multisampler zone internals deliberately remain a warning: the writer preserves
their bytes, but zone boundaries/root keys do not have enough device evidence
for a safe validator yet.

`tools/midi_to_xy.py` and `tools/spec_to_xy_image.py` run this preflight by
default. Errors stop the write; warnings are printed without blocking safe
round-trip preservation.
