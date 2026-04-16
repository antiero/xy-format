#!/usr/bin/env python3
"""Step component decoder v5 — analyze unnamed 8 and 9 (large E4 blocks)
and refine the 4-byte record interpretation.

Key findings so far:
- E4 block = component data for Track 1
- Mode byte after E4: 0x01 = mixed/per-step, 0x02 = uniform
- Mode 0x02 (uniform): 16 x 7-byte records with 0x0A separators = 128 bytes
- Mode 0x01 (mixed): first 20 entries of 4-byte [type val 00 00] are clean,
  then format breaks. Need to understand the full structure.
- unnamed 8: 586 bytes! unnamed 9: 584 bytes! Much larger.
"""

import os, glob

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


def find_sentinel_run(body, start):
    i = start + 10  # much smaller minimum to handle all sizes
    while i + 2 < len(body):
        if body[i] == 0xFF and body[i+1] == 0x00 and body[i+2] == 0x00:
            return i
        i += 1
    return None


def dump_e4_block(path: str, label: str):
    body = get_t1_body(path)
    e4 = body.find(b"\xE4", 0x80)
    if e4 == -1:
        return

    end = find_sentinel_run(body, e4)
    if end is None:
        return

    size = end - e4
    mode = body[e4 + 1]
    data = body[e4:end]

    print(f"\n{'='*80}")
    print(f"  {label}: E4 at 0x{e4:04X}, size={size} bytes, mode=0x{mode:02X}")
    print(f"{'='*80}")

    # Dump raw data
    print(f"\n  Raw data:")
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        print(f"    +{i:04d}  {hex_str}")

    if mode == 0x02:
        # Uniform: 7-byte records + 0x0A sep
        print(f"\n  Mode 0x02 (uniform): 7-byte records + 0x0A sep")
        pos = 1  # skip E4
        for step in range(16):
            rec = data[pos:pos+7]
            hex_str = " ".join(f"{b:02X}" for b in rec)
            print(f"    Step {step:2d}: [{hex_str}]  type=0x{rec[0]:02X}({COMP.get(rec[0],'?')})")
            pos += 7
            if step < 15 and pos < len(data):
                sep = data[pos]
                pos += 1

    elif mode == 0x01:
        # Parse as 4-byte entries
        print(f"\n  Mode 0x01: trying 4-byte entries [type val 00 00]")
        pos = 2  # skip E4 + mode
        entry_num = 0
        while pos + 3 < len(data):
            entry = data[pos:pos+4]
            comp_type = entry[0]
            val = entry[1]
            z1, z2 = entry[2], entry[3]
            name = COMP.get(comp_type, f"?({comp_type})")
            z_ok = "  " if z1 == 0 and z2 == 0 else f" z={z1:02X}{z2:02X}"
            print(f"    {entry_num:3d} @+{pos:3d}: [{' '.join(f'{b:02X}' for b in entry)}]  "
                  f"type=0x{comp_type:02X}({name:>6s}) val={val:3d}{z_ok}")
            entry_num += 1
            pos += 4
        print(f"    Total: {entry_num} entries, remaining bytes: {len(data) - pos}")

    return data


def analyze_u119_as_pairs():
    """Look at u119's 32 4-byte entries as step pairs."""
    body = get_t1_body(os.path.join(CORPUS, "unnamed 119.xy"))
    e4 = body.find(b"\xE4", 0x80)
    end = find_sentinel_run(body, e4)
    data = body[e4:end]

    print(f"\n{'='*80}")
    print("u119: 4-byte entries as STEP PAIRS (slot A + slot B)")
    print("=" * 80)

    # First 20 entries are clean (bytes 2-3 = 00 00)
    # These form 10 pairs (steps 0-9)
    pos = 2
    print(f"\n  Clean pairs (steps 0-9):")
    for step in range(10):
        a = data[pos:pos+4]
        b = data[pos+4:pos+8]
        a_name = COMP.get(a[0], "?")
        b_name = COMP.get(b[0], "?")
        print(f"    Step {step}: A=0x{a[0]:02X}({a_name:>6s}) val={a[1]:3d}  "
              f"B=0x{b[0]:02X}({b_name:>6s}) val={b[1]:3d}")
        pos += 8

    # Steps 10-15: remaining 48 bytes = 12 entries, but they're "broken"
    # Maybe these steps have different encoding
    print(f"\n  Remaining bytes for steps 10-15: {len(data) - pos} bytes")
    remaining = data[pos:]
    print(f"    Raw: {' '.join(f'{b:02X}' for b in remaining)}")

    # What if the "broken" part uses a DIFFERENT encoding?
    # Like a bitmap-based approach?
    # Or what if the 4-byte entries continue but with extra fields for certain types?


