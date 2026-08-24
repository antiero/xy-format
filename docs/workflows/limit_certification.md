# Limit Certification

Generate the four ordered acceptance projects:

```bash
python tools/build_limit_probes.py
```

The ignored `output/limit-probes/` directory will contain:

1. `01_scenes99.xy` — all 99 scene rows present; T1 cycles through 16 patterns.
2. `02_song96.xy` — Song 1 contains scene references 1…96.
3. `03_patterns16.xy` — T1 has 16 distinct patterns and a 16-scene chain.
4. `04_notes120.xy` — one 64-step T1 pattern contains exactly 120 notes.

The generator runs `xy.project_validation` on every file. Its regression test
also proves that adding note 121 is rejected before export.

## Device order

Load the files alphabetically on the current firmware. Confirm scene 99 can be
selected, the 96-entry song reaches its last entry, Pattern 16 plays, and the
120-note project loads and plays without truncation. Record each result:

```bash
python tools/corpus_lab.py record output/limit-probes/01_scenes99.xy pass --note "OS VERSION: scene 99 selected"
python tools/corpus_lab.py record output/limit-probes/02_song96.xy pass --note "OS VERSION: song reached entry 96"
python tools/corpus_lab.py record output/limit-probes/03_patterns16.xy pass --note "OS VERSION: pattern 16 played"
python tools/corpus_lab.py record output/limit-probes/04_notes120.xy pass --note "OS VERSION: 120-note pattern loaded and played"
```

Do not mark the roadmap acceptance boxes complete from an MTP transfer alone;
they require the corresponding device UI/playback observation.
