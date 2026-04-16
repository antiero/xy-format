#!/usr/bin/env python3
"""Analyze step component encoding in unnamed 118, 119, and 93b."""

import struct
import sys

TRACK_SIG = bytes([0x00, 0x00, 0x01, 0x03, 0xFF, 0x00, 0xFC, 0x00])

def find_track_blocks(data):
    """Find all track block start positions."""
    blocks = []
    pos = 0
    while True:
        idx = data.find(TRACK_SIG, pos)
        if idx == -1:
            break
        blocks.append(idx)
        pos = idx + 8
    return blocks

def hex_dump(data, offset=0, width=16, label=""):
    """Pretty hex dump."""
    if label:
        print(f"\n--- {label} ---")
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {offset+i:04X}  {hex_part:<{width*3}}  {ascii_part}")

def analyze_file(filepath, label):
    print(f"\n{'='*80}")
    print(f"FILE: {label}")
    print(f"Path: {filepath}")
    print(f"{'='*80}")

    with open(filepath, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    blocks = find_track_blocks(data)
    print(f"Found {len(blocks)} track blocks")

    if not blocks:
        print("ERROR: No track blocks found!")
        return

    # Track 1 = first block
    t1_start = blocks[0]
    print(f"\nTrack 1 block starts at: 0x{t1_start:04X}")

    # Type byte at block_start + 9
    type_byte = data[t1_start + 9]
    print(f"Type byte (block+0x09): 0x{type_byte:02X}")

    if type_byte == 0x07:
        body_start = t1_start + 10
        print(f"Body starts at: 0x{body_start:04X} (type-07, no padding)")
    elif type_byte == 0x05:
        body_start = t1_start + 12  # 2 padding bytes
        print(f"Body starts at: 0x{body_start:04X} (type-05, 2-byte padding)")
    else:
        print(f"WARNING: Unexpected type byte 0x{type_byte:02X}")
        body_start = t1_start + 10

    # Engine ID
    if type_byte == 0x07:
        engine_id = data[body_start + 0x0B]
    else:
        engine_id = data[body_start + 0x0D]
    print(f"Engine ID: 0x{engine_id:02X} ({'Drum' if engine_id == 0x03 else 'other'})")

    # Show the preamble area
    hex_dump(data[body_start:body_start+0x22], body_start, label="Body preamble (first 0x22 bytes)")

    # Slot table for Drum: body offset 0x22 (type-07)
    slot_table_offset = 0x22
    slot_table_start = body_start + slot_table_offset
    print(f"\nSlot table starts at: 0x{slot_table_start:04X} (body+0x{slot_table_offset:02X})")

    # Show a few slots around slot 47
    print(f"\nSlot entries (3 bytes each):")
    for s in range(44, 52):
        so = slot_table_start + s * 3
        if so + 3 <= len(data):
            b0, b1, b2 = data[so], data[so+1], data[so+2]
            status = "EMPTY" if (b0 == 0xFF and b1 == 0x00 and b2 == 0x00) else f"ACTIVE (byte2=0x{b2:02X})"
            print(f"  Slot {s:2d} @ 0x{so:04X}: {b0:02X} {b1:02X} {b2:02X}  [{status}]")

    # Slot 47
    slot47_start = slot_table_start + 47 * 3
    print(f"\nSlot 47 starts at: 0x{slot47_start:04X}")
    slot47_bytes = data[slot47_start:slot47_start+3]
    print(f"Slot 47 bytes: {' '.join(f'{b:02X}' for b in slot47_bytes)}")
    slot47_byte2 = slot47_bytes[2] if len(slot47_bytes) >= 3 else None
    print(f"Slot 47 byte 2: 0x{slot47_byte2:02X} ({'0xFF=empty' if slot47_byte2 == 0xFF else '0xE4=components?' if slot47_byte2 == 0xE4 else 'other'})")

    # Dump 200 bytes from slot 47
    hex_dump(data[slot47_start:slot47_start+200], slot47_start, label="200 bytes starting from slot 47")

    # Now look for data AFTER the slot table
    # The slot table has entries 0..47 (48 entries), or possibly more
    # Let's find where the slot table ends and what follows

    # Check how many slots exist by scanning for the end pattern
    print(f"\n--- Slot table scan (looking for non-FF-00-00 entries and table end) ---")
    active_slots = []
    for s in range(0, 64):  # check up to 64 slots
        so = slot_table_start + s * 3
        if so + 3 > len(data):
            print(f"  Hit end of data at slot {s}")
            break
        b0, b1, b2 = data[so], data[so+1], data[so+2]
        if not (b0 == 0xFF and b1 == 0x00 and b2 == 0x00):
            active_slots.append((s, b0, b1, b2))
            print(f"  Slot {s:2d} @ 0x{so:04X}: {b0:02X} {b1:02X} {b2:02X}  [NON-EMPTY]")

    if not active_slots:
        print("  All slots empty (FF 00 00)")

    # End of 48-slot table
    end_of_48_slots = slot_table_start + 48 * 3
    print(f"\nEnd of 48-slot table: 0x{end_of_48_slots:04X}")
    hex_dump(data[end_of_48_slots:end_of_48_slots+64], end_of_48_slots, label="64 bytes after slot table (48 slots)")

    # If there are active slots with byte2 != 0x00, look for component data
    # The component data should follow the slot table
    # Let's find the next track block to bound our search
    if len(blocks) > 1:
        t2_start = blocks[1]
        t1_end = t2_start
    else:
        t1_end = len(data)

    print(f"\nTrack 1 block extent: 0x{t1_start:04X} - 0x{t1_end:04X} ({t1_end - t1_start} bytes)")
    print(f"Body extent: 0x{body_start:04X} - 0x{t1_end:04X} ({t1_end - body_start} bytes)")

    # Show the LAST 200 bytes of the track body
    tail_start = max(body_start, t1_end - 200)
    hex_dump(data[tail_start:t1_end], tail_start, label=f"Last {t1_end - tail_start} bytes of T1 body")

    # Find where non-FF data starts after slot table
    after_slots = end_of_48_slots
    print(f"\n--- Searching for data after slot table ---")

    # Scan forward looking for the structure
    # Let's look at what follows the 48 slots
    remaining = data[end_of_48_slots:t1_end]
    print(f"Remaining bytes after 48 slots: {len(remaining)}")

    # Look for specific patterns
    # Try to identify step component data
    if len(remaining) > 0:
        hex_dump(remaining[:min(256, len(remaining))], end_of_48_slots,
                 label=f"First {min(256, len(remaining))} bytes after slot table")

    return data, blocks, body_start, slot_table_start, end_of_48_slots, t1_end


def compare_step_components(data118, info118, data119, info119):
    """Compare the step component regions between files."""
    print(f"\n{'='*80}")
    print("COMPARISON: unnamed 118 vs unnamed 119")
    print(f"{'='*80}")

    _, blocks118, body118, slots118, end118, t1end118 = info118
    _, blocks119, body119, slots119, end119, t1end119 = info119

    # Size comparison
    body_size_118 = t1end118 - (blocks118[0] + 10)
    body_size_119 = t1end119 - (blocks119[0] + 10)
    print(f"T1 body size 118: {body_size_118} bytes")
    print(f"T1 body size 119: {body_size_119} bytes")
    print(f"Difference: {body_size_119 - body_size_118} bytes")

    # After slot table comparison
    after118 = data118[end118:t1end118]
    after119 = data119[end119:t1end119]
    print(f"After-slots size 118: {len(after118)} bytes")
    print(f"After-slots size 119: {len(after119)} bytes")
    print(f"After-slots difference: {len(after119) - len(after118)} bytes")

    # Try to find the step component data in 118
    # Expected: 16 entries of 8 bytes each = 128 bytes
    print(f"\n--- Analyzing unnamed 118 step component data ---")
    print(f"Looking for 8-byte pattern: XX 02 00 00 00 04 00 00")

    # Search for the pattern in the after-slots region
    for offset in range(len(after118) - 8):
        b = after118[offset:offset+8]
        if b[1] == 0x02 and b[2:5] == b'\x00\x00\x00' and b[5] == 0x04 and b[6:8] == b'\x00\x00':
            abs_offset = end118 + offset
            print(f"  Found pattern at after-slots+{offset} (0x{abs_offset:04X}): {' '.join(f'{x:02X}' for x in b)}")

    # Let's also try scanning the whole T1 body for the pattern
    t1_body_118 = data118[body118:t1end118]
    print(f"\n  Scanning whole T1 body for pattern...")
    found_offsets = []
    for offset in range(len(t1_body_118) - 8):
        b = t1_body_118[offset:offset+8]
        if b[1] == 0x02 and b[2:5] == b'\x00\x00\x00' and b[5] == 0x04 and b[6:8] == b'\x00\x00':
            abs_offset = body118 + offset
            found_offsets.append((offset, abs_offset, b[0]))

    if found_offsets:
        print(f"  Found {len(found_offsets)} matches:")
        for rel, abs_off, first_byte in found_offsets:
            print(f"    body+0x{rel:04X} (0x{abs_off:04X}): first_byte=0x{first_byte:02X}")

        if len(found_offsets) >= 2:
            first_match_rel = found_offsets[0][0]
            last_match_rel = found_offsets[-1][0]
            region_start = body118 + first_match_rel
            region_end = body118 + last_match_rel + 8
            print(f"\n  Component region: 0x{region_start:04X} - 0x{region_end:04X} ({region_end - region_start} bytes)")
            hex_dump(data118[region_start:region_end], region_start,
                     label=f"Step component data (118): {len(found_offsets)} entries")
    else:
        print("  No matches found!")

    # Now do the same for 119
    print(f"\n--- Analyzing unnamed 119 step component data ---")
    t1_body_119 = data119[body119:t1end119]
    found_offsets_119 = []

    # For 119, we don't know the exact pattern. Let's look for differences from 118.
    # First, find where the files diverge
    min_len = min(len(t1_body_118), len(t1_body_119))
    first_diff = None
    for i in range(min_len):
        if t1_body_118[i] != t1_body_119[i]:
            first_diff = i
            break

    if first_diff is not None:
        abs_diff = body118 + first_diff
        print(f"  First difference at body+0x{first_diff:04X} (file offset ~0x{abs_diff:04X})")
        print(f"  118: {' '.join(f'{b:02X}' for b in t1_body_118[first_diff:first_diff+32])}")
        print(f"  119: {' '.join(f'{b:02X}' for b in t1_body_119[first_diff:first_diff+32])}")

        # Show context around the first difference
        ctx_start = max(0, first_diff - 16)
        ctx_end = min(min_len, first_diff + 48)
        hex_dump(t1_body_118[ctx_start:ctx_end], body118 + ctx_start,
                 label=f"118 context around first diff (body+0x{ctx_start:04X})")
        hex_dump(t1_body_119[ctx_start:ctx_end], body119 + ctx_start,
                 label=f"119 context around first diff (body+0x{ctx_start:04X})")
    else:
        print("  Bodies are identical up to min length!")

    # Count all differences
    diffs = []
    for i in range(min_len):
        if t1_body_118[i] != t1_body_119[i]:
            diffs.append(i)

    print(f"\n  Total differing bytes: {len(diffs)} (in shared region of {min_len} bytes)")
    if len(diffs) <= 50:
        for d in diffs:
            print(f"    body+0x{d:04X}: 118=0x{t1_body_118[d]:02X} 119=0x{t1_body_119[d]:02X}")

    # Extra bytes in 119
    if len(t1_body_119) > len(t1_body_118):
        extra = t1_body_119[len(t1_body_118):]
        print(f"\n  Extra bytes in 119 ({len(extra)} bytes):")
        hex_dump(extra, body119 + len(t1_body_118), label="Extra tail in 119")

    # Show the full divergent region in 119
    if first_diff is not None:
        region_119 = t1_body_119[first_diff:]
        region_118 = t1_body_118[first_diff:]
        print(f"\n  119 from first diff to end ({len(region_119)} bytes):")
        hex_dump(region_119[:min(256, len(region_119))], body119 + first_diff,
                 label="119 from first diff")
        print(f"\n  118 from first diff to end ({len(region_118)} bytes):")
        hex_dump(region_118[:min(256, len(region_118))], body118 + first_diff,
                 label="118 from first diff")


def main():
    base = "/Users/kevinmorrill/Documents/xy-format/src/one-off-changes-from-default"

    files = {
        "unnamed 118": f"{base}/unnamed 118.xy",
        "unnamed 119": f"{base}/unnamed 119.xy",
        "unnamed 93b": f"{base}/unnamed 93b.xy",
    }

    results = {}
    for label, path in files.items():
        try:
            data, blocks, body_start, slot_table_start, end_48, t1_end = analyze_file(path, label)
            results[label] = (data, blocks, body_start, slot_table_start, end_48, t1_end)
        except Exception as e:
            print(f"\nERROR analyzing {label}: {e}")
            import traceback
            traceback.print_exc()

    # Compare 118 and 119
    if "unnamed 118" in results and "unnamed 119" in results:
        d118 = results["unnamed 118"]
        d119 = results["unnamed 119"]

        with open(files["unnamed 118"], 'rb') as f:
            data118 = f.read()
        with open(files["unnamed 119"], 'rb') as f:
            data119 = f.read()

        compare_step_components(data118, d118, data119, d119)

if __name__ == "__main__":
    main()