def analyze_u8_structure():
    """unnamed 8 has a 586-byte E4 block. That's a LOT more data.
    Let's see what's in it."""
    body = get_t1_body(os.path.join(CORPUS, "unnamed 8.xy"))
    e4 = body.find(b"\xE4", 0x80)
    end = find_sentinel_run(body, e4)
    data = body[e4:end]

    print(f"\n{'='*80}")
    print(f"unnamed 8: E4 block = {len(data)} bytes")
    print("=" * 80)

    mode = data[1]
    print(f"Mode: 0x{mode:02X}")

    # 586 bytes. mode 01.
    # 586 - 2 = 584 payload bytes.
    # If 4-byte records: 584/4 = 146 entries.
    # If 32 entries per step (like u119 attempted): 146/32 ≈ 4.5. Hmm.
    # If this file has ALL 16 steps with step components...

    # Let me scan for 00 00 pairs to find record boundaries
    pos = 2
    entry_num = 0
    clean_entries = 0
    broken_entries = 0
    entries = []
    while pos + 3 < len(data):
        entry = data[pos:pos+4]
        z_ok = entry[2] == 0 and entry[3] == 0
        if z_ok:
            clean_entries += 1
        else:
            broken_entries += 1
        entries.append(entry)
        entry_num += 1
        pos += 4

    print(f"\n  4-byte entries: {entry_num} total, {clean_entries} clean, {broken_entries} broken")
    print(f"  Remaining: {len(data) - pos} bytes")

    # How far do clean entries go?
    last_clean = -1
    for i, e in enumerate(entries):
        if e[2] == 0 and e[3] == 0:
            last_clean = i

    first_broken = -1
    for i, e in enumerate(entries):
        if e[2] != 0 or e[3] != 0:
            first_broken = i
            break

    print(f"  First broken entry: #{first_broken}")
    print(f"  Last clean entry: #{last_clean}")

    # Print entries around the break point
    print(f"\n  Entries around first break (#{first_broken}):")
    for i in range(max(0, first_broken-3), min(len(entries), first_broken+5)):
        e = entries[i]
        hex_str = " ".join(f"{b:02X}" for b in e)
        z = "OK" if e[2] == 0 and e[3] == 0 else f"BROKEN z={e[2]:02X}{e[3]:02X}"
        name = COMP.get(e[0], f"?({e[0]})")
        print(f"    {i:3d}: [{hex_str}]  type=0x{e[0]:02X}({name}) val={e[1]:3d} {z}")


def scan_all_tracks():
    """Check ALL 16 tracks for E4 markers in unnamed 119."""
    print(f"\n{'='*80}")
    print("ALL TRACKS E4 scan: unnamed 119")
    print("=" * 80)

    path = os.path.join(CORPUS, "unnamed 119.xy")
    with open(path, "rb") as f:
        raw = f.read()

    # Find all 16 track signatures
    sigs = []
    pos = 0
    while True:
        idx = raw.find(TRACK_SIG, pos)
        if idx == -1:
            break
        sigs.append(idx)
        pos = idx + len(TRACK_SIG)

    print(f"  Found {len(sigs)} track signatures")

    for i, sig in enumerate(sigs):
        # Body extends to next signature preamble (or EOF)
        if i + 1 < len(sigs):
            body_end = sigs[i+1] - 4
        else:
            body_end = len(raw)
        body = raw[sig:body_end]

        e4 = body.find(b"\xE4", 0x0A)  # search from early in body
        if e4 == -1:
            print(f"  Track {i+1:2d}: no E4 marker (body size={len(body)})")
        else:
            end = find_sentinel_run(body, e4)
            size = end - e4 if end else "?"
            mode = body[e4+1] if e4+1 < len(body) else "?"
            print(f"  Track {i+1:2d}: E4 at body+0x{e4:04X}, mode=0x{mode:02X}, block size={size}")


def main():
    # Check unnamed 8 and 9 (large E4 blocks)
    for num in [8, 9]:
        path = os.path.join(CORPUS, f"unnamed {num}.xy")
        if os.path.exists(path):
            dump_e4_block(path, f"unnamed {num}")

    # Also check unnamed 118 and 119
    for num in [118, 119]:
        path = os.path.join(CORPUS, f"unnamed {num}.xy")
        if os.path.exists(path):
            dump_e4_block(path, f"unnamed {num}")

    analyze_u119_as_pairs()
    analyze_u8_structure()
    scan_all_tracks()


if __name__ == "__main__":
    main()
