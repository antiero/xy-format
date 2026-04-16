#!/usr/bin/env python3
"""
Analyze step component encoding in unnamed 118 vs 119 vs baseline.
Focus: find exact insertion point and decode the component data.
"""

import struct

TRACK_SIG = bytes([0x00, 0x00, 0x01, 0x03, 0xFF, 0x00, 0xFC, 0x00])

def find_track_blocks(data):
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
    if label:
        print(f"\n--- {label} ---")
    for i in range(0, len(data), width):
        chunk = data[i:i+width]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {offset+i:04X}  {hex_part:<{width*3}}  {ascii_part}")

def get_t1_body(data):
    """Get Track 1 body bytes and absolute offset."""
    blocks = find_track_blocks(data)
    t1_start = blocks[0]
    t2_start = blocks[1] if len(blocks) > 1 else len(data)
    type_byte = data[t1_start + 9]
    body_start = t1_start + 10 if type_byte == 0x07 else t1_start + 12
    return data[body_start:t2_start], body_start, type_byte

def main():
    base = "/Users/kevinmorrill/Documents/xy-format/src/one-off-changes-from-default"

    files = {
        "unnamed 1 (baseline)": f"{base}/unnamed 1.xy",
        "unnamed 118": f"{base}/unnamed 118.xy",
        "unnamed 119": f"{base}/unnamed 119.xy",
        "unnamed 93b": f"{base}/unnamed 93b.xy",
    }

    bodies = {}
    for label, path in files.items():
        with open(path, 'rb') as f:
            data = f.read()
        body, body_off, type_byte = get_t1_body(data)
        bodies[label] = (body, body_off, type_byte, data)
        print(f"{label}: T1 body at 0x{body_off:04X}, type=0x{type_byte:02X}, body_len={len(body)}")

    # Compare baseline vs 118 and 119
    baseline_body = bodies["unnamed 1 (baseline)"][0]

    print(f"\n{'='*80}")
    print("BASELINE vs UNNAMED 118: Finding insertion point")
    print(f"{'='*80}")

    body118 = bodies["unnamed 118"][0]
    off118 = bodies["unnamed 118"][1]

    # Find first difference
    min_len = min(len(baseline_body), len(body118))
    first_diff = None
    for i in range(min_len):
        if baseline_body[i] != body118[i]:
            first_diff = i
            break

    if first_diff is not None:
        print(f"First diff at body+0x{first_diff:04X} (file 0x{off118+first_diff:04X})")
        # Show context
        ctx = max(0, first_diff - 32)
        hex_dump(baseline_body[ctx:first_diff+64], off118+ctx, label="Baseline around diff")
        hex_dump(body118[ctx:first_diff+64], off118+ctx, label="118 around diff")
    else:
        print("No differences found in shared region!")

    # How many extra bytes does 118 have?
    extra_118 = len(body118) - len(baseline_body)
    print(f"\nBaseline body: {len(baseline_body)} bytes")
    print(f"118 body: {len(body118)} bytes")
    print(f"Extra in 118: {extra_118} bytes")

    # The step component data should be the extra bytes inserted at first_diff
    if first_diff is not None and extra_118 > 0:
        # Check if baseline[first_diff:] matches 118[first_diff+extra_118:]
        baseline_tail = baseline_body[first_diff:]
        body118_tail = body118[first_diff+extra_118:]
        match_after = baseline_tail == body118_tail
        print(f"Tail match after skipping {extra_118} bytes: {match_after}")

        if not match_after:
            # Find how many bytes differ in the tail
            tail_diffs = 0
            for i in range(min(len(baseline_tail), len(body118_tail))):
                if baseline_tail[i] != body118_tail[i]:
                    tail_diffs += 1
                    if tail_diffs <= 5:
                        print(f"  Tail diff at offset +{i}: baseline=0x{baseline_tail[i]:02X} 118=0x{body118_tail[i]:02X}")
            print(f"  Total tail diffs: {tail_diffs}")

            # Maybe the insertion isn't clean -- check a few bytes before the diff
            # Try to find the exact insertion boundary
            for try_offset in range(first_diff - 4, first_diff + 4):
                for try_extra in range(extra_118 - 4, extra_118 + 4):
                    if try_offset >= 0 and try_extra > 0:
                        bl_tail = baseline_body[try_offset:]
                        b118_tail = body118[try_offset + try_extra:]
                        if bl_tail == b118_tail:
                            print(f"  EXACT MATCH: insertion at body+0x{try_offset:04X}, {try_extra} bytes inserted")

        # Show the inserted data
        inserted = body118[first_diff:first_diff+extra_118]
        hex_dump(inserted, off118+first_diff, label=f"Inserted data in 118 ({extra_118} bytes)")

        # Check for the 8-byte pattern
        print(f"\nLooking for 8-byte entries in inserted data:")
        for i in range(0, len(inserted), 8):
            entry = inserted[i:i+8]
            if len(entry) == 8:
                vals = list(entry)
                print(f"  Entry {i//8:2d}: {' '.join(f'{b:02X}' for b in entry)}  "
                      f"(byte0=0x{vals[0]:02X}, byte1=0x{vals[1]:02X}, byte5=0x{vals[5]:02X})")

    # Now compare baseline vs 119
    print(f"\n{'='*80}")
    print("BASELINE vs UNNAMED 119: Finding insertion point")
    print(f"{'='*80}")

    body119 = bodies["unnamed 119"][0]
    off119 = bodies["unnamed 119"][1]
    extra_119 = len(body119) - len(baseline_body)

    print(f"119 body: {len(body119)} bytes")
    print(f"Extra in 119: {extra_119} bytes")

    first_diff_119 = None
    for i in range(min(len(baseline_body), len(body119))):
        if baseline_body[i] != body119[i]:
            first_diff_119 = i
            break

    if first_diff_119 is not None:
        print(f"First diff at body+0x{first_diff_119:04X} (file 0x{off119+first_diff_119:04X})")

        # Try to find exact insertion boundary
        found_match = False
        for try_offset in range(max(0, first_diff_119 - 8), first_diff_119 + 8):
            for try_extra in range(max(0, extra_119 - 8), extra_119 + 8):
                if try_offset >= 0 and try_extra > 0:
                    bl_tail = baseline_body[try_offset:]
                    b119_tail = body119[try_offset + try_extra:]
                    if bl_tail == b119_tail:
                        print(f"  EXACT MATCH: insertion at body+0x{try_offset:04X}, {try_extra} bytes inserted")

                        # Show the inserted data
                        inserted_119 = body119[try_offset:try_offset+try_extra]
                        hex_dump(inserted_119, off119+try_offset,
                                 label=f"Inserted data in 119 ({try_extra} bytes)")
                        found_match = True
                        break
            if found_match:
                break

        if not found_match:
            print("  No clean insertion found, showing raw diff area...")
            # Maybe there are also some byte modifications in addition to insertion
            # Show the area around the diff
            ctx = max(0, first_diff_119 - 16)
            hex_dump(baseline_body[ctx:first_diff_119+128], off119+ctx,
                     label="Baseline around 119 diff")
            hex_dump(body119[ctx:first_diff_119+128], off119+ctx,
                     label="119 around diff")

    # Direct comparison: 118 vs 119
    print(f"\n{'='*80}")
    print("DIRECT COMPARISON: 118 vs 119 (step component regions only)")
    print(f"{'='*80}")

    if first_diff is not None and first_diff_119 is not None:
        print(f"118 insertion point: body+0x{first_diff:04X}")
        print(f"119 insertion point: body+0x{first_diff_119:04X}")

        # Show the component region side by side
        # For 118: extra_118 bytes starting at first_diff
        # For 119: extra_119 bytes starting at first_diff_119

        region_118 = body118[first_diff:first_diff+extra_118]
        region_119 = body119[first_diff_119:first_diff_119+extra_119]

        hex_dump(region_118, off118+first_diff, label=f"118 component region ({len(region_118)} bytes)")
        hex_dump(region_119, off119+first_diff_119, label=f"119 component region ({len(region_119)} bytes)")

        # For 119, try to identify entry boundaries
        print(f"\n--- Attempting to decode 119 entries ---")
        print(f"119 region is {len(region_119)} bytes, looking for structure...")

        # Let's check: does 119 also have modifications outside the inserted region?
        # Check if there's a byte change in the slot table area too
        print(f"\n--- Checking slot table area changes ---")
        # The slot table for Drum T1 is at body+0x22, 48 entries of 3 bytes = 144 bytes
        # So slot table: body[0x22:0x22+144] = body[0x22:0xB2]
        slot_start = 0x22
        slot_end = slot_start + 48 * 3  # 0xB2
        print(f"Slot table: body+0x{slot_start:02X} to body+0x{slot_end:02X}")

        baseline_slots = baseline_body[slot_start:slot_end]
        slots_118 = body118[slot_start:slot_end]
        slots_119 = body119[slot_start:slot_end]

        print(f"\nBaseline slots == 118 slots: {baseline_slots == slots_118}")
        print(f"Baseline slots == 119 slots: {baseline_slots == slots_119}")

        if baseline_slots != slots_118:
            for i in range(len(baseline_slots)):
                if baseline_slots[i] != slots_118[i]:
                    slot_num = i // 3
                    byte_in_slot = i % 3
                    print(f"  Slot {slot_num}, byte {byte_in_slot}: baseline=0x{baseline_slots[i]:02X} 118=0x{slots_118[i]:02X}")

        if baseline_slots != slots_119:
            for i in range(len(baseline_slots)):
                if baseline_slots[i] != slots_119[i]:
                    slot_num = i // 3
                    byte_in_slot = i % 3
                    print(f"  Slot {slot_num}, byte {byte_in_slot}: baseline=0x{baseline_slots[i]:02X} 119=0x{slots_119[i]:02X}")

    # Check what the baseline slot table looks like (should be all FF 00 00)
    print(f"\n--- Baseline slot table sample ---")
    baseline_body_data = bodies["unnamed 1 (baseline)"][0]
    baseline_off = bodies["unnamed 1 (baseline)"][1]

    # Show last few slots and what follows
    slot_end_abs = baseline_off + 0x22 + 48 * 3
    hex_dump(baseline_body_data[0x22+42*3:0x22+48*3+32], baseline_off+0x22+42*3,
             label="Baseline: last 6 slots + 32 bytes after slot table")

    # Show where body+0xA7 is relative to slot table end
    print(f"\nSlot table end: body+0x{0x22+48*3:04X} = body+0x{0xB2:02X}")
    print(f"First diff in 118: body+0x{first_diff:04X}")
    print(f"Gap between slot end and first diff: {first_diff - 0xB2} bytes")

    # Show what's in that gap
    gap_start = 0xB2
    gap_end = first_diff
    if gap_end > gap_start:
        hex_dump(baseline_body_data[gap_start:gap_end+8], baseline_off+gap_start,
                 label=f"Baseline gap (body+0x{gap_start:02X} to body+0x{gap_end:04X})")
        hex_dump(body118[gap_start:gap_end+8], off118+gap_start,
                 label=f"118 gap (body+0x{gap_start:02X} to body+0x{gap_end:04X})")

    # Now analyze unnamed 93b
    print(f"\n{'='*80}")
    print("UNNAMED 93b: Notes-only (no step components expected)")
    print(f"{'='*80}")

    body93b = bodies["unnamed 93b"][0]
    off93b = bodies["unnamed 93b"][1]
    extra_93b = len(body93b) - len(baseline_body)

    print(f"93b body: {len(body93b)} bytes")
    print(f"Extra vs baseline: {extra_93b} bytes")

    first_diff_93b = None
    for i in range(min(len(baseline_body), len(body93b))):
        if baseline_body[i] != body93b[i]:
            first_diff_93b = i
            break

    if first_diff_93b is not None:
        print(f"First diff at body+0x{first_diff_93b:04X}")

        # Show some context
        ctx = max(0, first_diff_93b - 16)
        hex_dump(baseline_body_data[ctx:first_diff_93b+48], baseline_off+ctx,
                 label="Baseline around 93b diff")
        hex_dump(body93b[ctx:first_diff_93b+48], off93b+ctx,
                 label="93b around diff")

        # Check slot table
        slots_93b = body93b[slot_start:slot_end]
        print(f"\nBaseline slots == 93b slots: {baseline_slots == slots_93b}")
        if baseline_slots != slots_93b:
            for i in range(min(len(baseline_slots), len(slots_93b))):
                if baseline_slots[i] != slots_93b[i]:
                    slot_num = i // 3
                    byte_in_slot = i % 3
                    print(f"  Slot {slot_num}, byte {byte_in_slot}: baseline=0x{baseline_slots[i]:02X} 93b=0x{slots_93b[i]:02X}")

    # Final: decode the component entries more carefully
    print(f"\n{'='*80}")
    print("DETAILED COMPONENT DECODING")
    print(f"{'='*80}")

    # 118: 16 entries x 8 bytes = 128 bytes
    print(f"\n--- unnamed 118: component entries (should be all same component type) ---")
    if first_diff is not None:
        comp_data = body118[first_diff:first_diff+extra_118]
        for i in range(0, len(comp_data), 8):
            entry = comp_data[i:i+8]
            if len(entry) < 8:
                print(f"  Entry {i//8}: INCOMPLETE ({len(entry)} bytes): {' '.join(f'{b:02X}' for b in entry)}")
                continue
            # Parse the 8 bytes
            b = list(entry)
            print(f"  Step {i//8:2d}: {' '.join(f'{b[j]:02X}' for j in range(8))}  "
                  f"| comp_id={b[0]:3d}(0x{b[0]:02X}) "
                  f"flags=0x{b[1]:02X} "
                  f"p1={struct.unpack_from('<H', entry, 2)[0]:5d} "
                  f"p2=0x{b[4]:02X} "
                  f"p3={struct.unpack_from('<H', entry, 5)[0]:5d} "
                  f"p4=0x{b[7]:02X}")

    # 119: variable entries, 2 extra bytes more than 118
    print(f"\n--- unnamed 119: component entries (different types per step) ---")
    if first_diff_119 is not None:
        comp_data_119 = body119[first_diff_119:first_diff_119+extra_119]

        # First try: assume 8-byte entries like 118 (130/8 = 16.25, so maybe not)
        print(f"Total component bytes: {len(comp_data_119)}")
        print(f"If 8-byte entries: {len(comp_data_119)/8:.2f} entries")

        # Let's try decoding as 8-byte entries
        for i in range(0, min(len(comp_data_119), 17*8), 8):
            entry = comp_data_119[i:i+8]
            if len(entry) < 8:
                print(f"  Entry {i//8}: INCOMPLETE ({len(entry)} bytes): {' '.join(f'{b:02X}' for b in entry)}")
                continue
            b = list(entry)
            print(f"  Step {i//8:2d}: {' '.join(f'{b[j]:02X}' for j in range(8))}  "
                  f"| comp_id={b[0]:3d}(0x{b[0]:02X}) "
                  f"flags=0x{b[1]:02X} "
                  f"p1={struct.unpack_from('<H', entry, 2)[0]:5d} "
                  f"p2=0x{b[4]:02X} "
                  f"p3={struct.unpack_from('<H', entry, 5)[0]:5d} "
                  f"p4=0x{b[7]:02X}")

        # Also try: maybe the header/slot table entry encodes component count
        # and 119 has a 2-byte prefix before the entries
        print(f"\n  Trying with 2-byte prefix (skip first 2 bytes):")
        print(f"  Prefix: {' '.join(f'{b:02X}' for b in comp_data_119[:2])}")
        remaining = comp_data_119[2:]
        print(f"  Remaining: {len(remaining)} bytes = {len(remaining)/8:.2f} entries")
        for i in range(0, len(remaining), 8):
            entry = remaining[i:i+8]
            if len(entry) < 8:
                print(f"    Entry {i//8}: INCOMPLETE: {' '.join(f'{b:02X}' for b in entry)}")
                continue
            b = list(entry)
            print(f"    Step {i//8:2d}: {' '.join(f'{b[j]:02X}' for j in range(8))}  "
                  f"| comp_id={b[0]:3d}(0x{b[0]:02X}) "
                  f"flags=0x{b[1]:02X}")

if __name__ == "__main__":
    main()
