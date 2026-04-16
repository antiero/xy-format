#!/usr/bin/env python3
"""Compare step component data regions in unnamed 118 vs unnamed 119."""

import sys
import os

# Paths
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_118 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 118.xy")
FILE_119 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 119.xy")

TRACK_SIG = b"\x00\x00\x01\x03\xff\x00\xfc\x00"


def find_track1(data: bytes) -> int:
    """Find offset of Track 1 signature."""
    idx = data.find(TRACK_SIG)
    if idx == -1:
        raise ValueError("Track signature not found")
    return idx


def hexdump(data: bytes, offset: int = 0, width: int = 8) -> str:
    """Format bytes as hex dump with offsets."""
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {offset+i:04X}  {hex_str:<{width*3}}  {ascii_str}")
    return "\n".join(lines)


def find_all_e4(body: bytes) -> list:
    """Find all 0xE4 bytes in the body."""
    positions = []
    idx = 0
    while True:
        idx = body.find(b"\xE4", idx)
        if idx == -1:
            break
        positions.append(idx)
        idx += 1
    return positions


def count_sentinel_ff00(body: bytes, start: int, end: int) -> list:
    """Find ff 00 00 patterns in a range."""
    positions = []
    for i in range(start, min(end, len(body)) - 2):
        if body[i] == 0xFF and body[i+1] == 0x00 and body[i+2] == 0x00:
            positions.append(i)
    return positions


def analyze_file(path: str, label: str):
    print(f"\n{'='*80}")
    print(f"  {label}: {os.path.basename(path)}")
    print(f"{'='*80}")

    with open(path, "rb") as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    # Find Track 1
    sig_offset = find_track1(data)
    print(f"Track 1 signature at file offset: 0x{sig_offset:04X}")

    # Body starts at signature (the preamble is 4 bytes before)
    # Actually, from the container code: body = data[preamble_start+4 : next_preamble]
    # The signature IS the start of the body.
    # But the user says "body starting at block_start+10" — that's 10 bytes into signature
    # Let's use the full body from signature to next track

    # Find next track signature
    next_sig = data.find(TRACK_SIG, sig_offset + len(TRACK_SIG))
    if next_sig == -1:
        body_end = len(data)
    else:
        body_end = next_sig - 4  # 4-byte preamble before next sig

    body = data[sig_offset:body_end]
    print(f"Track 1 body: {len(body)} bytes (file offsets 0x{sig_offset:04X} - 0x{body_end:04X})")

    # Type byte
    type_byte = body[9]
    print(f"Type byte (body[9]): 0x{type_byte:02X}")

    # Engine ID
    if type_byte == 0x05:
        engine_id = body[0x0D]
    else:
        engine_id = body[0x0B]
    print(f"Engine ID: 0x{engine_id:02X}")

    # For type-07, slot table starts at body offset 0x22
    # Print body[0x20:0x30] for context
    print(f"\nBody[0x20..0x40] (slot table region):")
    print(hexdump(body[0x20:0x40], 0x20))

    # Find all E4 markers
    e4_positions = find_all_e4(body)
    print(f"\nAll 0xE4 byte positions in body: {[f'0x{p:04X}' for p in e4_positions]}")

    # Look for E4 in the slot table area (0x22 - 0x200)
    e4_in_range = [p for p in e4_positions if 0x20 <= p <= 0x200]
    print(f"0xE4 in slot table area (0x20-0x200): {[f'0x{p:04X}' for p in e4_in_range]}")

    for e4_off in e4_in_range:
        print(f"\n--- E4 marker at body offset 0x{e4_off:04X} ---")

        # 3 bytes before
        if e4_off >= 3:
            before = body[e4_off-3:e4_off]
            print(f"  3 bytes BEFORE E4: {' '.join(f'{b:02X}' for b in before)}")

        # Byte after E4 (flag/mode byte)
        if e4_off + 1 < len(body):
            after_byte = body[e4_off + 1]
            print(f"  Byte AFTER E4 (flag/mode): 0x{after_byte:02X}")

        # Dump up to 140 bytes after E4
        dump_end = min(e4_off + 140, len(body))
        dump_data = body[e4_off:dump_end]
        print(f"\n  Full data block ({len(dump_data)} bytes from E4):")
        print(hexdump(dump_data, e4_off))

    # Look for alloc byte 0x06 near E4 markers
    print(f"\nSearching for alloc byte 0x06 in body[0x20..0x100]:")
    for i in range(0x20, min(0x100, len(body))):
        if body[i] == 0x06:
            context = body[max(0,i-4):i+5]
            print(f"  0x06 at body offset 0x{i:04X}, context: {' '.join(f'{b:02X}' for b in context)}")

    # Count ff 00 00 sentinels
    sentinels_early = count_sentinel_ff00(body, 0x20, 0x80)
    sentinels_mid = count_sentinel_ff00(body, 0x80, 0x200)
    print(f"\nFF 00 00 sentinels in body[0x20..0x80]: {len(sentinels_early)} at {[f'0x{p:04X}' for p in sentinels_early]}")
    print(f"FF 00 00 sentinels in body[0x80..0x200]: {len(sentinels_mid)} at {[f'0x{p:04X}' for p in sentinels_mid]}")

    # Also dump broader area for context: body[0x20..0x120]
    print(f"\n  Full body[0x20..0x120] ({min(0x100, len(body)-0x20)} bytes):")
    end = min(0x120, len(body))
    print(hexdump(body[0x20:end], 0x20))

    return sig_offset, body


