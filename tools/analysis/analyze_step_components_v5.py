#!/usr/bin/env python3
"""
v5: Now we understand the structure:
- Baseline: 52 `00 FF 00` slot entries + `00 DF` header + track params
- 118/119: 44 `00 FF 00` slot entries + step component block + `FF 00 00` padding + `06` header + track params

The step component block starts at body+0xA6 (byte 0 = 0x00, byte 1 = 0xE4).
The 0xE4 seems to be a marker for "step components present".

Let's now decode the component entries precisely and figure out:
1. The exact component entry structure
2. How 118 (same component on all 16 steps) differs from 119 (different component per step)
3. Where the FF padding goes and how the header byte changes
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

    # ===========================================================================
    # STRUCTURE SUMMARY
    # ===========================================================================
    # Baseline (no step components):
    #   body+0x22: 52 x `00 FF 00` (slot entries)  [156 bytes, ends at body+0xBE]
    #   body+0xBE: 00 DF [header]
    #   body+0xC0: 40 00 00 01 40 00 00 ... [track parameters]
    #
    # 118/119 (with step components):
    #   body+0x22: 44 x `00 FF 00` (slot entries)  [132 bytes, ends at body+0xA6]
    #   body+0xA6: 00 E4 XX [component header: 00, marker=0xE4, subtype byte]
    #   body+0xA9: component entries...
    #   padding: N x `FF 00 00` entries
    #   header: 06
    #   body+???: 40 00 00 01 40 00 00 ... [track parameters]

    # So: 52 - 44 = 8 slot entries were removed and replaced by component data.
    # The missing 8 slots = 24 bytes.
    # The component data (excluding the 3-byte header) is:
    # 118: body size diff = 1949 - 1824 = 125 extra bytes
    # 119: body size diff = 1951 - 1824 = 127 extra bytes
    # Plus the 24 bytes freed from slots = total component + padding area

    # Let me find the EXACT boundaries by looking for the `40 00 00 01 40` track param signature

    # Baseline: track params start at body+0xC0
    # Find it:
    bl_tp_sig = b'\x40\x00\x00\x01\x40'
    bl_tp_start = body_bl.index(bl_tp_sig) - 1  # include the preceding byte (0xDF or 0x06)
    # Actually, the preceding 2 bytes are `00 DF` in baseline
    # Let's be more precise: find `40 00 00 01 40` and look at what precedes it

    print("="*80)
    print("TRACK PARAMETER REGION IDENTIFICATION")
    print("="*80)

    for label, body, off in [("Baseline", body_bl, off_bl), ("118", body_118, off_118), ("119", body_119, off_119)]:
        idx = body.index(bl_tp_sig)
        # The byte before `40` is the count byte (0x06 in 118/119, what in baseline?)
        # Actually let's look at a few bytes before
        pre = body[idx-3:idx]
        print(f"\n{label}: '40 00 00 01 40' found at body+0x{idx:04X}")
        print(f"  Preceding 3 bytes: {' '.join(f'{b:02X}' for b in pre)}")
        print(f"  Region body+0x{idx-3:04X}: {' '.join(f'{b:02X}' for b in body[idx-3:idx+12])}")

    # So baseline has: `00 00 DF 40 00 00 01 40...` at body+0xBD
    # 118 has: ... `FF 00 00 06 40 00 00 01 40...`
    # 119 has: ... `FF 00 00 06 40 00 00 01 40...`
    # The `06` byte is the track param header (replacing `DF`? No... `00 DF` vs `00 06`)
    # Actually: baseline `00 00 DF` -> 3 bytes before `40`
    #           118/119: `00 00 06` -> 3 bytes before `40`
    # Wait no, let me look again at baseline:
    # `00 DF 40 00 00 01 40` at body+0xBE
    # body+0xBE = 00, body+0xBF = DF, body+0xC0 = 40

    print("\n" + "="*80)
    print("SLOT TABLE STRUCTURE HYPOTHESIS")
    print("="*80)

    # The slot table may actually be:
    # - Not `00 FF 00` x N entries
    # - But rather a structure where:
    #   - Each entry is 3 bytes
    #   - Byte 0 = always 0x00 (separator/padding)
    #   - Byte 1 = slot value (0xFF = empty, 0xE4 = has step components, 0xDF = terminator/header)
    #   - Byte 2 = parameter

    # Let's re-read the entire post-0x22 region with this lens
    print("\nRe-reading slot table as (separator, value, param) tuples:")
    print("\nBaseline last 10 entries + terminator:")
    for i in range(42, 54):
        offset = 0x22 + i * 3
        if offset + 3 > len(body_bl):
            break
        b0, b1, b2 = body_bl[offset], body_bl[offset+1], body_bl[offset+2]
        note = ""
        if b1 == 0xFF:
            note = "empty"
        elif b1 == 0xDF:
            note = "TERMINATOR/HEADER"
        elif b1 == 0xE4:
            note = "STEP COMPONENTS"
        print(f"  [{i:2d}] body+0x{offset:04X}: {b0:02X} {b1:02X} {b2:02X}  [{note}]")

    print("\n118 entries from slot 42:")
    for i in range(42, 60):
        offset = 0x22 + i * 3
        if offset + 3 > len(body_118):
            break
        b0, b1, b2 = body_118[offset], body_118[offset+1], body_118[offset+2]
        note = ""
        if b1 == 0xFF:
            note = "empty"
        elif b1 == 0xE4:
            note = "STEP COMPONENTS"
        elif b0 == 0x0A and b1 == 0x02:
            note = "comp data"
        print(f"  [{i:2d}] body+0x{offset:04X}: {b0:02X} {b1:02X} {b2:02X}  [{note}]")

    # Hmm, the slot table entries being 3-byte aligned with the component data doesn't
    # quite work because the component entries are 8 bytes, not 3.

    # NEW APPROACH: Let's look at the COMPLETE changed region byte by byte
    # In the unified view (body+0xA6 onwards through the padding)

    print("\n" + "="*80)
    print("COMPLETE CHANGED REGION: BYTE-LEVEL DECODE")
    print("="*80)

    # For 118, the component region is body[0xA6:convergence]
    # Convergence: where `06 40 00 00 01 40` appears
    # In baseline: `00 DF 40 00 00 01 40` (DF at body+0xBF)
    # In 118: `06 40 00 00 01 40` appears where?
    conv_118 = body_118.index(b'\x06\x40\x00\x00\x01\x40')
    conv_119 = body_119.index(b'\x06\x40\x00\x00\x01\x40')

    # Hmm wait -- does baseline have `06` too? Let me check
    try:
        conv_bl = body_bl.index(b'\x06\x40\x00\x00\x01\x40')
        print(f"Baseline '06 40...' at body+0x{conv_bl:04X}")
    except ValueError:
        print(f"Baseline does NOT have '06 40 00 00 01 40'")
        # It has DF instead of 06
        conv_bl_df = body_bl.index(b'\xDF\x40\x00\x00\x01\x40')
        print(f"Baseline 'DF 40...' at body+0x{conv_bl_df:04X}")

    print(f"118 '06 40...' at body+0x{conv_118:04X}")
    print(f"119 '06 40...' at body+0x{conv_119:04X}")

    # So in baseline, the header byte is 0xDF, in 118/119 it's 0x06
    # These are at different body offsets due to the inserted component data

    # The complete changed region in 118 is body[0xA6 : conv_118]
    # (from end of clean slots to the 0x06 header byte)
    region_118 = body_118[0xA6:conv_118]
    region_119 = body_119[0xA6:conv_119]
    region_bl = body_bl[0xA6:conv_bl_df]  # In baseline, from same start to 0xDF header

    print(f"\nBaseline region body[0xA6:0x{conv_bl_df:04X}]: {len(region_bl)} bytes")
    hex_dump(region_bl, off_bl+0xA6, label="Baseline body[0xA6:header]")

    print(f"\n118 region body[0xA6:0x{conv_118:04X}]: {len(region_118)} bytes")
    hex_dump(region_118, off_118+0xA6, label="118 body[0xA6:header]")

    print(f"\n119 region body[0xA6:0x{conv_119:04X}]: {len(region_119)} bytes")
    hex_dump(region_119, off_119+0xA6, label="119 body[0xA6:header]")

    # Now let's analyze these regions.
    # Baseline: 25 bytes = 8 more `00 FF 00` entries + 1 trailing `00`
    # 25 / 3 = 8.33... So 8 entries (24 bytes) + 1 byte (0x00)
    # That last 0x00 is the separator before DF

    # 118: let's find the structure
    # First byte: 0x00 (separator)
    # Second byte: 0xE4 (marker)
    # Third byte: 0x02 (subtype)
    # Then: component entries
    # Then: padding with FF 00 00 entries
    # Then: 0x00 separator before 0x06 header... wait, let me check

    print(f"\n118 last 4 bytes of region: {' '.join(f'{b:02X}' for b in region_118[-4:])}")
    print(f"119 last 4 bytes of region: {' '.join(f'{b:02X}' for b in region_119[-4:])}")

    # Now let's decode entry by entry
    print("\n" + "="*80)
    print("STRUCTURED DECODE OF 118 REGION")
    print("="*80)

    r = region_118
    pos = 0

    # First 3 bytes: header
    print(f"\nHeader: {r[0]:02X} {r[1]:02X} {r[2]:02X}")
    print(f"  byte0={r[0]:02X} (separator), byte1={r[1]:02X} (marker=0xE4), byte2={r[2]:02X} (subtype)")
    pos = 3

    # Now look for the repeating pattern
    # From hex dump, after header (3 bytes): 00 00 00 04 00 00 0A 02 00 00 00 04 00 00 0A
    # Wait, that doesn't match what I expected.
    # Let me re-examine:
    # Region 118 starts: 00 E4 02 00 00 00 04 00 00 0A 02 00 00 00 04 00 00 0A ...
    # If header is `00 E4 02`, then data starts with `00 00 00 04 00 00 0A 02`
    # But earlier we identified the 8-byte pattern as `XX 02 00 00 00 04 00 00`
    # Starting from byte 3: `00 00 00 04 00 00 0A 02` -- that's different

    # Hmm, let me reconsider. Maybe the header is just `00 E4` (2 bytes)
    # Then byte 2 (0x02) is the start of the first entry

    # With 2-byte header: entries start at offset 2
    # 118 region = 149 bytes, minus 2 header = 147 bytes for entries
    # 147 / 8 = 18.375 -- no
    # With 3-byte header: 149 - 3 = 146 / 8 = 18.25 -- no

    # Let me try: what if the ENTIRE region is just entries in a different format?
    # Or what if the entry size varies?

    # Look at the raw bytes again from body+0xA7 (after the 0x00 separator):
    # E4 02 00 00 00 04 00 00 | 0A 02 00 00 00 04 00 00 | ...
    # First entry: E4 02 00 00 00 04 00 00
    # Remaining:   0A 02 00 00 00 04 00 00 (x14)
    # Then FF 00 00 padding

    # So: if entries are 8 bytes, starting at body+0xA7:
    # Entry 0:  E4 02 00 00 00 04 00 00  (body+0xA7)
    # Entry 1:  0A 02 00 00 00 04 00 00  (body+0xAF)
    # ...
    # Entry 15: 0A 02 00 00 00 04 00 00  (body+0xA7 + 15*8 = body+0x11F)
    # That's 16 entries = 128 bytes (body+0xA7 to body+0x127)
    # Then padding: FF 00 00 FF 00 00 ... up to the header

    # But what about the `00` at body+0xA6?
    # In baseline, body+0xA6 = `00` (part of `00 FF 00` slot entry)
    # In 118, body+0xA6 = `00` (same)
    # So body+0xA6 is the last byte of slot 43 (which is `00 FF 00`, byte 2 = 0x00)
    # And the component data starts at body+0xA7

    # Wait, but in the baseline, body+0xA6..0xA8 = `00 FF 00` (slot 44)
    # In 118, body+0xA6..0xA8 = `00 E4 02`
    # So slot 44's middle byte changed from 0xFF to 0xE4.
    # This means slot 44 IS the component header!

    # Structure: slot 44 = (00 E4 XX) where XX is the component subtype
    # Then following immediately: 16 x 8-byte step component entries
    # Then: remaining slots 45-51 become FF 00 00 padding (7 entries = 21 bytes)
    # Then: the header byte changes from DF to 06

    print(f"\nREVISED STRUCTURE:")
    print(f"  Slot 44 (body+0xA6): 00 E4 XX = component presence marker")
    print(f"    XX=0x02 in 118, XX=0x01 in 119")
    print(f"  body+0xA9: 16 step component entries, each 8 bytes = 128 bytes")
    print(f"  After entries: padding with FF/00 bytes, then 06 header byte")

    # Let's verify this for 118
    print(f"\n--- 118 component entries (starting at body+0xA9) ---")
    entry_start = 0xA9
    entries_118 = []
    for i in range(16):
        offset = entry_start + i * 8
        entry = body_118[offset:offset+8]
        entries_118.append(entry)
        print(f"  Step {i:2d} (body+0x{offset:04X}): {' '.join(f'{b:02X}' for b in entry)}")

    # After 16 entries: body+0xA9 + 128 = body+0x129
    after_entries_118 = 0xA9 + 128  # = 0x129
    print(f"\nAfter entries at body+0x{after_entries_118:04X}:")
    hex_dump(body_118[after_entries_118:after_entries_118+32], off_118+after_entries_118)

    # Count FF/00 padding until `06 40`
    pad_start = after_entries_118
    while body_118[pad_start] in (0xFF, 0x00):
        pad_start += 1
    print(f"Padding ends at body+0x{pad_start:04X}: 0x{body_118[pad_start]:02X}")
    print(f"Padding length: {pad_start - after_entries_118} bytes")

    # The header byte
    print(f"Header byte: 0x{body_118[pad_start]:02X} (should be 0x06)")
    print(f"Next: {' '.join(f'{body_118[pad_start+i]:02X}' for i in range(8))}")

    # Verify: after the header, the track parameters should match baseline
    # Baseline track params start at body+0xC0
    # 118 track params start at body+(pad_start+1)
    # Actually the header is `06 40 00 00 01 40...`
    # and baseline is `DF 40 00 00 01 40...`
    # So the header byte changed but the rest should match

    bl_params = body_bl[conv_bl_df+1:]  # After DF
    e118_params = body_118[conv_118+1:]  # After 06
    print(f"\nTrack params match (after header byte): {bl_params == e118_params}")

    # Now do the same for 119
    print(f"\n--- 119 component entries (starting at body+0xA9) ---")
    entries_119 = []
    for i in range(16):
        offset = entry_start + i * 8
        entry = body_119[offset:offset+8]
        entries_119.append(entry)
        print(f"  Step {i:2d} (body+0x{offset:04X}): {' '.join(f'{b:02X}' for b in entry)}")

    after_entries_119 = 0xA9 + 128
    print(f"\nAfter entries at body+0x{after_entries_119:04X}:")
    hex_dump(body_119[after_entries_119:after_entries_119+32], off_119+after_entries_119)

    pad_start_119 = after_entries_119
    while body_119[pad_start_119] in (0xFF, 0x00):
        pad_start_119 += 1
    print(f"Padding ends at body+0x{pad_start_119:04X}: 0x{body_119[pad_start_119]:02X}")
    print(f"Padding length: {pad_start_119 - after_entries_119} bytes")
    print(f"Header byte: 0x{body_119[pad_start_119]:02X}")

    e119_params = body_119[conv_119+1:]
    print(f"Track params match (after header byte): {bl_params == e119_params}")

    # Now let's decode the actual entry values
    print(f"\n{'='*80}")
    print("STEP COMPONENT ENTRY DECODING")
    print(f"{'='*80}")

    # 118: all steps have the same component (same type on all 16 steps)
    # Entry format hypothesis: byte0=component_id, bytes1-7=parameters
    # Or: (comp_type, param1, param2, param3) in some packing

    print(f"\n--- 118 entries (same component on all steps) ---")
    print(f"  Step 0 (first):   {' '.join(f'{b:02X}' for b in entries_118[0])}")
    print(f"  Steps 1-15 (all): {' '.join(f'{b:02X}' for b in entries_118[1])}")

    # entry[0] = 0xE4 (step 0) vs 0x0A (steps 1-15)
    # Wait -- step 0's first byte is 0xE4? That's the same as the slot 44 marker!
    # Hmm, but that seems unlikely. Let me re-check.

    # Actually wait -- I made an error. Let me re-read:
    # body+0xA7 = E4, body+0xA8 = 02 (these are slot 44 bytes 1,2)
    # body+0xA9 = entry start
    # Entry 0 at body+0xA9: 00 00 00 04 00 00 0A 02

    # Wait, that doesn't match what I printed above. Let me re-check my entry parsing.
    # entry_start = 0xA9
    # body_118[0xA9:0xA9+8] should be the first entry
    print(f"\nDouble-checking body_118[0xA9:0xA9+8]:")
    print(f"  {' '.join(f'{body_118[i]:02X}' for i in range(0xA9, 0xA9+8))}")

    # Hmm, that gives: 00 00 00 04 00 00 0A 02
    # But the hex dump earlier showed body+0xA7: E4 02 00 00 00 04 00 00
    # So if I start entries at 0xA7 instead of 0xA9:
    print(f"\nAlternative: entries starting at body+0xA7:")
    for i in range(16):
        offset = 0xA7 + i * 8
        entry = body_118[offset:offset+8]
        print(f"  Step {i:2d} (body+0x{offset:04X}): {' '.join(f'{b:02X}' for b in entry)}")

    after_entries_alt = 0xA7 + 128
    print(f"\nAfter 16 entries at body+0x{after_entries_alt:04X}:")
    hex_dump(body_118[after_entries_alt:after_entries_alt+32], off_118+after_entries_alt)

    # This gives:
    # Step 0: E4 02 00 00 00 04 00 00
    # Step 1-15: 0A 02 00 00 00 04 00 00
    # After: FF 00 00 ...
    # This is much cleaner! 16 entries x 8 bytes = 128 bytes.

    # And for 119:
    print(f"\n119 entries starting at body+0xA7:")
    for i in range(16):
        offset = 0xA7 + i * 8
        entry = body_119[offset:offset+8]
        print(f"  Step {i:2d} (body+0x{offset:04X}): {' '.join(f'{b:02X}' for b in entry)}")

    after_entries_119_alt = 0xA7 + 128
    print(f"\nAfter 16 entries at body+0x{after_entries_119_alt:04X}:")
    hex_dump(body_119[after_entries_119_alt:after_entries_119_alt+32], off_119+after_entries_119_alt)

    # WAIT. For 119, step 0 = E4 01 00 04 00 00 0B 02
    # That doesn't match the pattern. But for 118, step 0 = E4 02 00 00 00 04 00 00
    # which matches steps 1-15 except the first byte (E4 vs 0A).

    # Let me reconsider: maybe the entry IS 8 bytes, but the first byte of the first entry
    # is special (acts as both marker and entry data).

    # Or: the first entry has byte0 = 0xE4 as a region marker, and bytes 1-7 are the entry.
    # Then subsequent entries have byte0 = their normal value.

    # For 118:
    #   Entry 0: E4 | 02 00 00 00 04 00 00  -> (marker) + entry(02, 00, 00, 00, 04, 00, 00)
    #   Entry 1: 0A | 02 00 00 00 04 00 00  -> entry(0A, 02, 00, 00, 00, 04, 00, 00)?
    # That's 7-byte entries with a 1-byte header? 1 + 16*7 = 113. No, doesn't match.

    # Simpler: just 8-byte entries, byte0 is the component identifier
    # Entry 0 byte0 = 0xE4 (region marker repurposed as first entry's component ID?)
    # That seems wrong.

    # ALTERNATIVE: Maybe entries are 7 bytes, and there's a 2-byte header (E4 XX)
    # 2 + 16*7 = 114. Total region to padding = 128. No.

    # Or: what if the region has: 1-byte marker (E4) + X-byte entries?
    # 1 + 16 * 8 = 129. But from 0xA7 to padding at 0x127 is 128 bytes.
    # Doesn't work with 1-byte header.

    # Let me just accept 8-byte entries starting at body+0xA7 and decode both files
    # with a focus on understanding what changed.

    # THE KEY DIFFERENCE: slot 44 in the baseline is `00 FF 00` (empty)
    # In 118, the bytes at the same position (body+0xA6, 0xA7, 0xA8) are `00 E4 02`
    # But wait -- if the component entries start at body+0xA7, the `00` at body+0xA6
    # is NOT part of the component data. It's the last byte of slot 43.

    # So the 16 component entries occupy body[0xA7:0x127] = 128 bytes
    # These REPLACE what was: 8 empty `00 FF 00` entries (24 bytes at body[0xA7:0xBE])
    #                          + `00` separator (1 byte at body[0xBE])
    # That's 25 bytes replaced by 128 bytes = 103 extra bytes for entries
    # Plus we need to account for the padding region after entries

    # Let me trace what happens to the DF/06 header byte:
    # Baseline body+0xBF = DF
    # 118 body+0x{conv_118} = 06
    print(f"\nBaseline DF at body+0x{conv_bl_df:04X}")
    print(f"118 06 at body+0x{conv_118:04X}")
    print(f"Shift: {conv_118 - conv_bl_df} = 118 bytes ahead")
    print(f"This should equal: 128 (entries) - 24 (replaced slots) - 1 (replaced separator) + padding")

    # Actually let me just count what's between end of entries and the 06 byte in 118
    between = body_118[0x127:conv_118]
    print(f"\n118 bytes between end-of-entries (body+0x127) and header (body+0x{conv_118:04X}):")
    hex_dump(between, off_118+0x127, label=f"{len(between)} bytes of padding/structure")

    between_119 = body_119[0x127:conv_119]
    print(f"\n119 bytes between end-of-entries (body+0x127) and header (body+0x{conv_119:04X}):")
    hex_dump(between_119, off_119+0x127, label=f"{len(between_119)} bytes of padding/structure")

    # Now the BIG QUESTION for 119: its entries DON'T have a clean 8-byte pattern
    # Let me look at this differently. Maybe entries are variable length in 119.

    # For 119, let's examine the hex more carefully:
    print(f"\n{'='*80}")
    print("119 ENTRY STRUCTURE ANALYSIS")
    print(f"{'='*80}")

    # 119 body[0xA7:] starts with:
    # E4 01 00 04 00 00 0B 02 00 00 00 04 00 00 0A 04
    # 00 00 01 02 00 00 09 08 00 00 02 05 00 00 08 10
    # 00 00 03 04 00 00 07 20 00 00 04 04 00 00 06 40
    # 00 00 05 04 00 00 05 80 00 00 06 04 00 00 05 01
    # 00 00 06 01 00 00 04 02 00 00 07 04 00 00 03 04
    # 00 00 07 04 04 00 00 00 02 08 00 00 08 04 02 00
    # 00 01 10 00 00 09 02 02 00 00 00 00 20 00 00 0A
    # 02 02 00 01 00 04 00 00 0A 02 02 00 00 00 00 04

    # Looking at 118's entries:
    # E4 02 00 00 00 04 00 00 | 0A 02 00 00 00 04 00 00 | (repeat)
    # Byte layout: B0 B1 B2 B3 B4 B5 B6 B7
    # 118: B0=comp_id, B1=0x02, B2-B3=0x0000, B4=0x00, B5=0x04, B6-B7=0x0000

    # For 119, if we assume the SAME 8-byte entry format:
    # Step  0: E4 01 00 04 00 00 0B 02
    #   comp_id=0xE4, B1=0x01, B2-B3=0x0004, B4=0x00, B5=0x00, B6-B7=0x020B
    # That doesn't look right either.

    # HYPOTHESIS: Maybe the first 2 bytes are a HEADER, not part of entry 0.
    # Header = E4 XX where XX indicates something
    # In 118: header = E4 02, then 16 entries of 7 bytes: `00 00 00 04 00 00 0A`?
    # 2 + 16*7 = 114. But we have 128 bytes. Nope.

    # HYPOTHESIS: Header = 1 byte (E4), then entries of 8 bytes
    # In 118: header = E4, entries start at 0xA8
    # Entry 0: 02 00 00 00 04 00 00 0A
    # Entry 1: 02 00 00 00 04 00 00 0A
    # ... (all same)
    # 1 + 16*8 = 129. We have 128 bytes from 0xA7 to 0x127. So 1 + 15.875*8 -- nope.

    # WAIT. Let me reconsider the exact end. Where exactly does padding start?
    # 118 body[0x127]: let me check
    print(f"\n118 body[0x125:0x130]:")
    for i in range(0x125, 0x130):
        print(f"  body+0x{i:04X}: 0x{body_118[i]:02X}")

    # After the entries: does it end with a clean 8-byte boundary or not?
    # Let me scan for the first FF byte after body+0xA7 in 118
    first_ff_118 = 0xA7
    while body_118[first_ff_118] != 0xFF:
        first_ff_118 += 1
    print(f"\n118: first FF after component start at body+0x{first_ff_118:04X}")
    entry_data_len = first_ff_118 - 0xA7
    print(f"Entry data length: {entry_data_len} bytes")
    print(f"If 8-byte entries: {entry_data_len / 8} entries")

    # Same for 119
    first_ff_119 = 0xA7
    while body_119[first_ff_119] != 0xFF:
        first_ff_119 += 1
    print(f"\n119: first FF after component start at body+0x{first_ff_119:04X}")
    entry_data_119_len = first_ff_119 - 0xA7
    print(f"Entry data length: {entry_data_119_len} bytes")
    print(f"If 8-byte entries: {entry_data_119_len / 8} entries")

    # SHOW the raw entry data for 119
    print(f"\n119 raw entry data ({entry_data_119_len} bytes):")
    hex_dump(body_119[0xA7:first_ff_119], off_119+0xA7)

    # Try to decode 119 with VARIABLE entry sizes
    # Key observation from 118: entries 1-15 are `0A 02 00 00 00 04 00 00`
    # where 0x0A = component id for "Ratchet" (step component type 10)
    # and entry 0 is `E4 02 00 00 00 04 00 00` where E4 = 228

    # What if E4 is NOT a component id but a HEADER byte, and the actual entry
    # for step 0 in 118 is `02 00 00 00 04 00 00` (7 bytes)?
    # Then total = 1 + 15*8 + 7 = 1 + 120 + 7 = 128. Yes!

    # OR: what if E4 is indeed a header, and entries are: header(1) + 16 entries
    # But entry size varies? In 118 all entries would be: `02 00 00 00 04 00 00 0A`
    # = 8 bytes starting from `02`. Then 1 + 16*8 = 129. Off by 1.

    # Let me try yet another hypothesis:
    # HEADER = 0xE4 (1 byte)
    # Then each step entry = (comp_id:1, flags:1, value:2, ???:1, ???:2) = 7 bytes
    # In 118: header=E4, subtype=02
    # Then 16 entries of `00 00 00 04 00 00 0A` = 7*16=112 + 2 = 114. Nope.

    # SIMPLEST: The entries are 8 bytes, starting at body+0xA7.
    # 118 has exactly 16 entries (128 bytes from 0xA7 to 0x127).
    # The first entry byte0=0xE4 means the region IS the component block (marker+data merged)
    # In 119, we have 130 bytes of non-FF data (from 0xA7 to first_ff_119)
    # 130 / 8 = 16.25 -- not clean.

    # COULD IT BE that 119 has more than 16 entries?
    # 119 has different components per step. What if some step components need more bytes?

    # Let me look for a pattern by trying to align 119 data as component entries
    # with known component types

    # OP-XY step components: Ratchet, Note Repeat, Glide, Probability, Random, etc.
    # Let's see what IDs might make sense.

    # In 118: first entry has byte0=0xE4=228, entries 1-15 have byte0=0x0A=10
    # If 0x0A is "Ratchet" (10th component), what is 0xE4?

    # RADICAL RETHINK: What if the 3 bytes at body+0xA6 (00 E4 02/01) are NOT
    # a slot entry but a component block HEADER, and the entries start at body+0xA9?

    # 118: header = 00 E4 02, entries at body+0xA9
    # Non-FF data from 0xA9: 00 00 00 04 00 00 0A 02 00 00 00 04 00 00 0A...
    # First FF at 0xA7+128 = 0x127, but data starts at 0xA9, so data = 0x127-0xA9 = 126 bytes
    # Hmm, 126 / 7 = 18, 126 / 8 = 15.75

    # Let me find first FF after 0xA9 for 118:
    first_ff_from_a9 = 0xA9
    while body_118[first_ff_from_a9] != 0xFF:
        first_ff_from_a9 += 1
    entry_len_from_a9 = first_ff_from_a9 - 0xA9
    print(f"\n118: data from body+0xA9 to first FF = {entry_len_from_a9} bytes")
    print(f"  /7 = {entry_len_from_a9/7:.2f}, /8 = {entry_len_from_a9/8:.2f}")

    # 119: header = 00 E4 01, entries at body+0xA9
    first_ff_from_a9_119 = 0xA9
    while body_119[first_ff_from_a9_119] != 0xFF:
        first_ff_from_a9_119 += 1
    entry_len_119_from_a9 = first_ff_from_a9_119 - 0xA9
    print(f"119: data from body+0xA9 to first FF = {entry_len_119_from_a9} bytes")
    print(f"  /7 = {entry_len_119_from_a9/7:.2f}, /8 = {entry_len_119_from_a9/8:.2f}")

    # Hmm 126/7 = 18 is promising for 118 but not for 16 steps.
    # Let me try yet another approach: look at the bytes AFTER the entry data

    # For 118 if we have 16 entries at 8 bytes = 128 bytes from 0xA7:
    # body[0x127] = FF -- yes, that's clean.
    # Then body[0x127:conv_118] is all FF 00 00 padding
    # That works for 118!

    # For 119 with 16 entries at 8 bytes from 0xA7:
    # body[0xA7+128] = body[0x127]
    print(f"\n119 body[0x127]: 0x{body_119[0x127]:02X}")
    # If it's not FF, the entries extend beyond 128 bytes

    # Let me look at 119's data from body+0xA7+120:
    print(f"\n119 body[0x11F:0x135]:")
    hex_dump(body_119[0x11F:0x135], off_119+0x11F)

    # Interesting! 119 has:
    # body[0x127]: the 8-byte entries would be at indices 0-15 ending at 0x127
    # But 0x127 might have data, not FF

    # Let me just look at the COMPLETE non-FF data block in 119 from body+0xA7:
    print(f"\n119 complete non-FF block from body+0xA7:")
    end_119 = 0xA7
    while end_119 < len(body_119) and body_119[end_119] != 0xFF:
        end_119 += 1
    data_block_119 = body_119[0xA7:end_119]
    print(f"  Length: {len(data_block_119)} bytes (0xA7 to 0x{end_119:04X})")
    hex_dump(data_block_119, off_119+0xA7)

    # 130 bytes. Let me try:
    # Header: 2 bytes (E4 01)
    # Entries: 128 bytes = 16 x 8
    # Total: 130 bytes. PERFECT!

    print(f"\n{'='*80}")
    print("HYPOTHESIS: 2-byte header + 16 x 8-byte entries")
    print("="*80)

    # 118: E4 02 | then 16 entries of 8 bytes = 128 bytes. Total = 130 bytes.
    # But 118's non-FF block is 128 bytes (from 0xA7 to 0x127).
    # That's 128, not 130. So: header(E4 02) = 2 bytes + entries = 126 bytes.
    # 126/8 = 15.75. Nope.

    # OR: 118 has 128 bytes = no header + 16 entries.
    # 119 has 130 bytes = 2-byte header + 16 entries.
    # But that doesn't make sense -- they should have the same structure.

    # FINAL CHECK: maybe the 00 at body+0xA6 is PART of the component block
    # (not part of slot 43)
    # Then:
    # 118 block: body[0xA6:first_ff] = 00 E4 02 <entries> = 129 bytes? No, 0x127-0xA6=129
    # 119 block: body[0xA6:first_ff] = 00 E4 01 <entries> = 131 bytes? 0x{end_119}-0xA6=131

    # 129 = 1 + 16*8 = 129. YES! If the header is 1 byte (00) and entries are 16x8=128
    # But then what is E4 02? It's the first 2 bytes of entry 0.
    # 131 = 1 + 16*8 + 2. Off by 2.

    # OK I think the answer is simpler: the "slot table" has a different number of entries
    # than I thought. Let me count more carefully.

    # What if the structure is:
    # body+0x22: 44 slots x 3 bytes = 132 bytes (body+0x22 to body+0xA6)
    # body+0xA6: remaining slots become component entries. How many?
    # body+0xA6 to end-of-block minus padding

    # Actually, let me look at body+0xA7 as an E4 marker that signals:
    # "The next (N) entries are step component data, not slot data"
    # And then after the entries, remaining slots are FF-filled

    # For 118: marker at 0xA7 = E4, next byte = 0x02
    # Followed by: 00 00 00 04 00 00 0A 02 00 00 00 04 00 00 0A ...
    # This pattern `00 00 00 04 00 00 0A` repeating suggests 7-byte entries
    # After `E4 02` (which is 2 bytes), we have 126 bytes of data, 126/7 = 18
    # But 18 isn't 16. Unless there are 18 entries for some reason.

    # You know what, let me just try 7-byte entries from body+0xA9:
    print(f"\n--- 118: 7-byte entries from body+0xA9 ---")
    for i in range(18):
        offset = 0xA9 + i * 7
        if offset + 7 > len(body_118):
            break
        entry = body_118[offset:offset+7]
        is_ff = all(b in (0xFF, 0x00) for b in entry)
        marker = " [PADDING]" if is_ff else ""
        print(f"  Entry {i:2d}: {' '.join(f'{b:02X}' for b in entry)}{marker}")

    print(f"\n--- 119: 7-byte entries from body+0xA9 ---")
    for i in range(20):
        offset = 0xA9 + i * 7
        if offset + 7 > len(body_119):
            break
        entry = body_119[offset:offset+7]
        is_ff = all(b in (0xFF, 0x00) for b in entry)
        marker = " [PADDING]" if is_ff else ""
        print(f"  Entry {i:2d}: {' '.join(f'{b:02X}' for b in entry)}{marker}")

if __name__ == "__main__":
    main()
