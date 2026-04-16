#!/usr/bin/env python3
"""Compare structural details of two .xy files to diagnose firmware crashes.

Usage:
    python tools/compare_n110.py

Compares:
  - Known good: src/unnamed 110.xy  (n110 device-captured)
  - Generated:  output/bring_me_to_life_v2.xy
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from xy.container import XYProject

GOOD_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "unnamed 110.xy")
GEN_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "bring_me_to_life_v2.xy")


def load_project(path: str) -> XYProject:
    with open(path, "rb") as f:
        data = f.read()
    return XYProject.from_bytes(data)


def hex_dump(data: bytes, max_bytes: int = 0) -> str:
    """Return space-separated hex of data, optionally truncated."""
    if max_bytes and len(data) > max_bytes:
        return " ".join(f"{b:02X}" for b in data[:max_bytes]) + " ..."
    return " ".join(f"{b:02X}" for b in data)


def print_file_details(label: str, proj: XYProject, raw: bytes) -> None:
    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")

    # Pre-track region
    pt = proj.pre_track
    print(f"\nPre-track region: {len(pt)} bytes (0x{len(pt):X})")

    # Hex dump of descriptor area 0x50-0x80
    start, end = 0x50, min(0x80, len(pt))
    if start < len(pt):
        print(f"\nPre-track bytes 0x50-0x{end:02X} (descriptor area):")
        for row_start in range(start, end, 16):
            row_end = min(row_start + 16, end)
            hex_part = " ".join(f"{pt[i]:02X}" for i in range(row_start, row_end))
            ascii_part = "".join(
                chr(pt[i]) if 32 <= pt[i] < 127 else "." for i in range(row_start, row_end)
            )
            print(f"  0x{row_start:04X}: {hex_part:<48s}  |{ascii_part}|")
    else:
        print(f"  (pre-track too short for 0x50-0x80 range)")

    # If pre-track is longer than 0x80, also dump up to 0xA0
    if len(pt) > 0x80:
        ext_end = min(0xA0, len(pt))
        print(f"\nPre-track bytes 0x80-0x{ext_end:02X} (extended descriptor area):")
        for row_start in range(0x80, ext_end, 16):
            row_end = min(row_start + 16, ext_end)
            hex_part = " ".join(f"{pt[i]:02X}" for i in range(row_start, row_end))
            ascii_part = "".join(
                chr(pt[i]) if 32 <= pt[i] < 127 else "." for i in range(row_start, row_end)
            )
            print(f"  0x{row_start:04X}: {hex_part:<48s}  |{ascii_part}|")

    # Track blocks summary
    print(f"\nNumber of track blocks: {len(proj.tracks)}")
    print(f"\n{'Idx':>3s}  {'Preamble':<12s}  {'Type':>4s}  {'BodyLen':>8s}  {'First 20 bytes of body':<62s}  {'Last 10 bytes'}")
    print(f"{'---':>3s}  {'--------':<12s}  {'----':>4s}  {'-------':>8s}  {'-'*62:<62s}  {'-'*30}")

    for tb in proj.tracks:
        preamble_hex = hex_dump(tb.preamble)
        body_len = len(tb.body)
        first20 = hex_dump(tb.body[:20])
        last10 = hex_dump(tb.body[-10:]) if body_len >= 10 else hex_dump(tb.body)
        type_byte = f"0x{tb.type_byte:02X}" if body_len > 9 else "N/A"
        print(f"{tb.index:>3d}  {preamble_hex:<12s}  {type_byte:>4s}  {body_len:>8d}  {first20:<62s}  {last10}")


def compare_preambles(good: XYProject, gen: XYProject) -> None:
    print(f"\n{'='*80}")
    print(f"  PREAMBLE COMPARISON (by slot position)")
    print(f"{'='*80}")
    print(f"\n{'Slot':>4s}  {'Good Preamble':<14s}  {'Gen Preamble':<14s}  {'Match':>5s}  {'Good Bars':>9s}  {'Gen Bars':>8s}")
    print(f"{'----':>4s}  {'-'*14:<14s}  {'-'*14:<14s}  {'-----':>5s}  {'-'*9:>9s}  {'-'*8:>8s}")

    for i in range(min(len(good.tracks), len(gen.tracks))):
        g = good.tracks[i]
        n = gen.tracks[i]
        g_hex = hex_dump(g.preamble)
        n_hex = hex_dump(n.preamble)
        match = "YES" if g.preamble == n.preamble else "** NO **"
        g_bars = g.bar_count
        n_bars = n.bar_count
        print(f"{i:>4d}  {g_hex:<14s}  {n_hex:<14s}  {match:>8s}  {g_bars:>9d}  {n_bars:>8d}")


def compare_body_sizes(good: XYProject, gen: XYProject) -> None:
    print(f"\n{'='*80}")
    print(f"  BODY SIZE COMPARISON (all slots)")
    print(f"{'='*80}")
    print(f"\n{'Slot':>4s}  {'Good Size':>10s}  {'Gen Size':>10s}  {'Delta':>8s}  {'Good Type':>9s}  {'Gen Type':>8s}")
    print(f"{'----':>4s}  {'-'*10:>10s}  {'-'*10:>10s}  {'-'*8:>8s}  {'-'*9:>9s}  {'-'*8:>8s}")

    for i in range(min(len(good.tracks), len(gen.tracks))):
        g = good.tracks[i]
        n = gen.tracks[i]
        g_len = len(g.body)
        n_len = len(n.body)
        delta = n_len - g_len
        delta_str = f"{delta:+d}" if delta != 0 else "0"
        g_type = f"0x{g.type_byte:02X}" if len(g.body) > 9 else "N/A"
        n_type = f"0x{n.type_byte:02X}" if len(n.body) > 9 else "N/A"
        marker = "  <-- DIFF" if delta != 0 or g_type != n_type else ""
        print(f"{i:>4d}  {g_len:>10d}  {n_len:>10d}  {delta_str:>8s}  {g_type:>9s}  {n_type:>8s}{marker}")


def compare_t1_bodies(good: XYProject, gen: XYProject) -> None:
    """Deep comparison of T1 (slot 0) entries between the two files."""
    print(f"\n{'='*80}")
    print(f"  T1 (slot 0) DEEP BODY COMPARISON")
    print(f"{'='*80}")

    g = good.tracks[0]
    n = gen.tracks[0]

    print(f"\n  Good T1: body={len(g.body)} bytes, type=0x{g.type_byte:02X}, preamble={hex_dump(g.preamble)}")
    print(f"  Gen  T1: body={len(n.body)} bytes, type=0x{n.type_byte:02X}, preamble={hex_dump(n.preamble)}")

    # Find first differing byte
    min_len = min(len(g.body), len(n.body))
    first_diff = None
    diff_count = 0
    for j in range(min_len):
        if g.body[j] != n.body[j]:
            if first_diff is None:
                first_diff = j
            diff_count += 1

    if first_diff is not None:
        print(f"\n  First diff at body offset 0x{first_diff:04X} (byte {first_diff})")
        print(f"  Total differing bytes in shared range: {diff_count}")
        # Show context around first diff
        ctx_start = max(0, first_diff - 8)
        ctx_end = min(min_len, first_diff + 24)
        print(f"\n  Good body[0x{ctx_start:04X}:0x{ctx_end:04X}]:")
        print(f"    {hex_dump(g.body[ctx_start:ctx_end])}")
        print(f"  Gen  body[0x{ctx_start:04X}:0x{ctx_end:04X}]:")
        print(f"    {hex_dump(n.body[ctx_start:ctx_end])}")
    elif len(g.body) != len(n.body):
        print(f"\n  Bodies match for first {min_len} bytes, but lengths differ")
        if len(n.body) > len(g.body):
            print(f"  Gen has {len(n.body) - len(g.body)} extra bytes at end:")
            print(f"    {hex_dump(n.body[min_len:min_len+40])}")
        else:
            print(f"  Good has {len(g.body) - len(n.body)} extra bytes at end:")
            print(f"    {hex_dump(g.body[min_len:min_len+40])}")
    else:
        print(f"\n  Bodies are IDENTICAL ({min_len} bytes)")


def scan_all_blocks(good: XYProject, gen: XYProject) -> None:
    """Check if the generated file has extra blocks or different block counts
    beyond the standard 16 instrument tracks."""
    print(f"\n{'='*80}")
    print(f"  PREAMBLE BYTE-LEVEL DIFF (all tracks with differences)")
    print(f"{'='*80}")

    any_diff = False
    for i in range(min(len(good.tracks), len(gen.tracks))):
        g = good.tracks[i]
        n = gen.tracks[i]
        if g.preamble != n.preamble:
            any_diff = True
            print(f"\n  Slot {i}:")
            for byte_idx in range(4):
                gb = g.preamble[byte_idx]
                nb = n.preamble[byte_idx]
                marker = " <-- DIFF" if gb != nb else ""
                print(f"    preamble[{byte_idx}]: good=0x{gb:02X}  gen=0x{nb:02X}{marker}")

    if not any_diff:
        print("\n  All preambles match!")


def main() -> None:
    good_path = os.path.abspath(GOOD_PATH)
    gen_path = os.path.abspath(GEN_PATH)

    print(f"Good file: {good_path}")
    print(f"Gen  file: {gen_path}")

    for path, label in [(good_path, "GOOD"), (gen_path, "GENERATED")]:
        if not os.path.exists(path):
            print(f"ERROR: {label} file not found: {path}")
            sys.exit(1)

    with open(good_path, "rb") as f:
        good_raw = f.read()
    with open(gen_path, "rb") as f:
        gen_raw = f.read()

    print(f"\nGood file size: {len(good_raw)} bytes")
    print(f"Gen  file size: {len(gen_raw)} bytes")
    print(f"Size delta: {len(gen_raw) - len(good_raw):+d} bytes")

    # Parse
    good_proj = XYProject.from_bytes(good_raw)
    gen_proj = XYProject.from_bytes(gen_raw)

    # 1 & 2: Print details for each file
    print_file_details("GOOD: src/unnamed 110.xy", good_proj, good_raw)
    print_file_details("GENERATED: output/bring_me_to_life_v2.xy", gen_proj, gen_raw)

    # 3: Preamble comparison by slot
    compare_preambles(good_proj, gen_proj)

    # 4: T1 deep body comparison
    compare_t1_bodies(good_proj, gen_proj)

    # 5: Body size comparison all tracks
    compare_body_sizes(good_proj, gen_proj)

    # 6: Preamble byte-level diffs
    scan_all_blocks(good_proj, gen_proj)

    # 7: Pre-track comparison
    print(f"\n{'='*80}")
    print(f"  PRE-TRACK REGION COMPARISON")
    print(f"{'='*80}")
    g_pt = good_proj.pre_track
    n_pt = gen_proj.pre_track
    print(f"\n  Good pre-track: {len(g_pt)} bytes")
    print(f"  Gen  pre-track: {len(n_pt)} bytes")

    if g_pt == n_pt:
        print(f"  Pre-track regions are IDENTICAL")
    else:
        min_pt = min(len(g_pt), len(n_pt))
        first_diff = None
        for j in range(min_pt):
            if g_pt[j] != n_pt[j]:
                first_diff = j
                break

        if first_diff is not None:
            print(f"  First diff at offset 0x{first_diff:04X}")
            ctx_start = max(0, first_diff - 4)
            ctx_end = min(min_pt, first_diff + 32)
            print(f"\n  Good pre-track[0x{ctx_start:04X}:0x{ctx_end:04X}]:")
            print(f"    {hex_dump(g_pt[ctx_start:ctx_end])}")
            print(f"  Gen  pre-track[0x{ctx_start:04X}:0x{ctx_end:04X}]:")
            print(f"    {hex_dump(n_pt[ctx_start:ctx_end])}")
        elif len(g_pt) != len(n_pt):
            print(f"  Shared bytes match, but lengths differ by {len(n_pt) - len(g_pt):+d}")
            if len(n_pt) > len(g_pt):
                print(f"  Gen extra bytes at end: {hex_dump(n_pt[min_pt:min_pt+32])}")
            else:
                print(f"  Good extra bytes at end: {hex_dump(g_pt[min_pt:min_pt+32])}")


if __name__ == "__main__":
    main()
