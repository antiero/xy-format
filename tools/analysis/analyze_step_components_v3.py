#!/usr/bin/env python3
"""
v3: Focus on understanding the exact layout change.
The diff starts at body+0xA7, which is INSIDE the slot table (body+0x22..0xB2).
This means either:
  a) The slot table is shorter than 48 entries, or
  b) Some slots are being repurposed, or
  c) The step components ARE stored within the slot table area

Let's look at the actual slot boundaries more carefully.
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

def get_t1_info(data):
    blocks = find_track_blocks(data)
    t1_start = blocks[0]
    t2_start = blocks[1] if len(blocks) > 1 else len(data)
    type_byte = data[t1_start + 9]
    if type_byte == 0x07:
        body_start = t1_start + 10
    else:
        body_start = t1_start + 12
    body = data[body_start:t2_start]
    return body, body_start, type_byte

def main():
    base = "/Users/kevinmorrill/Documents/xy-format/src/one-off-changes-from-default"

    # Load all files
    with open(f"{base}/unnamed 1.xy", 'rb') as f:
        data_bl = f.read()
    with open(f"{base}/unnamed 118.xy", 'rb') as f:
        data_118 = f.read()
    with open(f"{base}/unnamed 119.xy", 'rb') as f:
        data_119 = f.read()

    body_bl, off_bl, _ = get_t1_info(data_bl)
    body_118, off_118, _ = get_t1_info(data_118)
    body_119, off_119, _ = get_t1_info(data_119)

    print(f"Baseline: body at 0x{off_bl:04X}, {len(body_bl)} bytes (type-05)")
    print(f"118:      body at 0x{off_118:04X}, {len(body_118)} bytes (type-07)")
    print(f"119:      body at 0x{off_119:04X}, {len(body_119)} bytes (type-07)")

    # CRITICAL INSIGHT: baseline is type-05, 118/119 are type-07
    # Type-05 has 2 extra padding bytes at block+10,11 before the body
    # So the body starts 2 bytes EARLIER in type-07
    # But the body CONTENT should be the same modulo the padding
    # Actually -- type-05 body starts at block+12, type-07 body starts at block+10
    # The preamble bytes within the body should be identical

    print(f"\n{'='*80}")
    print("STRUCTURAL ALIGNMENT CHECK")
    print(f"{'='*80}")

    # Confirm the preambles match
    print(f"\nBaseline preamble (body[0:0x22]):")
    hex_dump(body_bl[0:0x22], off_bl)
    print(f"\n118 preamble (body[0:0x22]):")
    hex_dump(body_118[0:0x22], off_118)

    # They should match
    if body_bl[0:0x22] == body_118[0:0x22]:
        print("\nPreambles MATCH (good)")
    else:
        print("\nPreambles DIFFER:")
        for i in range(0x22):
            if body_bl[i] != body_118[i]:
                print(f"  body+0x{i:02X}: bl=0x{body_bl[i]:02X} 118=0x{body_118[i]:02X}")

    # Now look at the slot table area
    # Slot table = 48 entries x 3 bytes = 144 bytes at body+0x22
    # body+0x22 = slot 0 start
    # body+0x22 + 48*3 = body+0xB2 = slot table end
    # body+0xA7 = first diff = slot table byte at offset 0xA7 - 0x22 = 0x85
    # 0x85 / 3 = 44.333... so it's in the middle of slot 44

    print(f"\n{'='*80}")
    print("SLOT TABLE ANALYSIS")
    print(f"{'='*80}")

    slot_offset = 0x22
    first_diff_offset = 0xA7
    slot_containing_diff = (first_diff_offset - slot_offset) // 3
    byte_within_slot = (first_diff_offset - slot_offset) % 3
    print(f"First diff at body+0x{first_diff_offset:02X}")
    print(f"This is within slot {slot_containing_diff}, byte {byte_within_slot}")

    # Show the slot table entries that differ
    print(f"\n--- Slot table entries around the diff ---")
    for s in range(40, 48):
        so = slot_offset + s * 3
        bl_entry = body_bl[so:so+3]
        e118_entry = body_118[so:so+3]
        e119_entry = body_119[so:so+3]
        bl_hex = ' '.join(f'{b:02X}' for b in bl_entry)
        e118_hex = ' '.join(f'{b:02X}' for b in e118_entry)
        e119_hex = ' '.join(f'{b:02X}' for b in e119_entry)
        marker = "  <-- DIFF" if bl_entry != e118_entry or bl_entry != e119_entry else ""
        print(f"  Slot {s:2d}: baseline={bl_hex}  118={e118_hex}  119={e119_hex}{marker}")

    # Now the key question: what comes AFTER the slot table?
    # In baseline: body[0xB2:]
    # In 118: body[0xB2:] should have the step component data prepended
    print(f"\n{'='*80}")
    print("AFTER SLOT TABLE (body+0xB2)")
    print(f"{'='*80}")

    hex_dump(body_bl[0xB2:0xB2+64], off_bl+0xB2, label="Baseline body+0xB2..+64")
    hex_dump(body_118[0xB2:0xB2+64], off_118+0xB2, label="118 body+0xB2..+64")
    hex_dump(body_119[0xB2:0xB2+64], off_119+0xB2, label="119 body+0xB2..+64")

    # But wait -- slots 44-47 are DIFFERENT. Let's see exactly what changed in each slot.
    print(f"\n{'='*80}")
    print("DETAILED SLOT 44-47 BYTE ANALYSIS")
    print(f"{'='*80}")

    for s in [44, 45, 46, 47]:
        so = slot_offset + s * 3
        print(f"\n  Slot {s} (body+0x{so:02X}):")
        print(f"    Baseline: {body_bl[so]:02X} {body_bl[so+1]:02X} {body_bl[so+2]:02X}")
        print(f"    118:      {body_118[so]:02X} {body_118[so+1]:02X} {body_118[so+2]:02X}")
        print(f"    119:      {body_119[so]:02X} {body_119[so+1]:02X} {body_119[so+2]:02X}")

    # NEW HYPOTHESIS: Maybe the slot table is only 44 entries (132 bytes), not 48
    # And what follows the 44-slot table is a DIFFERENT structure
    # Let's check: body+0x22 + 44*3 = body+0xA6
    # The first diff is at body+0xA7, which is the 2nd byte of what we're calling "slot 44"
    # So maybe it's 44 slots + some other structure
    # OR: the first byte of "slot 44" is the same in all (0x00), and the diff is at position 1

    print(f"\n{'='*80}")
    print("HYPOTHESIS: 44 SLOTS + STEP COMPONENT HEADER")
    print(f"{'='*80}")

    # body+0xA6 = end of hypothetical 44 slots
    # What's at body+0xA6 in each file?
    print(f"body+0xA6: baseline=0x{body_bl[0xA6]:02X}  118=0x{body_118[0xA6]:02X}  119=0x{body_119[0xA6]:02X}")
    print(f"body+0xA7: baseline=0x{body_bl[0xA7]:02X}  118=0x{body_118[0xA7]:02X}  119=0x{body_119[0xA7]:02X}")
    print(f"body+0xA8: baseline=0x{body_bl[0xA8]:02X}  118=0x{body_118[0xA8]:02X}  119=0x{body_119[0xA8]:02X}")

    # Let's look at body[0xA4:0xB8] in detail
    hex_dump(body_bl[0xA4:0xBE], off_bl+0xA4, label="Baseline body+0xA4..0xBE")
    hex_dump(body_118[0xA4:0xBE], off_118+0xA4, label="118 body+0xA4..0xBE")
    hex_dump(body_119[0xA4:0xBE], off_119+0xA4, label="119 body+0xA4..0xBE")

    # ANOTHER HYPOTHESIS: The slot table layout includes a variable-length suffix
    # Let's look at what ALL default slots look like
    print(f"\n{'='*80}")
    print("DEFAULT SLOT PATTERNS")
    print(f"{'='*80}")
    print(f"\nFirst 10 slots (baseline):")
    for s in range(10):
        so = slot_offset + s * 3
        print(f"  Slot {s:2d}: {body_bl[so]:02X} {body_bl[so+1]:02X} {body_bl[so+2]:02X}")

    print(f"\nLast 10 slots (baseline, slots 38-47):")
    for s in range(38, 48):
        so = slot_offset + s * 3
        print(f"  Slot {s:2d}: {body_bl[so]:02X} {body_bl[so+1]:02X} {body_bl[so+2]:02X}")

    # OK: baseline has ALL slots as `00 FF 00` - that's the empty pattern for this T1 body
    # Not `FF 00 00` as we assumed. The slot entries are `00 FF 00`.

    # Let's re-examine what "slot 44" byte 1 changing means
    # baseline slot 44 = 00 FF 00
    # 118 slot 44     = 00 E4 02
    # 119 slot 44     = 00 E4 01
    # So byte 0 stays 0x00, byte 1 changes from 0xFF to 0xE4, byte 2 changes from 0x00 to 0x02/0x01

    # Wait... 0xE4 - what if this is a length byte or component count?
    # 0xE4 = 228. Hmm, that's large.
    # OR: if we read the 3-byte slot as a u24 LE:
    #   baseline: 00 FF 00 = 0x00FF00 = 65280
    #   118:      00 E4 02 = 0x02E400 = 189440
    #   119:      00 E4 01 = 0x01E400 = 123904

    # Let's try another approach: maybe the region starting at body+0xA7 has a
    # completely different structure when step components are present

    print(f"\n{'='*80}")
    print("RE-EXAMINING THE DIFF REGION WITH DIFFERENT ENTRY SIZE")
    print(f"{'='*80}")

    # For 118: the extra data is 125 bytes (body_118 is 125 longer than baseline)
    # But some bytes in the slot table also changed (at body+0xA7, 0xA8)
    # Let's find the EXACT set of changes

    print(f"\n--- All byte differences: baseline vs 118 ---")
    all_diffs_118 = []
    min_len = min(len(body_bl), len(body_118))
    for i in range(min_len):
        if body_bl[i] != body_118[i]:
            all_diffs_118.append(i)
    print(f"Total diffs in shared region: {len(all_diffs_118)}")
    if len(all_diffs_118) <= 30:
        for d in all_diffs_118:
            print(f"  body+0x{d:04X}: bl=0x{body_bl[d]:02X}  118=0x{body_118[d]:02X}")

    # Now: does baseline[X:] == 118[X+125:] for some X?
    # We know the extra is 125 bytes. Let's find the exact insertion point.
    print(f"\n--- Finding exact insertion point for 118 ---")
    extra = len(body_118) - len(body_bl)
    print(f"Extra bytes: {extra}")

    for insert_at in range(0xA0, 0xC0):
        if body_bl[insert_at:] == body_118[insert_at + extra:]:
            print(f"  Clean insertion at body+0x{insert_at:04X}: baseline[0x{insert_at:04X}:] == 118[0x{insert_at+extra:04X}:]")
            # Show what was inserted
            inserted = body_118[insert_at:insert_at+extra]
            hex_dump(inserted, off_118+insert_at, label=f"Inserted {extra} bytes at body+0x{insert_at:04X}")
            break

    # And the bytes that changed BEFORE the insertion point
    print(f"\n--- Bytes changed before insertion ---")
    for i in range(insert_at):
        if body_bl[i] != body_118[i]:
            print(f"  body+0x{i:04X}: bl=0x{body_bl[i]:02X}  118=0x{body_118[i]:02X}")

    # Same for 119
    print(f"\n--- Finding exact insertion point for 119 ---")
    extra_119 = len(body_119) - len(body_bl)
    print(f"Extra bytes: {extra_119}")

    for insert_at_119 in range(0xA0, 0xC0):
        if body_bl[insert_at_119:] == body_119[insert_at_119 + extra_119:]:
            print(f"  Clean insertion at body+0x{insert_at_119:04X}: baseline[0x{insert_at_119:04X}:] == 119[0x{insert_at_119+extra_119:04X}:]")
            inserted_119 = body_119[insert_at_119:insert_at_119+extra_119]
            hex_dump(inserted_119, off_119+insert_at_119, label=f"Inserted {extra_119} bytes at body+0x{insert_at_119:04X}")
            break
    else:
        print("  No clean insertion found!")
        # Try wider range
        for insert_at_119 in range(0x80, 0xF0):
            if body_bl[insert_at_119:] == body_119[insert_at_119 + extra_119:]:
                print(f"  Clean insertion at body+0x{insert_at_119:04X}")
                inserted_119 = body_119[insert_at_119:insert_at_119+extra_119]
                hex_dump(inserted_119, off_119+insert_at_119, label=f"Inserted {extra_119} bytes")
                break
        else:
            # Maybe there are also byte modifications. Try ignoring some trailing bytes.
            print("  Still no clean match. Checking for modifications + insertion...")
            # Try: find where baseline tail matches 119 tail, counting from the end
            for tail_len in range(1, 200):
                if body_bl[-tail_len:] == body_119[-tail_len:]:
                    pass
                else:
                    max_matching_tail = tail_len - 1
                    break
            else:
                max_matching_tail = min(len(body_bl), len(body_119))

            print(f"  Max matching tail: {max_matching_tail} bytes")
            # The insertion + modification is in the first (len - max_matching_tail) bytes
            mod_region_bl = len(body_bl) - max_matching_tail
            mod_region_119 = len(body_119) - max_matching_tail
            print(f"  Modified region: baseline[0:{mod_region_bl}] vs 119[0:{mod_region_119}]")
            print(f"  Modification adds {mod_region_119 - mod_region_bl} bytes")

            hex_dump(body_bl[mod_region_bl-8:mod_region_bl+8], off_bl+mod_region_bl-8,
                     label=f"Baseline around boundary (body+0x{mod_region_bl-8:04X})")
            hex_dump(body_119[mod_region_119-8:mod_region_119+8], off_119+mod_region_119-8,
                     label=f"119 around boundary (body+0x{mod_region_119-8:04X})")

    # Now check: bytes changed before insertion in 119
    if 'insert_at_119' in dir():
        print(f"\n--- Bytes changed before insertion in 119 ---")
        for i in range(insert_at_119):
            if body_bl[i] != body_119[i]:
                print(f"  body+0x{i:04X}: bl=0x{body_bl[i]:02X}  119=0x{body_119[i]:02X}")

    # DECODE the inserted data properly
    print(f"\n{'='*80}")
    print("FINAL DECODING")
    print(f"{'='*80}")

    # 118: inserted data
    if 'insert_at' in dir():
        ins_118 = body_118[insert_at:insert_at+extra]
        print(f"\n118 inserted data at body+0x{insert_at:04X} ({extra} bytes):")
        # Try different entry sizes
        for entry_size in [7, 8, 5, 6, 9, 10]:
            if extra % entry_size == 0:
                n_entries = extra // entry_size
                print(f"\n  If {entry_size}-byte entries: {n_entries} entries")
                for i in range(n_entries):
                    entry = ins_118[i*entry_size:(i+1)*entry_size]
                    print(f"    Entry {i:2d}: {' '.join(f'{b:02X}' for b in entry)}")
            elif (extra-1) % entry_size == 0:
                n_entries = (extra-1) // entry_size
                print(f"\n  If 1-byte header + {entry_size}-byte entries: {n_entries} entries (header=0x{ins_118[0]:02X})")
                for i in range(n_entries):
                    entry = ins_118[1+i*entry_size:1+(i+1)*entry_size]
                    print(f"    Entry {i:2d}: {' '.join(f'{b:02X}' for b in entry)}")
            elif (extra-2) % entry_size == 0:
                n_entries = (extra-2) // entry_size
                print(f"\n  If 2-byte header + {entry_size}-byte entries: {n_entries} entries (header={ins_118[0]:02X} {ins_118[1]:02X})")
                for i in range(n_entries):
                    entry = ins_118[2+i*entry_size:2+(i+1)*entry_size]
                    print(f"    Entry {i:2d}: {' '.join(f'{b:02X}' for b in entry)}")
            elif (extra-3) % entry_size == 0:
                n_entries = (extra-3) // entry_size
                print(f"\n  If 3-byte header + {entry_size}-byte entries: {n_entries} entries (header={ins_118[0]:02X} {ins_118[1]:02X} {ins_118[2]:02X})")
                for i in range(n_entries):
                    entry = ins_118[3+i*entry_size:3+(i+1)*entry_size]
                    print(f"    Entry {i:2d}: {' '.join(f'{b:02X}' for b in entry)}")

if __name__ == "__main__":
    main()
