#!/usr/bin/env python3
"""Decode step component records in unnamed 118 vs unnamed 119.

Focus on the E4 marker block structure and per-step encoding.
"""

import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_118 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 118.xy")
FILE_119 = os.path.join(BASE, "src/one-off-changes-from-default/unnamed 119.xy")

TRACK_SIG = b"\x00\x00\x01\x03\xff\x00\xfc\x00"

# Known step component types (from OP-XY spec: 14 types)
COMPONENT_TYPES = {
    0x00: "None/Default",
    0x01: "Note Length",
    0x02: "Velocity",
    0x03: "Probability",
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
    0x0E: "Delay",
}


def get_t1_body(path: str) -> bytes:
    with open(path, "rb") as f:
        data = f.read()
    sig = data.find(TRACK_SIG)
    next_sig = data.find(TRACK_SIG, sig + len(TRACK_SIG))
    body_end = next_sig - 4 if next_sig != -1 else len(data)
    return data[sig:body_end]


def decode_component_block(body: bytes, label: str):
    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")

    # Find E4 marker
    e4_off = body.find(b"\xE4", 0x80)
    if e4_off == -1:
        print("  E4 marker not found!")
        return

    print(f"E4 marker at body offset: 0x{e4_off:04X}")

    # Flag/mode byte right after E4
    mode = body[e4_off + 1]
    print(f"Mode byte (E4+1): 0x{mode:02X}")

    if mode == 0x02:
        print("  -> Mode 0x02: UNIFORM (all steps same component)")
        # In uniform mode, the record is compact:
        # E4 02 [component_data...] repeated identically for each step
        # Let's figure out the per-step record size
        # From the hex dump: E4 02 00 00 00 04 00 00 | 0A 02 00 00 00 04 00 00 | 0A ...
        # The first record after E4 02 is: 00 00 00 04 00 00
        # Then separator 0A, then: 02 00 00 00 04 00 00
        # Wait, let me look more carefully.

        # Actually the uniform data after E4 02:
        # 00 00 00 04 00 00 | 0A 02 00 00 00 04 00 00 | 0A 02 ...
        # Looks like: [6-byte record] then (0A [7-byte record]) x15
        # OR: the pattern is 8-byte records with 0A as separator
        # Let me just dump and parse by looking for repeating patterns

        # Full dump of the component data region
        region = body[e4_off:e4_off + 140]
        print(f"\n  Raw data ({len(region)} bytes):")
        for i in range(0, len(region), 16):
            chunk = region[i:i+16]
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            print(f"    +{i:03X}  {hex_str}")

        # Parse the uniform records
        # Pattern: E4 02 [record0] 0A [record1] 0A ... 0A [record15] FF
        pos = e4_off + 2  # skip E4 02
        print(f"\n  Parsing 16 step records (uniform mode 0x02):")
        for step in range(16):
            if step == 0:
                # First record: no separator
                pass
            else:
                # Expect 0x0A separator
                sep = body[pos]
                if sep != 0x0A:
                    print(f"    Step {step}: expected separator 0x0A, got 0x{sep:02X} at offset 0x{pos:04X}")
                pos += 1

            # Read 8 bytes of record data
            rec = body[pos:pos+8]
            # Try to decode: [type_byte] [param1] [00] [00] [param2] [00] [00] [00]
            # Or: bytes as fields
            print(f"    Step {step:2d}: {' '.join(f'{b:02X}' for b in rec)}  "
                  f"(type=0x{rec[0]:02X}={COMPONENT_TYPES.get(rec[0], '?')}, "
                  f"param_u16={int.from_bytes(rec[1:3], 'little')}, "
                  f"field3=0x{rec[3]:02X}, "
                  f"field4_u16={int.from_bytes(rec[4:6], 'little')}, "
                  f"field6=0x{rec[6]:02X}, field7=0x{rec[7]:02X})")
            pos += 6  # skip record

        # What's after the last record?
        print(f"\n  After records, body[0x{pos:04X}]: {' '.join(f'{body[pos+i]:02X}' for i in range(8))}")

    elif mode == 0x01:
        print("  -> Mode 0x01: MIXED (each step has different component)")

        # Full dump
        region = body[e4_off:e4_off + 150]
        print(f"\n  Raw data ({len(region)} bytes):")
        for i in range(0, len(region), 16):
            chunk = region[i:i+16]
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            print(f"    +{i:03X}  {hex_str}")

        # Parse records -- need to figure out record size
        # From 119: E4 01 00 04 00 00 0B 02 00 00 00 04 00 00 0A 04 00 00 01 ...
        # Let me try: after E4 01, each record is 7 bytes + 0A separator?
        # Or variable...
        # Let me try treating it as a stream and looking for patterns

        pos = e4_off + 2  # skip E4 01
        print(f"\n  Parsing 16 step records (mixed mode 0x01):")

        # Let me try a different approach: dump record-by-record
        # In mode 02, record was 6 bytes with 0A separator
        # Let me try: first record no separator, subsequent have separator
        # But the data values vary, so the "separator" might not be 0A

        # Alternative: maybe mode 01 = per-step type prefix + value
        # E4 01 | 00 04 00 00 0B | 02 00 00 00 04 00 00 0A
        # Hmm, that doesn't parse cleanly either.

        # Let me try fixed 8-byte records (including type+value) after E4 01:
        for step in range(16):
            rec = body[pos:pos+8]
            print(f"    Step {step:2d} @ 0x{pos:04X}: {' '.join(f'{b:02X}' for b in rec)}")
            pos += 8

        # Reset and try a different record size
        print(f"\n  Trying variable parsing - looking for known component type IDs:")
        pos = e4_off + 2
        remaining = body[pos:pos+140]
        # Find all positions of bytes 0x00-0x0E in the data
        # that could be component type bytes

    else:
        print(f"  -> Unknown mode 0x{mode:02X}")
        region = body[e4_off:e4_off + 140]
        print(f"\n  Raw data ({len(region)} bytes):")
        for i in range(0, len(region), 16):
            chunk = region[i:i+16]
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            print(f"    +{i:03X}  {hex_str}")

    # Find the alloc byte and surrounding context
    # Look for the 0x06 byte that appears after the FF 00 00 sentinel run
    # following the component data
    sentinel_run_start = None
    for i in range(e4_off + 120, min(e4_off + 200, len(body)) - 2):
        if body[i] == 0xFF and body[i+1] == 0x00 and body[i+2] == 0x00:
            sentinel_run_start = i
            break

    if sentinel_run_start:
        # Count consecutive FF 00 00 triplets
        j = sentinel_run_start
        while j + 2 < len(body) and body[j] == 0xFF and body[j+1] == 0x00 and body[j+2] == 0x00:
            j += 3
        sentinel_count = (j - sentinel_run_start) // 3
        print(f"\n  Post-component FF 00 00 sentinel run: {sentinel_count} entries")
        print(f"    From 0x{sentinel_run_start:04X} to 0x{j:04X}")
        print(f"    Byte after sentinels: 0x{body[j]:02X} at 0x{j:04X}")
        # Print context around the alloc byte
        print(f"    Context at 0x{j:04X}: {' '.join(f'{body[j+i]:02X}' for i in range(16))}")

    # ---- Now let's understand the 2-byte size difference ----
    print(f"\n  Component data region size:")
    # Count from E4 to the start of the post-component sentinel run
    if sentinel_run_start:
        data_size = sentinel_run_start - e4_off
        print(f"    From E4 (0x{e4_off:04X}) to sentinel run (0x{sentinel_run_start:04X}): {data_size} bytes")


