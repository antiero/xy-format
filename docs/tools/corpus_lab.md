# corpus_lab.py

`tools/corpus_lab.py` is the SQLite-backed corpus index/query tool for cross-file structural analysis.

## Database
- Default path: `output/corpus_lab.sqlite`

## Indexed Data
- File-level: `path`, `source`, `size`, `sha1`, parse status/error, and
  historical raw-scan columns kept for old database compatibility.
- Legacy raw-scan columns such as `pre_track_len`, `pre56_hex`,
  `ff_table_start`, `descriptor_var_hex`, `logical_entries`, `pre0..pre3`,
  `body_len`, `type_byte`, and tail-event metadata are **not** canonical
  decoded-image format fields.
- Test outcomes: `status` (`pass|crash|untested`), optional `error_class`, note, timestamp.

## Common Commands
- `python tools/corpus_lab.py index`
- `python tools/corpus_lab.py sql "SELECT name,size,logical_entries FROM files ORDER BY size DESC LIMIT 20"`
- `python tools/corpus_lab.py report clone-pre1`
- `python tools/corpus_lab.py report topology --where "f.source='oneoff'"`
- `python tools/corpus_lab.py record output/k04_song_safefix2_12347.xy pass --note "device OK"`
- `python tools/corpus_lab.py results --where "f.name LIKE 'k0%'"`
- `python tools/corpus_lab.py report result-summary`

## Current Use

Use this tool primarily for corpus inventory and device outcome tracking. For
new decoded-image field analysis, prefer `tools/analyze_spatial_variance.py`,
`tools/analysis/decoded_diff.py`, and the inspection modules listed in
`docs/parse_capability_checklist.md`.
