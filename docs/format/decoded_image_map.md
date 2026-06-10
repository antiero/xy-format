# Decoded Image Map (Canonical)

> The `.xy` file after its 8-byte header is one RLE stream (see
> `docs/format/record_structure.md` §0 and `xy/rle.py`). This document
> maps the **decoded RAM image** — the firmware's project struct — built
> from a corpus-wide join of decoded diffs × the one-off change log
> (2026-06-09). Offsets are for baseline `unnamed 1.xy`
> (decoded size 289,521 bytes) unless marked track-relative.

## Image Layout

```
0x00000          global header            (3,449 bytes)
0x00D79 + k*0x45D4   track struct k=0..15 (17,876 bytes each)
end − 53         footer: song table       (53 bytes)
```

`3,449 + 16×17,876 + 53 = 289,521` exactly. Adding a pattern inserts one
more 17,876-byte struct (clones in raw space were full copies because the
struct *is* the pattern). Track structs grow only via count-prefixed
vectors (notes: +12 bytes each).

## Global Header Fields

| offset | field | evidence |
|---|---|---|
| 0x00 | tempo, u16 LE tenths of BPM (+ related byte at 0x04 region) | u4, u5 |
| 0x03 | groove type | u11, u12 |
| 0x04 | metronome/click volume | u10 |
| 0x06 | song/scene count-ish (songs: u13; scenes: 152/153 touch 0x06–0x07) | u13, u152 |
| 0x07 | selected song/scene ordinal | u149, u151 |
| 0x55–0x64 | per-track MIDI channel array, 1 byte/track (T1=0x55 … T16=0x64) | u41, u54 |
| 0x68 / 0x6C / 0x70 | master EQ low / mid / high (4-byte fields) | u14, u15, u16 |

(Scene records — the 33-byte structs of `record_structure.md` §4 — also
live in the global region in scene-bearing files.)

## Track Struct (track-relative offsets; track base = header byte 0)

| offset | field | evidence |
|---|---|---|
| +0x00 | pattern count (leader) | header decode |
| +0x01 | bar count (`bars<<4` nibble byte) | u17–u19 |
| +0x02 | 0xF0 marker | — |
| +0x03 | signature `00 00 00 [scale] FF 00 FC 00` | — |
| +0x06 | **track scale** (0x01=½, 0x03=1, 0x05=2, 0x0E=16) | u20–u22 |
| +0x11 | u16: **8 = pristine, 0 = edited** — the raw "type 0x05/0x07 + `08 00` padding" was this field's RLE shadow; sticky (never returns to 8) | u51, u53, every edit file |
| +0x1C | M4/LFO type selector (5 bytes change on LFO swap) | u32 |
| +0x20 | M4 page on/off | u31, u33 |
| +0x21 | filter type (SVF/Ladder) | u28 |
| +0x25 | filter on/off | u29 |
| +0x3057 + 16×(step−1) | **step-component slot, 16 bytes per step**, one byte per component type within the slot (portamento +9, bend +10, tonality +11, jump +12, param +13, conditional +14, …) | u8/u9, u59–u77 |
| +0x3857 | engine parameter block: 4-byte values (param1 +0x3857, param4 +0x3863, …) | u23–u25, u96 |
| +0x3877 | M2 amp envelope ADSR (16 bytes) | u26 |
| +0x3897 | M3 filter knobs (16 bytes) | u30 |
| +0x38B7 | M4 values (16 bytes + extras) | u32, u33 |
| +0x38D7 | filter envelope ADSR (16 bytes) | u27 |
| +0x3900–0x393B | modulation routing matrix (modwheel/aftertouch/pitchbend targets & amounts) | u83, u84 |
| +0x3919 / +0x392F | velocity sensitivity / track high-pass filter | u82, u40 |
| +0x3CBF | 2-byte UI-state (last-touched?) — co-changes with edits | u40, u66, u82 |
| ~+0x456F | **note event area**: `[count u8]` + 12-byte note records `{u32 tick; u32 gate; u8 note; u8 vel; u8 flags[2]}` (tick 480/16th, gate 240 = default) | u81 decode |
| end | trailing zero region (raw-space "tail byte" = its run extension) | — |

**Aux tracks**: T15 = FX1, T16 = FX2 — FX type changes substitute in the
same engine-param offsets (+0x3857…) of those structs (u36, u37).
Engine swaps are size-preserving (param block fixed-size, u34).

## Footer (last 53 bytes)

The 14-slot song table (`record_structure.md` §5):
`[scene_count][scene_ids…][loop_word]` per song; song 2/3 edits land at
FOOTER+0x2/+0xA (u149, u151–153).

## Method

`tools/analysis/decoded_diff.py` against the baseline, joined with
`src/one-off-changes-from-default/op-xy_project_change_log.md`. Most
one-off files are pure substitutions of 1–16 bytes at the offsets above;
files that add notes/patterns grow by exactly 12 / 17,876 bytes.

## Open

- Event-type byte (raw 0x1C–0x2D) placement/meaning in decoded space.
- Full step-component slot byte order (per-type map is partial).
- The 0x4620 `40 1F` pairs and per-bar arrays near the event area.
- Sample-table region inside drum/sampler structs (decodes to large
  zero/FF fields; not yet field-mapped).
- Naive differ misaligns after insertions; an alignment-aware decoded
  diff would clean up note-file attributions.
