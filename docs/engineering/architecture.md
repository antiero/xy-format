# Architecture Notes

> Updated 2026-06-09 for the serialization-model breakthrough. The format
> is a byte-level RLE over the firmware's in-RAM project struct (see
> `docs/format/record_structure.md` §0). Parsing and authoring both go
> through the decoded image, not byte-level heuristics.

## Real Architecture

```
.xy file = 8-byte header + RLE-encoded image
image (~290 KB) = global header (3,449 B)
                + 16 track structs (17,876 B each, + clones for patterns)
                + 14-slot song-table footer
```

- Codec: `xy/rle.py` (`decode_project` / `encode_project`) — greedy
  canonical RLE; round-trips 245/246 corpus files byte-exact.
- Decoded field map: `docs/format/decoded_image_map.md`.
- Reading: decode → index fixed-offset struct fields / count-prefixed
  vectors. Legacy `xy/container.py` (signature-scan over raw bytes) still
  works but operates pre-RLE; prefer the decoded image for new analysis.
- Authoring: `docs/engineering/authoring.md` (`xy/image_writer.py`).

## Principles

- Decode→encode byte comparison is the first-line regression check
  (`tests/test_rle.py`).
- A valid file is a **reachable machine state**: the firmware asserts
  rather than validates, so author by constructing a coherent image
  (defaults + edits + consistent counts), never by inventing byte layouts.
- Keep undecoded regions opaque for round-trip safety; promote findings to
  `docs/format/*` only after corpus + (where possible) device validation.

## Historical Mental-Model Resources

- Legacy synthesis snapshot: `docs/logs/2026-02-13_agents_legacy_snapshot.md`.
- The full arc from heuristics to the struct model:
  `docs/state_of_understanding.md`.