def byte_diff(body1: bytes, body2: bytes, label1: str, label2: str, max_bytes: int = 400):
    print(f"\n{'='*80}")
    print(f"  BYTE-BY-BYTE DIFF: first {max_bytes} bytes of T1 body")
    print(f"{'='*80}")

    n = min(max_bytes, len(body1), len(body2))
    diffs = []
    for i in range(n):
        if body1[i] != body2[i]:
            diffs.append(i)

    print(f"Total differences in first {n} bytes: {len(diffs)}")
    if not diffs:
        print("  (no differences)")
        return

    # Group contiguous diffs into ranges
    ranges = []
    start = diffs[0]
    end = diffs[0]
    for d in diffs[1:]:
        if d == end + 1:
            end = d
        else:
            ranges.append((start, end))
            start = d
            end = d
    ranges.append((start, end))

    for rstart, rend in ranges:
        ctx_start = max(0, rstart - 2)
        ctx_end = min(n, rend + 3)
        print(f"\n  Diff region: body[0x{rstart:04X}..0x{rend:04X}] ({rend - rstart + 1} bytes)")
        print(f"  {label1} context [0x{ctx_start:04X}..0x{ctx_end:04X}]:")
        chunk1 = body1[ctx_start:ctx_end]
        print(f"    {' '.join(f'{b:02X}' for b in chunk1)}")
        # Mark changed bytes
        markers = []
        for i in range(ctx_start, ctx_end):
            if i in diffs:
                markers.append("^^")
            else:
                markers.append("  ")
        print(f"    {' '.join(markers)}")
        print(f"  {label2} context [0x{ctx_start:04X}..0x{ctx_end:04X}]:")
        chunk2 = body2[ctx_start:ctx_end]
        print(f"    {' '.join(f'{b:02X}' for b in chunk2)}")

    # Also show a side-by-side table of all diffs
    print(f"\n  Summary of all {len(diffs)} changed bytes:")
    print(f"  {'Offset':<10} {label1:<8} {label2:<8}")
    for d in diffs:
        print(f"  0x{d:04X}     0x{body1[d]:02X}     0x{body2[d]:02X}")


def main():
    sig118, body118 = analyze_file(FILE_118, "unnamed 118 (UNIFORM: Hold on all 16 steps)")
    sig119, body119 = analyze_file(FILE_119, "unnamed 119 (MIXED: 14 different types + 2 repeats)")
    byte_diff(body118, body119, "u118", "u119", max_bytes=400)

    # Extended diff for the full body overlap
    print(f"\n{'='*80}")
    print(f"  EXTENDED DIFF: full body overlap")
    print(f"{'='*80}")
    n = min(len(body118), len(body119))
    diffs_all = []
    for i in range(n):
        if body118[i] != body119[i]:
            diffs_all.append(i)
    print(f"Total diffs across {n} bytes: {len(diffs_all)}")
    if len(diffs_all) > len([d for d in diffs_all if d < 400]):
        extra = [d for d in diffs_all if d >= 400]
        print(f"  Diffs beyond byte 400: {len(extra)} at offsets {[f'0x{d:04X}' for d in extra[:20]]}{'...' if len(extra) > 20 else ''}")

    # Body size comparison
    print(f"\n  Body sizes: u118={len(body118)}, u119={len(body119)}, delta={len(body119)-len(body118)}")


if __name__ == "__main__":
    main()
