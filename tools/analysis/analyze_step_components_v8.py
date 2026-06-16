#!/usr/bin/env python3
"""
v8: The pattern is CLEAR for entries 0-9 as interleaved 4-byte pairs:
  [step_idx, param, 0, 0] [comp_id, bitmask_lo, bitmask_hi, 0]

Steps 0-9 decode perfectly as 8-byte entries from body+0xA9.
The break at entry 10 (record 20 in 4-byte view) has a non-zero byte 2.

KEY OBSERVATION: Step 7 (entry 9) has comp=3(NoteRepeat).
Entry 10 starts with step=7 again, suggesting step 7 has TWO components.
But byte 2 of step_data is non-zero (0x04).

HYPOTHESIS: Step 7 has stacked components. The second component entry
has an extra field (byte 2 non-zero). Let me decode the REST of the
data starting from the break point as variable entries.

Also: step 6 appears twice (entries 7 and 8) with different comps (Flam, Roll).
Step 0 appears twice (entries 0 and 1) with different comps (Glide, Swing).
So stacking is already present! The 8-byte alignment works for all stacked steps
up to entry 9.

The issue at entry 10: [07 04 04 00 00 00 02 08]
step=7, param=4, byte2=4, byte3=0 | comp=0, mask_lo=0, mask_mid=2, mask_hi=8

What if byte 2 is a SECONDARY PARAMETER for comp types that need it?
In that case the entry is still 8 bytes, but the interpretation changes.

But then entry 11 would be [00 00 08 04 02 00 00 01]:
step=0, param=0, byte2=8, byte3=4, comp=2, mask=0x010000
step=0 with comp=Ratchet? That doesn't fit the pattern of increasing step indices.

ALTERNATIVE: Maybe the 8-byte alignment is wrong after entry 9.
What if entry 9 is the LAST well-aligned entry, and the remaining data
has a different structure?

Let me try to decode entries from the break point using ONLY the step_idx
as a guide (looking for ascending step numbers with occasional repeats).
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

    # Data block from body+0xA9 (128 bytes for 119)
    data = body_119[0xA9:0xA9+128]

    # Clean entries 0-9 (80 bytes):
    print("="*80)
    print("119 CLEAN ENTRIES 0-9 (body+0xA9, 8 bytes each)")
    print("="*80)
    for i in range(10):
        e = data[i*8:(i+1)*8]
        step = e[0]
        param = e[1]
        comp = e[4]
        bm_lo = e[5]
        bm_hi = e[6]
        name = comp_names.get(comp, f"???({comp})")
        bitmask = bm_lo | (bm_hi << 8)
        print(f"  [{i:2d}] step={step:2d} param={param} comp={comp:2d}({name:12s}) "
              f"bitmask=0x{bitmask:04X} raw={' '.join(f'{b:02X}' for b in e)}")

    # Summary of step assignments:
    # Step 0: Glide(11), Swing(10) [2 components]
    # Step 1: Gate(9) [1 component]
    # Step 2: Velocity(8) [1 component]
    # Step 3: Transpose(7) [1 component]
    # Step 4: Nudge(6) [1 component]
    # Step 5: Flam(5) [1 component]
    # Step 6: Flam(5), Roll(4) [2 components]
    # Step 7: NoteRepeat(3) [1 component from entry 9]

    # Now: remaining data from byte 80 onwards (48 bytes)
    print(f"\n{'='*80}")
    print("119 REMAINING DATA FROM +80 (48 bytes)")
    print("="*80)
    remaining = data[80:]
    for i in range(0, len(remaining), 8):
        chunk = remaining[i:min(i+8, len(remaining))]
        print(f"  +{80+i:3d}: {' '.join(f'{b:02X}' for b in chunk)}")

    # Try decoding remaining as 8-byte entries:
    # [07 04 04 00 | 00 00 02 08] entry 10
    # [00 00 08 04 | 02 00 00 01] entry 11
    # [10 00 00 09 | 02 02 00 00] entry 12
    # [00 00 20 00 | 00 0A 02 02] entry 13
    # [00 01 00 04 | 00 00 0A 02] entry 14
    # [02 00 00 00 | 00 04 00 00] entry 15

    # Entry 15: step=2, param=0, comp=0(Prob), bitmask=0x0004
    # That has step=2 and bitmask bit 2. If bitmask bit 2 = step 1, this could be step 1?

    # Wait, let me reconsider. Looking at entries 0-9, the bitmask doubles:
    # 02, 04, 08, 10, 20, 40, 80, 01 00, 02 00, 04 00
    # As u16: 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024
    # Bits: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    #
    # The bitmask tracks the SEQUENTIAL ENTRY NUMBER, not the step.
    # Entry 0 -> bit 1, Entry 1 -> bit 2, etc.
    # After entry 9 (bit 10), next should be bit 11 = 0x0800.

    # Entry 10: bitmask bytes at [5:7] = 02 08 -> u16LE = 0x0802 = 2050
    # Binary: 100000000010 -- bits 1 and 11. That's TWO bits!

    # Unless... bytes [5:7] should be read differently.
    # What if the bitmask wraps at 8 bits and uses a SECOND byte?
    # e[5] = bitmask byte 0, e[6] = bitmask byte 1
    # Entry 9: e[5]=04, e[6]=00 -> byte0=bit2, byte1=0 -> entry bitmask = bit 10
    # (if byte0 = bits 0-7, byte1 = bits 8-15)
    # Entry 10: e[5]=02, e[6]=08 -> byte0=bit1, byte1=bit3(of hi)=bit 11
    # That's STILL multi-bit.

    # OBSERVATION: Entries 7 and 8 have bitmask 0x0001 and 0x0002 respectively.
    # Entry 7: bitmask 0x0001 = bit 0. But entry 0 had bit 1 (0x0002).
    # So the bitmask WRAPPED at entry 7 (after using bits 1-7).
    # Entry 7: bit 0, Entry 8: bit 1, Entry 9: bit 2.
    # So the bitmask is actually BYTE-wrapped: 7 bits per byte, then reset.
    # Bits used: entries 0-6 use bits 1-7 of byte 0.
    # Entries 7-13 use bits 0-6 of byte 1.
    # Entries 14-15+ would use byte 2.

    # Wait, that's not how single-byte bitmasks work.
    # Let me look at entries 0-6: bitmask low bytes: 02,04,08,10,20,40,80
    # These are bits 1,2,3,4,5,6,7 of the LOW byte.
    # Entries 7-9: low bytes: 01,02,04 BUT high bytes: 00,00,00
    # Wait no: entry 7: [05 01 00 00] -> bitmask bytes [1]=01, [2]=00
    # Entry 8: [04 02 00 00] -> bitmask bytes [1]=02, [2]=00
    # Entry 9: [03 04 00 00] -> bitmask bytes [1]=04, [2]=00

    # Hmm, let me re-examine. In the comp_info 4-byte field:
    # byte 0 = comp_id
    # byte 1 = bitmask low
    # byte 2 = bitmask high
    # byte 3 = always 0?

    # Entries 0-6: bitmask_lo = 02,04,08,10,20,40,80 (bits 1-7)
    # Entries 7-9: bitmask_lo = 01,02,04 and bitmask_hi = 00,00,00

    # WAIT! I was reading the wrong bytes. Let me be more careful.
    # Entry 0: raw = 00 04 00 00 0B 02 00 00
    #   step_data = [00, 04, 00, 00] -> step=0, param=4
    #   comp_info = [0B, 02, 00, 00] -> comp=11, byte1=02, byte2=00, byte3=00
    # Entry 7: raw = 06 04 00 00 05 01 00 00
    #   comp_info = [05, 01, 00, 00] -> comp=5, byte1=01, byte2=00, byte3=00

    # So bitmask bytes for entries 0-9 (from comp_info byte 1):
    # 02, 04, 08, 10, 20, 40, 80, 01, 02, 04
    # These are: 2,4,8,16,32,64,128, then 1,2,4
    # In binary: 00000010, 00000100, ..., 10000000, 00000001, 00000010, 00000100
    # After 128 (bit 7), it wraps to 1 (bit 0) and continues: 1,2,4,...
    # This is a ROTATING BITMASK within a single byte!
    # Bits 1-7 (entries 0-6), then bit 0 and up (entries 7+)
    # Why start at bit 1? Maybe bit 0 means "no component"?

    # OR: it's just a running counter that wraps modulo 8.
    # But 2,4,8,16,32,64,128 = bits 1-7 (7 entries), then 1,2,4 = bits 0-2 (3 entries)
    # After 8 entries in the low byte, the counter should move to the high byte.
    # Entry 8 (bit 8 overall) would be bitmask_hi bit 0 = byte2=01, byte1=00.
    # But entry 8 has byte1=02, byte2=00. Not what I expected.

    # Hmm, it seems like the bitmask just WRAPS within byte 1. After bit 7 (0x80),
    # it goes to bit 0 (0x01) of the SAME byte. No byte 2 usage.

    # Let me look at 118 to see what the bitmask looks like there:
    data_118_block = body_118[0xA9:0xA9+126]
    print(f"\n{'='*80}")
    print("118 ENTRIES (from body+0xA9, should all be the same component)")
    print("="*80)
    for i in range(16):
        off = i * 8
        if off + 8 > 126:
            e = data_118_block[off:]
            print(f"  [{i:2d}] TRUNCATED: {' '.join(f'{b:02X}' for b in e)}")
            break
        e = data_118_block[off:off+8]
        step = e[0]
        param = e[1]
        comp = e[4]
        bm = e[5]
        name = comp_names.get(comp, f"???({comp})")
        print(f"  [{i:2d}] step={step} param={param} comp={comp:2d}({name:12s}) "
              f"bitmask_lo=0x{bm:02X} raw={' '.join(f'{b:02X}' for b in e)}")

    # 118 entries: all `00 00 00 04 00 00 0A 02`
    # step=0, param=0, comp=0x0A(Swing), bitmask_lo=0x00
    # Wait, the param is 0 and comp is at position 4? That's weird.

    # In 118, reading from body+0xA9:
    # [00 00 00 04 00 00 0A 02]
    # If entry format is [step:1, param:1, 0, 0, comp:1, bm:1, 0, 0]:
    # step=0, param=0, comp=0, bm=0, trailing=0A 02
    # That puts comp=0 which doesn't match.

    # But if I read from body+0xA7 (including the E4):
    # Entry 0: [E4 02 00 00 00 04 00 00] -> comp at [4]=0x00
    # Entry 1: [0A 02 00 00 00 04 00 00] -> comp at [4]=0x00
    # Also comp=0.

    # UNLESS the 118 format is different (flag=0x02 at body+0xA8)
    # and uses a SHARED component ID rather than per-entry component ID.

    # Let me try: in 118, entries have NO per-entry comp ID.
    # The comp ID is in the header: body[0xA7]=0xE4? No, E4 is the marker.
    # Or body[0xA8]=0x02? But 0x02 = Ratchet. unnamed 118 probably has Ratchet on all steps.

    # Hmm wait. Let me reconsider the 118 entry format.
    # From body+0xA7: E4 02 00 00 00 04 00 00 0A 02 00 00 00 04 00 00 ...
    # What if entries are 8 bytes but shifted by 1 from what I've been trying?
    # Starting at body+0xA8:
    # Entry 0: [02 00 00 00 04 00 00 0A] -> comp at [4]=0x04? Or at [7]=0x0A?
    # If comp is at byte 7: comp=0x0A=Swing(10). ALL entries would have 0x0A at byte 7.

    # From body+0xA8, 16 entries of 8 bytes = 128 bytes through body+0x128:
    data_118_alt = body_118[0xA8:0xA8+128]
    print(f"\n{'='*80}")
    print("118 FROM body+0xA8 (16 x 8-byte entries)")
    print("="*80)
    for i in range(16):
        e = data_118_alt[i*8:(i+1)*8]
        # Try comp at byte 7:
        comp = e[7]
        name = comp_names.get(comp, f"???({comp})")
        print(f"  [{i:2d}]: {' '.join(f'{b:02X}' for b in e)}  comp_at_b7={comp}({name})")

    # Entry 15: [02 00 00 00 04 00 00 FF] -> byte 7 = 0xFF (padding!)
    # So the last entry has FF bleeding in. This confirms body+0xA8 is 1 byte too late.

    # From body+0xA7, if comp is at byte 0:
    # Entry 0: E4 -> comp=0xE4 (invalid)
    # Entry 1: 0A -> comp=10 (Swing) -- valid!

    # What if entry 0 at body+0xA7 is a HEADER ENTRY, not a real step component?
    # header: [E4 02 00 00 00 04 00 00] means marker=0xE4, type=0x02
    # Then entries 1-15 are the actual 15 step component entries?
    # But that gives only 15 steps, not 16.

    # UNLESS: header doubles as entry for step 0, with E4 being a special first-byte
    # that means "marker + comp_id" where the comp_id is actually separate.

    # OK STOP. Let me think about what's ACTUALLY different about 118 vs 119.

    # 118: body+0xA8 = 0x02 (flag byte). ALL entries are identical.
    # 119: body+0xA8 = 0x01 (flag byte). Entries differ per step.

    # What if 0x02 means "single component for all steps" (compact mode)
    # and 0x01 means "per-step component list" (expanded mode)?

    # In compact mode (0x02): [marker E4] [comp_id] [N bytes of per-step params]
    # In expanded mode (0x01): [marker E4] [flag] [N entries of (step, param, comp, bitmask)]

    # For 118 compact mode:
    # body+0xA7 = E4 (marker)
    # body+0xA8 = 0x02 (compact flag)
    # What's the comp_id? Maybe it's AFTER the flag?
    # body+0xA9 = 0x00. That's comp_id 0 = Probability? Doesn't seem right for "same on all".

    # For 118, the repeating pattern `0A 02 00 00 00 04 00 00` has 0x0A as the comp_id.
    # If I read entry 1 from body+0xAF (the second 8-byte block after E4 02):
    # [0A 02 00 00 00 04 00 00]
    # byte 0 = 0x0A = Swing(10)
    # byte 1 = 0x02
    # bytes 2-3 = 0x0000
    # byte 4 = 0x00
    # byte 5 = 0x04
    # bytes 6-7 = 0x0000

    # This pattern: comp=0x0A, then `02 00 00 00 04 00 00`.
    # In 119, entries are: [step param 00 00 comp bm 00 00]
    # In 118, if same format: step=0A(10?), param=02, comp=00, bm=04
    # step=10 doesn't make sense (only 16 steps 0-15).

    # UNLESS: 118 entries have comp ID at byte 0 and NO step index
    # (because all steps have it, step isn't needed).

    # 118 entry: [comp_id=0x0A, param=0x02, pad, pad, mystery=0x00, value=0x04, pad, pad]
    # comp=Swing(10), param=2, value=4

    # 119 entry: [step=N, param=M, pad, pad, comp_id=X, bitmask=Y, pad, pad]

    # So the two formats have DIFFERENT LAYOUTS for the same 8-byte entry!
    # In 118 (compact): byte 0 = comp_id, byte 1 = param, byte 5 = value
    # In 119 (expanded): byte 0 = step, byte 1 = param, byte 4 = comp_id, byte 5 = bitmask

    # For 118:
    # Entry 0: [E4 02 00 00 00 04 00 00] -> comp=0xE4?
    # That's the marker. So entry 0 is SPECIAL.
    # The pattern for entries 1-15: comp=0x0A, param=0x02, value=0x04

    # In 119:
    # Entry 0 (body+0xA7): [E4 01 00 04 00 00 0B 02]
    # byte 0 = E4 (marker), byte 1 = 01 (flag), byte 2-3 = 00 04 (???)
    # byte 4-5 = 00 00 (???), byte 6 = 0B (comp_id!), byte 7 = 02 (bitmask)

    # WAIT. What if in 119, entry 0 is:
    # [E4 01 00 04 00 00 0B 02] where:
    # E4 = marker (like 118)
    # 01 = flag (expanded mode)
    # 00 04 = step 0 param (u16 LE = 1024? Or bytes: step=0, param=4)
    # 00 00 = padding
    # 0B = comp_id = 11 (Glide)
    # 02 = bitmask

    # So the structure might be:
    # [marker:1, flag:1, step:1, param:1, pad:2, comp:1, bm:1]
    # Entry 0: marker=E4, flag=01, step=0, param=4, pad=0000, comp=0B, bm=02
    # Entry 1 (body+0xAF): [00 04 00 00 0A 04 00 00]
    # But this doesn't have marker or flag...

    # The marker is only in the FIRST entry! After that:
    # Entry 1: [00 04 00 00 0A 04 00 00]
    # If format is [pad:2, step:1, param:1, pad:2, comp:1, bm:1]:
    # pad=00 04, step=0, param=0, pad=0A 04, comp=0, bm=0. Nope.

    # Or: [step:1, param:1, pad:2, comp:1, bm:1, pad:2]
    # step=0, param=4, pad=0000, comp=0A, bm=04, pad=0000
    # comp=10(Swing), bm=0x04. THAT WORKS!

    # So 119 entries from body+0xA9 (after the 2-byte header E4 01):
    # Each entry: [step:1, param:1, 00, 00, comp:1, bm:1, 00, 00]
    # This is what I already had. The first 10 entries decode perfectly.

    # Now the BITMASK: for entries 0-9, bm values are:
    # 02, 04, 08, 10, 20, 40, 80, 01, 02, 04
    # This rotates through a single byte: starting at bit 1, going to bit 7,
    # then wrapping to bit 0 and continuing.
    # After entry 6 (bm=0x80), entry 7 starts at bm=0x01 (wraps around).
    # After entry 9 (bm=0x04), entry 10 should have bm=0x08.

    # Entry 10 raw: [07 04 04 00 00 00 02 08]
    # step=7, param=4, byte2=0x04(!), byte3=0, comp=0, bm=0x02, byte6=0x08(!)
    # byte2 is non-zero! And comp=0.

    # Unless entry 10 has a DIFFERENT structure because it's a multi-component
    # step or a component with extra parameters.

    # Let me try: what if entry 10's byte 2 is PART OF THE PREVIOUS ENTRY?
    # What if entry 9 is 9 bytes, not 8?
    # Entry 9 (9 bytes): [07 04 00 00 03 04 00 00 07]
    # Then entry 10 (8 bytes): [04 04 00 00 00 02 08 00]
    # step=4, param=4, comp=0, bm=2. Still doesn't look right.

    # What if entry 9 is 10 bytes?
    # Entry 9: [07 04 00 00 03 04 00 00 07 04]
    # Entry 10: [04 00 00 00 02 08 00 00]
    # step=4, param=0, comp=0x02(Ratchet), bm=0x08. Step=4? But we're past step 7.

    # What if entry 10 is PRECEDED by a 2-byte extension to entry 9?
    # Entry 9 base: [07 04 00 00 03 04 00 00]
    # Extension: [07 04] (step=7, extra_param=4)
    # Entry 10: [04 00 00 00 02 08 00 00]
    # This doesn't make sense either.

    # DIFFERENT APPROACH: Let me try reading entries as 5 bytes each.
    # header (E4 01) at body+0xA7, then from body+0xA9:
    # 128 bytes / 5 bytes = 25.6. Not clean.

    # What about 6 bytes each?
    # 128 / 6 = 21.33. Nope.

    # Back to 8 bytes. Let me check if entries 10-15 make sense
    # if the COMP and BITMASK are at DIFFERENT positions.
    # What if for some entries, the comp is at byte 2 instead of byte 4?

    # Entry 10: [07 04 04 00 00 00 02 08]
    # If comp is at byte 2: comp=4(Roll), bm at byte 3=0. param=4.
    # Then bytes 4-7: 00 00 02 08 = extra data?

    # This is getting nowhere. Let me check what DOCUMENTATION exists for these files.
    # The file numbering suggests unnamed 118 and 119 are part of a series of experiments.

    # Let me look at this problem from the HARDWARE side.
    # OP-XY step components can be stacked (multiple per step).
    # The device has exactly 14 component types.
    # Each can be applied to any of 16 steps.

    # BITMASK REINTERPRETATION:
    # What if the bitmask isn't sequential but identifies WHICH STEPS have this component?
    # In 118 (all same), the bitmask would be 0xFFFF (all 16 steps).
    # In 119 (different per step), each entry has a single-step bitmask.

    # For 118, entries from body+0xA9: [00 00 00 04 00 00 0A 02]
    # If we read as: [pad:4, bitmask:u16_LE, comp_id, param]
    # pad=00000004, bitmask=0x0000, comp=0x0A, param=0x02
    # bitmask=0 doesn't make sense.

    # What if: [bitmask_lo:u16_LE, bitmask_hi:u16_LE, comp_id, param, pad, pad]
    # Entry (118): bitmask=0x0000 0x0400, comp=0x00, param=0x0A...  Nope.

    # Let me try: the ENTIRE 8 bytes as a single u64:
    # 118 entry: 00 00 00 04 00 00 0A 02 = u64LE = 0x020A000004000000
    # 119 entry 0: 00 04 00 00 0B 02 00 00 = u64LE = 0x0000020B00000400

    # Let me try: for 119, step_bitmask = u16 at bytes 0-1, comp_id at byte 4, value at byte 5
    print(f"\n{'='*80}")
    print("119: step_bitmask as u16LE at bytes 0-1")
    print("="*80)

    for i in range(16):
        e = data[i*8:(i+1)*8]
        bm = struct.unpack_from('<H', e, 0)[0]
        comp = e[4]
        val = e[5]
        name = comp_names.get(comp, f"???({comp})")
        # Which bits are set in bm?
        bits = [j for j in range(16) if bm & (1 << j)]
        print(f"  [{i:2d}]: bm=0x{bm:04X}={bm:016b} comp={comp:2d}({name:12s}) val=0x{val:02X} "
              f"bits={bits} raw={' '.join(f'{b:02X}' for b in e)}")

    # step_bitmask: 0x0400, 0x0400, 0x0201, 0x0502, 0x0403, 0x0404, 0x0405, 0x0406, 0x0106, 0x0407
    # bits: [10], [10], [0,9], [1,8,10], [0,2,10], [2,10], [0,2,10], [1,2,10], [1,2,8], [0,2,10]
    # These don't look like single-step bitmasks.

    # FINAL APPROACH: Let me try parsing the 119 data as 6+2 = 8 bytes per entry
    # where the entry is: [step:1, comp:1, param:1, bitmask:1, value_u16:2, pad:2]
    print(f"\n{'='*80}")
    print("119: [step:1, comp:1, param:1, bitmask:1, value_u16:2, pad:2]")
    print("="*80)
    for i in range(16):
        e = data[i*8:(i+1)*8]
        step = e[0]
        comp = e[1]
        param = e[2]
        bm = e[3]
        value = struct.unpack_from('<H', e, 4)[0]
        name = comp_names.get(comp, f"???({comp})")
        print(f"  [{i:2d}]: step={step:2d} comp={comp:2d}({name:12s}) param={param} bm=0x{bm:02X} "
              f"value={value:5d} raw={' '.join(f'{b:02X}' for b in e)}")

    # step=0, comp=4, param=0, bm=0, value=0x020B=523, pad=0000
    # comp=4 is Roll. For step 0 that should be Glide(11). Doesn't match.

    # [step:1, param:1, comp:1, value:1, extra:4]?
    print(f"\n{'='*80}")
    print("119: [step:1, param:1, comp:1, value:1, extra:4]")
    print("="*80)
    for i in range(16):
        e = data[i*8:(i+1)*8]
        step = e[0]
        param = e[1]
        comp = e[2]
        value = e[3]
        extra = struct.unpack_from('<I', e, 4)[0]
        name = comp_names.get(comp, f"???({comp})")
        print(f"  [{i:2d}]: step={step:2d} param={param} comp={comp:2d}({name:12s}) value={value} "
              f"extra=0x{extra:08X}")

    # step=0, param=4, comp=0, value=0, extra=0x0000020B
    # comp=0 = Probability. Not matching.

    # I keep coming back to: [step, param, pad, pad, comp, bitmask, pad, pad]
    # works for entries 0-9, breaks at 10.

    # Let me check: maybe the problem is that unnamed 119 has step components
    # on fewer than 16 steps, and entries 10+ have a DIFFERENT meaning
    # (like a footer or padding).

    # From the clean entries 0-9:
    # Step 0: Glide + Swing (2 entries)
    # Step 1: Gate (1 entry)
    # Step 2: Velocity (1 entry)
    # Step 3: Transpose (1 entry)
    # Step 4: Nudge (1 entry)
    # Step 5: Flam (1 entry)
    # Step 6: Flam + Roll (2 entries)
    # Step 7: NoteRepeat (1 entry)
    # That's 10 entries covering steps 0-7.
    # Steps 8-15 might not have components, so entries 10-15 could be PADDING.

    # But then what's in entries 10-15? Let me check if they're all zeros or padding:
    print(f"\n{'='*80}")
    print("ENTRIES 10-15: ARE THEY PADDING?")
    print("="*80)
    for i in range(10, 16):
        e = data[i*8:(i+1)*8]
        is_zero = all(b == 0 for b in e)
        print(f"  [{i:2d}]: {' '.join(f'{b:02X}' for b in e)}  all_zero={is_zero}")

    # They're NOT all zeros. So either they're valid entries with different format,
    # or my interpretation is wrong.

    # Let me look at this problem from 118 and check if the same decode works.
    # 118 from body+0xA9 as [step, param, pad, pad, comp, bm, pad, pad]:
    # [00 00 00 04 00 00 0A 02]
    # step=0, param=0, pad=00 04, comp=0x00(Prob), bm=0x00
    # That gives comp=0 and param=0. But 118 should have Swing(10) or something.

    # The format [step, param, 0, 0, comp, bm, 0, 0] from body+0xA9 ONLY works for 119.
    # For 118, the repeating pattern is `00 00 00 04 00 00 0A 02` which decodes as
    # step=0, param=0, but we know all 16 steps have the component.

    # Maybe for 118 (compact mode), the format is DIFFERENT:
    # [bitmask_u16:2, pad:2, param:1, pad:1, comp:1, value:1] or similar.

    # Let me try 118 from body+0xA9: [00 00 00 04 00 00 0A 02]
    # What if it's: [pad:2, param_u16:2, pad:2, comp:1, value:1]
    # param_u16=0x0400=1024, comp=0x0A(Swing), value=0x02=2
    # That gives Swing with param=1024 and value=2. Plausible!

    # Check: all 16 entries have the same param and comp? YES (from the hex dump,
    # all entries are identical: 00 00 00 04 00 00 0A 02).

    # For 119 with the SAME format: [pad:2, param_u16:2, pad:2, comp:1, value:1]
    # Entry 0: pad=0004, param=0x0000, pad=0x020B, comp=0x00, value=0x00
    # That gives comp=0(Prob) which doesn't match.

    # Hmm. The format seems genuinely different between 118 and 119.

    # Let me try one more thing: what if the ENTIRE component block encoding
    # uses a different ENTRY WIDTH based on the flag byte?
    # Flag 0x02: entry width = 8 bytes, format = [pad:2, param:2, pad:2, comp:1, value:1]
    # Flag 0x01: entry width = 8 bytes, format = [step:1, param:1, pad:2, comp:1, bm:1, pad:2]

    # For 118 (flag 0x02):
    # Entries from body+0xA9, 126 bytes / 8 = 15.75.
    # HMMMM. What if flag 0x02 entries are 7 bytes?
    # 126 / 7 = 18. That's still not 16.

    # What if flag 0x02 means entries start at body+0xA8 (not 0xA9)?
    # From body+0xA8: [02 00 00 00 04 00 00 0A] x 16 (the last has 0xFF at byte 7)
    # If format is [value:1, pad:3, param_u16:2, comp:1, ?:1]:
    # value=2, param=0x0004=4, comp=0x00, ?=0x0A
    # comp=0 doesn't work.

    # Or: [flag:1, pad:3, param:1, pad:1, comp:1, bm:1]
    # flag=2, param=4, comp=0x0A(Swing), bm=2
    # Swing with param=4, bitmask=2. And this repeats for all entries.
    # That works semantically! flag=2 might mean "this is a compact entry".

    # So for 118 from body+0xA8: entry = [02 00 00 00 04 00 00 0A]
    # decoded as: flag/type=0x02, pad=000000, param=0x04, pad=0x00, comp=0x0A, bm=0x02(?)
    # But bm=0x02 for ALL entries, which means all entries have bitmask bit 1 set.
    # A single bitmask value for all entries doesn't help identify steps.

    # Unless bitmask=0x02 means "all steps" in compact mode (bit 1 = "all active").

    # I think the key insight is:
    # 118 flag=0x02: same component on all steps, entries DON'T need step index
    # 119 flag=0x01: different component per step, entries include step index

    # And the entry FORMAT differs between the two modes!

    # For 118, the DATA per step might be simpler. Let me try 4-byte entries:
    # From body+0xA9: 126 bytes / 4 = 31.5. Nope.
    # From body+0xA8: 127 bytes / 4 = 31.75. Nope.

    # 7-byte entries from body+0xA8: 127 / 7 = 18.14. Nope.
    # 7-byte from body+0xA9: 126 / 7 = 18. Could be 18 entries of 7 bytes.
    # But why 18 for 16 steps?

    # WHAT IF I'VE BEEN WRONG ABOUT THE NUMBER OF SLOTS?
    # Let me check: how many `00 FF 00` slots are there in unnamed 118?
    # Earlier we found: baseline=52, 118=44, 119=44.
    # Difference = 8 slots removed (24 bytes).
    # Plus the extra bytes: 118=125 extra, 119=127 extra.
    # So total component data = 24 (removed slots) + 125 (extra) - 1 (header byte change) = 148?
    # Hmm, that's the region size we calculated (150/152 bytes).

    # Actually, let me look at the TOTAL region again:
    # Baseline region (body+0xA6 to DF header): 25 bytes (8 slots + 1 byte)
    # 118 region: 150 bytes (body+0xA6 to 06 header)
    # 119 region: 152 bytes

    # 118 region - baseline region = 125 extra bytes (matches body size difference)
    # 119 region - baseline region = 127 extra bytes (matches)

    # The 150 bytes in 118 = 3 (header: 00 E4 02) + N entries + M padding
    # Let me count the padding in 118's region:
    # Region: body[0xA6:0x13C]
    region_118 = body_118[0xA6:0x13C]
    ff_count = sum(1 for b in region_118 if b == 0xFF)
    zero_count = sum(1 for b in region_118 if b == 0x00)
    other_count = len(region_118) - ff_count - zero_count
    print(f"\n{'='*80}")
    print(f"118 region stats (150 bytes): FF={ff_count}, 00={zero_count}, other={other_count}")

    # Count FF 00 00 triples:
    triple_count = 0
    for i in range(len(region_118) - 2):
        if region_118[i] == 0xFF and region_118[i+1] == 0x00 and region_118[i+2] == 0x00:
            triple_count += 1
    print(f"FF 00 00 triples: {triple_count}")

    # From the hex dump, the 118 region has:
    # 3 bytes header (00 E4 02)
    # ~128 bytes entry data (patterns with 0A, 02, 04)
    # ~19 bytes padding (FF 00 00 patterns)

    # 3 + 128 + 19 = 150. PERFECT!
    # But 19 bytes of padding = 6 x (FF 00 00) + 1 extra byte (00).
    # 6.33 triples. Not clean.

    # From the hex dump earlier:
    # body[0x127:0x13C] = FF 00 00 FF 00 00 FF 00 00 FF 00 00 FF 00 00 FF 00 00 FF 00 00
    # That's 21 bytes = 7 x (FF 00 00). But body[0xA6:0xA7] = 00.
    # So: header(00 E4 02) = 3 bytes + entries(0xA9 to 0x127) = 126 bytes + padding(0x127 to 0x13C) = 21 bytes
    # 3 + 126 + 21 = 150. YES!

    # For 119:
    region_119 = body_119[0xA6:0x13E]
    # 3 bytes header (00 E4 01)
    # 128 bytes entries (body+0xA9 to body+0x129)
    # 21 bytes padding (body+0x129 to body+0x13E)
    # 3 + 128 + 21 = 152. CORRECT!

    print(f"\n{'='*80}")
    print("DEFINITIVE STRUCTURE")
    print("="*80)
    print(f"""
