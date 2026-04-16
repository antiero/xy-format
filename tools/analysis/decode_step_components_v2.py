#!/usr/bin/env python3
"""Final step component decoder for unnamed 118 vs 119.

Key insight from raw data:
- u118 (uniform): E4 02 + 16 x 8-byte records = 130 total, but data=128 (last 2 bytes are FF sentinel start)
  Actually: E4 + (mode byte) + 16 x (record), where each record in mode 02 = 8 bytes
  u118 data size = 128: E4(1) + 02(1) + 15*8(120) + 6(last rec without trailing 0A) = 128. Yes!

- u119 (mixed): E4 01 + different encoding = 130 total
  u119 data size = 130: 2 extra bytes vs u118

Let's figure out the exact record format for each mode.

Mode 0x02 (uniform, u118):
  Record pattern: 02 00 00 00 04 00 00 0A  (8 bytes, 16 times)
  But last record: 02 00 00 00 04 00 00 [FF - start of sentinel]
  So actually: the 0x0A at position 7 is a separator between records, NOT part of the record.
  Record = 7 bytes: [type] [5 zero/param bytes] [sep/term]
  Wait, that doesn't work either because the last one has 0x0A too in the dump.

  Let me recount: E4 02 [6 bytes] 0A [6 bytes] 0A ... [6 bytes] FF
  E4(1) + mode(1) + 16*6 + 15*1(0A seps) = 2 + 96 + 15 = 113? No, data=128.

  128 bytes total = E4(1) + 16*7 + 15*1(0A) = 1 + 112 + 15 = 128. PERFECT!
  So: E4 [7-byte rec₀] 0A [7-byte rec₁] 0A ... 0A [7-byte rec₁₅]
  rec₀ = 02 00 00 00 04 00 00

Mode 0x01 (mixed, u119):
  130 bytes total = E4(1) + 16*n + 15*separators?
  If 8-byte records: E4(1) + 16*8 + 1 = 130. So 8-byte records + E4 + 1 extra?
  Or: E4(1) + mode(1) + body(128)? 128/16 = 8 bytes per record.

  That means:
  - mode 01: E4 + 01 + 16 * 8-byte records = 130 bytes, record = [type][value][00][00][param1][param2][00][00]
  - mode 02: E4 + 16 * (7-byte record + 0A sep) with last sep omitted... actually let me just verify by counting.
"""

import os, struct

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_118 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 118.xy")
FILE_119 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 119.xy")

TRACK_SIG = b"\x00\x00\x01\x03\xff\x00\xfc\x00"

# Step component type names from OP-XY documentation
COMP_NAMES = {
    0x00: "Note Length",
    0x01: "Velocity",
    0x02: "Probability",
    0x03: "Micro Timing",
    0x04: "Hold",
    0x05: "Ratchet",
    0x06: "Chance",
    0x07: "Swing",
    0x08: "Flam",
    0x09: "Pitch",
    0x0A: "Slide",
    0x0B: "Reverse",
    0x0C: "Pan",
    0x0D: "Filter",
    0x0E: "Delay Send",
}


def get_t1_body(path: str) -> bytes:
    with open(path, "rb") as f:
        data = f.read()
    sig = data.find(TRACK_SIG)
    next_sig = data.find(TRACK_SIG, sig + len(TRACK_SIG))
    body_end = next_sig - 4 if next_sig != -1 else len(data)
    return data[sig:body_end]


