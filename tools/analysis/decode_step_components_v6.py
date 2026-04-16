#!/usr/bin/env python3
"""Step component decoder v6 — focus on the broken region offset hypothesis.

CONFIRMED:
- Mode 02 (uniform): E4 + 16*7-byte records + 15*0x0A sep = 128. Perfect.
  Record: [type(1)] [val(1)] [00(1)] [00(1)] [param(1)] [00(1)] [00(1)]

- Mode 01 (mixed): 128 bytes payload. First 80 bytes = 20 clean 4-byte entries.
  Entries 0-19: [type(1)] [val(1)] [00(1)] [00(1)] — always zero-padded.
  Paired as (A,B) per step: steps 0-9 use 2 entries each.
  A+B type sums ~= 0x0A consistently.

QUESTION: What if entry 20 (step 10 slot A) has a 3-byte data + 2-byte padding = 5 bytes
(extra byte because val>255 or multi-byte param), causing all subsequent entries to
shift by 1 byte?

Let me try: entries 0-19 are 4 bytes each. Entry 20 is 5 bytes (extra val byte).
Then entries 21+ resume at 4-byte each from the new offset.
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


def try_parse_entries(payload, start_offset=0, label=""):
    """Try parsing 4-byte entries from start_offset."""
    pos = start_offset
    entries = []
    while pos + 3 < len(payload):
        entry = payload[pos:pos+4]
        z_ok = entry[2] == 0 and entry[3] == 0
        entries.append((pos, entry, z_ok))
        pos += 4
    return entries


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

    # ===== Try parsing from offset 82 (after the first "broken" 2 bytes) =====
    print("=" * 80)
    print("OFFSET TEST: skip 2 extra bytes in broken region")
    print("=" * 80)

    # The broken region starts at payload[80]: 07 04 04 00 00 00 02 08 ...
    # Entry 20 @ offset 80: [07 04 04 00] — has 04 in byte 2, BROKEN
    # What if the actual entry 20 is [07 04 04] (3 bytes) plus [00 00] (padding)?
    # Then entry 21 starts at offset 85: [00 02 08 00 00] → [00 02] + [08 00 00] ???
    # That doesn't work either.

    # What if entry 20 has an extra parameter byte?
    # [07 04] + [04 00 00] = type=Swing, val=4, extra_val=4, padding=00 00
    # That's 5 bytes: [type(1) val(1) extra(1) 00 00]
    # Then from offset 85: [00 02 08 00 00] = [type=0x00 val=0x02 extra=0x08 00 00] = 5-byte entry
    # From offset 90: [08 04 02 00 00] = [type=0x08 val=0x04 extra=0x02 00 00] = 5-byte entry
    # From offset 95: [01 10 00 00] = [type=0x01 val=0x10 00 00] = 4-byte entry (back to normal?)

    print(f"\nTrying 5-byte entries in broken region:")
    broken = payload[80:]
    pos = 0
    entry_num = 20
    results = []
    while pos < len(broken):
        remaining = len(broken) - pos
        if remaining < 4:
            break

        # Try 4-byte entry first
        entry4 = broken[pos:pos+4]
        z_ok_4 = entry4[2] == 0 and entry4[3] == 0

        # Try 5-byte entry
        entry5 = broken[pos:pos+5] if remaining >= 5 else None
        z_ok_5 = entry5 is not None and entry5[3] == 0 and entry5[4] == 0

        if z_ok_4:
            entry = entry4
            size = 4
        elif z_ok_5:
            entry = entry5
            size = 5
        else:
            # Force 4-byte and note the issue
            entry = entry4
            size = 4

        comp_type = entry[0]
        name = COMP.get(comp_type, f"?({comp_type})")
        hex_str = " ".join(f"{b:02X}" for b in entry)
        z_status = "OK" if (size == 4 and z_ok_4) or (size == 5 and z_ok_5) else "BROKEN"
        results.append((entry_num, 80+pos, entry, size, z_status, comp_type))
        print(f"  {entry_num:3d} @+{80+pos:3d} ({size}B): [{hex_str}]  "
              f"type=0x{comp_type:02X}({name:>6s}) {z_status}")

        pos += size
        entry_num += 1

    # Count total clean entries
    clean = sum(1 for _, _, _, _, z, _ in results if z == "OK")
    broken_count = sum(1 for _, _, _, _, z, _ in results if z != "OK")
    print(f"\n  Results: {len(results)} entries, {clean} clean, {broken_count} broken")

    # ===== Now try ADAPTIVE parsing: use zero-pair as alignment marker =====
    print(f"\n{'='*80}")
    print("ADAPTIVE PARSING: seek 00 00, determine entry boundaries")
    print("=" * 80)

    # The 00 00 pairs in the broken region are at local offsets:
    # 3,4,8,13,17,22,23,24,27,36,41,42,43,46
    # Each 00 00 terminates an entry. The entry data is everything between the
    # end of the previous 00 00 and the current 00 00.

    # Find all 00 00 pair endpoints in the full payload
    zz_ends = []  # offset of the byte AFTER each "00 00"
    i = 0
    while i < len(payload) - 1:
        if payload[i] == 0x00 and payload[i+1] == 0x00:
            zz_ends.append(i + 2)
            i += 2  # skip both zeros
        else:
            i += 1

    print(f"  00 00 terminators end at: {zz_ends}")

    # Each entry = [data...] [00 00]
    # data starts at the end of the previous terminator (or offset 0 for the first)
    entries_adaptive = []
    prev_end = 0
    for zz_end in zz_ends:
        data_start = prev_end
        data_end = zz_end - 2  # exclude the 00 00
        data_bytes = payload[data_start:data_end]
        entries_adaptive.append((data_start, data_bytes))
        prev_end = zz_end

    # Remaining bytes after last 00 00
    if prev_end < len(payload):
        remaining = payload[prev_end:]
        if len(remaining) > 0:
            entries_adaptive.append((prev_end, remaining))

    print(f"\n  Adaptive entries (terminated by 00 00):")
    for i, (off, data_bytes) in enumerate(entries_adaptive):
        hex_str = " ".join(f"{b:02X}" for b in data_bytes)
        if len(data_bytes) >= 1:
            comp_type = data_bytes[0]
            name = COMP.get(comp_type, f"?({comp_type})")
            val = data_bytes[1] if len(data_bytes) >= 2 else -1
        else:
            comp_type = -1
            name = "(empty)"
            val = -1
        print(f"    {i:3d} @+{off:3d} ({len(data_bytes):2d} data bytes): [{hex_str}]  "
              f"type=0x{comp_type:02X}({name:>6s}) val={val:3d}")

    # Count entries, pair into steps
    print(f"\n  Total entries: {len(entries_adaptive)}")
    print(f"  If paired (2 per step): {len(entries_adaptive) / 2:.1f} steps")

    # ===== Focus on entry sizes =====
    sizes = [len(d) for _, d in entries_adaptive]
    print(f"\n  Entry data sizes: {sizes}")
    print(f"  Size distribution:")
    from collections import Counter
    for size, count in sorted(Counter(sizes).items()):
        print(f"    {size} bytes: {count} entries")

    # ===== Pair into steps and show component assignments =====
    print(f"\n  Step assignments (pairing adjacent entries):")
    for step in range(len(entries_adaptive) // 2):
        i = step * 2
        off_a, data_a = entries_adaptive[i]
        off_b, data_b = entries_adaptive[i+1]
        a_type = data_a[0] if len(data_a) >= 1 else -1
        b_type = data_b[0] if len(data_b) >= 1 else -1
        a_name = COMP.get(a_type, f"?({a_type})")
        b_name = COMP.get(b_type, f"?({b_type})")
        a_val = data_a[1] if len(data_a) >= 2 else -1
        b_val = data_b[1] if len(data_b) >= 2 else -1
        a_hex = " ".join(f"{b:02X}" for b in data_a)
        b_hex = " ".join(f"{b:02X}" for b in data_b)
        print(f"    Step {step:2d}: A=0x{a_type:02X}({a_name:>6s}) [{a_hex}]  "
              f"| B=0x{b_type:02X}({b_name:>6s}) [{b_hex}]")

    # ===== Verify A+B sum pattern =====
    print(f"\n  A+B type sum check:")
    for step in range(len(entries_adaptive) // 2):
        i = step * 2
        a_type = entries_adaptive[i][1][0] if len(entries_adaptive[i][1]) >= 1 else -1
        b_type = entries_adaptive[i+1][1][0] if len(entries_adaptive[i+1][1]) >= 1 else -1
        if a_type >= 0 and b_type >= 0:
            print(f"    Step {step:2d}: A=0x{a_type:02X} + B=0x{b_type:02X} = 0x{a_type+b_type:02X} ({a_type+b_type})")


if __name__ == "__main__":
    main()
