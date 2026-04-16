#!/usr/bin/env python3
"""Step component decoder v7 — bitmask interpretation.

Key insight: the "val" bytes in the B-slot form a clear power-of-2 sequence:
  02, 04, 08, 10, 20, 40, 80, 01, 01, 02, 04...
  = 2, 4, 8, 16, 32, 64, 128, 1, 1, 2, 4...

These are BITMASK values! Each bit represents a step number.
With 16 steps, you need a 16-bit mask. The "val" byte is just 8 bits.
The entries with 3 data bytes have an EXTRA byte — the high byte of a 16-bit mask!

So the structure is:
  [type(1)] [mask(1-2 bytes)] [00 00]

For 2-byte data: mask is 8-bit (sufficient for steps 0-7)
For 3-byte data: mask is 16-bit LE (needed for steps 8-15)

This means the records are NOT per-step but per-COMPONENT-TYPE,
with a bitmask indicating WHICH steps have that component!
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
    i = e4 + 10
    while i + 2 < len(body119):
        if body119[i] == 0xFF and body119[i+1] == 0x00 and body119[i+2] == 0x00:
            break
        i += 1
    end = i
    payload = body119[e4+2:end]  # 128 bytes

    print("=" * 80)
    print("BITMASK INTERPRETATION: per-component-type records with step bitmask")
    print("=" * 80)
    print(f"\nPayload: {len(payload)} bytes")

    # Parse entries: [type(1)] [mask_bytes(N)] [00 00]
    # N is variable: mask needs enough bytes to represent all set steps.
    # Steps 0-7 need 1 byte, steps 8-15 need 2 bytes.

    # Actually, let me re-examine the adaptive entries:
    # Entry 0: [00 04] → type=0x00, mask=0x04 → step 2
    # Entry 1: [0B 02] → type=0x0B, mask=0x02 → step 1
    # Entry 2: [00 04] → type=0x00, mask=0x04 → step 2
    # Wait, that gives step 2 twice for NotLen. That's wrong unless there are multiple assignments.

    # Let me reconsider. The "val" in the A-slot isn't always a bitmask.
    # A-slot vals: 04, 04, 02, 05, 04, 04, 04, 04, 01, 04
    # B-slot vals: 02, 04, 08, 10, 20, 40, 80, 01, 02, 04

    # The B-slot is clearly power-of-2 (bitmask). The A-slot has 05 and is less regular.
    # Maybe the A-slot "val" is a PARAMETER VALUE (e.g., Hold=5 means hold for 5 ticks),
    # and the B-slot "val" is a step BITMASK.

    # But that means A and B are DIFFERENT KINDS of data!
    # A = [type(1)] [param_value(1)]
    # B = [type(1)] [step_bitmask(1 or 2 bytes)]

    # Actually wait. In mode 02 (uniform, u118), each 7-byte record is:
    # [02 00 00 00 04 00 00]
    # If 0x02=Hold with param=0, and 0x04=uTime with param=0...
    # Maybe the 7-byte record IS two compressed entries:
    # [type_A=02] [param_A=00] [00] [00] [type_B=04] [param_B=00] [00]
    # = 3 bytes for A + 1 padding + 3 bytes for B

    # In mode 01 (mixed, u119), the entries are split with 00 00 terminators:
    # [type param] [00 00] [type mask] [00 00]
    # Wait, that still doesn't explain the B-slot val being a bitmask.

    # Let me look at this from the SEMANTIC perspective.
    # unnamed 119: "14 different component types + 2 repeats" across 16 steps.
    # That means each step has ONE component type assigned.
    # The data must map step->type or type->steps.

    # If the data is a list of (type, bitmask) pairs:
    # Entry 0: type=0x00(NotLen), mask=0x04 → steps with NotLen = {step 2}
    # Entry 1: type=0x0B(Rev), mask=0x02 → steps with Rev = {step 1}
    # Entry 2: type=0x00(NotLen), mask=0x04 → steps with NotLen = {step 2} again?!
    # That's a duplicate, which makes no sense.

    # Unless entries come in PAIRS where the second is a "parameter mask" or "continuation."

    # ===== Let me try a completely different interpretation =====
    # What if the 128-byte payload represents 16 steps, each with an 8-byte record?
    # Record = [comp_A_type(1)] [comp_A_val(1)] [00] [00] [comp_B_type(1)] [comp_B_val(1)] [00] [00]
    # = 8 bytes per step, 16 steps = 128 bytes.
    # This works for steps 0-9 but breaks for steps 10-15 because zero-padding fails.

    # Maybe the zero-padding ISN'T zero-padding but a 2-byte field:
    # Record = [comp_A_type(1)] [comp_A_val(1)] [field_A(2)] [comp_B_type(1)] [comp_B_val(1)] [field_B(2)]
    # For steps 0-9, field_A = field_B = 0x0000 (default).
    # For steps 10+, field_A or field_B have non-zero values.

    print(f"\n{'='*80}")
    print("8-BYTE RECORDS: [type_A(1)] [val_A(1)] [field_A(2)] [type_B(1)] [val_B(1)] [field_B(2)]")
    print("=" * 80)

    for step in range(16):
        rec = payload[step*8:(step+1)*8]
        type_a = rec[0]
        val_a = rec[1]
        field_a = rec[2] | (rec[3] << 8)
        type_b = rec[4]
        val_b = rec[5]
        field_b = rec[6] | (rec[7] << 8)

        name_a = COMP.get(type_a, f"?({type_a})")
        name_b = COMP.get(type_b, f"?({type_b})")

        hex_str = " ".join(f"{b:02X}" for b in rec)
        print(f"  Step {step:2d}: [{hex_str}]  "
              f"A: type=0x{type_a:02X}({name_a:>6s}) val={val_a:3d} field=0x{field_a:04X}  "
              f"B: type=0x{type_b:02X}({name_b:>6s}) val={val_b:3d} field=0x{field_b:04X}")

    # For steps 10-15, type_A and type_B with the 8-byte interpretation:
    # Step 10: A=Swing(07) val=4 field=0x0004  B=NotLen(00) val=0 field=0x0802
    # Step 11: A=NotLen(00) val=0 field=0x0408  B=Hold(02) val=0 field=0x0100
    # Step 12: A=?(10) val=0 field=0x0900  B=Hold(02) val=2 field=0x0000
    # Step 13: A=NotLen(00) val=0 field=0x0020  B=NotLen(00) val=10 field=0x0202
    # Step 14: A=NotLen(00) val=1 field=0x0400  B=NotLen(00) val=0 field=0x020A
    # Step 15: A=Hold(02) val=0 field=0x0000  B=NotLen(00) val=4 field=0x0000

    # field_A values for steps 10-15: 0x0004, 0x0408, 0x0900, 0x0020, 0x0400, 0x0000
    # These look suspicious. 0x0004, 0x0408, 0x0900...

    # Wait — what if field_A is a STEP BITMASK showing which OTHER steps share this component?
    # Step 10: field_A=0x0004 → bit 2 set → this step shares Swing with step 2?
    # Step 11: field_A=0x0408 → bits 3, 10 set → shares with steps 3 and 10?

    # Actually, field_B for clean steps is always 0. Let me check the B-val more carefully.
    # Steps 0-9 B-vals: 02, 04, 08, 10, 20, 40, 80, 01, 02, 04
    # These are: 2^1, 2^2, 2^3, 2^4, 2^5, 2^6, 2^7, 2^0, 2^1, 2^2
    # That's step 1, step 2, step 3, ... step 7, step 0, step 1, step 2

    # This is rotating through bit positions. But it's not a bitmask for step N.
    # Step 0's B has bit 1 (step 1?), step 1's B has bit 2 (step 2?), etc.
    # That's not self-referential (step 0 doesn't reference step 0).

    # Unless the val field indicates a VALUE LEVEL or AMOUNT, not a bitmask.
    # Hold val=5 could mean "hold amount is 5", Flam val=16 could mean "flam amount is 16".

    # Let me check the A-vals: 4, 4, 2, 5, 4, 4, 4, 4, 1, 4
    # And the B-vals: 2, 4, 8, 16, 32, 64, 128, 1, 2, 4
    # A-vals are mostly 4 (default?), with 2, 5, 1 as exceptions.
    # B-vals are ALWAYS powers of 2 for steps 0-9.

    # Now look at A-val + B-val pairs:
    print(f"\n  Val analysis:")
    for step in range(16):
        rec = payload[step*8:(step+1)*8]
        print(f"  Step {step:2d}: A_val={rec[1]:3d} (0x{rec[1]:02X})  B_val={rec[5]:3d} (0x{rec[5]:02X})")

    # B_val power-of-2 sequence continues:
    # Step 0: 2 = 2^1
    # Step 1: 4 = 2^2
    # ...
    # Step 6: 128 = 2^7
    # Step 7: 1 = 2^0 (wraps)
    # Step 8: 2 = 2^1
    # Step 9: 4 = 2^2

    # For steps 10-15 (in 8-byte view):
    # Step 10: B_val=0 (no bit set?)
    # Step 11: B_val=0
    # Step 12: B_val=2 = 2^1
    # Step 13: B_val=10 = 0x0A (NOT power of 2!)
    # Step 14: B_val=0
    # Step 15: B_val=4 = 2^2

    # The pattern clearly breaks. So the 8-byte fixed record doesn't work for all 16 steps.

    # ===== WHAT IF the val byte indicates which "page" of a multi-page component config? =====
    # Or what if it's actually the component's PARAMETER VALUE (like "hold strength")?

    # In mode 02 (uniform Hold on all steps):
    # Each record: [02 00 00 00 04 00 00]
    # type_A = 0x02 = Hold, val_A = 0
    # type_B = 0x04 = uTime, val_B = 0
    # Both vals are 0 = default parameter values.
    # This makes sense: Hold assigned to all steps, default strength.

    # In mode 01 (mixed):
    # Step 0: A=NotLen val=4, B=Rev val=2
    # Step 1: A=NotLen val=4, B=Slide val=4
    # Both steps have NotLen(0x00) as primary. val=4 for NotLen.
    # Step 3: A=Hold val=5. That's a different val than u118's val=0 for Hold.

    # So each step has TWO component slots (A and B), each with a type and a value.
    # The value is a parameter for that component type.
    # Steps 0-9 are clean because their "field" words are 0x0000.
    # Steps 10-15 have non-zero "field" words, which might be ADDITIONAL parameters.

    # ===== Let me check against the u118 MODE 02 format =====
    # Mode 02: 7-byte record = [type_A(1)] [val_A(1)] [field_A(2)] [type_B(1)] [val_B(1)] [field_B(1)]
    # Wait, that's only 7 bytes: 1+1+2+1+1+1 = 7. Close!
    # Or: [type_A(1)] [val_A(1)] [00] [00] [type_B(1)] [00] [00] (val_B absent)
    # Or: [type_A(1)] [00] [00] [00] [type_B(1)] [00] [00]

    # In u118, all records are [02 00 00 00 04 00 00].
    # type_A=0x02, then [00 00 00], then type_B=0x04, then [00 00].
    # If val_A is byte[1]=0 and field_A is bytes[2:4]=0x0000:
    # That leaves type_B at byte[4]=0x04, val_B at byte[5]=0 and field_B at byte[6]=0.
    # But field_B is only 1 byte, not 2. Unless the mode 02 format packs differently.

    # MODE 02: 7 bytes per step
    #   [type_A(1)] [val_A(1)] [00(1)] [00(1)] [type_B(1)] [val_B(1)] [00(1)]
    #   = type_A + val_A + pad(2) + type_B + val_B + pad(1) = 7 bytes

    # MODE 01: 8 bytes per step
    #   [type_A(1)] [val_A(1)] [fieldA(2)] [type_B(1)] [val_B(1)] [fieldB(2)]
    #   = type_A + val_A + field(2) + type_B + val_B + field(2) = 8 bytes

    # The DIFFERENCE is that mode 01 has an extra byte of "field" data per step.
    # Mode 02: 3+1+3 = 7 bytes (1-byte trailing pad)
    # Mode 01: 4+4 = 8 bytes (2-byte fields)

    # This gives: mode 02 = 1 + 16*7 + 15*1 = 128 ✓
    #             mode 01 = 1 + 1 + 16*8 = 130 ✓

    # And the non-zero field bytes in steps 10-15 indicate some component-specific
    # additional configuration that's present in mixed mode but not uniform mode.

    print(f"\n{'='*80}")
    print("DEFINITIVE INTERPRETATION:")
    print("  Mode 0x02 (uniform): 7-byte record = [typeA(1) valA(1) 00 00 typeB(1) valB(1) 00]")
    print("  Mode 0x01 (mixed):   8-byte record = [typeA(1) valA(1) fA_lo fA_hi typeB(1) valB(1) fB_lo fB_hi]")
    print("=" * 80)

    # Full decode
    for step in range(16):
        rec = payload[step*8:(step+1)*8]
        type_a = rec[0]
        val_a = rec[1]
        fa = int.from_bytes(rec[2:4], 'little')
        type_b = rec[4]
        val_b = rec[5]
        fb = int.from_bytes(rec[6:8], 'little')

        name_a = COMP.get(type_a, f"?({type_a})")
        name_b = COMP.get(type_b, f"?({type_b})")

        fa_str = f" fA=0x{fa:04X}" if fa else ""
        fb_str = f" fB=0x{fb:04X}" if fb else ""

        print(f"  Step {step:2d}: A={name_a}(0x{type_a:02X}) val={val_a:3d}{fa_str}  "
              f"B={name_b}(0x{type_b:02X}) val={val_b:3d}{fb_str}")

    # ===== Cross-validate: check that all 14 component types appear somewhere =====
    all_types_a = set()
    all_types_b = set()
    for step in range(16):
        rec = payload[step*8:(step+1)*8]
        all_types_a.add(rec[0])
        all_types_b.add(rec[4])

    all_types = all_types_a | all_types_b
    print(f"\n  All component types across A+B slots: {sorted(all_types)}")
    print(f"  Named: {[COMP.get(t, f'?({t})') for t in sorted(all_types)]}")
    print(f"  Count: {len(all_types)} (expect 14+?)")

    # Missing types (0x00-0x0E that don't appear):
    expected = set(range(0x0F))  # 0x00 through 0x0E
    missing = expected - all_types
    missing_strs = [f"0x{t:02X}({COMP.get(t, '?')})" for t in sorted(missing)]
    print(f"  Missing from 0x00-0x0E: {missing_strs}")

    # Extra types (not in 0x00-0x0E):
    extra = all_types - expected
    if extra:
        print(f"  Extra types: {[f'0x{t:02X}' for t in sorted(extra)]}")

    # ===== u118 for comparison =====
    print(f"\n{'='*80}")
    print("u118 (uniform Hold) for reference:")
    print("=" * 80)

    body118 = get_t1_body(os.path.join(CORPUS, "unnamed 118.xy"))
    e4_118 = body118.find(b"\xE4", 0x80)
    i = e4_118 + 10
    while i + 2 < len(body118):
        if body118[i] == 0xFF and body118[i+1] == 0x00 and body118[i+2] == 0x00:
            break
        i += 1
    end_118 = i
    data_118 = body118[e4_118:end_118]

    # Mode 02: 7-byte records
    pos = 1  # skip E4
    for step in range(16):
        rec = data_118[pos:pos+7]
        type_a = rec[0]
        val_a = rec[1]
        type_b = rec[4]
        val_b = rec[5]
        name_a = COMP.get(type_a, f"?({type_a})")
        name_b = COMP.get(type_b, f"?({type_b})")
        print(f"  Step {step:2d}: A={name_a}(0x{type_a:02X}) val={val_a:3d}  "
              f"B={name_b}(0x{type_b:02X}) val={val_b:3d}")
        pos += 7
        if step < 15:
            pos += 1  # skip 0x0A sep


if __name__ == "__main__":
    main()
