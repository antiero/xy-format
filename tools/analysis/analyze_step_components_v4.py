#!/usr/bin/env python3
"""
v4: The insight is that both 118 and 119 modify byte body+0xA7 from 0xFF to 0xE4,
and both modify bytes after that in the slot-table region (body+0xA7..0xBF).

The CLEAN insertion point differs:
  118: clean insertion at body+0xBF, 125 bytes, plus modifications in body[0xA7:0xBF]
  119: clean insertion at body+0xC0, 127 bytes, plus modifications in body[0xA7:0xC0]

This means the step component data spans from body+0xA7 into the inserted region.
The total component payload is:
  118: body[0xA7:0xBF] modified (24 bytes) + 125 bytes inserted = component region overlapping
  119: body[0xA7:0xC0] modified (25 bytes) + 127 bytes inserted

Let's look at the COMPLETE modified region (body+0xA7 through end of insertion)
as a unified block and try to decode it.
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
    blocks = find_track_blocks(data)
    t1_start = blocks[0]
    t2_start = blocks[1] if len(blocks) > 1 else len(data)
    type_byte = data[t1_start + 9]
    body_start = t1_start + 10 if type_byte == 0x07 else t1_start + 12
    return data[body_start:t2_start], body_start

def main():
    base = "/Users/kevinmorrill/Documents/xy-format/src/one-off-changes-from-default"

    with open(f"{base}/unnamed 1.xy", 'rb') as f:
        data_bl = f.read()
    with open(f"{base}/unnamed 118.xy", 'rb') as f:
        data_118 = f.read()
    with open(f"{base}/unnamed 119.xy", 'rb') as f:
        data_119 = f.read()

    body_bl, off_bl = get_t1_body(data_bl)
    body_118, off_118 = get_t1_body(data_118)
    body_119, off_119 = get_t1_body(data_119)

    # The modified region starts at body+0xA7 in both files.
    # In the baseline, body[0xA7] = 0xFF (part of slot pattern `00 FF 00`)
    # In 118/119, body[0xA7] = 0xE4

    # Where does the modified region END?
    # For 118: insertion at body+0xBF, 125 bytes. So the inserted data ends at body+0xBF+125 = body+0x13C
    # After that, body_118[0x13C:] == body_bl[0xBF:] (the tail is just the baseline shifted)
    # BUT there's also modifications at body+0xBD (bl=0xDF, 118=0x06)
    # Wait, let me recalculate. The clean insertion was at body+0xBF for 118.
    # Let me verify: body_bl[0xBF:] == body_118[0xBF+125:]

    # First, verify the clean insertion points
    extra_118 = len(body_118) - len(body_bl)  # 125
    extra_119 = len(body_119) - len(body_bl)  # 127

    # Check: body_bl[0xBF:] == body_118[0xBF+125:]?
    match_bf = body_bl[0xBF:] == body_118[0xBF + extra_118:]
    print(f"118: body_bl[0xBF:] == body_118[0x{0xBF+extra_118:04X}:] ? {match_bf}")

    match_c0 = body_bl[0xC0:] == body_119[0xC0 + extra_119:]
    print(f"119: body_bl[0xC0:] == body_119[0x{0xC0+extra_119:04X}:] ? {match_c0}")

    # So the total "changed" region in 118 is body[0xA7:0xBF+125] = body[0xA7:0x13C]
    # = 0x13C - 0xA7 = 149 bytes
    # In baseline, the same region is body[0xA7:0xBF] = 24 bytes
    # So 149 - 24 = 125 extra bytes (matches!)

    # For 119: changed region body[0xA7:0xC0+127] = body[0xA7:0x13F]
    # = 0x13F - 0xA7 = 152 bytes
    # In baseline, same region body[0xA7:0xC0] = 25 bytes
    # 152 - 25 = 127 extra bytes (matches!)

    # BUT WAIT. Let me re-examine. The baseline at body+0xBF is... what?
    print(f"\nBaseline body+0xBD..0xC5: {' '.join(f'{body_bl[i]:02X}' for i in range(0xBD, 0xC5))}")
    print(f"118 body+0xBD..0xC5:      {' '.join(f'{body_118[i]:02X}' for i in range(0xBD, 0xC5))}")

    # body_bl[0xBF] should match body_118[0xBF+125] = body_118[0x13C]
    print(f"\nBaseline body[0xBF] = 0x{body_bl[0xBF]:02X}")
    print(f"118 body[0x13C] = 0x{body_118[0x13C]:02X}")

    # Hmm, there are ALSO modifications at body+0xBD (0xDF -> 0x06) which is AFTER the slot table
    # Let me re-check: is body+0xBD within the modification or is it in the "inserted" part?

    # Actually, the v3 script found clean insertion at body+0xBF for 118.
    # That means body_bl[0xBF:] == body_118[0xBF+125:]
    # And the pre-insertion modifications are in body[0xA7:0xBF]

    # Let me check if 0xBD is within the pre-insertion modified zone
    # 0xBD < 0xBF, so yes it's in the modified zone
    print(f"\nBody+0xBD is within modified zone [0xA7:0xBF]")
    print(f"  baseline: 0x{body_bl[0xBD]:02X}")
    print(f"  118:      0x{body_118[0xBD]:02X}")

    # Now let's look at the COMPLETE modified+inserted region for each file
    print(f"\n{'='*80}")
    print("COMPLETE MODIFIED REGIONS")
    print(f"{'='*80}")

    # For 118: body[0xA7:0xBF+125] in 118 = body_118[0xA7:0x13C]
    region_118_start = 0xA7
    region_118_end = 0xBF + extra_118  # 0x13C
    region_118 = body_118[region_118_start:region_118_end]

    # For the baseline, same absolute positions would be body[0xA7:0xBF]
    region_bl_for_118 = body_bl[region_118_start:0xBF]

    print(f"\n118 modified region: body[0x{region_118_start:04X}:0x{region_118_end:04X}] = {len(region_118)} bytes")
    print(f"Baseline same region: body[0x{region_118_start:04X}:0x00BF] = {len(region_bl_for_118)} bytes")
    hex_dump(region_bl_for_118, off_bl+region_118_start, label="Baseline body[0xA7:0xBF]")
    hex_dump(region_118, off_118+region_118_start, label="118 body[0xA7:0x13C]")

    # For 119: body[0xA7:0xC0+127] in 119 = body_119[0xA7:0x13F]
    region_119_end = 0xC0 + extra_119  # 0x13F
    region_119 = body_119[region_118_start:region_119_end]
    region_bl_for_119 = body_bl[region_118_start:0xC0]

    print(f"\n119 modified region: body[0x{region_118_start:04X}:0x{region_119_end:04X}] = {len(region_119)} bytes")
    hex_dump(region_bl_for_119, off_bl+region_118_start, label="Baseline body[0xA7:0xC0]")
    hex_dump(region_119, off_119+region_118_start, label="119 body[0xA7:0x13F]")

    # KEY INSIGHT: Let's look at the full region including the byte BEFORE (body+0xA6)
    # body+0xA6 = 0x00 in all three (this is part of the previous slot entry's byte 0)
    # body+0xA7 = 0xFF (baseline) / 0xE4 (118/119) -- this could be a HEADER byte

    print(f"\n{'='*80}")
    print("TRYING DIFFERENT ENTRY DECODINGS ON THE COMPONENT REGION")
    print(f"{'='*80}")

    # The region in 118 is 149 bytes. Let's try to find the right entry structure.
    # Observation: In 118, there's a clear repeating pattern `0A 02 00 00 00 04 00 00`
    # with the first entry being `E4 02 00 00 00 04 00 00`
    # BUT that's if we read from body+0xA7 with 8-byte entries.
    # 149 / 8 = 18.625 -- doesn't divide evenly
    # 149 - 5 = 144 / 8 = 18 -- with 5-byte trailer
    # But what are those 5 trailing bytes?

    # Let's look at the END of the 118 region
    print(f"\nLast 16 bytes of 118 region:")
    hex_dump(region_118[-16:], off_118+region_118_start+len(region_118)-16)

    # Hmm. Let's trace the pattern more carefully.
    # From the v2 output, the pattern `E4 02 00 00 00 04 00 00` starts at body+0xA7 (file 0x0131)
    # Then `0A 02 00 00 00 04 00 00` repeats 15 times.
    # That's 16 * 8 = 128 bytes for entries.
    # Total region is 149 bytes. 149 - 128 = 21 bytes of non-entry data.
    # Where are those 21 bytes?

    # Let's see: after 16 entries (128 bytes from body+0xA7), we're at body+0xA7+128 = body+0x127
    # But the region goes to body+0x13C. So the trailing 21 bytes are body[0x127:0x13C]:
    trailing_118 = body_118[0xA7+128:region_118_end]
    print(f"\n118 trailing bytes after 16 entries ({len(trailing_118)} bytes):")
    hex_dump(trailing_118, off_118+0xA7+128)

    # Compare with baseline at the same relative position
    # These trailing bytes in 118 correspond to baseline body[0xBF-21+128:] ... no.
    # Actually, the entries replaced the baseline body[0xA7:0xBF] (24 bytes)
    # which was just `FF 00 00 FF 00 00 FF 00 00 ...` (slot entries)
    # And we added 128 bytes of entries.
    # The remaining 21 bytes of the region must be the tail of the slot table
    # that got shifted.

    # Wait, let's reconsider. The "slot table" might not end at body+0xB2.
    # Let's look at what comes after the slot table in the BASELINE
    # body+0xB2 in baseline:
    print(f"\nBaseline body+0xB0..0xD0:")
    hex_dump(body_bl[0xB0:0xD0], off_bl+0xB0)

    # The baseline has FF 00 00 pattern continuing PAST body+0xB2!
    # Let's count: how many `00 FF 00` / `FF 00 00` entries are there total?
    # Starting from body+0x22:
    print(f"\nCounting slot-like entries from body+0x22:")
    pos = 0x22
    count = 0
    while pos + 3 <= len(body_bl):
        b0, b1, b2 = body_bl[pos], body_bl[pos+1], body_bl[pos+2]
        if b0 == 0x00 and b1 == 0xFF and b2 == 0x00:
            count += 1
            pos += 3
        elif b0 == 0xFF and b1 == 0x00 and b2 == 0x00:
            count += 1
            pos += 3
        else:
            break
    print(f"  Found {count} entries ending at body+0x{pos:04X}")
    print(f"  Next bytes: {' '.join(f'{body_bl[pos+i]:02X}' for i in range(8))}")

    # Hmm, but this is ambiguous because `00 FF 00` read as 3-byte entries
    # could be misaligned. Let's try a different approach: find where the
    # last `FF` byte is before non-slot data starts.
    print(f"\nScanning for end of FF-region in baseline:")
    last_ff_pos = 0x22
    for i in range(0x22, min(0x200, len(body_bl))):
        if body_bl[i] == 0xFF:
            last_ff_pos = i
    first_non_ff_after_slots = None
    for i in range(0x22, min(0x200, len(body_bl))):
        if body_bl[i] != 0x00 and body_bl[i] != 0xFF:
            first_non_ff_after_slots = i
            break
    print(f"  Last 0xFF at body+0x{last_ff_pos:04X}")
    print(f"  First non-00/FF at body+0x{first_non_ff_after_slots:04X}")
    print(f"  Byte at that position: 0x{body_bl[first_non_ff_after_slots]:02X}")
    hex_dump(body_bl[first_non_ff_after_slots-4:first_non_ff_after_slots+16],
             off_bl+first_non_ff_after_slots-4,
             label="Baseline around first non-slot byte")

    # The first non-00/FF byte tells us where the slot region really ends
    # Let's do the same for 118 and 119
    print(f"\n118 scan:")
    first_non = None
    for i in range(0x22, min(0x200, len(body_118))):
        if body_118[i] != 0x00 and body_118[i] != 0xFF:
            first_non = i
            break
    print(f"  First non-00/FF at body+0x{first_non:04X}: 0x{body_118[first_non]:02X}")

    # AH -- 0xE4 at body+0xA7 IS the first non-00/FF byte in 118!
    # And in baseline, 0xDF is the first non-00/FF byte.
    # So the slot region in baseline goes from body+0x22 to... let's find it precisely.

    print(f"\n{'='*80}")
    print("PRECISE SLOT REGION BOUNDARIES")
    print(f"{'='*80}")

    # In baseline, find the pattern end
    # The slots are `00 FF 00` repeated. Let's scan until we hit something else.
    pos = 0x22
    slot_entries = []
    while pos + 3 <= len(body_bl):
        entry = body_bl[pos:pos+3]
        if entry == b'\x00\xFF\x00':
            slot_entries.append(pos)
            pos += 3
        else:
            break

    print(f"Baseline: {len(slot_entries)} consecutive '00 FF 00' entries from body+0x22 to body+0x{pos:04X}")
    print(f"Next byte at body+0x{pos:04X}: 0x{body_bl[pos]:02X}")
    hex_dump(body_bl[pos:pos+24], off_bl+pos, label="Baseline data after slot entries")

    # Check: is it 52 slots? 48 + 4 = 52?
    # 52 * 3 = 156, 0x22 + 156 = 0x22 + 0x9C = 0xBE
    # Let's see: 55 * 3 = 165, 0x22 + 165 = 0x22 + 0xA5 = 0xC7

    # For 118:
    pos_118 = 0x22
    slot_entries_118 = []
    while pos_118 + 3 <= len(body_118):
        entry = body_118[pos_118:pos_118+3]
        if entry == b'\x00\xFF\x00':
            slot_entries_118.append(pos_118)
            pos_118 += 3
        else:
            break

    print(f"\n118: {len(slot_entries_118)} consecutive '00 FF 00' entries from body+0x22 to body+0x{pos_118:04X}")
    print(f"Next byte at body+0x{pos_118:04X}: 0x{body_118[pos_118]:02X}")
    hex_dump(body_118[pos_118:pos_118+24], off_118+pos_118, label="118 data after slot entries")

    # For 119:
    pos_119 = 0x22
    slot_entries_119 = []
    while pos_119 + 3 <= len(body_119):
        entry = body_119[pos_119:pos_119+3]
        if entry == b'\x00\xFF\x00':
            slot_entries_119.append(pos_119)
            pos_119 += 3
        else:
            break

    print(f"\n119: {len(slot_entries_119)} consecutive '00 FF 00' entries from body+0x22 to body+0x{pos_119:04X}")
    print(f"Next byte at body+0x{pos_119:04X}: 0x{body_119[pos_119]:02X}")
    hex_dump(body_119[pos_119:pos_119+24], off_119+pos_119, label="119 data after slot entries")

    # NOW: The slot entries are followed by different data.
    # Baseline: N slots + <something starting with 0xDF>
    # 118: fewer slots + <0xE4 ...> (step components?) + <something>
    # 119: fewer slots + <0xE4 ...> (step components?) + <something>

    # Let's see what follows the slots in each:
    print(f"\n{'='*80}")
    print("DATA AFTER SLOT ENTRIES")
    print(f"{'='*80}")

    # For baseline, show the region after slots
    post_slots_bl = body_bl[pos:]
    post_slots_118 = body_118[pos_118:]
    post_slots_119 = body_119[pos_119:]

    # Find where these diverge from each other
    # The first non-slot byte in baseline is at body+0xBE (0xDF)
    # The first non-slot byte in 118 is at body+0xA7 (0xE4)
    # The first non-slot byte in 119 is at body+0xA7 (0xE4)

    # So baseline has 52 slots, 118 has 45 slots, 119 has 45 slots
    # Wait, let me compute:
    # baseline: slot entries end at body+pos = body+0xBE -> (0xBE - 0x22) / 3 = 0x9C / 3 = 52
    # 118: slot entries end at body+pos_118 = body+0xA7 -> (0xA7 - 0x22) / 3 = 0x85 / 3 = 44.33
    # Hmm, that's not integer. Let me recheck.

    bl_slot_count = (pos - 0x22) // 3
    e118_slot_count = (pos_118 - 0x22) // 3
    e119_slot_count = (pos_119 - 0x22) // 3

    print(f"\nSlot counts: baseline={bl_slot_count}, 118={e118_slot_count}, 119={e119_slot_count}")
    print(f"Slot region sizes: baseline={pos - 0x22}, 118={pos_118 - 0x22}, 119={pos_119 - 0x22}")

    # Now show the complete post-slot data for each
    hex_dump(post_slots_bl[:64], off_bl+pos, label=f"Baseline post-slot (first 64 of {len(post_slots_bl)} bytes)")
    hex_dump(post_slots_118[:64], off_118+pos_118, label=f"118 post-slot (first 64 of {len(post_slots_118)} bytes)")
    hex_dump(post_slots_119[:64], off_119+pos_119, label=f"119 post-slot (first 64 of {len(post_slots_119)} bytes)")

    # Let's now look at the STRUCTURE of the post-slot data
    # It appears there's a header byte (0xDF in baseline, 0xE4 in 118/119)
    # followed by different content

    # For 118 post-slot data: starts with E4 02 00 00 00 04 00 00 0A 02 ...
    # That's the step component entries!
    # After the entries, there should be the same data as baseline

    # Let's find where 118's post-slot data converges with baseline's post-slot data
    print(f"\n{'='*80}")
    print("FINDING CONVERGENCE POINT")
    print(f"{'='*80}")

    # Search for baseline post_slots_bl content within 118's post_slots_118
    # The baseline post-slot starts with DF 40 00 00 01 40 ...
    # Find this pattern in 118's post-slot data
    bl_signature = post_slots_bl[:8]  # First 8 bytes of baseline post-slot
    print(f"Looking for baseline signature: {' '.join(f'{b:02X}' for b in bl_signature)}")

    found_at = None
    for i in range(len(post_slots_118) - 8):
        if post_slots_118[i:i+8] == bl_signature:
            found_at = i
            break

    if found_at is not None:
        print(f"Found in 118 at post-slot offset +{found_at} (body+0x{pos_118+found_at:04X})")
        print(f"Step component data: post-slot bytes 0..{found_at} = {found_at} bytes")
        comp_data_118 = post_slots_118[:found_at]
        hex_dump(comp_data_118, off_118+pos_118, label=f"118 STEP COMPONENT DATA ({found_at} bytes)")

        # Verify: remaining data matches baseline
        remaining_match = post_slots_118[found_at:] == post_slots_bl[:]
        print(f"\n118 post-slot[{found_at}:] == baseline post-slot[:] ? {remaining_match}")
        if not remaining_match:
            # Find differences
            a = post_slots_118[found_at:]
            b_data = post_slots_bl[:]
            for i in range(min(len(a), len(b_data))):
                if a[i] != b_data[i]:
                    print(f"  Diff at +{i}: 118=0x{a[i]:02X} bl=0x{b_data[i]:02X}")
                    break
    else:
        print("Baseline signature NOT found in 118 post-slot data!")

        # Try matching with the second byte changed (DF -> 06 for 118)
        for i in range(len(post_slots_118) - len(post_slots_bl)):
            match_count = 0
            for j in range(min(20, len(post_slots_bl))):
                if post_slots_118[i+j] == post_slots_bl[j]:
                    match_count += 1
            if match_count >= 18:  # Allow 2 diffs in first 20 bytes
                print(f"Near-match at offset +{i} ({match_count}/20 match)")
                hex_dump(post_slots_118[i:i+24], off_118+pos_118+i, label="118")
                hex_dump(post_slots_bl[:24], off_bl+pos, label="baseline")
                break

    # Same for 119
    print(f"\n--- 119 convergence ---")
    found_at_119 = None
    for i in range(len(post_slots_119) - 8):
        if post_slots_119[i:i+8] == bl_signature:
            found_at_119 = i
            break

    if found_at_119 is not None:
        print(f"Found in 119 at post-slot offset +{found_at_119} (body+0x{pos_119+found_at_119:04X})")
        comp_data_119 = post_slots_119[:found_at_119]
        hex_dump(comp_data_119, off_119+pos_119, label=f"119 STEP COMPONENT DATA ({found_at_119} bytes)")
    else:
        # The header byte might differ. Let's just look for `40 00 00 01 40`
        alt_sig = b'\x40\x00\x00\x01\x40'
        for i in range(len(post_slots_119) - 5):
            if post_slots_119[i:i+5] == alt_sig:
                # Check if the byte before is 0x06 (like 118) or something else
                header_byte = post_slots_119[i-1] if i > 0 else None
                print(f"Found '40 00 00 01 40' at offset +{i}, preceding byte = 0x{header_byte:02X}")
                comp_end = i - 1  # The component data ends just before the header byte
                comp_data_119 = post_slots_119[:comp_end]
                hex_dump(comp_data_119, off_119+pos_119, label=f"119 STEP COMPONENT DATA ({comp_end} bytes)")

                # Show the convergence
                hex_dump(post_slots_119[comp_end:comp_end+24], off_119+pos_119+comp_end,
                         label="119 convergence point")
                hex_dump(post_slots_bl[:24], off_bl+pos,
                         label="Baseline convergence point")
                break

    # Final analysis: decode 118 step component entries
    print(f"\n{'='*80}")
    print("FINAL ENTRY DECODE")
    print(f"{'='*80}")

    if found_at is not None:
        data = comp_data_118
        print(f"\n118 component data: {len(data)} bytes")

        # We know from hex that it has the pattern:
        # E4 02 00 00 00 04 00 00
        # 0A 02 00 00 00 04 00 00  (x15)
        # Then some remaining bytes

        # Let's check if there's a clean 8-byte entry structure
        n_full = len(data) // 8
        remainder = len(data) % 8
        print(f"  {n_full} full 8-byte entries + {remainder} remainder bytes")

        for i in range(n_full):
            entry = data[i*8:(i+1)*8]
            print(f"  Entry {i:2d}: {' '.join(f'{b:02X}' for b in entry)}")

        if remainder:
            print(f"  Remainder: {' '.join(f'{b:02X}' for b in data[n_full*8:])}")

    # Now let's look at what bytes differ between the baseline post-slot header
    # and the 118/119 post-slot "after component" data
    # The baseline starts with `DF 40 00 00 01 40 00 00 01 40 ...`
    # What does 118 have at the same structural position?

    print(f"\n{'='*80}")
    print("POST-COMPONENT HEADER COMPARISON")
    print(f"{'='*80}")

    if found_at is not None:
        print(f"\nBaseline post-slot header: {' '.join(f'{b:02X}' for b in post_slots_bl[:16])}")
        after_comp_118 = post_slots_118[found_at:found_at+16]
        print(f"118 after components:      {' '.join(f'{b:02X}' for b in after_comp_118)}")

    # Let's also check: are the slot counts actually 45 and 52?
    # Or is there a header byte before the slot data?
    # body+0x22 in baseline starts: 00 FF 00 00 FF 00 ...
    # So the first byte is 0x00. That's also the first byte of each slot entry.

    # Actually -- what if the table isn't 48 or 52 3-byte entries?
    # What if slot table byte 0 is always 0x00 and it's actually:
    # byte0=always_zero, byte1=value (0xFF=empty), byte2=flags?
    # In that case, 44+1 slot-like entries get modified in 118

    # Let me check what the slot 44 entry looks like in 118 more carefully
    # Slot 44 = body[0xA6:0xA9] = baseline: 00 FF 00, 118: 00 E4 02
    # If 0xE4 is a "present" marker and 0x02 is flags/count...

    # IMPORTANT: slot 44 byte 1 = 0xE4 in BOTH 118 and 119
    # Slot 44 byte 2 = 0x02 in 118, 0x01 in 119
    # This could be: byte1=0xE4 means "step components present",
    # byte2 = variant/subtype?

    print(f"\n{'='*80}")
    print("SLOT 44 HEADER BYTE ANALYSIS")
    print(f"{'='*80}")
    print(f"Slot 44 byte 1: baseline=0xFF (empty), 118=0xE4, 119=0xE4")
    print(f"Slot 44 byte 2: baseline=0x00, 118=0x02, 119=0x01")
    print(f"Hypothesis: 0xE4 = step components present, byte2 = subtype or count modifier")

if __name__ == "__main__":
    main()
