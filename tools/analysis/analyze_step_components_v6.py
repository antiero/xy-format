#!/usr/bin/env python3
"""
v6: Focus on 119's entry structure by looking at it as variable-length entries.

Key observations so far:
- 118: non-FF data from body+0xA7 is EXACTLY 128 bytes (16 x 8)
  Entry pattern: E4/0A 02 00 00 00 04 00 00
  All 16 steps have the same component (0x0A=10 is likely the component ID)
  Step 0 has 0xE4 instead of 0x0A in byte0 (marker + first step merged?)

- 119: non-FF data from body+0xA7 is 130 bytes (128 + 2)
  Different components per step. The 2 extra bytes must come from somewhere.

- In both: `00 E4 XX` appears at body+0xA6 (slot 44 position)
  118: XX=0x02, 119: XX=0x01

Let me try: what if the entries have a variable number of parameter bytes,
and some component types need more parameters than others?
Or: what if steps without components are omitted, and a step index byte is present?

Let me look at 119 with fresh eyes, trying to identify each entry.
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

def get_t1_body(data):
    blocks = find_track_blocks(data)
    t1_start = blocks[0]
    t2_start = blocks[1] if len(blocks) > 1 else len(data)
    type_byte = data[t1_start + 9]
    body_start = t1_start + 10 if type_byte == 0x07 else t1_start + 12
    return data[body_start:t2_start], body_start

def main():
    base = "/Users/kevinmorrill/Documents/xy-format/src/one-off-changes-from-default"

    with open(f"{base}/unnamed 118.xy", 'rb') as f:
        data_118 = f.read()
    with open(f"{base}/unnamed 119.xy", 'rb') as f:
        data_119 = f.read()

    body_118, off_118 = get_t1_body(data_118)
    body_119, off_119 = get_t1_body(data_119)

    # Non-FF data blocks:
    # 118: body[0xA7:0x127] = 128 bytes
    # 119: body[0xA7:0x129] = 130 bytes

    d118 = body_118[0xA7:0x127]
    d119 = body_119[0xA7:0x129]

    print("118 component block (128 bytes):")
    for i in range(0, len(d118), 8):
        chunk = d118[i:i+8]
        print(f"  +{i:3d}: {' '.join(f'{b:02X}' for b in chunk)}")

    print(f"\n119 component block (130 bytes):")
    for i in range(0, len(d119), 8):
        chunk = d119[i:min(i+8, len(d119))]
        print(f"  +{i:3d}: {' '.join(f'{b:02X}' for b in chunk)}")

    # Let me think about this differently.
    # In 118, each step has the same component. unnamed 118 documentation says
    # "step components on all 16 steps". What specific step component?
    # The OP-XY has 14 step component types.

    # In 119, each step has a DIFFERENT component. unnamed 119 probably cycles through
    # the available components.

    # For 118, the entry is: 0A 02 00 00 00 04 00 00
    # If we read this as little-endian values:
    # byte 0 = 0x0A = 10 (component type)
    # byte 1 = 0x02 (subtype or parameter)
    # bytes 2-3 = 0x0000 (parameter 1 as u16 LE)
    # byte 4 = 0x00
    # bytes 5-6 = 0x0004 = 1024 (parameter 2 as u16 LE)
    # byte 7 = 0x00

    # For step 0 in 118: E4 02 00 00 00 04 00 00
    # byte 0 = 0xE4 = 228 -- this is NOT a valid component type

    # WAIT: 0xE4 is at body+0xA7. Slot 44 byte 1 is at body+0xA7.
    # What if 0xE4 is a MARKER that replaces the 0xFF of the empty slot,
    # and the component data starts at body+0xA8?

    # Then body+0xA8 = 0x02 in 118, 0x01 in 119
    # This could be the component count modifier or flags

    # Data from body+0xA8:
    # 118: 02 00 00 00 04 00 00 0A | 02 00 00 00 04 00 00 0A | ... (repeating)
    # 119: 01 00 04 00 00 0B 02 00 | 00 00 04 00 00 0A 04 00 | ...

    # For 118 starting at body+0xA8, if entries are 8 bytes:
    # Entry 0: 02 00 00 00 04 00 00 0A -> comp=0x02, then 0A at byte7
    # Entry 1: 02 00 00 00 04 00 00 0A -> same
    # This has 0x0A always at the END. What if the entry is (params, comp_id)?
    # Like: 6 param bytes + 1 byte comp_id + 1 byte something?

    # Actually, let me try swapping the byte order of the 8-byte entry:
    # 118 entry (from +0xA7): 0A 02 00 00 00 04 00 00
    # Read as: comp_id=0x0A, data=02 00 00 00 04 00 00
    # This seems natural. Let me try reading 119 the same way.

    # 119 from +0xA7 as 8-byte entries:
    # Entry 0: E4 01 00 04 00 00 0B 02 -- comp_id=0xE4? No, that's the marker.

    # OK what if in 118, E4 is NOT part of the entry but a 1-byte header?
    # Then entries start at body+0xA8:
    # 118 from +0xA8: 02 00 00 00 04 00 00 | 0A 02 00 00 00 04 00 00 | 0A 02 ...
    # Length from 0xA8 to 0x127 = 127 bytes. 127 / 7 = 18.14. Nope.

    # What about: 1-byte header (E4) + 1-byte flags (02/01) = 2-byte header
    # Then entries from body+0xA9:
    # 118: 00 00 00 04 00 00 0A 02 | 00 00 00 04 00 00 0A 02 | ...
    # Length: 0x127 - 0xA9 = 126 bytes. 126 / 7 = 18. 126 / 8 = 15.75
    # 126 / 6 = 21. Nope.

    # 119 from body+0xA9:
    # 00 04 00 00 0B 02 00 00 | 00 04 00 00 0A 04 00 00 | 01 02 00 00 09 ...
    # Length: 0x129 - 0xA9 = 128 bytes. 128 / 8 = 16!

    # AHA! 119 from body+0xA9 has exactly 128 bytes = 16 x 8-byte entries!
    # And 118 from body+0xA9 has 126 bytes = NOT 16 x 8.

    # But wait: for 118, body[0xA7] = E4, body[0xA8] = 02
    # For 119, body[0xA7] = E4, body[0xA8] = 01
    # What if the "02" in 118 means the FIRST ENTRY starts 2 bytes earlier (merged)?
    # And "01" means the first entry starts 1 byte earlier?

    # OR: E4 is a 1-byte header, then bytes until the entry data = 0x02 vs 0x01 bytes?
    # No, that would mean header is at 0xA7, 0xA8 is data start for 118 (offset=2-2=0xA8)
    # and 0xA8 is data start for 119 too (offset=1-1=0xA8). That doesn't explain the size difference.

    # NEW IDEA: What if 0xE4 at body+0xA7 replaces the slot's 0xFF marker,
    # and body+0xA8 (=0x02/0x01) is the original slot byte 2, which now encodes
    # the number of EXTRA bytes added?

    # 118: byte2=0x02, extra=128 bytes for entries, non-FF block=128 bytes
    # 119: byte2=0x01, extra=130 bytes for entries, non-FF block=130 bytes
    # That doesn't match either.

    # Let me try: entries from body+0xA9 for BOTH, 8 bytes each:
    print(f"\n{'='*80}")
    print("TRYING: 2-byte header (E4 XX) + entries from body+0xA9, 8 bytes each")
    print(f"{'='*80}")

    print(f"\n118 header: E4 {body_118[0xA8]:02X}")
    print(f"118 entries from body+0xA9 (126 bytes):")
    for i in range(16):
        off = 0xA9 + i * 8
        if off + 8 > 0xA9 + 126:
            entry = body_118[off:0xA9+126]
            print(f"  Step {i:2d}: {' '.join(f'{b:02X}' for b in entry)} [TRUNCATED to {len(entry)} bytes]")
        else:
            entry = body_118[off:off+8]
            print(f"  Step {i:2d}: {' '.join(f'{b:02X}' for b in entry)}")

    print(f"\n119 header: E4 {body_119[0xA8]:02X}")
    print(f"119 entries from body+0xA9 (128 bytes = 16 x 8):")
    for i in range(16):
        off = 0xA9 + i * 8
        entry = body_119[off:off+8]
        print(f"  Step {i:2d}: {' '.join(f'{b:02X}' for b in entry)}")

    # 119 entries look much more regular from body+0xA9!
    # Let me decode them:
    # Step  0: 00 04 00 00 0B 02 00 00  -- comp=0x0B(11), value=0x04=4
    # Step  1: 00 04 00 00 0A 04 00 00  -- comp=0x0A(10), value=0x04=4
    # Step  2: 01 02 00 00 09 08 00 00  -- comp=0x09(9), value=?
    # Step  3: 02 05 00 00 08 10 00 00  -- comp=0x08(8), value=?
    # ...
    # The pattern seems to be: each entry has bytes at position 0,1,4,5
    # with positions 2,3,6,7 being zero

    # Wait, let me look at it differently.
    # If I split each 8-byte entry as TWO 4-byte fields:
    print(f"\n119 entries as pairs of u32 LE:")
    for i in range(16):
        off = 0xA9 + i * 8
        entry = body_119[off:off+8]
        val1 = struct.unpack_from('<I', entry, 0)[0]
        val2 = struct.unpack_from('<I', entry, 4)[0]
        print(f"  Step {i:2d}: {val1:#010x} {val2:#010x}  ({val1:10d} {val2:10d})")

    # Or as pairs of u16:
    print(f"\n119 entries as quads of u16 LE:")
    for i in range(16):
        off = 0xA9 + i * 8
        entry = body_119[off:off+8]
        v0 = struct.unpack_from('<H', entry, 0)[0]
        v1 = struct.unpack_from('<H', entry, 2)[0]
        v2 = struct.unpack_from('<H', entry, 4)[0]
        v3 = struct.unpack_from('<H', entry, 6)[0]
        print(f"  Step {i:2d}: {v0:5d} {v1:5d} {v2:5d} {v3:5d}  ({v0:#06x} {v1:#06x} {v2:#06x} {v3:#06x})")

    # Now I see something! Looking at 119 entries from body+0xA9:
    # Step  0: 00 04 00 00 | 0B 02 00 00
    # Step  1: 00 04 00 00 | 0A 04 00 00
    # Step  2: 01 02 00 00 | 09 08 00 00
    # ...
    # The second u32 has a decreasing first byte: 0B, 0A, 09, 08, 07, 06, 05, 05, 04, 03, ...
    # That looks like a STEP INDEX counting down? Or a component ID counting down?

    # And what about the FIRST u32? Values:
    # 0x0400, 0x0400, 0x0201, 0x0502, 0x0403, 0x0404, 0x0405, 0x0406, 0x0106, 0x0407, ...
    # Hmm, if I read the first 2 bytes as (step_index, parameter):
    # (0x00, 0x04), (0x00, 0x04), (0x01, 0x02), (0x02, 0x05), (0x03, 0x04), (0x04, 0x04)...
    # The first byte increments: 0,0,1,2,3,4,5,6,6,7,7,7,8,9,10,10
    # Not a clean sequence.

    # Let me try reading 119 entries differently. What if each entry is:
    # (step:1, comp_type:1, param1:2, param2:2, param3:2)?
    # OR: two independent half-entries of 4 bytes each?

    # Let me look at the second half of each entry (bytes 4-7):
    print(f"\n119 second-half bytes (4-7):")
    for i in range(16):
        off = 0xA9 + i * 8
        entry = body_119[off:off+8]
        half2 = entry[4:8]
        print(f"  Step {i:2d}: {' '.join(f'{b:02X}' for b in half2)}")

    # Second half: 0B 02 00 00 | 0A 04 00 00 | 09 08 00 00 | 08 10 00 00 |
    # 07 20 00 00 | 06 40 00 00 | 05 80 00 00 | 05 01 00 00 | 04 02 00 00 |
    # 03 04 00 00 | 02 08 00 00 | 01 10 00 00 | 00 20 00 00 | ...

    # AH HA! The second half shows a clear pattern:
    # byte4 = 0B, 0A, 09, 08, 07, 06, 05, 05, 04, 03, 02, 01, 00, ...
    # byte5 = 02, 04, 08, 10, 20, 40, 80, 01, 02, 04, 08, 10, 20, ...
    #
    # byte5 is doubling! 2,4,8,16,32,64,128,1,2,4,8,16,32,...
    # And byte4 is decrementing (with a repeat at 5)
    #
    # Together, bytes 4-5 form a 16-bit LE value:
    # 0x020B=523, 0x040A=1034, 0x0809=2057, 0x1008=4104, 0x2007=8199,
    # 0x4006=16390, 0x8005=32773, 0x0105=261, 0x0204=516, 0x0403=1027,
    # 0x0802=2050, 0x1001=4097, 0x2000=8192, ...
    # Hmm, not a clean doubling.

    # Wait, what if it's a BITMASK? Let me read bytes 4-7 as a u32:
    print(f"\n119 bytes 4-7 as u32 LE:")
    for i in range(16):
        off = 0xA9 + i * 8
        val = struct.unpack_from('<I', body_119, off+4)[0]
        print(f"  Step {i:2d}: {val:#010x} = {val:10d} = {val:032b}")

    # And bytes 0-3:
    print(f"\n119 bytes 0-3 as u32 LE:")
    for i in range(16):
        off = 0xA9 + i * 8
        val = struct.unpack_from('<I', body_119, off)[0]
        print(f"  Step {i:2d}: {val:#010x} = {val:10d} = {val:032b}")

    # And let's do the same for 118:
    print(f"\n118 entries from body+0xA9 (as 8 bytes, 15.75 entries):")
    print("Bytes 4-7 as u32 LE:")
    for i in range(16):
        off = 0xA9 + i * 8
        if off + 8 > 0xA9 + 126:
            break
        val = struct.unpack_from('<I', body_118, off+4)[0]
        print(f"  Step {i:2d}: {val:#010x} = {val:10d} = {val:032b}")

    # Hmm. Let me try yet another entry alignment for 118.
    # What if 118's header is 2 bytes (E4 02) and entries are 7 bytes?
    # Header = body[0xA7:0xA9] = E4 02
    # Entries from body+0xA9: 126 bytes / 7 = 18 entries

    print(f"\n{'='*80}")
    print("118: 7-byte entries from body+0xA9 (18 entries)")
    print(f"{'='*80}")
    for i in range(18):
        off = 0xA9 + i * 7
        entry = body_118[off:off+7]
        print(f"  Entry {i:2d}: {' '.join(f'{b:02X}' for b in entry)}")

    # And 119 with 2-byte header (E4 01) then entries from body+0xA9:
    # 128 bytes / 7 = 18.28. Nope.
    # 128 / 8 = 16. That's clean!

    # So: 118 has 126 data bytes (not cleanly divisible) and 119 has 128 (16 x 8).
    # The 2-byte difference is body[0xA8]=0x02 vs 0x01.

    # REVELATION: What if body[0xA8] tells us the entry size?
    # 118: body[0xA8] = 0x02 -> entries are... 7 bytes? (126/18=7, but 18 != 16)
    # 119: body[0xA8] = 0x01 -> entries are 8 bytes? (128/16=8)

    # Or body[0xA8] tells us the number of EXTRA bytes per entry beyond the base size?
    # 118: base + 2 = 7+2=9? 126/9=14. No.
    # 119: base + 1 = 7+1=8. 128/8=16. Yes!

    # Hmm, maybe I'm overcomplicating. Let me look at what CHANGED between 118 and 119.
    # 118 = same component on all 16 steps
    # 119 = different component per step
    # If the component has a TYPE and a PARAMETER, and the type differs per step in 119,
    # the encoding might include a type byte per step in 119 but not in 118
    # (since all are the same type in 118).

    # Hypothesis: shared-type encoding vs per-step-type encoding
    # body[0xA8] = 0x02 means "shared type" (type encoded once)
    # body[0xA8] = 0x01 means "per-step type" (type in each entry)

    # 118 shared type: E4 0x02 [type] [16 x N-byte param entries]
    # But what's the type in 118? If header is E4 02, maybe the type follows at body+0xA9?
    # body+0xA9 = 0x00. Hmm.

    # Actually let me look at the 118 entries as 7-byte more carefully:
    # They all look the same: 00 00 00 04 00 00 0A
    # And: 02 00 00 00 04 00 00
    # These rotate by 1 position. This is just the 8-byte repeating pattern
    # `00 00 00 04 00 00 0A 02` misaligned by 1 byte.

    # So really, the data in 118 IS `0A 02 00 00 00 04 00 00` repeating,
    # but the block starts 1 byte earlier with E4.

    # Let me check: does the 118 block from body+0xA7 have exactly the pattern
    # E4 followed by (0A 02 00 00 00 04 00 00) x N + trailing?
    # body+0xA7 = E4
    # body+0xA8: 02 00 00 00 04 00 00 0A 02 00 00 00 04 00 00 0A ...
    # So after E4, the repeating unit is: `02 00 00 00 04 00 00 0A`
    # And body+0xA8 to body+0x127 = 127 bytes = 15.875 * 8. Not clean.

    # OR: E4 is a standalone byte, then 127 bytes of entry data.
    # 127 = ? No clean division.

    # I think the simplest explanation is:
    # 118: 16 entries of 8 bytes starting at body+0xA7, where byte 0 of entry 0 = 0xE4 (marker)
    # 119: 16 entries of 8 bytes starting at body+0xA7, PLUS 2 extra bytes
    #       (because some entries need 2 extra bytes for additional parameters)

    # But WHERE are the 2 extra bytes in 119? Let me look at the non-FF block:
    # 119 non-FF: 130 bytes from body+0xA7
    # 118 non-FF: 128 bytes from body+0xA7
    # Difference: 2 bytes

    # What if in 119, some steps have DOUBLE components (2 components stacked)?
    # An extra entry of 2 bytes? Or 2 entries of 1 byte each?

    # Let me look at the LAST bytes of the 119 non-FF block:
    # ...0A 02 02 00 00 00 00 04 00 00
    # Ends at body+0x129.
    # body[0x125:0x129] = 00 04 00 00
    # body[0x127:0x129] = 00 00

    # And 118 ends at body+0x127:
    # ...0A 02 00 00 00 04 00 00
    # body[0x11F:0x127] = 0A 02 00 00 00 04 00 00

    # Interesting: in 119, after the main 128-byte block, there's `00 00` before the FFs.

    # Let me look at body+0xA8 (second byte of component block) again:
    # 118: 0x02
    # 119: 0x01
    # What if this byte encodes something about HOW MANY additional 2-byte params follow?
    # 118: 02 -> 2 additional bytes would be 130 total. But 118 has 128. Off by 2!
    # 119: 01 -> 1 additional... hmm.

    # OK, I think I need to approach this from a COMPLETELY different angle.
    # Let me look at what UI change unnamed 118 and 119 represent.

    # According to the project memory: "~91 minimally-edited .xy files, each has one documented UI change"
    # But the specific changes for 118 and 119 aren't documented in the memory.
    # Let me check if there's a manifest or README.

    print(f"\n{'='*80}")
    print("ATTEMPTING TO IDENTIFY COMPONENT TYPES")
    print(f"{'='*80}")

    # From OP-XY docs, the 14 step component types are:
    # (The exact list varies, but common ones include:)
    # Probability, Ratchet, Note Repeat, Spark, Roll, Flam, Nudge,
    # Transpose, Velocity, Gate Length, Swing, Glide, Humanize, Random
    #
    # If the component IDs start at 0x00 and go to 0x0D (14 types):
    # In 119, looking at the second-half byte 4: 0B,0A,09,08,07,06,05,05,04,03,02,01,00,...
    # These go from 11 down to 0 -- that's 12 unique values, matching component IDs!
    # The repeat at 5 (steps 6 and 7) could be two different parameters of the same component.

    # But wait -- step 10 onwards: 07 04 04 00 00 00 02 08
    # With 8-byte alignment from body+0xA9, this doesn't work cleanly.
    # With a different alignment it might.

    # FINAL ATTEMPT: Let me try entries as having a consistent structure but
    # with the entry_data portion varying.
    # What if each entry is: (step_index:u8, comp_type:u8, comp_param:u16, step_bitmask:u32)?
    # Or: (comp_param:u32_le, comp_type:u8, step_bitmask:u24)?

    # Let me decode 119 from body+0xA9 with 8-byte entries and annotate:
    print(f"\n119 entries from body+0xA9, decoded as (first_u32, comp_id, param_u16, trailing_byte):")
    for i in range(16):
        off = 0xA9 + i * 8
        entry = body_119[off:off+8]
        first = struct.unpack_from('<I', entry, 0)[0]
        comp = entry[4]
        param = struct.unpack_from('<H', entry, 5)[0]
        trail = entry[7]
        print(f"  Step {i:2d}: [{' '.join(f'{b:02X}' for b in entry)}]  "
              f"first={first:#010x} comp={comp:3d}(0x{comp:02X}) param={param:5d}(0x{param:04X}) trail=0x{trail:02X}")

    # Hmm comp byte goes: 0B,0A,09,08,07,06,05,05,04,03,02,01,00,0A,0A,0A
    # Not a clean sequence.

    # Let me try: What if the whole block is NOT fixed-size entries but rather
    # a LIST OF (step_index, component_type, parameters)?
    # Where each component type may have a different parameter count?

    # Let me try to parse 119 from body+0xA9 as variable entries:
    print(f"\n{'='*80}")
    print("119 VARIABLE ENTRY PARSE ATTEMPT")
    print(f"{'='*80}")

    # If each entry starts with (step_index, component_type), followed by parameters:
    data = body_119[0xA9:0x129]
    pos = 0
    entries = []

    # Looking at the raw bytes:
    # 00 04 00 00 0B 02 00 00 | 00 04 00 00 0A 04 00 00 | 01 02 00 00 09 08 00 00
    # What if: step=0, value=0x0004=4, comp=0x0B=11, param=0x0002=2, padding=0x0000
    # And the structure is: (value:u16le, padding:u16, comp:u8, param:u8, padding:u16)?

    # Actually, I bet the structure from body+0xA9 is:
    # 16 entries of 8 bytes each, where:
    # [u8 step_value1] [u8 param1] [u16 zero] [u8 comp_id] [u8 param2] [u16 zero]
    # Which is really TWO 4-byte values per step: (val, zero, comp, zero)

    # But for 118, entries from body+0xA9 are `00 00 00 04 00 00 0A 02`
    # Swapping: maybe it's: [u16 param] [u16 zero] [u8 comp_id] [u8 param2] [u16 zero]
    # param=0x0000, zero=0x0400, comp=0x00, param2=0x0A, zero=0x0002

    # Hmm, I'm going in circles. Let me just compute whether 119 entries from
    # body+0xA9 really are 16 x 8 bytes.
    # 119: body[0xA9:0x129] = 128 bytes = 16 * 8. CONFIRMED.

    # And 118: body[0xA9:0x127] = 126 bytes. NOT 16 * 8.
    # body[0x127] = 0xFF (padding), body[0x128] = 0x00, body[0x129] = 0x00

    # What if 118 entries from body+0xA8 instead of 0xA9?
    # body[0xA8:0x128] = 128 bytes = 16 * 8. Let me check body[0x128]:
    print(f"\n118 body[0x127]: 0x{body_118[0x127]:02X}")
    print(f"118 body[0x128]: 0x{body_118[0x128]:02X}")

    # If body[0x128] = 0x00, then body[0xA8:0x128] = 128 bytes
    # But does it include FF bytes? Let me check:
    # body_118[0xA8] = 0x02, and we know entries repeat until body+0x127 where FF starts.
    # So body[0xA8:0x127] = 127 bytes (no FF in this range).
    # body[0x127] = 0xFF.
    # So body[0xA8:0x128] includes an FF at position 127.

    # 118 from body+0xA8, entries as 8 bytes:
    print(f"\n118 from body+0xA8 as 8-byte entries:")
    for i in range(16):
        off = 0xA8 + i * 8
        entry = body_118[off:off+8]
        print(f"  Step {i:2d}: {' '.join(f'{b:02X}' for b in entry)}")

    # Entry 15: 00 00 04 00 00 FF 00 00
    # That has an FF in position 5! That's clearly crossing into padding.

    # What if entries from body+0xA8 are 7 bytes in 118?
    # 126 / 7 = 18. Nope, need 16.

    # WAIT. What about this: the marker byte E4 at body+0xA7 REPLACES slot 44's
    # 0xFF. And body+0xA8 = 0x02 replaces slot 44's 0x00.
    # So slot 44 = (00, E4, 02) means "component present, flag=0x02"
    # Then the component DATA starts at body+0xA9.
    # In 118: 126 bytes of data, In 119: 128 bytes.

    # 126 = 16 * 7 + 14. Nope.
    # Maybe 118 has FEWER than 16 step entries because some steps are "same as default"?
    # If 118 has 16 entries at 7 bytes, that's 112. 126-112=14. Extra 14 bytes?

    # OK I think I need to look at this from the SEMANTICS of unnamed 118 and 119.
    # What step components were set and on which steps?

    # Let me check if there's documentation in the repo
    print(f"\n{'='*80}")
    print("CHECKING FOR FILE DOCUMENTATION")
    print(f"{'='*80}")

    # Let's just look at the raw data one more time with a fresh perspective.
    # 118 non-FF block from body+0xA7: 128 bytes
    # = E4 02 | 00 00 00 04 00 00 | 0A 02 00 00 00 04 00 00 | ... | 0A 02 00 00 00
    #   ^marker  ^entry1(8B if we       ^entry2(8B)
    #    & slot   start here - but only 6B)

    # What if the structure is:
    # body[0xA6] = 0x00 (slot separator)
    # body[0xA7] = 0xE4 (component marker replacing 0xFF)
    # body[0xA8] = component_type = 0x02 in 118, 0x01 in 119
    # body[0xA9:] = entry data

    # And the entry sizes differ based on component_type?
    # type 0x02: entries = 126 bytes / 16 = 7.875 (nope)
    # type 0x01: entries = 128 bytes / 16 = 8.0 (yes!)

    # Maybe type 0x02 means "compact encoding" with fewer bytes per entry?
    # 126 / 18 = 7.0 (18 entries of 7 bytes? But why 18?)

    # OR: What if body[0xA8] is NOT the component type but the number of
    # component TYPES in the block?
    # 118: 0x02 = 2 types? But all entries look the same...
    # 119: 0x01 = 1 type? But entries are all different...
    # That's backwards.

    # Hmm wait -- 118: 0x02. What if it's the number of PARAMETERS per entry?
    # With 2 params, entry = 2*4 = 8 bytes? Or 2*2+header = 6 bytes?
    # 119: 0x01 = 1 parameter per entry = 8 bytes? 128/16=8. Hmm.

    # I think I need to accept that 118's block from body+0xA7 is 128 bytes
    # with 16 x 8-byte entries, and the 0xE4 in byte 0 of entry 0 is a special marker.

    # And 119's block from body+0xA7 is 130 bytes, which might be 128 + 2 bytes
    # for entries that need the extra space.

    # THE 2 EXTRA BYTES: They appear at the END of the 119 block.
    # 118 last entry ends at body+0x127 (FF starts)
    # 119 non-FF data extends to body+0x129 (2 more bytes: `00 00`)
    # These `00 00` bytes could be padding for alignment.

    # Let me compare the last entries of 119:
    # Step 14 (from body+0xA7): body[0xA7+14*8:+8] = body[0x117:0x11F] = 02 02 00 01 00 04 00 00
    # Step 15 (from body+0xA7): body[0x11F:0x127] = 0A 02 02 00 00 00 00 04
    # Then body[0x127:0x129] = 00 00 (the extra 2 bytes)

    # What if step 15's entry in 119 is actually 10 bytes (8+2)?
    # body[0x11F:0x129] = 0A 02 02 00 00 00 00 04 00 00 (10 bytes)

    # Or: what if some component types have an EXTRA 2-byte parameter?
    # In 119, certain steps might have a component that needs extra params.

    # Let me try parsing 119 as variable-width entries.
    # Looking at the SECOND u32 of each entry, byte 4 seems to be the component ID
    # (counting down from 0x0B to 0x00).
    # What if AFTER each entry, if the component has extra params, there are N more bytes?

    # Scrap all that. Let me try one more interpretation: entries from body+0xA9.
    # 119 = 128 bytes = 16 x 8 bytes from body+0xA9. PERFECT.
    # 118 = 126 bytes = ? from body+0xA9. NOT clean at 8 bytes.

    # What if 118 has only 15 entries (15*8=120) + 6 bytes of header/footer?
    # Or: what if 118's E4 02 is a 2-byte header and entries are from body+0xA9?
    # With 126 bytes, maybe it's 15 entries x 8 = 120 + 6 padding?
    # Or 16 entries of different size?

    # SIMPLEST REMAINING HYPOTHESIS:
    # body[0xA7] = marker E4
    # body[0xA8] = flag byte (0x01=per-step types, 0x02=uniform type)
    # When flag=0x02 (uniform): body[0xA9] = component_type, then 16 entries of 7 bytes
    #   1 + 1 + 1 + 16*7 = 115. Total from 0xA7 = 128 - that doesn't work.
    #   How about: 1(marker) + 1(flag) + 1(type) + 16*7 + 13(padding) = 128?
    #   16*7=112, 1+1+1+112=115, padding=13. Hmm, not clean.

    # What if flag=0x02 means body[0xA8:0xA9] is a 1-byte type, then 16 entries of (7+0)=7 bytes?
    # 118: marker(1) + flag(1) + type(1) = 3 bytes header
    # Entries from body+0xAA: 125 bytes. 125/7=17.86. Nope.

    # OK, one more: what if entries from body+0xA9 include a LEADING byte?
    # 118: data starts `00 00 00 04 00 00 0A 02 | 00 00 00 04 00 00 0A 02 | ...`
    # 119: data starts `00 04 00 00 0B 02 00 00 | 00 04 00 00 0A 04 00 00 | ...`
    # These look SHIFTED by 1 byte!

    # What if it's the SAME format, but 118's entries are shifted by 1 byte
    # because of the extra "02" header byte?

    # 118 from body+0xA8 (after E4): 02 00 00 00 04 00 00 0A | 02 00 00 00 04 00 00 0A | ...
    # 119 from body+0xA8 (after E4): 01 00 04 00 00 0B 02 00 | 00 00 04 00 00 0A 04 00 | ...

    # For 118, the repeating pattern from body+0xA8 is: 02 00 00 00 04 00 00 0A
    # For 119, it's more complex.
    # If I read 118 from body+0xA8 as (02 00 00 00 04 00 00) then 0A as first byte of next...
    # That's 7-byte entries with the 0A rolling into the next.

    # FINAL FINAL: Let me just look at it as 16 x 8-byte entries from body+0xA7
    # for BOTH files and accept that 119 has 2 extra bytes at the end.

    print(f"\n{'='*80}")
    print("DEFINITIVE DECODE: 16 x 8-byte entries from body+0xA7")
    print(f"{'='*80}")

    # OP-XY step components (14 types, IDs 0-13 decimal):
    comp_names = {
        0: "Probability", 1: "Spark", 2: "Ratchet", 3: "Note Repeat",
        4: "Roll", 5: "Flam", 6: "Nudge", 7: "Transpose",
        8: "Velocity", 9: "Gate", 10: "Swing", 11: "Glide",
        12: "Humanize", 13: "Random"
    }

    print(f"\n118 (uniform component):")
    for i in range(16):
        off = 0xA7 + i * 8
        entry = body_118[off:off+8]
        b = list(entry)
        # Try: byte0=comp_id/marker, byte1=param
        comp = b[0]
        comp_name = comp_names.get(comp, f"??? (0x{comp:02X})")
        print(f"  Step {i:2d}: {' '.join(f'{x:02X}' for x in b)}  "
              f"comp={comp_name}, b1=0x{b[1]:02X}, b5=0x{b[5]:02X}")

    print(f"\n119 (per-step components):")
    for i in range(16):
        off = 0xA7 + i * 8
        entry = body_119[off:off+8]
        b = list(entry)
        comp = b[0]
        comp_name = comp_names.get(comp, f"??? (0x{comp:02X})")
        print(f"  Step {i:2d}: {' '.join(f'{x:02X}' for x in b)}  "
              f"comp={comp_name}, b1=0x{b[1]:02X}, b5=0x{b[5]:02X}")

    # Check 119 remaining 2 bytes
    print(f"\n119 extra bytes at body+0x127: {body_119[0x127]:02X} {body_119[0x128]:02X}")

    # Let me try the REVERSE byte order for component ID:
    # What if the comp ID is at byte 5 or byte 7, not byte 0?
    print(f"\n119 with comp_id at byte 4 of each entry:")
    for i in range(16):
        off = 0xA7 + i * 8
        entry = body_119[off:off+8]
        b = list(entry)
        comp = b[4]
        comp_name = comp_names.get(comp, f"??? (0x{comp:02X})")
        print(f"  Step {i:2d}: {' '.join(f'{x:02X}' for x in b)}  comp={comp_name}")

    # byte4 for 119: 00,00,00,00,00,00,00,00,00,00,04,02,00,20,00,00 - nope

    # What about the SECOND-HALF hypothesis from above?
    # 119 from body+0xA9, second half (bytes 4-7): comp goes 0B,0A,09,08,07,06,05,05,04,03,...
    # That's 11,10,9,8,7,6,5,5,4,3,...
    # But there are only 14 types (0-13). This could work!

    # Let me reconsider: entries from body+0xA9, each 8 bytes:
    # First 4 bytes = STEP DATA, Second 4 bytes = COMPONENT INFO
    print(f"\n119 from body+0xA9: split as [step_data(4)][comp_info(4)]:")
    for i in range(16):
        off = 0xA9 + i * 8
        step_data = body_119[off:off+4]
        comp_info = body_119[off+4:off+8]
        comp_id = comp_info[0]
        comp_param = comp_info[1]
        comp_name = comp_names.get(comp_id, f"??? (0x{comp_id:02X})")
        step_val = struct.unpack_from('<H', step_data, 0)[0]
        step_param = struct.unpack_from('<H', step_data, 2)[0]
        print(f"  Step {i:2d}: data={' '.join(f'{b:02X}' for b in step_data)} "
              f"comp={' '.join(f'{b:02X}' for b in comp_info)}  "
              f"| comp_id={comp_id}({comp_name}) param=0x{comp_param:02X} "
              f"| step_val={step_val} step_param={step_param}")

if __name__ == "__main__":
    main()
