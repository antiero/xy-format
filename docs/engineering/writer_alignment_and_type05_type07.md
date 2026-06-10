> **SUPERSEDED (2026-06-09).** This describes the pre-RLE writer model.
> The format is RLE-compressed C structs; author via the decoded image.
> See `docs/engineering/authoring.md` and `docs/format/decoded_image_map.md`.
> Retained for historical context.

# Writer Alignment and Type 0x05/0x07

## Problem Summary
Writer-produced files crashed with `num_patterns > 0` because type/layout alignment rules were violated.

## Verified Rule
- `type=0x05`: includes 2-byte padding (`08 00`) before parameter payload.
- `type=0x07`: padding removed; payload starts 2 bytes earlier.

## Root Cause (Solved)
The writer flipped type semantics without removing stale padding, shifting downstream fields and causing deserialize-time assertion failures.

## Required Behavior
- On `0x05 -> 0x07`, remove the 2-byte padding and keep downstream field alignment correct.
- Alternatively, keep `0x05` path untouched and write compatible payloads for that layout.

## Related Findings
- Handle table is 12 entries of 3 bytes, not 16.
- Uniform shift propagation across downstream tracks is expected when block length changes.

## History
Original session notes: `docs/logs/2025-02-11_variable_length_and_writer_root_cause.md`.