def aligned_comparison():
    """Compare the component data blocks aligned by record."""
    body118 = get_t1_body(FILE_118)
    body119 = get_t1_body(FILE_119)

    e4_118 = body118.find(b"\xE4", 0x80)
    e4_119 = body119.find(b"\xE4", 0x80)

    print(f"\n{'='*80}")
    print(f"  ALIGNED RECORD COMPARISON")
    print(f"{'='*80}")

    # Both E4 at same offset
    print(f"E4 offsets: u118=0x{e4_118:04X}, u119=0x{e4_119:04X}")

    # Uniform (118): E4 02 [6-byte rec] (0A [6-byte rec])x15
    # Total: 2 + 6 + 15*(1+6) = 2 + 6 + 105 = 113 bytes? No wait...

    # Let me count the actual data
    # u118 from E4: E4 02 00 00 00 04 00 00 | 0A 02 00 00 00 04 00 00 | 0A ...
    # First record after E4 02: 00 00 00 04 00 00 (6 bytes)
    # Then 0A separator, then: 02 00 00 00 04 00 00 (7 bytes)
    # Wait, that's 7 not 6. Let me re-count.

    print(f"\n  u118 (uniform) data after E4:")
    d118 = body118[e4_118:e4_118+140]
    for i in range(0, min(140, len(d118)), 8):
        chunk = d118[i:i+8]
        print(f"    +{i:03d} (0x{e4_118+i:04X})  {' '.join(f'{b:02X}' for b in chunk)}")

    print(f"\n  u119 (mixed) data after E4:")
    d119 = body119[e4_119:e4_119+140]
    for i in range(0, min(140, len(d119)), 8):
        chunk = d119[i:i+8]
        print(f"    +{i:03d} (0x{e4_119+i:04X})  {' '.join(f'{b:02X}' for b in chunk)}")

    # Now let's try to detect record boundaries
    # In u118, the repeating 0A suggests it's a separator
    # Pattern: E4 02 [rec0] 0A [rec1] 0A [rec2] ...
    # rec0: 00 00 00 04 00 00
    # rec1: 02 00 00 00 04 00 00 (7 bytes?!)
    # That's asymmetric. Let me look at it differently:
    # E4 02 | 00 00 00 04 00 00 0A | 02 00 00 00 04 00 00 0A | ...
    # That gives 7-byte records with trailing 0A for each.
    # Except the very first one.
    # Let me check: maybe 02 is part of the record, not the header

    # u118 after E4: 02 00 00 00 04 00 00 0A | 02 00 00 00 04 00 00 0A | ...
    # That's 8-byte records! With the 02 being the first byte of each record!
    # 16 records x 8 bytes = 128 bytes + 1 (E4 header) = 129 from E4

    print(f"\n  Trying 8-byte records (including mode/type byte):")
    print(f"  u118 records:")
    pos = e4_118 + 1  # skip E4
    for step in range(16):
        rec = body118[pos:pos+8]
        rec_type = rec[0]
        # For Hold: 02 00 00 00 04 00 00 0A
        # type=0x02, then 6 bytes of params, then 0x0A terminator?
        print(f"    Step {step:2d}: {' '.join(f'{b:02X}' for b in rec)}")
        pos += 8

    # Check what comes after 16 records
    print(f"    After 16 records at 0x{pos:04X}: {' '.join(f'{body118[pos+i]:02X}' for i in range(8))}")

    print(f"\n  u119 records:")
    pos = e4_119 + 1  # skip E4
    for step in range(16):
        rec = body119[pos:pos+8]
        print(f"    Step {step:2d}: {' '.join(f'{b:02X}' for b in rec)}")
        pos += 8

    print(f"    After 16 records at 0x{pos:04X}: {' '.join(f'{body119[pos+i]:02X}' for i in range(8))}")

    # Let me try yet another approach:
    # What if mode byte 01 vs 02 changes the record size?
    # u118 mode=02, total data = 128 bytes? + 2 header?
    # u119 mode=01, total data = 130 bytes? + 2 header?
    # u119 is 2 bytes larger total

    # Let me count from E4 to the first FF 00 00 after the block
    for label, body, e4 in [("u118", body118, e4_118), ("u119", body119, e4_119)]:
        # Find FF 00 00 after the component data
        i = e4 + 120  # minimum expected
        while i + 2 < len(body):
            if body[i] == 0xFF and body[i+1] == 0x00 and body[i+2] == 0x00:
                break
            i += 1
        data_size = i - e4
        print(f"\n  {label}: E4 at 0x{e4:04X}, first FF 00 00 after at 0x{i:04X}, data size = {data_size} bytes")
        print(f"    Data: {' '.join(f'{body[e4+j]:02X}' for j in range(data_size))}")


def main():
    body118 = get_t1_body(FILE_118)
    body119 = get_t1_body(FILE_119)

    decode_component_block(body118, "unnamed 118 (UNIFORM: Hold on all 16 steps)")
    decode_component_block(body119, "unnamed 119 (MIXED: 14 different types + 2 repeats)")
    aligned_comparison()


if __name__ == "__main__":
    main()
