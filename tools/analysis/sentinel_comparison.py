#!/usr/bin/env python3
"""Deep structural comparison of FF 00 00 sentinel tables across specimens."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from xy.container import XYProject

CORPUS = Path(__file__).resolve().parent.parent / "src" / "one-off-changes-from-default"

# Files to analyze
MULTI_STEP = ["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"]
SINGLE_STEP = ["unnamed 59.xy", "unnamed 61.xy", "unnamed 62.xy", "unnamed 66.xy", "unnamed 68.xy"]
BASELINE = ["unnamed 1.xy"]
ALL_FILES = BASELINE + SINGLE_STEP + MULTI_STEP

SENTINEL = bytes([0xFF, 0x00, 0x00])

# Focus region for structural sentinels
REGION_START = 0x0010
REGION_END = 0x0120  # Generous range to catch everything


def find_all_sentinel_offsets(body: bytes, region_start=0, region_end=None):
    """Find all occurrences of FF 00 00 in body within region."""
    if region_end is None:
        region_end = len(body)
    offsets = []
    pos = region_start
    while pos <= region_end - 3:
        idx = body.find(SENTINEL, pos, region_end)
        if idx == -1:
            break
        offsets.append(idx)
        pos = idx + 1  # Allow overlapping searches (though unlikely)
    return offsets


def group_contiguous_runs(offsets):
    """Group offsets into contiguous runs (entries at N, N+3, N+6...)."""
    if not offsets:
        return []
    runs = []
    current_run = [offsets[0]]
    for i in range(1, len(offsets)):
        if offsets[i] == current_run[-1] + 3:
            current_run.append(offsets[i])
        else:
            runs.append(current_run)
            current_run = [offsets[i]]
    runs.append(current_run)
    return runs


def analyze_file(name):
    """Load file and analyze Track 1 sentinel structure."""
    path = CORPUS / name
    proj = XYProject.from_bytes(path.read_bytes())
    track = proj.tracks[0]  # Track 1
    body = track.body
    type_byte = body[0x09] if len(body) > 0x09 else None

    # Find sentinels in structural region
    region_offsets = find_all_sentinel_offsets(body, REGION_START, REGION_END)
    # Also find sentinels in ENTIRE body for completeness
    all_offsets = find_all_sentinel_offsets(body, 0, len(body))

    runs = group_contiguous_runs(region_offsets)

    return {
        "name": name,
        "body_size": len(body),
        "type_byte": type_byte,
        "region_offsets": region_offsets,
        "all_offsets": all_offsets,
        "runs": runs,
        "body": body,
    }


def main():
    results = {}
    for name in ALL_FILES:
        results[name] = analyze_file(name)

    # -- Section 1: Summary Table --
    print("=" * 100)
    print("SENTINEL TABLE COMPARISON (FF 00 00 entries in Track 1 body)")
    print("=" * 100)
    print()
    print(f"{'File':<20} {'Body Size':>10} {'Type':>6} {'Region FF0000':>14} {'Total FF0000':>13} {'Runs':>6}")
    print("-" * 75)
    for name in ALL_FILES:
        r = results[name]
        print(f"{name:<20} {r['body_size']:>10} 0x{r['type_byte']:02X}   {len(r['region_offsets']):>10}     {len(r['all_offsets']):>10}  {len(r['runs']):>5}")

    # -- Section 2: Run Breakdown --
    print()
    print("=" * 100)
    print("RUN BREAKDOWN (contiguous FF 00 00 sequences in region 0x0010-0x0120)")
    print("=" * 100)
    for name in ALL_FILES:
        r = results[name]
        print(f"\n  {name} (body={r['body_size']}, type=0x{r['type_byte']:02X}):")
        if not r['runs']:
            print("    (no sentinel runs in region)")
        for i, run in enumerate(r['runs']):
            start = run[0]
            end = run[-1] + 2  # Last byte of last entry
            count = len(run)
            print(f"    Run {i+1}: start=0x{start:04X}, count={count:>3}, end=0x{end:04X} (span={end - start + 1} bytes)")

    # -- Section 3: Offset-by-offset comparison --
    print()
    print("=" * 100)
    print("OFFSET-BY-OFFSET SENTINEL PRESENCE (region 0x0010-0x0120)")
    print("=" * 100)

    # Collect all unique sentinel offsets across all files
    all_unique_offsets = set()
    for name in ALL_FILES:
        all_unique_offsets.update(results[name]['region_offsets'])
    all_unique_offsets = sorted(all_unique_offsets)

    # Build presence matrix
    header = f"{'Offset':>8}"
    for name in ALL_FILES:
        short = name.replace("unnamed ", "u").replace(".xy", "")
        header += f" {short:>8}"
    print(header)
    print("-" * len(header))

    for offset in all_unique_offsets:
        row = f"0x{offset:04X}  "
        for name in ALL_FILES:
            r = results[name]
            body = r['body']
            if offset in r['region_offsets']:
                row += f" {'FF0000':>8}"
            elif offset + 2 < len(body):
                b = body[offset:offset+3]
                row += f" {b[0]:02X}{b[1]:02X}{b[2]:02X}".rjust(9)
            else:
                row += f" {'---':>8}"
        print(row)

    # -- Section 4: Key comparison - unnamed 118 vs 118b --
    print()
    print("=" * 100)
    print("KEY COMPARISON: unnamed 118.xy vs unnamed 118b.xy")
    print("What replaces sentinels when they are 'consumed'?")
    print("=" * 100)

    r118 = results["unnamed 118.xy"]
    r118b = results["unnamed 118b.xy"]
    body118 = r118["body"]
    body118b = r118b["body"]

    # Offsets where 118 has FF 00 00 but 118b doesn't
    only_in_118 = set(r118["region_offsets"]) - set(r118b["region_offsets"])
    only_in_118b = set(r118b["region_offsets"]) - set(r118["region_offsets"])
    in_both = set(r118["region_offsets"]) & set(r118b["region_offsets"])

    print(f"\n  Sentinels in 118 only:  {len(only_in_118)} at offsets {['0x%04X' % o for o in sorted(only_in_118)]}")
    print(f"  Sentinels in 118b only: {len(only_in_118b)} at offsets {['0x%04X' % o for o in sorted(only_in_118b)]}")
    print(f"  Sentinels in both:      {len(in_both)} at offsets {['0x%04X' % o for o in sorted(in_both)]}")

    if only_in_118:
        print("\n  Sentinels CONSUMED in 118b (present in 118, absent in 118b):")
        for offset in sorted(only_in_118):
            b118 = body118[offset:offset+3]
            if offset + 2 < len(body118b):
                b118b = body118b[offset:offset+3]
                print(f"    0x{offset:04X}: 118={b118.hex(' ')} -> 118b={b118b.hex(' ')}")
                # Show wider context
                ctx_start = max(0, offset - 6)
                ctx_end = min(len(body118b), offset + 9)
                print(f"           118  context [{ctx_start:04X}-{ctx_end:04X}]: {body118[ctx_start:ctx_end].hex(' ')}")
                print(f"           118b context [{ctx_start:04X}-{ctx_end:04X}]: {body118b[ctx_start:ctx_end].hex(' ')}")
            else:
                print(f"    0x{offset:04X}: 118={b118.hex(' ')} -> 118b=BEYOND BODY END")

    if only_in_118b:
        print("\n  Sentinels ADDED in 118b (absent in 118, present in 118b):")
        for offset in sorted(only_in_118b):
            if offset + 2 < len(body118):
                b118 = body118[offset:offset+3]
            else:
                b118 = b"---"
            b118b = body118b[offset:offset+3]
            print(f"    0x{offset:04X}: 118={b118.hex(' ') if isinstance(b118, bytes) and len(b118) == 3 else '---'} -> 118b={b118b.hex(' ')}")

    # -- Section 5: Full diff of 118 vs 118b in sentinel region --
    print()
    print("=" * 100)
    print("BYTE-LEVEL DIFF: unnamed 118 vs 118b (region 0x0010-0x0120)")
    print("=" * 100)

    min_len = min(len(body118), len(body118b), REGION_END)
    diff_count = 0
    for offset in range(REGION_START, min_len):
        if body118[offset] != body118b[offset]:
            diff_count += 1
            if diff_count <= 200:  # Limit output
                print(f"  0x{offset:04X}: 118=0x{body118[offset]:02X}  118b=0x{body118b[offset]:02X}")
    if diff_count > 200:
        print(f"  ... ({diff_count - 200} more differences)")
    print(f"\n  Total byte differences in region: {diff_count}")

    # Also check if bodies are different lengths
    if len(body118) != len(body118b):
        print(f"  NOTE: Body sizes differ! 118={len(body118)}, 118b={len(body118b)}, delta={len(body118b)-len(body118)}")

    # -- Section 6: Compare multi-step files against baseline --
    print()
    print("=" * 100)
    print("MULTI-STEP FILES vs BASELINE (unnamed 1.xy)")
    print("=" * 100)

    baseline = results["unnamed 1.xy"]
    baseline_offsets = set(baseline["region_offsets"])
    baseline_body = baseline["body"]

    for name in MULTI_STEP:
        r = results[name]
        offsets = set(r['region_offsets'])
        body = r['body']

        consumed = baseline_offsets - offsets
        added = offsets - baseline_offsets
        common = baseline_offsets & offsets

        print(f"\n  {name}:")
        print(f"    Baseline sentinels: {len(baseline_offsets)}, This file: {len(offsets)}")
        print(f"    Common: {len(common)}, Consumed: {len(consumed)}, Added: {len(added)}")

        if consumed:
            print(f"    Consumed sentinel offsets: {['0x%04X' % o for o in sorted(consumed)]}")
            for offset in sorted(consumed):
                if offset + 2 < len(body):
                    replacement = body[offset:offset+3]
                    print(f"      0x{offset:04X}: baseline=FF 00 00 -> this={replacement.hex(' ')}")
                    # Wider context
                    ctx_s = max(0, offset - 3)
                    ctx_e = min(len(body), offset + 6)
                    print(f"        context: {body[ctx_s:ctx_e].hex(' ')}")

    # -- Section 7: Also scan outside the region for completeness --
    print()
    print("=" * 100)
    print("FF 00 00 OCCURRENCES OUTSIDE REGION (0x0120+)")
    print("=" * 100)
    for name in ALL_FILES:
        r = results[name]
        outside = [o for o in r['all_offsets'] if o >= REGION_END]
        if outside:
            print(f"\n  {name}: {len(outside)} occurrences outside region:")
            for o in outside[:20]:  # Limit
                body = r['body']
                ctx_s = max(0, o - 3)
                ctx_e = min(len(body), o + 6)
                print(f"    0x{o:04X}: context={body[ctx_s:ctx_e].hex(' ')}")
            if len(outside) > 20:
                print(f"    ... ({len(outside) - 20} more)")
        else:
            print(f"  {name}: none outside region")

    # -- Section 8: Hex dump of sentinel region for all files --
    print()
    print("=" * 100)
    print("HEX DUMP OF SENTINEL REGION (0x0020-0x00A0) for key files")
    print("=" * 100)
    KEY_FILES = ["unnamed 1.xy", "unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"]
    for name in KEY_FILES:
        r = results[name]
        body = r['body']
        print(f"\n  {name}:")
        for row_start in range(0x0020, min(0x00A0, len(body)), 16):
            row_end = min(row_start + 16, len(body))
            hex_str = " ".join(f"{body[i]:02X}" for i in range(row_start, row_end))
            ascii_str = "".join(chr(body[i]) if 32 <= body[i] < 127 else "." for i in range(row_start, row_end))
            print(f"    {row_start:04X}: {hex_str:<48} {ascii_str}")


if __name__ == "__main__":
    main()
