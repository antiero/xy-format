#!/usr/bin/env python3
"""Final step component analysis — focus on the u119 structure.

CONFIRMED so far:
- E4 marker at body offset 0x00B1 in Track 1
- Mode 0x02 (uniform): E4 + 16 * 7-byte records + 15 * 0x0A separators = 128 bytes
  Record: [type(1)] [val(1)] [00] [00] [param(1)] [00] [00]
  All 16 identical for u118 (Hold): [02 00 00 00 04 00 00]
- Mode 0x01 (mixed): E4 + mode(1) + 128 bytes payload = 130 total

Now let me crack the u119 payload by examining the data as 4-byte entries
paired into steps, and understanding why the pairing breaks after step 9.

The key observation: B_val for clean entries is powers of 2 cycling.
Steps 0-9 clean (20 entries). After that, bytes misalign on 4-byte boundaries.
BUT the raw data shows 00-00 pairs at regular intervals even in the "broken" region,
just not aligned to 4-byte record boundaries.

What if some entries are 4 bytes and others are LONGER? Specifically, what if
certain component types require extra parameter bytes?
"""

import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(BASE, "src/one-off-changes-from-default")
TRACK_SIG = b"\x00\x00\x01\x03\xff\x00\xfc\x00"

COMP = {
    0x00: "NotLen", 0x01: "Vel", 0x02: "Hold", 0x03: "Prob",
    0x04: "uTime", 0x05: "Ratch", 0x06: "Chnce", 0x07: "Swing",
    0x08: "Flam", 0x09: "Pitch", 0x0A: "Slide", 0x0B: "Rev",
    0x0C: "Pan", 0x0D: "Filtr", 0x0E: "Delay",
}


def get_t1_body(path: str) -> bytes:
    with open(path, "rb") as f:
        data = f.read()
    sig = data.find(TRACK_SIG)
    next_sig = data.find(TRACK_SIG, sig + len(TRACK_SIG))
    body_end = next_sig - 4 if next_sig != -1 else len(data)
    return data[sig:body_end]


