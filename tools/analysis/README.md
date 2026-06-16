# tools/analysis/

Research, probing, and one-off scripts. These are **not** part of the
user-facing contract — they're the evidence trail behind decode decisions.

Scripts here typically fall into one of these classes:
- **`analyze_*`** — corpus sweeps and structural analyses used to build
  decoded-image field hypotheses.
- **`decode_*`**, **`compare_*`** — incremental attempts at cracking
  specific decoded-image regions.
- **`diff_*`**, **`investigate_*`**, **`hunt_*`** — focused A/B byte
  diffing helpers used during single-file deep decodes.
- **`generate_*`** — probe-pack generators that emit `output/scene-probes/`
  and similar directories for device testing.
- **`scene_*`**, **`sentinel_*`**, **`scan_*`**, **`survey_*`** —
  structural indexing helpers.
- **`verify_*`**, **`test_reproduction.py`** — point-in-time validation
  scripts; prefer the pytest suite (`tests/`) for regression coverage.

## When to reach for something here

- You're reproducing an experiment documented in `docs/logs/`. The log
  usually names the exact script.
- You're cracking a new byte region and want templates from similar
  prior work.

## When NOT to reach for something here

- You need to generate a file users will load on device. Use one of the
  top-level user-facing tools instead (see `../`).
- You need a safe, reviewable authoring path. Use `xy/image_writer.py` or
  `tools/spec_to_xy_image.py`.

## Graduating a script

If a script in here represents a rule that's now device-verified, the
right move is usually:
1. Promote the rule into `xy/` as a library function with tests.
2. Expose it through `xy/image_writer.py` or a decoded-image inspection module.
3. Delete or archive the original script with a pointer to its
   replacement.

Scripts here can be deleted without notice if they no longer reproduce
or are superseded by decoded rules.
