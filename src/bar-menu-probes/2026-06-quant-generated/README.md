# 2026-06 Quantization Generated Probe Set

PC-authored probes for the BAR menu quantization byte on Scene 1, Track 1,
Pattern 1. Baseline: `../2026-06-bar-menu/bar0.xy`.

Confirmed device formula:

```text
ui = floor(raw * 100 / 255)
```

First pass: all original files matched their filename expectation except
`qg-r253-expect-098.xy`, which displayed `99`. That file was renamed to
`qg-r253-expect-099.xy`, and the hypothesis changed from `/256` to `/255`.
Second pass: the added top-end probes all matched their filename expectations.

The pack intentionally samples boundary flips, especially the top-end buckets,
not all 256 raw bytes.

| File | Raw | Expected UI |
| --- | ---: | ---: |
| `qg-r000-expect-000.xy` | `0x00` | 0 |
| `qg-r002-expect-000.xy` | `0x02` | 0 |
| `qg-r003-expect-001.xy` | `0x03` | 1 |
| `qg-r006-expect-002.xy` | `0x06` | 2 |
| `qg-r008-expect-003.xy` | `0x08` | 3 |
| `qg-r063-expect-024.xy` | `0x3F` | 24 |
| `qg-r064-expect-025.xy` | `0x40` | 25 |
| `qg-r067-expect-026.xy` | `0x43` | 26 |
| `qg-r127-expect-049.xy` | `0x7F` | 49 |
| `qg-r128-expect-050.xy` | `0x80` | 50 |
| `qg-r131-expect-051.xy` | `0x83` | 51 |
| `qg-r191-expect-074.xy` | `0xBF` | 74 |
| `qg-r192-expect-075.xy` | `0xC0` | 75 |
| `qg-r244-expect-095.xy` | `0xF4` | 95 |
| `qg-r245-expect-096.xy` | `0xF5` | 96 |
| `qg-r246-expect-096.xy` | `0xF6` | 96 |
| `qg-r247-expect-096.xy` | `0xF7` | 96 |
| `qg-r248-expect-097.xy` | `0xF8` | 97 |
| `qg-r249-expect-097.xy` | `0xF9` | 97 |
| `qg-r250-expect-098.xy` | `0xFA` | 98 |
| `qg-r251-expect-098.xy` | `0xFB` | 98 |
| `qg-r252-expect-098.xy` | `0xFC` | 98 |
| `qg-r253-expect-099.xy` | `0xFD` | 99 |
| `qg-r254-expect-099.xy` | `0xFE` | 99 |
| `qg-r255-expect-100.xy` | `0xFF` | 100 |

Device inspection result:

All listed files loaded and displayed the expected quantization number in the
BAR menu for Track 1, Pattern 1.

The exact decode/display formula is pinned. The writer can encode a desired UI
value by choosing any raw byte in that display bucket; the smallest raw for a UI
value is `ceil(ui * 255 / 100)`.
