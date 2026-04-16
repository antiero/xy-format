#!/usr/bin/env python3
"""Step component decoder v3 — focus on the two-field interpretation.

The data for u119 (mode 01, mixed) parsed as 8-byte records has byte[0]
counting 0,0,1,2,3,4,5,6,6,7,7,0,?,0,0,2 — this looks like TWO fields
are interleaved. Let me try the interpretation where:
  - Field A (byte[0]): component type for HALF the steps
  - Field B (byte[4]): component type for the OTHER half

Or perhaps: the 8-byte record actually encodes TWO steps, not one.
In u118, all records are: 02 00 00 00 04 00 00 — maybe byte[0]=02 is
one step's type, byte[4]=04 is the next step's type?

u118 pairs: (02,04) for all — but we know ALL steps are Hold. If Hold=02 or Hold=04...
We need more corpus files to resolve, but let me try both interpretations.
"""

import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_118 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 118.xy")
FILE_119 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 119.xy")

TRACK_SIG = b"\x00\x00\x01\x03\xff\x00\xfc\x00"


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
    body118 = get_t1_body(FILE_118)
    body119 = get_t1_body(FILE_119)

    e4_118 = body118.find(b"\xE4", 0x80)
    e4_119 = body119.find(b"\xE4", 0x80)

    end_118 = find_sentinel_run(body118, e4_118)
    end_119 = find_sentinel_run(body119, e4_119)

    # ===== Mode 02 (u118, uniform): 128 bytes =====
    # Structure: E4 + 16 * (7-byte rec) + 15 * (1-byte 0x0A sep) = 128
    print("=" * 80)
    print("u118 (UNIFORM Hold) — 7-byte records, 0x0A separators")
    print("=" * 80)

    pos = e4_118 + 1
    recs_118 = []
    for step in range(16):
        rec = body118[pos:pos+7]
        recs_118.append(rec)
        pos += 7
        if step < 15:
            pos += 1  # skip 0x0A

    # Each 7-byte record: 02 00 00 00 04 00 00
    # Let's parse as: [type_A(1)] [val_A(1)] [pad(1)] [pad(1)] [type_B(1)] [val_B(1)] [pad(1)]
    # Or: [field0] [field1] [00] [00] [field4] [00] [00]
    # In uniform mode, type_A=0x02 and type_B=0x04 are BOTH hold-related, just different fields.

    print(f"\nRaw 7-byte records:")
    for step, rec in enumerate(recs_118):
        hex_str = " ".join(f"{b:02X}" for b in rec)
        print(f"  Step {step:2d}: [{hex_str}]")

    print(f"\nTwo-field interpretation (each rec = 2 half-step descriptors?):")
    for step, rec in enumerate(recs_118):
        # Split: [A_type(1) A_val(1) 00 00] [B_type(1) B_val(1) 00]
        # No, the layout doesn't split evenly into 4+3.
        # Try: [A_type(1)] [A_param(2)] [00] [B_type(1)] [B_param(2)]
        a_type, a_param_lo, a_param_hi, zero, b_type, b_param_lo, b_param_hi = rec
        print(f"  Step {step:2d}: A=0x{a_type:02X}(param={a_param_lo | (a_param_hi<<8)}), "
              f"mid=0x{zero:02X}, B=0x{b_type:02X}(param={b_param_lo | (b_param_hi<<8)})")

    # ===== Mode 01 (u119, mixed): 130 bytes =====
    # Structure: E4 + mode(1) + 16 * 8-byte records = 130 (validated: hits FF perfectly)
    print(f"\n{'='*80}")
    print("u119 (MIXED) — 8-byte records, no separators")
    print("=" * 80)

    pos = e4_119 + 2
    recs_119 = []
    for step in range(16):
        rec = body119[pos:pos+8]
        recs_119.append(rec)
        pos += 8

    print(f"\nRaw 8-byte records:")
    for step, rec in enumerate(recs_119):
        hex_str = " ".join(f"{b:02X}" for b in rec)
        print(f"  Step {step:2d}: [{hex_str}]")

    # Now parse as: [type_A(1)] [val_A(1)] [00] [00] [type_B(1)] [val_B(1)] [00] [00]
    print(f"\nTwo-field interpretation:")
    for step, rec in enumerate(recs_119):
        a_type = rec[0]
        a_val = rec[1]
        a_z1, a_z2 = rec[2], rec[3]
        b_type = rec[4]
        b_val = rec[5]
        b_z1, b_z2 = rec[6], rec[7]
        print(f"  Step {step:2d}: A_type=0x{a_type:02X} A_val=0x{a_val:02X} [{a_z1:02X} {a_z2:02X}]  "
              f"B_type=0x{b_type:02X} B_val=0x{b_val:02X} [{b_z1:02X} {b_z2:02X}]")

    # The A-field type sequence: 0,0,1,2,3,4,5,6,6,7,7,0,10,0,0,2
    # The B-field type sequence: 0B,0A,09,08,07,06,05,05,04,03,00,02,02,0A,0A,00
    # B-field counts DOWN from 0x0B!
    # Steps 0-9: B goes 0B,0A,09,08,07,06,05,05,04,03 — that's 11 down to 3 (with 05 repeated)
    # Steps 10-15: B is 00,02,02,0A,0A,00 — weird

    # A-field counting UP: 0,0,1,2,3,4,5,6,6,7,7,0,10,0,0,2
    # This looks like TWO overlapping component type assignments.
    # A = "primary component", B = "secondary component"?

    # Actually wait — maybe the 8 bytes encode something completely different.
    # Let me look at the BIT PATTERNS in the "val" fields:

    print(f"\nBit pattern analysis for B_val field:")
    for step, rec in enumerate(recs_119):
        b_val = rec[5]
        # power of 2?
        if b_val > 0 and (b_val & (b_val - 1)) == 0:
            bit = b_val.bit_length() - 1
            print(f"  Step {step:2d}: B_val=0x{b_val:02X} ({b_val:3d}) = 2^{bit}")
        else:
            print(f"  Step {step:2d}: B_val=0x{b_val:02X} ({b_val:3d})")

    # B_val: 02,04,08,10,20,40,80,01,02,04,00,00,02,02,00,00
    # That's: 2,4,8,16,32,64,128,1,2,4,0,0,2,2,0,0
    # Steps 0-7: powers of 2 ascending: 2^1, 2^2, ..., 2^7, then 2^0
    # This looks like a 1-hot BITMASK — 8 steps per bit group?
    # Or maybe it's an ALLOCATION BITMAP for which step has which component.

    print(f"\nLet me try: B_val as a bitmask, B_type as component ID")
    print(f"Building a step->component map from the bitmask interpretation:")

    # Hypothesis: each record says "component B_type is assigned to bits set in B_val"
    # with bit 0 = step N*8+0, bit 1 = step N*8+1, etc.
    # But B_val has only 1 bit set per record, and B_type counts down...
    # It's more like: "step X has component B_type" where X is encoded as the bit position.

    # Wait, let me think about this differently.
    # What if the record format is:
    # [step_index(1)] [value_A(1)] [00] [00] [component_type(1)] [bitmask(1)] [00] [00]
    # Where step_index groups by something, and bitmask indicates step(s).

    # A_type values: 0,0,1,2,3,4,5,6,6,7,7,0,10,0,0,2
    # These look like they could be step indices or group indices.
    # B_type values: 0B,0A,09,08,07,06,05,05,04,03,00,02,02,0A,0A,00
    # These count mostly downward.

    # Hmm, let me try BITFIELD interpretation:
    # rec = [step_lo(1)] [param(1)] [param(1)] [param(1)] [comp_type(1)] [step_bitmask(1)] [extra(1)] [extra(1)]
    # or [comp_type(1)] [param(1)] [00] [00] [secondary_type(1)] [param2(1)] [00] [00]

    # I think the cleanest interpretation might be that each 8-byte record stores
    # TWO component slots per step: a "primary" and "secondary".
    # In u118 (uniform Hold), ALL steps have primary=0x02 and secondary=0x04.
    # In u119 (mixed), each step can have different primary and secondary.

    # But the naming 0x02="Hold" for ALL steps in u118 is suspicious since we KNOW Hold was set.
    # And the u119 secondary (B) column counts down from 0x0B which = "Reverse" in my current mapping.

    # Let me reconsider the mapping: maybe 0x02 IS Hold (not Probability).
    # OP-XY spec says 14 step component types. Let me try numbering:
    COMP2 = {
        0x00: "Note Length",
        0x01: "Velocity",
        0x02: "Hold",          # <-- changed from Probability
        0x03: "Probability",   # <-- shifted
        0x04: "Micro Timing",  # <-- shifted
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

    print(f"\n{'='*80}")
    print("REVISED MAPPING (0x02=Hold)")
    print("=" * 80)

    print(f"\nu118 primary type: 0x02 = {COMP2.get(0x02, '?')} -- MATCHES 'Hold on all steps'!")
    print(f"u118 secondary type: 0x04 = {COMP2.get(0x04, '?')}")

    print(f"\nu119 records with revised mapping:")
    for step, rec in enumerate(recs_119):
        a_type = rec[0]
        a_val = rec[1]
        b_type = rec[4]
        b_val = rec[5]
        a_name = COMP2.get(a_type, f"?({a_type})")
        b_name = COMP2.get(b_type, f"?({b_type})")
        print(f"  Step {step:2d}: primary=0x{a_type:02X}({a_name:>12s}) val={a_val:3d}  "
              f"| secondary=0x{b_type:02X}({b_name:>12s}) val={b_val:3d}")

    # Check uniqueness for the primary column
    a_types = [rec[0] for rec in recs_119]
    b_types = [rec[4] for rec in recs_119]
    print(f"\nPrimary (A) types: {[f'{t:02X}' for t in a_types]}")
    print(f"  Unique: {sorted(set(a_types))} ({len(set(a_types))} unique)")
    print(f"Secondary (B) types: {[f'{t:02X}' for t in b_types]}")
    print(f"  Unique: {sorted(set(b_types))} ({len(set(b_types))} unique)")

    # ===== Let me also check the value fields more carefully =====
    print(f"\n{'='*80}")
    print("VALUE/PARAMETER ANALYSIS")
    print("=" * 80)

    # u118: rec = [02 00 00 00 04 00 00]
    # byte 1 = 0x00 (A_val), byte 5 = 0x00 (B_val)
    # All zeros = default values (component assigned but no parameter change)

    # u119: A_val varies: 04,04,02,05,04,04,04,04,01,04,04,00,00,00,01,00
    # B_val varies: 02,04,08,10,20,40,80,01,02,04,00,00,02,02,00,00
    print(f"\nu119 field-by-field analysis:")
    print(f"  {'Step':>4}  {'b0':>3}  {'b1':>3}  {'b2':>3}  {'b3':>3}  {'b4':>3}  {'b5':>4}  {'b6':>3}  {'b7':>3}")
    for step, rec in enumerate(recs_119):
        vals = [f"{b:3d}" for b in rec]
        hex_vals = [f" {b:02X}" for b in rec]
        print(f"  {step:4d}  {' '.join(hex_vals)}")

    # b5 (secondary val) for steps 0-9: 02,04,08,10,20,40,80,01,02,04
    # That's: 1<<1, 1<<2, 1<<3, 1<<4, 1<<5, 1<<6, 1<<7, 1<<0, 1<<1, 1<<2
    # It cycles through bit positions! This is definitely a BITMASK.

    # Maybe it's an allocation bitmap: 16 bits across 2 bytes (b5 low, b6 high?)
    print(f"\nBitmask analysis (bytes 5-6 as u16 LE):")
    for step, rec in enumerate(recs_119):
        bitmask = rec[5] | (rec[6] << 8)
        print(f"  Step {step:2d}: bitmask=0x{bitmask:04X} ({bitmask:016b}) B_type=0x{rec[4]:02X}")

    # Or maybe bytes 5+6 = 16-bit value, bytes 6+7 = 16-bit value...
    # Actually the pattern for b5: 02,04,08,10,20,40,80,01,02,04,02,00,02,02,00,00
    # These look like power-of-2 shifted, with the pattern cycling.
    # b5b6 as u16: 0002,0004,0008,0010,0020,0040,0080,0001,0002,0004,...
    # That's just the same but clearer: bit 1, bit 2, ..., bit 7, bit 0, bit 1, bit 2...
    # A perfect rotating bit pattern!

    # ===== Compare against unnamed 1 (pristine baseline) =====
    print(f"\n{'='*80}")
    print("BASELINE COMPARISON (unnamed 1 — pristine default)")
    print("=" * 80)

    FILE_1 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 1.xy")
    body1 = get_t1_body(FILE_1)
    e4_1 = body1.find(b"\xE4", 0x80)
    if e4_1 == -1:
        print("No E4 marker in unnamed 1 T1!")
    else:
        end_1 = find_sentinel_run(body1, e4_1)
        size_1 = end_1 - e4_1 if end_1 else "?"
        mode_1 = body1[e4_1 + 1]
        print(f"E4 at 0x{e4_1:04X}, size={size_1} bytes, mode=0x{mode_1:02X}")
        data_1 = body1[e4_1:end_1] if end_1 else body1[e4_1:e4_1+140]
        for i in range(0, len(data_1), 8):
            chunk = data_1[i:i+8]
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            print(f"  +{i:03d}  {hex_str}")


if __name__ == "__main__":
    main()
