# PC-Generated Brain Bucket Validation

PC-authored probes from `t09-brain-baseline.xy` for device load tests. Each file
writes a candidate T9 encoder word at `+0x385B` (key) or `+0x385F` (scale), then
re-encodes. **Not device-confirmed yet.**

Hypothesis under test:

```text
key_index   = floor(raw * 12 / 0x80000000)
scale_index = floor(raw *  7 / 0x80000000)
```

Bucket boundaries (inclusive, contiguous, full `0x00000000..0x7FFFFFFF` range):

```text
lo(k)  = ceil(k * M / N)
hi(k)  = floor(((k + 1) * M - 1) / N)     where M = 0x80000000
```

## Brain key/root — 12 buckets @ T9 `+0x385B`

| Bucket | Output | Lowest raw | Lowest hex | Highest raw | Highest hex |
| -----: | ------ | ---------: | ---------: | ----------: | ----------: |
| 0 | C | 0 | `0x00000000` | 178,956,970 | `0x0AAAAAAA` |
| 1 | C# | 178,956,971 | `0x0AAAAAAB` | 357,913,941 | `0x15555555` |
| 2 | D | 357,913,942 | `0x15555556` | 536,870,911 | `0x1FFFFFFF` |
| 3 | D# | 536,870,912 | `0x20000000` | 715,827,882 | `0x2AAAAAAA` |
| 4 | E | 715,827,883 | `0x2AAAAAAB` | 894,784,853 | `0x35555555` |
| 5 | F | 894,784,854 | `0x35555556` | 1,073,741,823 | `0x3FFFFFFF` |
| 6 | F# | 1,073,741,824 | `0x40000000` | 1,252,698,794 | `0x4AAAAAAA` |
| 7 | G | 1,252,698,795 | `0x4AAAAAAB` | 1,431,655,765 | `0x55555555` |
| 8 | G# | 1,431,655,766 | `0x55555556` | 1,610,612,735 | `0x5FFFFFFF` |
| 9 | A | 1,610,612,736 | `0x60000000` | 1,789,569,706 | `0x6AAAAAAA` |
| 10 | A# | 1,789,569,707 | `0x6AAAAAAB` | 1,968,526,677 | `0x75555555` |
| 11 | B | 1,968,526,678 | `0x75555556` | 2,147,483,647 | `0x7FFFFFFF` |

## Brain scale — 7 buckets @ T9 `+0x385F`

| Bucket | Output | Lowest raw | Lowest hex | Highest raw | Highest hex |
| -----: | ------ | ---------: | ---------: | ----------: | ----------: |
| 0 | major | 0 | `0x00000000` | 306,783,378 | `0x12492492` |
| 1 | dorian | 306,783,379 | `0x12492493` | 613,566,756 | `0x24924924` |
| 2 | phrygian | 613,566,757 | `0x24924925` | 920,350,134 | `0x36DB6DB6` |
| 3 | lydian | 920,350,135 | `0x36DB6DB7` | 1,227,133,513 | `0x49249249` |
| 4 | mixolydian | 1,227,133,514 | `0x4924924A` | 1,533,916,891 | `0x5B6DB6DB` |
| 5 | minor | 1,533,916,892 | `0x5B6DB6DC` | 1,840,700,269 | `0x6DB6DB6D` |
| 6 | locrian | 1,840,700,270 | `0x6DB6DB6E` | 2,147,483,647 | `0x7FFFFFFF` |

## Files (38)

Two probes per bucket: `-lo-` (lowest raw) and `-hi-` (highest raw). Expected UI
is in the filename (`pcgen-expect-key-{note}-{lo|hi}-{raw}.xy` or
`pcgen-expect-scale-{mode}-{lo|hi}-{raw}.xy`).

Regenerate:

```bash
PYTHONPATH=. python tools/generate_brain_pcgen_probes.py
```

If any file loads but shows a different key/scale, keep the returned file and
record the observed UI value below before analysis.

## Device results

_(append after MTP round-trip)_
