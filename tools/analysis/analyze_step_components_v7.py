#!/usr/bin/env python3
"""
v7: Key insight from v6:

119 from body+0xA9 decoded as [step_data(4)][comp_info(4)] shows a clear pattern
for steps 0-9, but breaks at step 10.

The pattern for steps 0-9:
  Step 0:  step_data=[00 04 00 00]  comp_info=[0B 02 00 00]  comp=Glide(11)
  Step 1:  step_data=[00 04 00 00]  comp_info=[0A 04 00 00]  comp=Swing(10)
  Step 2:  step_data=[01 02 00 00]  comp_info=[09 08 00 00]  comp=Gate(9)
  Step 3:  step_data=[02 05 00 00]  comp_info=[08 10 00 00]  comp=Velocity(8)
  Step 4:  step_data=[03 04 00 00]  comp_info=[07 20 00 00]  comp=Transpose(7)
  Step 5:  step_data=[04 04 00 00]  comp_info=[06 40 00 00]  comp=Nudge(6)
  Step 6:  step_data=[05 04 00 00]  comp_info=[05 80 00 00]  comp=Flam(5)
  Step 7:  step_data=[06 04 00 00]  comp_info=[05 01 00 00]  comp=Flam(5) again!
  Step 8:  step_data=[06 01 00 00]  comp_info=[04 02 00 00]  comp=Roll(4)
  Step 9:  step_data=[07 04 00 00]  comp_info=[03 04 00 00]  comp=NoteRepeat(3)

Steps 6 and 7 BOTH have comp=5 (Flam). Step 7 has step_data byte0=6 and step 8 also
has step_data byte0=6. This means step 6 has TWO components stacked!

So step_data byte 0 IS the step index. When a step has multiple components,
they get multiple entries.

The comp_info byte 1 is a BITMASK that doubles each time:
02, 04, 08, 10, 20, 40, 80, 01, 02, 04, ...
This is bit 1, bit 2, bit 3, etc. -- a STEP BITMASK!

Wait no -- that's in the comp_info, which should describe the component, not the step.
Let me re-examine with the hypothesis that:
  comp_info = [comp_id, bitmask_lo, bitmask_hi_lo, bitmask_hi_hi]
  step_data = [step_index, param, 0, 0]

The bitmask doubling pattern suggests these might be per-step presence bitmasks,
where bit N = step N has this component type.

Actually, looking more carefully:
  comp_info byte1 = 02, 04, 08, 10, 20, 40, 80, 01, 02, 04
  These are: 1<<1, 1<<2, 1<<3, 1<<4, 1<<5, 1<<6, 1<<7, 1<<8 (wrapping), 1<<9, 1<<10
  But 0x01=1<<0 not 1<<8. Unless it's a u16LE: 0x0002, 0x0004, 0x0008, ...
  0x0080, then 0x0100 (=1<<8), 0x0200 (=1<<9), 0x0400 (=1<<10)

Let me decode the 4-byte comp_info as: [comp_id:u8, bitmask:u24_LE]
Or as: [comp_id:u8, bitmask_b1, bitmask_b2, bitmask_b3]
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

    with open(f"{base}/unnamed 119.xy", 'rb') as f:
        data_119 = f.read()
    with open(f"{base}/unnamed 118.xy", 'rb') as f:
        data_118 = f.read()

    body_119, off_119 = get_t1_body(data_119)
    body_118, off_118 = get_t1_body(data_118)

    comp_names = {
        0: "Probability", 1: "Spark", 2: "Ratchet", 3: "NoteRepeat",
        4: "Roll", 5: "Flam", 6: "Nudge", 7: "Transpose",
        8: "Velocity", 9: "Gate", 10: "Swing", 11: "Glide",
        12: "Humanize", 13: "Random"
    }

    # 119 data from body+0xA9 = 128 bytes
    data = body_119[0xA9:0xA9+128]

    print("="*80)
    print("119 ENTRIES: [step_data(4)][comp_info(4)] from body+0xA9")
    print("="*80)
    print(f"comp_info decoded as [comp_id:u8, bitmask:u24_LE]\n")

    for i in range(16):
        entry = data[i*8:(i+1)*8]
        sd = entry[0:4]  # step data
        ci = entry[4:8]  # comp info

        step_idx = sd[0]
        step_param = sd[1]
        comp_id = ci[0]
        # bitmask as u24 LE: ci[1] | (ci[2] << 8) | (ci[3] << 16)
        bitmask = ci[1] | (ci[2] << 8) | (ci[3] << 16)
        comp_name = comp_names.get(comp_id, f"??? ({comp_id})")

        print(f"  [{i:2d}] step={step_idx:2d} param=0x{step_param:02X}({step_param:3d}) "
              f"pad={sd[2]:02X}{sd[3]:02X}  "
              f"comp={comp_id:2d}({comp_name:12s}) bitmask=0x{bitmask:06X} "
              f"= {bitmask:024b}")

    # Now the bitmask pattern:
    # 0x000002 = bit 1
    # 0x000004 = bit 2
    # 0x000008 = bit 3
    # 0x000010 = bit 4
    # 0x000020 = bit 5
    # 0x000040 = bit 6
    # 0x000080 = bit 7
    # 0x000100 = bit 8
    # 0x000200 = bit 9
    # 0x000400 = bit 10
    # These are single-bit bitmasks, each advancing by 1 bit!
    # So each entry sets ONE bit. If unnamed 119 has one component per step,
    # and each step has a different component type, then:
    # bit 1 = step 0, bit 2 = step 1, etc.
    # BUT step 0 has bitmask = bit 1, not bit 0. Offset by 1?

    # Let me check: does the step index match the bit position?
    print(f"\nBit position analysis:")
    for i in range(16):
        entry = data[i*8:(i+1)*8]
        ci = entry[4:8]
        bitmask = ci[1] | (ci[2] << 8) | (ci[3] << 16)
        if bitmask > 0:
            bit_pos = bitmask.bit_length() - 1
        else:
            bit_pos = -1
        step_idx = entry[0]
        print(f"  [{i:2d}] step={step_idx} bit_pos={bit_pos} match={step_idx == bit_pos - 1}")

    # Hmm, if bitmask bit 1 corresponds to step 0, bit 2 to step 1, etc.:
    # Bits are 1-indexed! bit N = step N-1
    # Let's check:
    print(f"\nWith 1-indexed bits (bit N = step N-1):")
    for i in range(16):
        entry = data[i*8:(i+1)*8]
        ci = entry[4:8]
        bitmask = ci[1] | (ci[2] << 8) | (ci[3] << 16)
        if bitmask > 0:
            bit_pos = bitmask.bit_length() - 1
            step_from_bit = bit_pos - 1
        else:
            bit_pos = -1
            step_from_bit = -1
        step_idx = entry[0]
        print(f"  [{i:2d}] step_idx={step_idx} bit_pos={bit_pos} step_from_bit={step_from_bit} match={step_idx == step_from_bit}")

    # Now let me check what happens at the BREAK point (around entry 10).
    # Entries 10 onwards might have step 10 with 2 components,
    # which would shift everything by one 8-byte entry.

    print(f"\n{'='*80}")
    print("119 RAW BYTES AROUND BREAK (entries 9-12)")
    print(f"{'='*80}")

    for i in range(8, 14):
        entry = data[i*8:(i+1)*8]
        sd = entry[0:4]
        ci = entry[4:8]
        step_idx = sd[0]
        comp_id = ci[0]
        bitmask = ci[1] | (ci[2] << 8) | (ci[3] << 16)
        comp_name = comp_names.get(comp_id, f"???")
        print(f"  [{i:2d}] raw={' '.join(f'{b:02X}' for b in entry)}  "
              f"step={step_idx} comp={comp_id}({comp_name}) bitmask=0x{bitmask:06X}")

    # Entry 10: raw=07 04 04 00 00 00 02 08
    # step=7, param=0x04, pad=04 00
    # comp=0, bitmask=0x080200
    # This has step=7 but should be step 10 (if sequential). AND comp=0 (Probability).
    # The bitmask 0x080200 has MULTIPLE bits set: bits 9, 17, 19.
    # That doesn't make sense for a single-step component.

    # HYPOTHESIS: The entries are NOT 8-byte aligned from body+0xA9 for all 16 entries.
    # Some steps have EXTRA entries (stacked components).
    # The step_idx byte tells us which step, so we can handle variable-length.

    # Let me re-parse with STEP INDEX tracking:
    print(f"\n{'='*80}")
    print("119 RE-PARSE: Track step_idx to detect stacked components")
    print(f"{'='*80}")

    pos = 0
    entry_num = 0
    while pos < 128:
        if pos + 8 > 128:
            remainder = data[pos:]
            print(f"  REMAINDER ({len(remainder)} bytes): {' '.join(f'{b:02X}' for b in remainder)}")
            break

        entry = data[pos:pos+8]
        sd = entry[0:4]
        ci = entry[4:8]

        step_idx = sd[0]
        step_param = sd[1]
        comp_id = ci[0]
        bitmask = ci[1] | (ci[2] << 8) | (ci[3] << 16)
        comp_name = comp_names.get(comp_id, f"??? ({comp_id})")

        # Check if bitmask is a single bit (power of 2)
        is_single_bit = bitmask > 0 and (bitmask & (bitmask - 1)) == 0

        print(f"  [{entry_num:2d}] @+{pos:3d}: step={step_idx:2d} param=0x{step_param:02X} "
              f"comp={comp_id:2d}({comp_name:12s}) bitmask=0x{bitmask:06X} "
              f"single_bit={is_single_bit}")

        pos += 8
        entry_num += 1

    # The bitmask breaks at entry 10 (step_idx=7, not 10).
    # What if instead of 8-byte entries, entries for some components are 6 bytes?
    # Or what if the structure is different?

    # ALTERNATIVE: Maybe the format is NOT [4-byte step_data][4-byte comp_info]
    # Let me try: [2-byte header][2-byte step_bitmask][2-byte comp_id_param][2-byte value]

    # Actually, let me look at 119 data as a STREAM and try to decode comp entries
    # where each entry is:
    #   step_index: u8
    #   comp_type: u8
    #   param_value: u16 LE
    #   bitmask: u16 LE  (or u24 or u32)

    # From the working entries (0-9):
    # Entry 0: step=0, param=4, pad=0000, comp=11, bitmask=0x000002
    # Entry 1: step=0, param=4, pad=0000, comp=10, bitmask=0x000004
    # Wait: steps 0 and 1 both have step=0! So step 0 has TWO components (Glide and Swing)!

    # Let me re-read more carefully:
    # Entry 0: [00 04 00 00] [0B 02 00 00] -> step=0, param=4, comp=11, mask=0x02
    # Entry 1: [00 04 00 00] [0A 04 00 00] -> step=0, param=4, comp=10, mask=0x04
    # Entry 2: [01 02 00 00] [09 08 00 00] -> step=1, param=2, comp=9, mask=0x08
    # Entry 3: [02 05 00 00] [08 10 00 00] -> step=2, param=5, comp=8, mask=0x10
    # Entry 4: [03 04 00 00] [07 20 00 00] -> step=3, param=4, comp=7, mask=0x20
    # Entry 5: [04 04 00 00] [06 40 00 00] -> step=4, param=4, comp=6, mask=0x40
    # Entry 6: [05 04 00 00] [05 80 00 00] -> step=5, param=4, comp=5, mask=0x80
    # Entry 7: [06 04 00 00] [05 01 00 00] -> step=6, param=4, comp=5, mask=0x0100
    #   WAIT: comp=5 again! AND step=6.
    #   But step 5 also had comp=5. So step 5 and step 6 BOTH have Flam?
    #   OR: entry 6 has step=5,comp=5 and entry 7 has step=6,comp=5.
    #   That means comp 5 (Flam) is on BOTH step 5 and step 6.
    #   But unnamed 119 should have different components per step...

    # Actually maybe step 0 has TWO components (entries 0 and 1: Glide and Swing).
    # Let me track by step:
    print(f"\n{'='*80}")
    print("119 STEP GROUPING (from body+0xA9, 8-byte entries)")
    print(f"{'='*80}")

    steps = {}
    for i in range(16):
        entry = data[i*8:(i+1)*8]
        step_idx = entry[0]
        comp_id = entry[4]
        param = entry[1]
        bitmask = entry[5] | (entry[6] << 8) | (entry[7] << 16)
        comp_name = comp_names.get(comp_id, f"???")
        if step_idx not in steps:
            steps[step_idx] = []
        steps[step_idx].append((i, comp_id, comp_name, param, bitmask))

    for step in sorted(steps.keys()):
        print(f"\n  Step {step}:")
        for entry_idx, comp_id, comp_name, param, bitmask in steps[step]:
            print(f"    Entry {entry_idx}: comp={comp_id}({comp_name}) param={param} bitmask=0x{bitmask:06X}")

    # This grouping shows that the entries go up to step=7 and then break.
    # After step=7, the alignment is wrong.
    # Let me consider: what if there are MORE THAN 16 entries (since some steps
    # have multiple components), and the total data is 128 bytes?
    # 128 / 8 = 16 entries. But with stacking, we might need 17+ entries to cover 16 steps.
    # But we only have 128 bytes = 16 entries.

    # WAIT: the 119 non-FF block is 130 bytes (body+0xA7 to body+0x129).
    # If header is 2 bytes (E4 01), then 128 bytes remain = 16 x 8.
    # If header is 0 bytes (E4 01 is part of entry 0), then 130 bytes, which is 16x8+2.

    # 16 entries might not be enough for 16 steps if some have 2 components.
    # But unnamed 119 is "different component per step" -- each step gets ONE
    # different component type. So we need exactly 16 entries.

    # Let me reconsider: maybe the ENTRY SIZE is not 8 but varies.
    # What if entries are 5 bytes: (step_idx, comp_id, param, bitmask_lo, bitmask_hi)?
    # 128 / 5 = 25.6. Nope.
    # 130 / 5 = 26. Possible but weird.

    # What about 4 bytes per entry? 128/4 = 32 entries.
    # Maybe each step has TWO 4-byte entries (step_data and comp_info)?
    # Then 32/2 = 16 steps. Could work!

    # But then why does 118 have 128 bytes for 16 steps with the SAME component?
    # If format is 2x4 per step = 8 per step, 128/8 = 16. Same for both.

    # I think the structure IS 8 bytes per entry but the alignment in 119 goes wrong
    # because there is a DIFFERENT packing.

    # NEW IDEA: What if the entry structure depends on body[0xA8]?
    # body[0xA8] = 0x02 -> entries as: [comp_id:u8 flag:u8 00 00 00 param:u8 00 00]
    #   (118 pattern: 0A 02 00 00 00 04 00 00)
    # body[0xA8] = 0x01 -> entries as: [step_idx:u8 param:u8 00 00 comp_id:u8 bitmask:u8 00 00]
    #   (119 pattern for steps 0-9 works!)

    # With 0x02: same component for ALL steps (comp_id in first byte, step bitmask not needed)
    # With 0x01: different component per step (step_idx needed in first byte)

    # Under this model, 118 entries are:
    # [comp_id=0x0A, flag=0x02, 0x00, 0x00, 0x00, param=0x04, 0x00, 0x00] x 16
    # comp_id=10 (Swing), param=4

    # And 119 entries should be:
    # [step, param, 0, 0, comp, bitmask, 0, 0] x 16 = 128 bytes from body+0xA9.
    # This WORKS for steps 0-9 but BREAKS at entry 10.

    # The BREAK at entry 10: raw = [07 04 04 00 00 00 02 08]
    # If we read: step=7, param=4, bytes 2-3 = 04 00 (NOT ZERO!), comp=0, bitmask bytes = 02 08 00
    # The 04 at byte 2 is unexpected.

    # What if byte 2 is a SECONDARY PARAMETER? Some components might have 2 params.
    # Flam has: delay and velocity?
    # Let me check: entry 7 (first with comp=5 Flam): [06 04 00 00 05 01 00 00]
    # step=6, param1=4, param2=0, 0, comp=5, bitmask=0x0100
    # Then entry 8: [06 01 00 00 04 02 00 00]
    # step=6, param1=1, param2=0, 0, comp=4, bitmask=0x0200
    # Step 6 has: Flam(param=4) and Roll(param=1)?

    # Entry 9: [07 04 00 00 03 04 00 00] -> step=7, param=4, comp=3(NoteRepeat), mask=0x0400
    # Entry 10: [07 04 04 00 00 00 02 08] -> step=7, param=4, byte2=4!
    # This could be step 7 with a SECOND component. But then comp would be at byte 4=0x00...

    # Unless the entries are VARIABLE: most are 8 bytes, but some components require
    # 10 bytes (8 + 2 extra param bytes). This would explain the 130 vs 128 byte difference!

    # Let me try: parse entries as variable-length based on component type
    print(f"\n{'='*80}")
    print("119 VARIABLE-LENGTH ENTRY PARSE (8 base + extra for some types)")
    print(f"{'='*80}")

    # The 2 extra bytes in 119 mean ONE entry has 2 extra bytes.
    # From the data, the break happens around entry 10.
    # Let me try: entries 0-9 are 8 bytes each, entry 10 is 10 bytes, entries 11-15 are 8 bytes.
    # 10 * 8 + 1 * 10 + 5 * 8 = 80 + 10 + 40 = 130. But data from body+0xA9 is 128.
    # Unless header is from body+0xA7 to body+0xA9 (2 bytes), and data is 128 bytes.

    # With all entries from body+0xA9:
    # If entry 10 is 10 bytes and rest are 8:
    # 15 * 8 + 1 * 10 = 120 + 10 = 130. But data is 128 bytes.
    # Doesn't work.

    # If TWO entries are 6 bytes and rest are 8:
    # 14 * 8 + 2 * 6 = 112 + 12 = 124. Nope.

    # What about from body+0xA7 (130 bytes total)?
    # Header: E4 01 (2 bytes)
    # Entries: 128 bytes = 16 * 8. Clean!
    # OR: no header, and entries have different alignment.

    # Let me try: ALL 130 bytes are entries.
    # 130 / 10 = 13 entries of 10 bytes?
    print(f"\n119 as 10-byte entries from body+0xA7 (13 entries):")
    full_data = body_119[0xA7:0xA7+130]
    for i in range(13):
        entry = full_data[i*10:(i+1)*10]
        print(f"  [{i:2d}]: {' '.join(f'{b:02X}' for b in entry)}")

    # 130 / 5 = 26? 2 records per step?
    # Let me try 5-byte records from body+0xA9 (128 bytes):
    # 128 / 5 = 25.6. Nope.

    # From body+0xA9, 4-byte records: 128 / 4 = 32 records = 2 per step
    print(f"\n119 as 4-byte records from body+0xA9 (32 records = 2 per step):")
    data = body_119[0xA9:0xA9+128]
    for i in range(32):
        rec = data[i*4:(i+1)*4]
        val = struct.unpack_from('<I', rec, 0)[0]
        print(f"  [{i:2d}]: {' '.join(f'{b:02X}' for b in rec)}  (u32={val:#010x})")

    # That gives us pairs. Let me pair them up:
    print(f"\n119 as 16 steps with TWO 4-byte values each:")
    for step in range(16):
        rec1 = data[step*8:step*8+4]
        rec2 = data[step*8+4:step*8+8]
        v1 = struct.unpack_from('<I', rec1, 0)[0]
        v2 = struct.unpack_from('<I', rec2, 0)[0]
        comp_id = rec2[0]
        comp_name = comp_names.get(comp_id, f"???")
        print(f"  Step {step:2d}: [{' '.join(f'{b:02X}' for b in rec1)}] [{' '.join(f'{b:02X}' for b in rec2)}]  "
              f"comp={comp_id}({comp_name})")

    # Steps 0-9 decode cleanly with comp_id at rec2[0].
    # Step 10 onwards breaks because rec2[0] = 0x00 (Probability) which doesn't
    # match the expected counting-down pattern.

    # CRITICAL TEST: Let me try a DIFFERENT entry size.
    # What if each entry is: step_idx(1) + comp_id(1) + param(1) + bitmask(2) = 5 bytes?
    # Or: step_idx(1) + comp_id(1) + bitmask(1) = 3 bytes?

    # Actually, I just realized: entry 10 starts at byte 80 of the data block.
    # The comp_info for entry 10 would be at byte 84.
    # What's there? data[84:88] = 00 00 02 08
    # comp=0, bitmask bytes = 00 02 08 -> bitmask = 0x080200
    # That's bits 9, 17, 19. Multi-bit bitmask!

    # Unless the bitmask field is only 1 byte, not 3.
    # If entry format is: [step:1, param:1, comp:1, bitmask:1, padding:4] = 8 bytes?
    # Then for entry 0 from body+0xA9: step=0, param=4, comp=0, bitmask=0
    # That has comp=0 for all entries, which doesn't match.

    # OK, let me try: [step:1, param:1, pad:2, comp:1, bitmask_u16_LE:2, pad:1]
    # From body+0xA9 entry 0: step=0, param=4, pad=0000, comp=0x0B, bitmask=0x0002, pad=0
    # That's comp=11(Glide), bitmask=bit 1. WORKS for entries 0-9!

    # Entry 10 from body+0xA9: [07 04 04 00 00 00 02 08]
    # step=7, param=4, pad=0400, comp=0x00, bitmask=0x0002, pad=0x08
    # The pad field is 0x0400 (not 0x0000). This is where it breaks.

    # UNLESS: this entry belongs to step 7 as a SECOND component,
    # and the format for entry 10 is:
    # step=7, param=4, param2=4, pad=0, comp=0(Probability), bitmask=0x0802=2050=bits 1,9,11
    # That's odd. Multi-bit bitmask shouldn't happen for a single entry.

    # Let me reconsider the bitmask interpretation.
    # Maybe the bitmask is NOT per-step but something else entirely.
    # What if byte 5 (after comp_id) is just ANOTHER parameter, not a bitmask?

    # For steps 0-9: byte 5 values are 02,04,08,10,20,40,80,01,02,04
    # These look like they DOUBLE each time, which is suspicious for a "parameter" but
    # very natural for a bitmask. But they're in the comp_info, not the step_data.

    # What if the bitmask indicates which STEP this component applies to?
    # And the step_data byte 0 is NOT a step index but something else?

    # For steps 0-9 (from body+0xA9):
    # step_data byte 0: 0,0,1,2,3,4,5,6,6,7
    # bitmask u16: 0x0002, 0x0004, 0x0008, 0x0010, 0x0020, 0x0040, 0x0080, 0x0100, 0x0200, 0x0400
    # bitmask bit: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

    # step_data[0] increments but repeats at 0 (entries 0,1) and 6 (entries 7,8).
    # bitmask bit strictly increments without repeats.

    # This suggests the BITMASK is the true step indicator, and step_data[0] is
    # something else. But bitmask bit 1 corresponds to step 0, bit 2 to step 1, etc.
    # Then entries 0,1 both have step_data[0]=0 but bitmasks for steps 0 and 1.
    # And entries 7,8 have step_data[0]=6 but bitmasks for steps 7 and 8.

    # So step_data[0] might be the COMPONENT NUMBER or ORDER, not the step index.
    # Or it's an index into a component table.

    # WAIT: steps 0 and 1 have the same step_data[0]=0 but different comps (11 and 10).
    # Steps 7 and 8 have step_data[0]=6 but comps 5 and 4.
    # The step_data[0] SKIPS when there are multiple components:
    # 0,0,1,2,3,4,5,6,6,7
    # The jumps are: 0->0 (repeat), 0->1, 1->2, 2->3, 3->4, 4->5, 5->6, 6->6 (repeat), 6->7
    # It increments when the STEP changes, not when the entry changes!

    # So step_data[0] IS the step index after all. Steps 0 and 6 have 2 components each.
    # The bitmask bits don't correspond to step indices; they correspond to ENTRY indices.
    # Bit N = "this is entry N" or "this component is the Nth unique one in the block"

    # Actually no -- the bitmask doubling by factor of 2 each time strongly suggests
    # it's just a sequential counter: entry 0 -> bit 1, entry 1 -> bit 2, etc.
    # The purpose might be to identify each entry uniquely, like an ID.

    # Let me now figure out the TOTAL number of entries needed.
    # If step_data[0] is the step index, and we need to reach step 15:
    # The pattern is: 0,0,1,2,3,4,5,6,6,7 for entries 0-9
    # So entries 10-15 should continue: 7 or 8, 8 or 9, 9 or 10, ...

    # If we assume the alignment IS correct at 8 bytes per entry from body+0xA9:
    # Entry 10: step=7 -- still on step 7? Triple component?
    # Let me check if step 7 might have 3 components.

    # Actually, the fact that entry 10 has pad=0x0400 (nonzero) but prior entries have pad=0x0000
    # suggests the alignment shifted. A PREVIOUS entry was larger than 8 bytes.

    # Let me try: what if some entries are 8+2=10 bytes?
    # Looking at entry 9: [07 04 00 00 03 04 00 00] -- step=7, comp=3(NoteRepeat)
    # What if entry 9 is 10 bytes instead of 8?
    # Then entry 9 = [07 04 00 00 03 04 00 00 07 04] (first 10 bytes starting at pos 72)
    # And entry 10 starts at pos 82: data[82:90] = [04 00 00 00 02 08 00 00]
    # step=4, comp=0x02(Ratchet), bitmask byte = 0x08
    # Hmm, step=4 doesn't fit the progression.

    # Let me try: entry 10 (comp=Ratchet?) starts 2 bytes later than expected
    # Offset the remaining entries by +2:
    print(f"\n{'='*80}")
    print("119 SHIFTED PARSE: entries 0-9 at 8 bytes, then +2 shift")
    print(f"{'='*80}")

    data = body_119[0xA9:0xA9+128]
    for i in range(10):
        entry = data[i*8:(i+1)*8]
        step_idx = entry[0]
        comp_id = entry[4]
        comp_name = comp_names.get(comp_id, f"???")
        bitmask_byte = entry[5]
        print(f"  [{i:2d}] @+{i*8:3d}: step={step_idx} comp={comp_id:2d}({comp_name:12s}) "
              f"raw={' '.join(f'{b:02X}' for b in entry)}")

    # After 10 entries (80 bytes), try offset +2:
    offset_shift = 82  # 80 + 2
    remaining_bytes = 128 - offset_shift  # 46 bytes
    print(f"\n  Shifted by +2 from entry 10 (starting at data+{offset_shift}):")
    print(f"  Remaining: {remaining_bytes} bytes = {remaining_bytes / 8:.2f} entries")

    for i in range(remaining_bytes // 8):
        pos = offset_shift + i * 8
        entry = data[pos:pos+8]
        step_idx = entry[0]
        comp_id = entry[4]
        comp_name = comp_names.get(comp_id, f"???")
        print(f"  [{10+i:2d}] @+{pos:3d}: step={step_idx} comp={comp_id:2d}({comp_name:12s}) "
              f"raw={' '.join(f'{b:02X}' for b in entry)}")

    # And what about the 2 skipped bytes?
    skipped = data[80:82]
    print(f"\n  Skipped bytes at +80: {' '.join(f'{b:02X}' for b in skipped)}")

    # Try: entry 10 is 10 bytes (8 regular + 2 extra)
    entry_10_10 = data[80:90]
    print(f"\n  If entry 10 is 10 bytes: {' '.join(f'{b:02X}' for b in entry_10_10)}")
    print(f"  step={entry_10_10[0]} comp={entry_10_10[4]}({comp_names.get(entry_10_10[4], '???')})")

    # After entry 10 (10 bytes), entries 11-15 at 8 bytes:
    for i in range(5):
        pos = 90 + i * 8
        if pos + 8 > 128:
            break
        entry = data[pos:pos+8]
        step_idx = entry[0]
        comp_id = entry[4]
        comp_name = comp_names.get(comp_id, f"???")
        print(f"  [{11+i:2d}] @+{pos:3d}: step={step_idx} comp={comp_id:2d}({comp_name:12s}) "
              f"raw={' '.join(f'{b:02X}' for b in entry)}")

    # Hmm let me try yet another approach.
    # What if the entries DON'T have a fixed stride but are decoded by looking
    # at the component type to determine the entry length?

    # Or SIMPLER: what if the bitmask is not in the entry but is external,
    # and each entry is just: [comp_id:1, param:1, value:2] = 4 bytes?
    # Then step_data and comp_info are each 4-byte entries for DIFFERENT things.
    # Like: the first 16 u32s are step data, the next 16 u32s are comp data?

    # 32 * 4 = 128 bytes from body+0xA9. Let me try:
    print(f"\n{'='*80}")
    print("119 AS TWO ARRAYS OF 16 x u32 LE from body+0xA9")
    print(f"{'='*80}")

    data = body_119[0xA9:0xA9+128]
    step_vals = []
    comp_vals = []
    for i in range(16):
        step_vals.append(struct.unpack_from('<I', data, i * 4)[0])
    for i in range(16):
        comp_vals.append(struct.unpack_from('<I', data, 64 + i * 4)[0])

    print("\nStep values (first 16 u32s):")
    for i, v in enumerate(step_vals):
        b = data[i*4:i*4+4]
        print(f"  [{i:2d}]: {' '.join(f'{x:02X}' for x in b)}  = {v:#010x} = {v}")

    print("\nComp values (second 16 u32s):")
    for i, v in enumerate(comp_vals):
        b = data[64+i*4:64+i*4+4]
        print(f"  [{i:2d}]: {' '.join(f'{x:02X}' for x in b)}  = {v:#010x} = {v}")

if __name__ == "__main__":
    main()