def main():
    body118 = get_t1_body(FILE_118)
    body119 = get_t1_body(FILE_119)

    e4_118 = body118.find(b"\xE4", 0x80)
    e4_119 = body119.find(b"\xE4", 0x80)

    # Find end of component data (first FF 00 00 after)
    def find_sentinel_run(body, start):
        i = start + 100  # minimum
        while i + 2 < len(body):
            if body[i] == 0xFF and body[i+1] == 0x00 and body[i+2] == 0x00:
                return i
            i += 1
        return None

    end_118 = find_sentinel_run(body118, e4_118)
    end_119 = find_sentinel_run(body119, e4_119)

    size_118 = end_118 - e4_118
    size_119 = end_119 - e4_119

    print("=" * 80)
    print("STEP COMPONENT DATA: STRUCTURAL ANALYSIS")
    print("=" * 80)
    print(f"u118 (uniform Hold): E4 at 0x{e4_118:04X}, ends at 0x{end_118:04X}, size = {size_118} bytes")
    print(f"u119 (mixed types):  E4 at 0x{e4_119:04X}, ends at 0x{end_119:04X}, size = {size_119} bytes")
    print(f"Size delta: {size_119 - size_118} bytes")

    # ===== MODE 0x02 (uniform, u118) =====
    print(f"\n{'='*80}")
    print("MODE 0x02: UNIFORM (unnamed 118 - Hold on all 16 steps)")
    print("=" * 80)

    mode_118 = body118[e4_118 + 1]
    print(f"Mode byte: 0x{mode_118:02X}")

    # Layout hypothesis: E4 + 16 * (7-byte record + 1-byte sep) = 1 + 128 = 129?
    # No, data = 128, so: E4(1) + first_rec(7) + 15*(1sep + 7rec) = 1 + 7 + 15*8 = 128. YES!
    # The mode byte IS the first byte of rec0!

    # Alternative: mode byte(1) is separate, then 15 recs of 8 bytes + 1 rec of 7
    # 1 + 1 + 15*8 + 7 = 129? No.

    # Let me just try: skip E4, then 16 records of 8 bytes each:
    # That's 1 + 128 = 129 bytes, but data = 128. Off by 1.

    # Try: E4(1) + mode(1) + 16*7 + 15*1(sep) + 1*0(no trailing sep) = 1+1+112+15 = 129. Nope.

    # Actual raw: E4 02 00 00 00 04 00 00 0A 02 00 00 00 04 00 00 0A ...
    # If I strip E4 and treat the rest as a flat stream:
    # 02 00 00 00 04 00 00 | 0A | 02 00 00 00 04 00 00 | 0A | ...
    # That's 7-byte record + 1-byte separator = 8 per step
    # 128 - 1(E4) = 127. 127 / 8 = 15.875. Doesn't divide evenly.

    # 128 - 1(E4) = 127. If last record has no separator: 15*8 + 7 = 127. YES!
    # So: E4 + rec0(7) sep(1) rec1(7) sep(1) ... rec14(7) sep(1) rec15(7)
    # =  E4 + 15*(7+1) + 7 = 1 + 120 + 7 = 128. PERFECT!

    print(f"\nFormat: E4 + 16 x 7-byte records with 0x0A separator (no trailing sep)")
    print(f"Record = [type(1)] [value(1)] [00] [00] [00] [param(1)] [00]")
    print(f"Total: 1 + 15*(7+1) + 7 = 128 bytes")

    pos = e4_118 + 1  # skip E4
    print(f"\n  Step  Type  Value  Param  Raw")
    for step in range(16):
        rec = body118[pos:pos+7]
        comp_type = rec[0]
        comp_name = COMP_NAMES.get(comp_type, f"?({comp_type})")
        hex_str = " ".join(f"{b:02X}" for b in rec)
        print(f"  {step:4d}  0x{comp_type:02X} ({comp_name:>12s})  val={rec[1]:3d}  "
              f"b2={rec[2]:02X} b3={rec[3]:02X} b4={rec[4]:02X} p={rec[5]:3d} b6={rec[6]:02X}  [{hex_str}]")
        pos += 7
        # Check separator
        if step < 15:
            sep = body118[pos]
            if sep != 0x0A:
                print(f"         *** Expected separator 0x0A, got 0x{sep:02X} at 0x{pos:04X}")
            pos += 1

    # Verify we ended at the sentinel
    print(f"\n  After records: pos=0x{pos:04X}, byte=0x{body118[pos]:02X} (expect 0xFF)")

    # ===== MODE 0x01 (mixed, u119) =====
    print(f"\n{'='*80}")
    print("MODE 0x01: MIXED (unnamed 119 - 14 different types + 2 repeats)")
    print("=" * 80)

    mode_119 = body119[e4_119 + 1]
    print(f"Mode byte: 0x{mode_119:02X}")

    # 130 bytes total. 130 - 1(E4) = 129.
    # If same 7+1 format: 15*8 + 7 = 127 + E4 = 128. But we have 130.
    # So mode 01 has a DIFFERENT record size.

    # 130 - 1(E4) - 1(mode) = 128. 128/16 = 8 bytes per record.
    # Let me try: E4 + mode(1) + 16 * 8-byte records = 1+1+128 = 130. PERFECT!

    # So in mode 01, the mode byte is separate, and each record is 8 bytes (no separator).
    # In mode 02, the mode byte IS rec[0] (always 0x02=Hold), and records are 7+1sep.
    # Wait, that's confusing. Let me re-think.

    # Actually maybe mode 02 works like this too:
    # E4 + mode(1) + 16 * 7-byte records + 15 * 1-byte separators
    # = 1 + 1 + 112 + 15 = 129? No, data = 128.

    # OR: In mode 02, the "mode byte 02" IS the type field of the first record:
    # E4 [type0=02] [6 bytes] 0A [type1=02] [6 bytes] 0A ...
    # That's: 1(E4) + 16*(1type + 6params) + 15(seps) = 1 + 112 + 15 = 128. YES!

    # In mode 01:
    # E4 01 [type0] [param 6 bytes] [type1] [param 6 bytes] ...
    # 1(E4) + 1(mode) + 16*(1type + 6params) + 15(seps) = 1+1+112+15 = 129? No, data=130.

    # OR mode 01: extra byte per record?
    # E4 01 + 16 * 8-byte records = 1+1+128 = 130. YES!
    # But then what happened to the separators?

    # Let me check if there ARE 0x0A separators in the u119 data:
    data_119 = body119[e4_119:end_119]
    print(f"\nSearching for 0x0A bytes in u119 component data:")
    for i, b in enumerate(data_119):
        if b == 0x0A:
            print(f"  0x0A at offset +{i} (abs 0x{e4_119+i:04X}), context: "
                  f"{' '.join(f'{data_119[max(0,i-2)+j]:02X}' for j in range(min(5, len(data_119)-max(0,i-2))))}")

    # OK let me try something completely different.
    # Looking at u119 raw: E4 01 00 04 00 00 0B 02 00 00 00 04 00 00 0A ...
    # If 8-byte records after E4 01:
    #   rec0: 00 04 00 00 0B 02 00 00
    #   rec1: 00 04 00 00 0A 04 00 00
    # rec1 has 0A as byte 4 — that might be component type 0x0A = Slide

    # Let me try treating mode 01 as: E4(1) + mode(1) + 16 * 8-byte records = 130
    # Each 8-byte record: [?] [val] [00] [00] [type] [param1_lo] [param1_hi] [00]
    # OR: [?] [val] [00] [00] [type] [param] [00] [00]

    print(f"\nFormat hypothesis: E4 + mode(1) + 16 x 8-byte records = 130 bytes")
    pos = e4_119 + 2  # skip E4 + mode
    print(f"\n  Step  Raw bytes                     Interpretations")
    for step in range(16):
        rec = body119[pos:pos+8]
        hex_str = " ".join(f"{b:02X}" for b in rec)

        # Try multiple field layouts
        # Layout A: [00] [val] [00] [00] [type] [paramLo] [paramHi] [00]
        type_a = rec[4]
        # Layout B: [type_lo] [type_hi] [00] [00] [val] [param_bits] [00] [00]
        # Layout C: [?] [?] [00] [00] [type] [?] [?] [00]

        # Looking at u118: rec = 02 00 00 00 04 00 00 (Hold=0x04 would be at position 4 OR...)
        # u118 all recs: [02] 00 00 [00] 04 00 00
        # If type = rec[0]: 0x02 = Probability? But we KNOW it's Hold!
        # If type = rec[4]: 0x04 = Hold!
        # So type is at rec[4].

        # For u119 rec0: 00 04 00 00 0B 02 00 00 → type=0x0B=Reverse
        # rec1: 00 04 00 00 0A 04 00 00 → type=0x0A=Slide
        # rec2: 01 02 00 00 09 08 00 00 → type=0x09=Pitch
        # That seems to count DOWN from 0x0B!

        type_at_4 = rec[4]
        name_4 = COMP_NAMES.get(type_at_4, f"?({type_at_4})")

        # Also try type at rec[0]
        type_at_0 = rec[0]
        name_0 = COMP_NAMES.get(type_at_0, f"?({type_at_0})")

        print(f"  {step:4d}  [{hex_str}]  "
              f"type@4=0x{type_at_4:02X}({name_4:>12s})  "
              f"type@0=0x{type_at_0:02X}({name_0:>12s})")
        pos += 8

    # Verify end
    print(f"\n  After records: pos=0x{pos:04X}, byte=0x{body119[pos]:02X} (expect 0xFF)")

    # ===== Now let me look at u118 with the SAME "type at position 4" theory =====
    print(f"\n{'='*80}")
    print("RE-ANALYSIS: type field at position 4 in 7-byte records")
    print("=" * 80)

    # u118 mode 02: record = 7 bytes, type at [4]?
    # rec: 02 00 00 00 04 00 00 → type@4 = 0x04 = Hold.
    # rec[0]=0x02 could be "value" or "parameter"

    # u119 mode 01: record = 8 bytes, type at [4]?
    # rec0: 00 04 00 00 0B 02 00 00 → type@4 = 0x0B = Reverse
    # The extra byte compared to mode 02: maybe an additional param byte?

    # Let me try a DIFFERENT grouping for u119.
    # What if mode 01 records are also 7 bytes + 1-byte separator, but there's 1 extra mode byte?
    # E4 01 + rec0(7) sep(1) rec1(7) sep(1) ... rec15(7) = 2 + 15*8 + 7 = 129? But data=130.
    # That's off by 1. What if there's a trailing separator too?
    # E4 01 + 16*(7+1) = 2 + 128 = 130.
    # But mode 02: E4 + 16*7 + 15*1 = 1 + 112 + 15 = 128.
    # And: E4 + 16*(7+1) - 1(no trailing 0A because FF follows) = 1 + 127 = 128.

    # So maybe BOTH modes use the same 7-byte record + separator,
    # but mode 01 has the extra mode byte AND a trailing separator (8*16 + 2 = 130).
    # While mode 02 embeds the type-byte into the record and has no trailing sep (7*16 + 15 + 1 = 128).

    # Actually wait. In mode 02 (uniform), the first byte after E4 is 0x02.
    # If 0x02 IS the "uniform type" (i.e., "all steps are Probability" -- but we know it's Hold)...
    # Hmm, 0x02 != Hold(0x04).

    # Let me reconsider: maybe mode 02 means each record is ONLY the value/param,
    # with NO per-step type byte, because they're all the same type.
    # And mode 01 means each record includes a per-step type byte.

    # Mode 02: E4 [uniform_type=0x02?] + 16*7 + 15*1(sep) = 128.
    # But 0x02 = Probability, not Hold...
    # Unless the numbering is different from what I assumed.

    # Let me check what component type "Hold" actually is by looking at the mapping:
    print(f"\nComponent type mapping check:")
    print(f"  If 0x02 = Hold, then u118 (Hold everywhere) uses: E4 [type=02] ...")
    print(f"  In u119, type@[4] values would be: ", end="")
    pos = e4_119 + 2
    types = []
    for step in range(16):
        rec = body119[pos:pos+8]
        types.append(rec[4])
        pos += 8
    print(" ".join(f"{t:02X}" for t in types))
    print(f"  Names: {[COMP_NAMES.get(t, '?') for t in types]}")

    # What if the component type numbering is:
    # 0x00=NoteLength, 0x01=Velocity, 0x02=Hold, 0x03=Probability, ...
    # Let me try: u119 step types (we know it has 14 different + 2 repeats)
    # Counting unique types:
    unique = sorted(set(types))
    print(f"  Unique types in u119: {[f'0x{t:02X}' for t in unique]} ({len(unique)} unique)")

    # Also look at byte [0] of each record in u119
    pos = e4_119 + 2
    byte0s = []
    for step in range(16):
        rec = body119[pos:pos+8]
        byte0s.append(rec[0])
        pos += 8
    print(f"  Byte[0] of each record: {[f'0x{b:02X}' for b in byte0s]}")
    unique_b0 = sorted(set(byte0s))
    print(f"  Unique byte[0]: {[f'0x{b:02X}' for b in unique_b0]} ({len(unique_b0)} unique)")

    # ===== Let's try 7-byte records with separator for BOTH modes =====
    print(f"\n{'='*80}")
    print("HYPOTHESIS: 7-byte records + separators for u119 too")
    print("=" * 80)

    # Mode 01: E4 01 + rec0(7) [sep] rec1(7) [sep] ...
    # 130 - 2 = 128. 128/8 = 16 exactly. So 16 * (7rec + 1sep) = 128.
    # But the last record would have a separator too (unlike mode 02).
    # Actually: 16 * 8 = 128. + 2 = 130. WORKS!

    pos = e4_119 + 2  # skip E4 + mode
    print(f"\n  Step  Record (7 bytes)                         Sep   Type@0  Type@4  Interpretation")
    for step in range(16):
        rec = body119[pos:pos+7]
        hex_str = " ".join(f"{b:02X}" for b in rec)
        sep = body119[pos+7] if pos+7 < len(body119) else None

        type_0 = rec[0]
        type_4 = rec[4]
        name_0 = COMP_NAMES.get(type_0, f"?{type_0}")
        name_4 = COMP_NAMES.get(type_4, f"?{type_4}")

        sep_str = f"0x{sep:02X}" if sep is not None else "N/A"

        print(f"  {step:4d}  [{hex_str}]  {sep_str}  "
              f"@0=0x{type_0:02X}({name_0:>12s})  @4=0x{type_4:02X}({name_4:>12s})")
        pos += 8  # 7 rec + 1 sep

    # ===== Let me try a completely different grouping for u119 =====
    # What if mode 01 means the records have an EXTRA type byte at the front?
    # Mode 01: E4 01 + 16 * (1type + 7value) = 2 + 128 = 130
    # Mode 02: E4 + (16 * 7value) + 15seps = 1 + 112 + 15 = 128

    print(f"\n{'='*80}")
    print("HYPOTHESIS: Mode 01 = per-step type(1) + 7-byte value (no separator)")
    print("            Mode 02 = global type in E4+1 + 7-byte values + 0A separators")
    print("=" * 80)

    # u119: E4 01 + 16 * (1+7) = 2+128 = 130
    pos = e4_119 + 2  # skip E4 + mode
    print(f"\n  u119 records (1-byte type + 7-byte payload):")
    for step in range(16):
        comp_type = body119[pos]
        payload = body119[pos+1:pos+8]
        hex_type = f"0x{comp_type:02X}"
        hex_payload = " ".join(f"{b:02X}" for b in payload)
        name = COMP_NAMES.get(comp_type, f"?({comp_type})")

        # Parse payload fields
        # In u118 uniform mode, the 7-byte record was: [type] [00] [00] [00] [04] [00] [00]
        # where type=02=Hold and byte[4]=0x04 is some param.
        # If we strip the type from the front: payload = [00] [00] [00] [04] [00] [00]
        # Wait, that's only 6 bytes. The 7-byte record in u118 is [02 00 00 00 04 00 00].
        # If type is split off: type=02, payload=[00 00 00 04 00 00] = 6 bytes.
        # But mode 01 has 7-byte payloads. Hmm.

        print(f"  {step:4d}  type={hex_type}({name:>12s})  payload=[{hex_payload}]")
        pos += 8

    # u118: E4 [type=02] + 16 * (6-byte payload + 0A sep) with last sep before FF
    # 1 + 1 + 16*6 + 15 = 1+1+96+15 = 113. But data=128. Nope.

    # Back to first working theory: E4 + 16*7rec + 15*0Asep = 128
    # In u118: rec = [02 00 00 00 04 00 00] = type(02) + 6 value bytes
    # In this theory, 0x02 IS the component type, the mode byte is just rec[0] of the first record.

    # So mode 02 means the first byte after E4 happens to be 0x02 (= component type of step 0).
    # And since all steps are the same type, they're all 0x02.

    # For u119 mode 01: the first byte after E4 is 0x01.
    # If 0x01 = Velocity (step 0's type), then mode byte isn't really a "mode" — it's step 0's type!
    # But then u119 is 130 bytes = E4 + 16*7rec + 15*0Asep + ???
    # 1 + 112 + 15 = 128 ≠ 130. Off by 2.

    # UNLESS u119 has 2 extra separator bytes somewhere.
    # OR the records in mode 01 are 8 bytes instead of 7.

    # Looking at u119 data after E4:
    # 01 00 04 00 00 0B 02 00  00 00 04 00 00 0A 04 00
    # If records alternate between 7-byte and 8-byte... no, that's weird.

    # Actually, let me try: what if the record size depends on the type?
    # Maybe some types have an extra parameter byte.

    # Let me look at this from the KNOWN CONTENT perspective.
    # u119 has specific component types on each step. What are they?
    # From the OP-XY UI, 14 different component types on 16 steps means most types once, 2 repeated.
    # The official 14 types: Note Length, Velocity, Probability, Micro Timing, Hold, Ratchet,
    # Chance, Swing, Flam, Pitch, Slide, Reverse, Pan, Filter (no Delay Send on drums?)

    # Let me dump just the raw bytes and look for patterns manually
    print(f"\n{'='*80}")
    print("RAW BYTES — looking for patterns")
    print("=" * 80)

    print(f"\nu118 data (128 bytes, all Hold):")
    d118 = body118[e4_118:end_118]
    for i in range(0, len(d118), 8):
        chunk = d118[i:i+8]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        # mark every 7th byte boundary
        print(f"  +{i:03d}  {hex_str}")

    print(f"\nu119 data (130 bytes, mixed):")
    d119 = body119[e4_119:end_119]
    for i in range(0, len(d119), 8):
        chunk = d119[i:i+8]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        print(f"  +{i:03d}  {hex_str}")

    # Let me try yet another approach: what if mode byte controls per-step struct:
    # Mode 02 = each step: [2-byte type_and_value] + [5-byte params]
    # Mode 01 = each step: [2-byte type_and_value] + [2-byte extra] + [4-byte params]

    # Actually let me re-examine u119 with a hypothesis that 0x0A bytes in u119 ARE separators
    # like in u118, and the "extra" data is the type field.

    # u119: E4 01 | 00 04 00 00 0B | 02 00 | 00 00 04 00 00 0A | 04 00 ...
    # Nah, that's messy.

    # Let me try: after E4, the first byte is mode.
    # Mode 0x02: uniform. Followed by 16 × 7-byte records separated by 0x0A.
    #   1(E4) + 1(mode=02) + 7(rec0) + 15*(1sep + 7rec) = 2 + 7 + 120 = 129. But data=128!
    #   So maybe: 1(E4) + 7(mode+rec0_6bytes) + 15*(1sep + 7bytes) = 1 + 7 + 120 = 128.
    #   Meaning mode byte counts as rec0[0].

    # Mode 0x01: mixed. Each record needs a type byte.
    # 1(E4) + 1(mode=01) + 16*(1type + 6params) + 15*1(sep) = 2 + 112 + 15 = 129. Nope, 130.
    # 1(E4) + 1(mode=01) + 16*(1type + 7params) = 2 + 128 = 130! YES! No separators!
    # So mode 01 has 8-byte records (type + 7 params, NO separators).
    # Mode 02 has 7-byte records (type merged into first byte + 6 params, WITH 0A separators).

    # Wait, that's the model where mode=01 means "per-step type, no sep" and
    # mode=02 means "uniform type, has sep." Let me verify:

    print(f"\n{'='*80}")
    print("FINAL HYPOTHESIS TEST")
    print("  Mode 0x02: E4 + (type+6params)*16 + 0A*15 seps = 128 bytes (type = rec[0])")
    print("  Mode 0x01: E4 + mode(1) + (type(1)+7params)*16 = 130 bytes (no seps)")
    print("=" * 80)

    # u118 mode 02: rec = 7 bytes starting with type
    print(f"\nu118 (mode 02) — 7-byte records with 0x0A separators:")
    pos = e4_118 + 1  # skip E4
    for step in range(16):
        rec = body118[pos:pos+7]
        comp_type = rec[0]
        name = COMP_NAMES.get(comp_type, f"?({comp_type})")
        hex_str = " ".join(f"{b:02X}" for b in rec)
        print(f"  Step {step:2d}: [{hex_str}]  type=0x{comp_type:02X} ({name})")
        pos += 7
        if step < 15:
            sep = body118[pos]
            assert sep == 0x0A, f"Expected 0x0A sep at 0x{pos:04X}, got 0x{sep:02X}"
            pos += 1

    next_byte = body118[pos]
    print(f"  After records: 0x{next_byte:02X} at 0x{pos:04X} (expect 0xFF)")
    assert next_byte == 0xFF

    # u119 mode 01: rec = 8 bytes (type + 7 params), no separators
    print(f"\nu119 (mode 01) — 8-byte records, no separators:")
    pos = e4_119 + 2  # skip E4 + mode(01)
    step_types = []
    for step in range(16):
        rec = body119[pos:pos+8]
        comp_type = rec[0]
        step_types.append(comp_type)
        name = COMP_NAMES.get(comp_type, f"?({comp_type})")
        hex_str = " ".join(f"{b:02X}" for b in rec)

        # Compare payload bytes [1:7] with u118's rec[1:7] for the same step
        print(f"  Step {step:2d}: [{hex_str}]  type=0x{comp_type:02X} ({name})")
        pos += 8

    next_byte = body119[pos]
    print(f"  After records: 0x{next_byte:02X} at 0x{pos:04X} (expect 0xFF)")
    assert next_byte == 0xFF

    print(f"\nAll u119 step types: {[f'0x{t:02X}' for t in step_types]}")
    unique_types = sorted(set(step_types))
    print(f"Unique types: {[f'0x{t:02X}' for t in unique_types]} ({len(unique_types)} unique)")
    print(f"Type names: {[COMP_NAMES.get(t, '?') for t in step_types]}")

    # ===== Post-component region comparison =====
    print(f"\n{'='*80}")
    print("POST-COMPONENT REGION (after FF 00 00 sentinels)")
    print("=" * 80)

    for label, body, end_off in [("u118", body118, end_118), ("u119", body119, end_119)]:
        # Count sentinel run
        j = end_off
        while j + 2 < len(body) and body[j] == 0xFF and body[j+1] == 0x00 and body[j+2] == 0x00:
            j += 3
        sentinel_count = (j - end_off) // 3
        print(f"\n  {label}: {sentinel_count} FF 00 00 sentinels from 0x{end_off:04X} to 0x{j:04X}")

        # Alloc byte and what follows
        print(f"  Byte at 0x{j:04X}: 0x{body[j]:02X}")
        context = body[j:j+24]
        hex_str = " ".join(f"{b:02X}" for b in context)
        print(f"  Context: {hex_str}")


if __name__ == "__main__":
    main()