def main():
    body119 = get_t1_body(os.path.join(CORPUS, "unnamed 119.xy"))
    e4 = body119.find(b"\xE4", 0x80)

    # Find end (FF 00 00 sentinel)
    i = e4 + 10
    while i + 2 < len(body119):
        if body119[i] == 0xFF and body119[i+1] == 0x00 and body119[i+2] == 0x00:
            break
        i += 1
    end = i

    data = body119[e4:end]  # 130 bytes: E4 01 + 128 payload
    payload = data[2:]  # 128 bytes after E4 + mode

    print("=" * 80)
    print("u119 PAYLOAD ANALYSIS: 128 bytes after E4 01")
    print("=" * 80)

    # Print with both 4-byte and 2-byte grouping
    print(f"\n  2-byte pair view:")
    for i in range(0, len(payload), 2):
        pair = payload[i:i+2]
        is_zero = pair == b"\x00\x00"
        mark = " <<<" if is_zero else ""
        print(f"    +{i:3d}: {pair[0]:02X} {pair[1]:02X}{mark}")

    # Count the "00 00" pairs
    zero_pairs = []
    for i in range(0, len(payload), 2):
        if payload[i:i+2] == b"\x00\x00":
            zero_pairs.append(i)
    print(f"\n  Zero pairs at offsets: {zero_pairs}")
    print(f"  Count: {len(zero_pairs)}")

    # The intervals between zero pairs:
    intervals = [zero_pairs[i+1] - zero_pairs[i] for i in range(len(zero_pairs)-1)]
    print(f"  Intervals: {intervals}")

    # Pattern: many intervals of 4 (= one 2-byte data pair between each zero pair)
    # This means the data is structured as: [2-byte data] [00 00] [2-byte data] [00 00] ...
    # = 4-byte entries: [data(2)] [zero(2)]

    # But wait — the payload starts at offset 0 which is NOT a zero pair.
    # The zero pairs start at offset 2, 6, 10, 14, ... (every 4 bytes starting from 2)
    # For the clean section: data[0:2] is "00 04", data[2:4] is "00 00",
    # data[4:6] is "0B 02", data[6:8] is "00 00", etc.

    # So the ACTUAL record is: [type(1)] [val(1)] [00(1)] [00(1)] = 4 bytes
    # With 32 records = 128 bytes.

    # The "break" happens at entry 20 where bytes 2-3 are no longer 00 00.
    # Let me look at it differently: maybe the 00 00 bytes are NOT padding but
    # are part of a VARIABLE-WIDTH value field.

    # In the clean section, type values range 0x00-0x0B and val values are small.
    # The "00 00" might be the high bytes of a u32 value: val_u32 = val | (b2<<8) | (b3<<16)

    # Let me reparse with this interpretation:
    print(f"\n  4-byte entries with u32 LE interpretation:")
    for i in range(32):
        entry = payload[i*4:(i+1)*4]
        comp_type = entry[0]
        val_u24 = entry[1] | (entry[2] << 8) | (entry[3] << 16)
        name = COMP.get(comp_type, f"?({comp_type})")
        hex_str = " ".join(f"{b:02X}" for b in entry)
        print(f"    {i:3d}: [{hex_str}]  type=0x{comp_type:02X}({name:>6s})  val_u24={val_u24:6d}")

    # Hmm, but the broken entries have type 0x10 (entry 24) which is not a valid component.
    # And many entries have type 0x00 which seems too common.

    # ===== COMPLETELY NEW APPROACH: treat the payload as a FLAT STREAM =====
    # What if the structure is NOT 4-byte records but rather:
    # [16-byte step-type-list] + [per-type parameter blocks]

    print(f"\n{'='*80}")
    print("FLAT STREAM: 16-byte type list + parameter blocks")
    print("=" * 80)

    # Check if first 16 bytes could be type IDs for each step:
    type_list = list(payload[:16])
    print(f"  First 16 bytes: {[f'0x{b:02X}' for b in type_list]}")
    print(f"  As types: {[COMP.get(b, '?') for b in type_list]}")
    # 00 04 00 00 0B 02 00 00 00 04 00 00 0A 04 00 00
    # Doesn't look like a pure type list (04 is a type, but 0B follows 00 00...)

    # ===== Maybe the data is organized by COMPONENT TYPE, not by step =====
    # i.e., "all steps with type X have these values"

    # ===== Let me try parsing as: [type] [step_bitmask_u16_LE] [value] =====
    # 4 bytes: [type(1)] [bitmask_lo(1)] [bitmask_hi(1)] [value(1)]
    # That's still 4 bytes but the fields are ordered differently.

    print(f"\n  Alt interpretation: [type(1)] [mask_lo(1)] [mask_hi(1)] [val(1)]:")
    for i in range(32):
        entry = payload[i*4:(i+1)*4]
        comp_type = entry[0]
        mask = entry[1] | (entry[2] << 8)
        val = entry[3]
        name = COMP.get(comp_type, f"?({comp_type})")
        steps = [s for s in range(16) if mask & (1 << s)]
        hex_str = " ".join(f"{b:02X}" for b in entry)
        print(f"    {i:3d}: [{hex_str}]  type=0x{comp_type:02X}({name:>6s})  mask=0x{mask:04X}  val={val:3d}  steps={steps}")

    # ===== Let me go back to the 4-byte [type val 00 00] interpretation =====
    # and try to understand the BROKEN region differently.
    # What if after the first 20 clean entries, there's a DIFFERENT data section?

    print(f"\n{'='*80}")
    print("SPLIT ANALYSIS: entries 0-19 (clean) vs bytes 80-127 (broken)")
    print("=" * 80)

    clean_region = payload[:80]  # 20 clean entries
    broken_region = payload[80:]  # 48 remaining bytes

    print(f"\n  Clean region (80 bytes = 20 entries):")
    for i in range(20):
        entry = clean_region[i*4:(i+1)*4]
        comp_type = entry[0]
        val = entry[1]
        name = COMP.get(comp_type, f"?({comp_type})")
        print(f"    {i:3d}: [{' '.join(f'{b:02X}' for b in entry)}]  "
              f"type=0x{comp_type:02X}({name:>6s}) val={val:3d}")

    print(f"\n  Broken region (48 bytes):")
    hex_str = " ".join(f"{b:02X}" for b in broken_region)
    print(f"    {hex_str}")

    # What if the broken region uses DIFFERENT entry sizes?
    # For example, entries with higher values need more bytes?
    # Let me try parsing the broken region as variable-size entries
    # where each entry starts with [type(1)] and continues until [00(1)] padding:

    print(f"\n  Broken region parsed as variable-length entries (stop at 00 00):")
    pos = 0
    entry_num = 0
    while pos < len(broken_region):
        # Try to find the next 00 00 boundary
        # Each entry: [type] [val] then continues until 00 00
        start = pos
        # Read until we see 00 00
        while pos + 1 < len(broken_region):
            if broken_region[pos] == 0x00 and broken_region[pos+1] == 0x00:
                pos += 2  # include the 00 00
                break
            pos += 1
        else:
            pos = len(broken_region)

        entry = broken_region[start:pos]
        hex_str = " ".join(f"{b:02X}" for b in entry)
        comp_type = entry[0] if len(entry) > 0 else -1
        name = COMP.get(comp_type, f"?({comp_type})")
        print(f"    {entry_num:3d} @+{80+start:3d} ({len(entry):2d} bytes): [{hex_str}]  "
              f"type=0x{comp_type:02X}({name})")
        entry_num += 1

    # ===== PAIRS REINTERPRETATION =====
    # The clean entries form PAIRS: (slot_A, slot_B) for each step.
    # 20 entries = 10 pairs = steps 0-9.
    # Steps 10-15 would need 12 more entries (6 steps * 2 slots).
    # 48 bytes / 4 = 12 entries. The math works!
    # But the 4-byte alignment is broken. Why?

    # UNLESS some steps have MORE than 2 component slots.
    # Or some entries have 3 bytes instead of 4 (compact encoding for certain types).

    # Let me try: the broken region has entries of VARYING sizes, totaling 48 bytes
    # for 6 steps with 2 slots each. If entries are sometimes 3 bytes:
    # 12 entries: some 4-byte, some larger?

    # Let me look at the 00 00 pairs in the broken region:
    print(f"\n  00 00 pairs in broken region:")
    for i in range(0, len(broken_region)-1):
        if broken_region[i] == 0x00 and broken_region[i+1] == 0x00:
            print(f"    at offset +{80+i} (local +{i})")

    # Local offsets with 00 00: let me count
    local_zeros = []
    for i in range(0, len(broken_region)-1):
        if broken_region[i] == 0x00 and broken_region[i+1] == 0x00:
            local_zeros.append(i)
    print(f"    Positions: {local_zeros}")
    print(f"    Intervals: {[local_zeros[i+1]-local_zeros[i] for i in range(len(local_zeros)-1)]}")

    # Let me try parsing from the broken region using the 00 00 markers as delimiters
    # Each record is: [data bytes...] [00 00]
    print(f"\n  Records delimited by 00 00:")
    pos = 0
    records = []
    while pos < len(broken_region):
        start = pos
        # Find next 00 00
        found = False
        for j in range(pos, len(broken_region) - 1):
            if broken_region[j] == 0x00 and broken_region[j+1] == 0x00:
                rec = broken_region[start:j+2]
                records.append((80 + start, rec))
                pos = j + 2
                found = True
                break
        if not found:
            # Remaining bytes
            rec = broken_region[start:]
            if len(rec) > 0:
                records.append((80 + start, rec))
            break

    for off, rec in records:
        hex_str = " ".join(f"{b:02X}" for b in rec)
        print(f"    @+{off:3d} ({len(rec):2d} bytes): [{hex_str}]")

    # How many records? Do they match 6 pairs (12 entries)?
    print(f"\n  Total records: {len(records)}")

    # ===== The REAL answer might be simpler =====
    # What if mode 01 uses the SAME 7-byte record as mode 02, but without 0A separators,
    # and instead with 00-byte separators (which look like padding)?

    # Mode 02: 128 = E4(1) + 16*7rec + 15*0A_sep
    # Mode 01: 130 = E4(1) + mode(1) + 16*7rec + 16*1_sep = 2 + 112 + 16 = 130

    # Wait, 16*7 + 16*1 = 128 + 2 = 130. That works!
    # Each step: 7-byte record + 1-byte separator (0x00)

    print(f"\n{'='*80}")
    print("HYPOTHESIS: mode 01 = 7-byte records + 0x00 separator (16 each)")
    print("  Total: E4(1) + mode(1) + 16*(7+1) = 130 bytes")
    print("=" * 80)

    pos = 0
    for step in range(16):
        rec = payload[pos:pos+7]
        sep = payload[pos+7] if pos+7 < len(payload) else None
        hex_str = " ".join(f"{b:02X}" for b in rec)
        sep_str = f"0x{sep:02X}" if sep is not None else "N/A"

        # Same field layout as mode 02: [type(1)] [val(1)] [00] [00] [param(1)] [00] [00]
        comp_type = rec[0]
        val = rec[1]
        param = rec[4]
        name = COMP.get(comp_type, f"?({comp_type})")

        # Check if rec[2:4] and rec[5:7] are zero (as in mode 02)
        z_inner = rec[2] == 0 and rec[3] == 0
        z_tail = rec[5] == 0 and rec[6] == 0

        z_status = ""
        if not z_inner:
            z_status += f" inner={rec[2]:02X}{rec[3]:02X}"
        if not z_tail:
            z_status += f" tail={rec[5]:02X}{rec[6]:02X}"

        print(f"  Step {step:2d}: [{hex_str}] sep={sep_str}  "
              f"type=0x{comp_type:02X}({name:>6s}) val={val:3d} param=0x{param:02X}{z_status}")
        pos += 8

    # This doesn't work because the zero padding breaks.
    # Let me try DIFFERENT field layout for 7-byte records in mode 01.

    # ===== What about this: mode 02 has a specific 7-byte record format, =====
    # ===== and mode 01 has PAIRED 4-byte entries but with a DIFFERENT boundary. =====

    # Actually, let me revisit. The clean entries 0-19 pair up as:
    # Step 0: [00 04 00 00] [0B 02 00 00] → entry A has component types ascending,
    #         entry B has them descending.
    # The A entries for steps 0-9: 00, 00, 01, 02, 03, 04, 05, 06, 06, 07
    # The B entries for steps 0-9: 0B, 0A, 09, 08, 07, 06, 05, 05, 04, 03

    # A counting UP, B counting DOWN. This is a COMPLEMENT pattern!
    # A+B ≈ 0x0B for each step. Let me check:
    print(f"\n{'='*80}")
    print("A+B COMPLEMENT CHECK")
    print("=" * 80)
    for step in range(10):
        a = payload[step*8]
        b = payload[step*8 + 4]
        print(f"  Step {step}: A=0x{a:02X} + B=0x{b:02X} = 0x{a+b:02X} ({a+b})")

    # A+B sums: 0B, 0A, 0A, 0A, 0A, 0A, 0A, 0B, 0C, 0A
    # NOT constant. So it's not a simple complement.

    # But notice the B values form a roughly descending sequence: 0B,0A,09,08,07,06,05,05,04,03
    # And A values roughly ascending: 00,00,01,02,03,04,05,06,06,07
    # This looks like each step gets TWO components:
    # - Component A (the "primary" one set by the user)
    # - Component B (the "secondary" one, perhaps mirrored)

    # With 14 component types total, each step having 2 would explain the interleaving.
    # The user set 14 different types + 2 repeats across 16 steps.
    # These are stored as pairs (2 per step), but what are the pairs?

    # Let me look at the A-B distribution:
    print(f"\n  Step-by-step component pairs (clean entries):")
    all_types_used = set()
    for step in range(10):
        a_type = payload[step*8]
        b_type = payload[step*8 + 4]
        a_name = COMP.get(a_type, "?")
        b_name = COMP.get(b_type, "?")
        all_types_used.add(a_type)
        all_types_used.add(b_type)
        print(f"  Step {step}: {a_name}(0x{a_type:02X}) + {b_name}(0x{b_type:02X})")

    print(f"\n  All types used in steps 0-9: {sorted(all_types_used)}")
    print(f"  That's {len(all_types_used)} unique types")

    # 0-9 use types: {0,1,2,3,4,5,6,7,8,9,10,11} = 12 types
    # Missing: 0x0C (Pan), 0x0D (Filter), 0x0E (Delay)
    # These must appear in steps 10-15 (the "broken" region)

    # ===== Try to decode steps 10-15 from the broken region =====
    # The broken region is 48 bytes at payload[80:128].
    # If each step still uses 8 bytes (4+4 pair), that's 6 steps * 8 = 48. PERFECT!
    # The issue must be that the 4-byte ALIGNMENT is off because the data at that point
    # has non-zero bytes in positions 2-3.

    # What if some entries are 4 bytes + extra?
    # Or what if the "00 00" padding simply isn't there for certain component types?

    # Let me try: steps 10-15 use COMPACT entries without 00 00 padding.
    # Entry = [type(1)] [val(1)] = 2 bytes.
    # 6 steps * 2 entries * 2 bytes = 24 bytes. But we have 48 bytes. Doesn't match.

    # Or: the entries in steps 10-15 use LARGER records because these component types
    # have additional parameters.

    # Let me try parsing the broken region using 00 00 as entry terminators:
    print(f"\n{'='*80}")
    print("BROKEN REGION: parsing with 00 00 as terminators")
    print("=" * 80)

    broken = payload[80:]
    print(f"  Raw: {' '.join(f'{b:02X}' for b in broken)}")

    # Find all 00 00 in the broken region
    zz_positions = []
    for i in range(len(broken) - 1):
        if broken[i] == 0x00 and broken[i+1] == 0x00:
            zz_positions.append(i)
    print(f"  00 00 at local offsets: {zz_positions}")

    # Filter out overlapping positions
    filtered = []
    prev = -2
    for p in zz_positions:
        if p > prev + 1:
            filtered.append(p)
            prev = p
    print(f"  Filtered 00 00 positions: {filtered}")

    # Parse entries between 00 00 markers
    entries = []
    pos = 0
    for zz in filtered:
        data_bytes = broken[pos:zz]
        entries.append((pos, data_bytes, broken[zz:zz+2]))
        pos = zz + 2

    # Remaining
    if pos < len(broken):
        entries.append((pos, broken[pos:], b""))

    print(f"\n  Entries:")
    for i, (off, data_bytes, term) in enumerate(entries):
        hex_data = " ".join(f"{b:02X}" for b in data_bytes)
        hex_term = " ".join(f"{b:02X}" for b in term)
        if len(data_bytes) >= 2:
            comp_type = data_bytes[0]
            name = COMP.get(comp_type, f"?({comp_type})")
        else:
            name = "?"
        print(f"    {i:3d} @+{80+off:3d} ({len(data_bytes):2d}+{len(term)} bytes): "
              f"[{hex_data}] [{hex_term}]  start_type={name}")


if __name__ == "__main__":
    main()
