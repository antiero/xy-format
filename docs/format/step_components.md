# Step Components

> **Model superseded (2026-06-09).** The byte-level facts here remain
> useful, but the format is RLE-compressed C structs; the canonical
> references are `docs/format/record_structure.md` and
> `docs/format/decoded_image_map.md`. See `docs/state_of_understanding.md`.


## Decoded-Image Location

Current authoring uses the fixed decoded-image track struct:

- Step component slots start at track struct `+0x3057`.
- There are 16 step slots.
- Each slot is 16 bytes.
- The first bytes are an enabled/component mask; following bytes hold component
  values.

`ImageProject.set_step_component(track, step, component, value)` writes this
table directly. It does not activate raw body layouts, compute allocation
markers, or emit compressed-space sentinels.

## Component Names

The canonical authoring names live in `ImageProject.STEP_COMPONENTS`:

```text
pulse, hold, multiply, velocity, ramp_up, ramp_down, random, portamento,
bend, tonality, jump, parameter, conditional, trigger
```

Bank-2 type `0x20` is confirmed as the 14th component type.

## Validation Status
- Multiple component types are byte-exact and device-verified through
  `tests/test_image_writer.py`.
- Some type-specific repeat/sub-parameter semantics remain open.

## Detailed Notes
- Historical section dump: `docs/logs/2026-02-13_agents_legacy_snapshot.md`