Component block structure:
  body+0xA6: 00 (slot separator, unchanged)
  body+0xA7: E4 (marker, replaces 0xFF of empty slot)
  body+0xA8: flag byte (0x02=compact/uniform, 0x01=expanded/per-step)
  body+0xA9 to end: entry data
  After entries: FF 00 00 padding (fills remaining slot space + expansion)
  After padding: 06 (track parameter header byte, was 0xDF in baseline)

Entry data:
  118 (flag=0x02): 126 bytes = 16 entries @ 7.875 bytes -- NOT CLEAN
    OR: 18 entries @ 7 bytes -- WHY 18?

  119 (flag=0x01): 128 bytes = 16 entries @ 8 bytes
    Format: [step:1, param:1, 00, 00, comp:1, bm:1, 00, 00]
    Verified for entries 0-9. Entries 10-15 misaligned (stacked components?).

REMAINING PUZZLE for 118:
  Pattern: 00 00 00 04 00 00 0A 02 (repeating)
  This repeats 15.75 times (126 bytes).
  The 15th full repeat ends at byte 120. Remaining 6 bytes: 00 00 00 04 00 00.
  Then byte 126 = body+0x127 = 0xFF (padding starts).

  Maybe: 15 entries of 8 bytes (120) + 6 bytes (3/4 of an entry) + 2 bytes absorbed into padding?
  Or: the pattern is actually 7 bytes repeating? Let me check!
