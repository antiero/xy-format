#!/usr/bin/env python3
"""Step component decoder v4 — per-COMPONENT-TYPE table interpretation.

Key insight: what if the records aren't "16 step records" but rather
"N component-type entries" where each entry says which steps have that type?

For u118 (uniform Hold), all 16 steps have the same type, so 16 identical records.
For u119 (mixed), each entry maps a component type to specific steps.

Also: let me try the interpretation where 0x0A separators exist in BOTH modes,
but mode 01 has variable-length or differently-structured records.
"""

import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_118 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 118.xy")
FILE_119 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 119.xy")

TRACK_SIG = b"\x00\x00\x01\x03\xff\x00\xfc\x00"

COMP = {
    0x00: "Note Length",
    0x01: "Velocity",
    0x02: "Hold",
    0x03: "Probability",
    0x04: "Micro Timing",
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


def find_sentinel_run(body, start):
    i = start + 100
    while i + 2 < len(body):
        if body[i] == 0xFF and body[i+1] == 0x00 and body[i+2] == 0x00:
            return i
        i += 1
    return None


def main():
    body119 = get_t1_body(FILE_119)
    body118 = get_t1_body(FILE_118)

    e4_119 = body119.find(b"\xE4", 0x80)
    end_119 = find_sentinel_run(body119, e4_119)
    e4_118 = body118.find(b"\xE4", 0x80)
    end_118 = find_sentinel_run(body118, e4_118)

    d119 = body119[e4_119:end_119]
    d118 = body118[e4_118:end_118]

    # ===== Let me try variable-length record parsing for u119 =====
    # Perhaps each component type entry has a header + per-step data?
    # Format: [comp_type] [param] [step_bitmask_u16_LE] [per-step-values...]

    # The data stream after E4 01 in u119:
    # 00 04 00 00 0B 02 00 00 00 04 00 00 0A 04 00 00 01 02 00 00 09 08 00 00 ...
    # With pairs: (00,04) (00,00) (0B,02) (00,00) (00,04) (00,00) (0A,04) (00,00) ...

    # What if each entry is: [comp_type(1)] [value(1)] [00] [00] = 4 bytes per step,
    # and there are 32 entries (2 per step, for 2 component slots)?

    print("=" * 80)
    print("HYPOTHESIS: 4-byte records (type + value + 00 + 00)")
    print("=" * 80)

    # u119: 130 bytes - E4(1) - mode(1) = 128 bytes data. 128/4 = 32 entries.
    # 32 = 16 steps * 2 slots per step!

    pos = 2  # skip E4 + mode
    print(f"\nu119 (mode 01, 130 bytes): 32 x 4-byte entries")
    entries = []
    for i in range(32):
        entry = d119[pos:pos+4]
        comp_type = entry[0]
        value = entry[1]
        z1, z2 = entry[2], entry[3]
        entries.append(entry)
        name = COMP.get(comp_type, f"?({comp_type})")
        step = i // 2
        slot = "A" if i % 2 == 0 else "B"
        hex_str = " ".join(f"{b:02X}" for b in entry)
        print(f"  [{hex_str}]  step={step:2d} slot={slot}  type=0x{comp_type:02X}({name:>12s}) val={value:3d} z={z1:02X}{z2:02X}")
        pos += 4

    # Check: do the zero bytes hold?
    print(f"\nChecking zero-byte consistency:")
    non_zero_count = 0
    for i, entry in enumerate(entries):
        if entry[2] != 0 or entry[3] != 0:
            non_zero_count += 1
            print(f"  Entry {i}: z1=0x{entry[2]:02X} z2=0x{entry[3]:02X} (NON-ZERO)")
    if non_zero_count == 0:
        print("  All zero-bytes are 0x00 -- pattern holds!")
    else:
        print(f"  {non_zero_count} entries have non-zero bytes -- pattern BROKEN")

    # ===== Same for u118 =====
    # u118: 128 bytes. 128 - 1(E4) = 127 bytes. Can't divide by 4.
    # 128/4 = 32 entries including E4 byte?
    # Actually in mode 02, no separate mode byte. 128 - 1(E4) = 127. 127/4 = 31.75. Nope.

    # What if mode 02 = 7-byte record = [type(1) + value(1) + 00 + 00 + param(1) + 00 + 00] per step
    # and 0x0A is a separator?
    # 16*7 + 15*1 + 1 = 128. Each 7-byte record = step has 1 type + params.
    # This works for uniform (all same type).

    # But what about the "4-byte per slot, 2 slots per step" idea?
    # u118 has "Hold" on all 16 steps. If each step has 2 slots and both are "Hold"...
    # Mode 02 has 128 bytes. 128 = 1(E4) + 16*(record), so record = (128-1)/16 ≈ 7.94. Not clean.
    # With separators: 128 = 1(E4) + 16*7 + 15*1 = 128. YES.

    # So mode 02 = 7 bytes/step = [type(1)] [val(1)] [00] [00] [type2(1)] [val2(1)] [00]
    # That's TWO 3.5-byte entries... not clean.

    # OR: mode 02 = 7 bytes = [slotA_type(1)] [padding(2)] [00] [slotB_type(1)] [padding(2)]
    # With padding = 0x00 bytes.

    # Let me instead look at what 0x04 means in the u118 records.
    # u118 rec: [02 00 00 00 04 00 00]
    # type_A=0x02=Hold, then 00 00, then 00, then type_B=0x04=Micro Timing, then 00 00.
    # So: [hold(1)][00][00] [00] [micro_timing(1)][00][00]
    # = Slot A: Hold(0x02) with zero param. Slot B: Micro Timing(0x04) with zero param.
    # But we set ALL steps to Hold, not Micro Timing...
    # Unless 0x04 is the "default" secondary slot, or Micro Timing is the second component.

    # Actually on OP-XY, each step CAN have 2 component types simultaneously (primary + secondary).
    # The default secondary might be Micro Timing.

    # FOR u119:
    # If 4-byte records with 32 entries (2 per step):
    # Step 0 slot A: Note Length(00), val=4
    # Step 0 slot B: [00 00] = zeros
    # Step 1 slot A: Reverse(0B), val=2
    # Step 1 slot B: [00 00] = zeros
    # That makes 8 steps for 32 entries... doesn't match 16 steps.

    # Wait, I got confused. Let me re-examine the 32-entry output above.
    # 32 entries grouped as step 0..15, slot A/B:
    # Step 0 slot A: NoteLength(00) val=4
    # Step 0 slot B: NoteLength(00) val=0
    # Step 1 slot A: Reverse(0B) val=2
    # Step 1 slot B: NoteLength(00) val=0
    # Step 2 slot A: NoteLength(00) val=4
    # Step 2 slot B: NoteLength(00) val=0
    # Many entries have non-zero z bytes, so this interpretation is BROKEN.

    # ===== Alternative: Look at it as a bitfield table =====
    # What if the structure after E4 01 is:
    # For each component type (0x00 through 0x0B = 12 types):
    #   [comp_type(1)] [value(1)] [bitmask_u16_LE(2)] [extra(4)]
    # = 8 bytes per type, ~12 types = 96 bytes? Nope, data is 128.

    # Or: [comp_type(1)] [param(1)] [step_bitmask_u16_LE(2)]
    # = 4 per type, 32 types = 128. But there are only 14 component types.

    # ===== Let me try a COMPLETELY DIFFERENT approach =====
    # Read the bytes positionally and look for WHERE the type IDs appear

    print(f"\n{'='*80}")
    print("POSITIONAL ANALYSIS: where do known type IDs (0x00-0x0E) appear?")
    print("=" * 80)

    d = d119[2:]  # skip E4 + mode
    print(f"\nu119 data after E4+mode ({len(d)} bytes):")
    for i, b in enumerate(d):
        if b <= 0x0E:
            name = COMP.get(b, "?")
            # Show context
            ctx_start = max(0, i-2)
            ctx = d[ctx_start:i+3]
            ctx_hex = " ".join(f"{c:02X}" for c in ctx)
            marker = " " * (i - ctx_start) * 3 + "^^"
            print(f"  offset +{i:3d}: 0x{b:02X} ({name:>12s})  ctx=[{ctx_hex}]")

    # ===== Actually, let me look at the SEPARATOR PATTERN for u119 =====
    # In u118, separators are 0x0A between 7-byte records.
    # In u119, if there are NO 0x0A bytes as separators (since 0x0A = Slide type),
    # then records must be fixed-size without separators.
    # But we found 0x0A at offsets +14, +111, +120 in the data.
    # +14 = d119[16] which in the 8-byte interpretation is rec1[6].
    # Let me check if those 0x0A are part of data or separators.

    # If u119 used 0x0A separators too:
    # 130 = 1(E4) + 1(mode) + N*rec + (N-1)*1
    # 128 = N*(rec+1) - 1
    # For N=16: rec = (129/16) = 8.0625. Not integer.

    # ===== Let me try reading this as a FLAT TABLE: 16 entries of varying types =====
    # Actually, let me just check: Are the entries in u119 really per-STEP or per-TYPE?
    # We expect 14 different types + 2 repeats = 16 entries.
    # The A-column (byte[0]) of 8-byte records: 0,0,1,2,3,4,5,6,6,7,7,0,10,0,0,2
    # That's NOT 14 unique values. Only 9 unique.
    # The B-column (byte[4]): 0B,0A,09,08,07,06,05,05,04,03,00,02,02,00,00,00
    # That's 11 unique values.

    # Neither column has 14 unique values. Let me think about what "14 different types + 2 repeats"
    # actually means in the UI. Maybe it means component_type values 0x00 through 0x0D,
    # plus 2 steps that repeat some types.

    # Let me COMBINE the two fields. If each 8-byte record represents a step with:
    # - component_type at byte[0] for slot A
    # - component_type at byte[4] for slot B
    # Then the FULL component assignment table is:
    # Step 0: (0x00, 0x0B) = (NoteLength, Reverse)
    # Step 1: (0x00, 0x0A) = (NoteLength, Slide)
    # ...but that gives 2 components per step, not 1.

    # WAIT. Maybe the OP-XY has 2 component slots per step (like parameter locks in Elektron).
    # unnamed 118 = "Hold" set on SLOT A for all steps (type A=0x02), and SLOT B is default (0x04).
    # unnamed 119 = different types on each step, BUT with the 8-byte record being BROKEN at step 10+.

    # The breakage at step 10+ might mean the 8-byte fixed interpretation is WRONG for mode 01.
    # Let me check if there's a variable-length scheme:

    print(f"\n{'='*80}")
    print("SCANNING: 0x00-byte pairs as possible separators in u119")
    print("=" * 80)

    # In u118: [02 00 00 00 04 00 00] 0A [02 00 00 00 04 00 00] 0A ...
    # In u119: [type_A val_A 00 00 type_B val_B 00 00] [type_A val_A 00 00 type_B val_B 00 00]
    # Could the "00 00" pairs be padding/alignment markers?
    # Let me look at where "00 00" appears:

    d = d119[2:]  # skip E4 + mode
    print(f"\n  Dumping data with '00 00' pairs highlighted:")
    for i in range(0, len(d), 2):
        pair = d[i:i+2]
        if len(pair) < 2:
            break
        flag = " <<< zero pair" if pair == b"\x00\x00" else ""
        print(f"  +{i:3d}: {pair[0]:02X} {pair[1]:02X}{flag}")

    # Actually let me try the cleanest interpretation yet: the data IS 16 records of 8 bytes
    # in mode 01, and the "broken" steps 10-15 just have unusual values because
    # the component types REALLY ARE those values, and my component mapping is wrong.
    # The 0x10 at step 12 byte[0] might be a valid type ID beyond the 0x0E I assumed.

    # Let me check the OP-XY spec more carefully:
    # OP-XY has 14 step component types. If numbered 0x00-0x0D, then 0x10 is out of range.
    # But numbered 0x01-0x0E, then 0x10 is also out of range.
    # UNLESS there are hidden/unnamed types.

    # Let me check if the 8-byte records with CLEAN zero padding at b2,b3,b6,b7
    # hold for steps 0-9 and break at step 10:
    print(f"\n{'='*80}")
    print("ZERO-PADDING CHECK for 8-byte records")
    print("=" * 80)

    pos = 2
    for step in range(16):
        rec = d119[pos:pos+8]
        z_ok = rec[2] == 0 and rec[3] == 0 and rec[6] == 0 and rec[7] == 0
        hex_str = " ".join(f"{b:02X}" for b in rec)
        status = "OK" if z_ok else f"BROKEN (b2={rec[2]:02X} b3={rec[3]:02X} b6={rec[6]:02X} b7={rec[7]:02X})"
        print(f"  Step {step:2d}: [{hex_str}] zeros: {status}")
        pos += 8

    # So the 4+4 byte interpretation fails after step 9.
    # This strongly suggests the record size is NOT 8 bytes for mode 01.

    # ===== Let me try: mode 01 = variable record size =====
    # Each record: [type(1)] [param(1)] [00 00] = 4 bytes
    # But some types have more data?
    # 128/4 = 32 entries. Maybe 2 per step (component pair)?

    print(f"\n{'='*80}")
    print("TRYING: 4-byte entries, reading until FF (component-type table)")
    print("=" * 80)

    pos = 2
    entries = []
    while pos + 3 < len(d119):
        # Check for sentinel
        if d119[pos] == 0xFF and d119[pos+1] == 0x00:
            break
        entry = d119[pos:pos+4]
        entries.append((pos, entry))
        pos += 4

    print(f"  Found {len(entries)} 4-byte entries:")
    for i, (off, entry) in enumerate(entries):
        hex_str = " ".join(f"{b:02X}" for b in entry)
        comp_type = entry[0]
        name = COMP.get(comp_type, f"?({comp_type})")
        print(f"  {i:3d} @+{off:3d}: [{hex_str}]  type=0x{comp_type:02X}({name})")

    # Count types
    types_seen = [entry[0] for _, entry in entries]
    print(f"\n  Types: {[f'0x{t:02X}' for t in types_seen]}")
    print(f"  Unique: {sorted(set(types_seen))} ({len(set(types_seen))} unique)")

    # ===== OK last try — maybe mode 01 uses the same 7+1 format as mode 02, =====
    # ===== just with a leading mode byte that doesn't count as a type =====
    # Mode 01: E4 + 01 + [7-byte rec0] [0A sep] [7-byte rec1] ... [7-byte rec15]
    # 1 + 1 + 16*7 + 15 = 129 ≠ 130. Off by 1.
    # What if mode 01 has a trailing 0A too?
    # 1 + 1 + 16*7 + 16 = 130. YES!
    # That means: 16 records of 7 bytes each, with 0x00 (not 0x0A!) as separator,
    # plus a trailing separator.

    print(f"\n{'='*80}")
    print("TRYING: mode 01 = mode(1) + 16*(7-byte rec + 1-byte sep)")
    print("        = E4(1) + 01(1) + 16*8 = 130")
    print("=" * 80)

    # In mode 02, separator = 0x0A. In mode 01, separator = 0x00?
    pos = 2  # skip E4 + mode
    for step in range(16):
        rec = d119[pos:pos+7]
        sep = d119[pos+7]
        hex_str = " ".join(f"{b:02X}" for b in rec)
        comp_type = rec[0]
        name = COMP.get(comp_type, f"?({comp_type})")
        print(f"  Step {step:2d}: [{hex_str}] sep=0x{sep:02X}  type=0x{comp_type:02X}({name})")
        pos += 8

    # In this model:
    # rec[0] = comp type (ascending: 00,00,01,02,03,04,05,06,06,07...)
    # rec[1:7] = 6 bytes of params
    # sep = 0x00 for most, sometimes other values

    # But wait — if separator is always 0x00, it could just be the 8th byte of the record.
    # So this is equivalent to 8-byte records with no explicit separator.
    # Which is what we already tried and it breaks at step 10.

    # ===== FINAL APPROACH: compare u119 with a different u1XX that has =====
    # ===== a DIFFERENT known component type set to understand the encoding =====

    # Let me check all unnamed files for their E4 mode bytes
    print(f"\n{'='*80}")
    print("CORPUS SCAN: E4 marker and mode bytes across unnamed files")
    print("=" * 80)

    corpus_dir = os.path.join(BASE, "src/one-off-changes-from-default")
    import glob
    xy_files = sorted(glob.glob(os.path.join(corpus_dir, "unnamed *.xy")))

    results = []
    for path in xy_files:
        with open(path, "rb") as f:
            data = f.read()
        sig = data.find(TRACK_SIG)
        if sig == -1:
            continue
        next_sig = data.find(TRACK_SIG, sig + len(TRACK_SIG))
        body_end = next_sig - 4 if next_sig != -1 else len(data)
        body = data[sig:body_end]

        e4 = body.find(b"\xE4", 0x80)
        if e4 == -1:
            continue

        mode = body[e4 + 1]
        # Find end
        end = find_sentinel_run(body, e4)
        size = end - e4 if end else "?"

        fname = os.path.basename(path)
        num = int(fname.split()[1].split('.')[0])
        results.append((num, fname, e4, mode, size))

    # Show only those that differ from baseline
    # First find the baseline (unnamed 1)
    baseline = [r for r in results if r[0] == 1]
    if baseline:
        base_mode = baseline[0][3]
        base_size = baseline[0][4]
    else:
        base_mode = None
        base_size = None

    print(f"\nBaseline (unnamed 1): mode=0x{base_mode:02X}, size={base_size}" if base_mode is not None else "\nNo baseline found")

    print(f"\nFiles with E4 mode or size different from baseline:")
    for num, fname, e4, mode, size in results:
        if mode != base_mode or size != base_size:
            print(f"  {fname:>25s}: E4 at 0x{e4:04X}, mode=0x{mode:02X}, size={size}")

    print(f"\nAll unique (mode, size) combinations:")
    combos = set()
    for num, fname, e4, mode, size in results:
        combos.add((mode, size))
    for mode, size in sorted(combos):
        count = sum(1 for r in results if r[3] == mode and r[4] == size)
        examples = [r[1] for r in results if r[3] == mode and r[4] == size][:3]
        print(f"  mode=0x{mode:02X} size={size}: {count} files (e.g. {', '.join(examples)})")


if __name__ == "__main__":
    main()