""")

    # Check if the 118 pattern is 7 bytes: 00 00 00 04 00 00 0A repeating
    # vs 8 bytes: 00 00 00 04 00 00 0A 02
    d118 = body_118[0xA9:0xA9+126]
    print("Checking 118 for 7-byte repeat:")
    pat7 = d118[0:7]  # 00 00 00 04 00 00 0A
    matches7 = sum(1 for i in range(0, 126, 7) if d118[i:i+7] == pat7)
    print(f"  7-byte pattern '{' '.join(f'{b:02X}' for b in pat7)}': {matches7}/18 matches")

    pat8 = d118[0:8]  # 00 00 00 04 00 00 0A 02
    matches8 = sum(1 for i in range(0, 126, 8) if d118[i:i+8] == pat8)
    print(f"  8-byte pattern '{' '.join(f'{b:02X}' for b in pat8)}': {matches8}/15 matches")

    # Let me also just verify: is the ENTIRE 126 bytes one repeating 8-byte pattern?
    # If so, byte 126 should be the FIRST byte of the pattern.
    # d118[120:126] = the last 6 bytes. If pattern is 8, this is 6/8 of the pattern.
    last6 = d118[120:126]
    first6 = d118[0:6]
    print(f"\n  First 6 bytes: {' '.join(f'{b:02X}' for b in first6)}")
    print(f"  Last 6 bytes:  {' '.join(f'{b:02X}' for b in last6)}")
    print(f"  Match: {first6 == last6}")

    # If they match, the pattern IS 8 bytes but the data is truncated at 126 = 15*8 + 6.
    # The last 2 bytes of the 16th entry (which would be `0A 02`) are missing!
    # But body[0x127] = 0xFF and body[0x128] = 0x00.
    # What if 0xFF 0x00 is the last 2 bytes of the 16th entry?
    # Then entry 16 = [00 00 00 04 00 00 FF 00] -- that has 0xFF, which the parser
    # might interpret as padding. But it's actually the last entry.

    # Hmm, let me check body[0x127] and body[0x128]:
    print(f"\n118 body[0xA9+126] = body[0x127] = 0x{body_118[0x127]:02X}")
    print(f"118 body[0xA9+127] = body[0x128] = 0x{body_118[0x128]:02X}")

    # So byte 126 (from entry start) = 0xFF.
    # If 16 entries at 8 bytes = 128 bytes, the 16th entry would be:
    # d118[120:128] but d118 only has 126 bytes. The last 2 bytes are at body[0x127:0x129]:
    # = FF 00.
    # 16th entry: [00 00 00 04 00 00 FF 00] <- has 0xFF replacing 0x0A

    # WAIT: what if the last entry intentionally has 0xFF in the comp_id position?
    # For compact mode (flag=0x02), maybe the last entry is a TERMINATOR
    # with comp_id=0xFF meaning "end of list".

    # So the structure might be:
    # Header: 00 E4 02
    # 15 entries of 8 bytes: comp=0x0A, same params
    # 1 terminator entry of 8 bytes: comp=0xFF (end marker)
    # Padding

    entry_16_118 = body_118[0xA9+120:0xA9+128]
    print(f"\n118 entry 16 (including FF): {' '.join(f'{b:02X}' for b in entry_16_118)}")
    # 00 00 00 04 00 00 FF 00 -- comp at byte 6 = 0xFF. TERMINATOR!

    # And for 119:
    entry_16_119 = body_119[0xA9+120:0xA9+128]
    print(f"119 entry 16 (last 8 bytes): {' '.join(f'{b:02X}' for b in entry_16_119)}")
    # 02 00 00 00 00 04 00 00

    # Hmm, 119 doesn't have FF in the last entry.
    # What comes AFTER body+0xA9+128 in 119?
    print(f"119 body[0x129:0x131]: {' '.join(f'{body_119[i]:02X}' for i in range(0x129, 0x131))}")
    # FF 00 00 FF 00 00 FF 00 -- padding starts!

    # So 119 has exactly 128 bytes of entry data (16 entries of 8 bytes)
    # followed by FF padding. No terminator entry needed.

    # And 118 has entries that INCLUDE a terminator entry with FF in the comp position.
    # So 118 has 15 real entries + 1 terminator = 16 x 8 = 128 bytes... but from body+0xA9
    # we only have 126 bytes before the first FF.

    # Unless the terminator is [00 00 00 04 00 00] + [FF 00] where FF starts the padding.
    # The entry is only 6 bytes, not 8, and then padding follows immediately.

    # Actually, I think the RIGHT way to read this is:
    # 118 from body+0xA9: entries of 8 bytes, terminated by FF in byte 6:
    # Entry 0-14: [00 00 00 04 00 00 0A 02] (15 identical)
    # Entry 15: [00 00 00 04 00 00 FF 00] (terminator - FF in comp position)
    # After 16*8=128 bytes, we're at body+0x129, but earlier analysis showed the
    # non-FF boundary at body+0x127. The FF at position 126 (within entry 15)
    # is actually part of the entry, not the start of padding.
    # The TRUE padding starts at body+0x129 (after 128 bytes from body+0xA9).

    # Let me verify:
    print(f"\n118 body[0x128]: 0x{body_118[0x128]:02X}")  # byte 127 from entries = entry 15 byte 7
    print(f"118 body[0x129]: 0x{body_118[0x129]:02X}")  # should be start of padding

    # If body[0x129] = 0x00 or 0xFF, it's padding.
    # But there might be `00 00 FF 00 00 FF ...` which starts with 00s.

    # Actually, from the v5 output:
    # 118 between end-of-entries and header: body[0x127:0x13C] = 21 bytes
    # FF 00 00 FF 00 00 ...
    # So body[0x127] = 0xFF, and THAT is the first padding byte.

    # But if entry 15 = body[0xA9+120:0xA9+128] = body[0x121:0x129]:
    # body[0x121:0x129] = 00 00 00 04 00 00 [FF at 0x127] 00
    # The FF is within the entry! Body[0x129] = 0x00.
    # body[0x129:0x131]: let me check
    print(f"118 body[0x129]: 0x{body_118[0x129]:02X}")
    print(f"118 body[0x12A]: 0x{body_118[0x12A]:02X}")
    print(f"118 body[0x12B]: 0x{body_118[0x12B]:02X}")
    print(f"118 body[0x12C]: 0x{body_118[0x12C]:02X}")

    # OK let me just dump the exact bytes around the boundary
    print(f"\n118 body[0x11F:0x135]:")
    for i in range(0x11F, 0x135):
        print(f"  body+0x{i:04X}: 0x{body_118[i]:02X}", end="")
        if i == 0xA9 + 120:
            print("  <-- entry 15 start", end="")
        if i == 0xA9 + 128:
            print("  <-- entry 15 end (if 8 bytes)", end="")
        if body_118[i] == 0xFF:
            print("  <-- FF", end="")
        print()

    # And for 119:
    print(f"\n119 body[0x11F:0x135]:")
    for i in range(0x11F, 0x135):
        print(f"  body+0x{i:04X}: 0x{body_119[i]:02X}", end="")
        if i == 0xA9 + 120:
            print("  <-- entry 15 start", end="")
        if i == 0xA9 + 128:
            print("  <-- entry 15 end (if 8 bytes)", end="")
        if body_119[i] == 0xFF:
            print("  <-- FF", end="")
        print()

if __name__ == "__main__":
    main()
