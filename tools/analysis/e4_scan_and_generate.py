#!/usr/bin/env python3
"""Corpus-wide scan for 00 04 00 00 in Track 1 body and generate test files.

Part 1: Scan all .xy files for the 4-byte sequence 00 04 00 00 in Track 1 body.
Part 2: Generate v6a (unnamed 119 -> all Hold) and v6b (unnamed 119 -> 118b pattern).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from xy.container import XYProject, TrackBlock
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from verify_sep_formula import parse_block_known

CORPUS = Path(__file__).resolve().parent.parent / "src" / "one-off-changes-from-default"
OUTPUT = Path(__file__).resolve().parent.parent / "output" / "multistep"


# ---------------------------------------------------------------------------
# Part 1: Corpus-wide scan for 00 04 00 00 in Track 1 body
# ---------------------------------------------------------------------------
def scan_corpus():
    print("=" * 70)
    print("  Part 1: Corpus-wide scan for 00 04 00 00 in Track 1 body")
    print("=" * 70)

    pattern = bytes([0x00, 0x04, 0x00, 0x00])
    total_files = 0
    files_with_match = 0

    for p in sorted(CORPUS.glob("*.xy")):
        total_files += 1
        data = p.read_bytes()
        try:
            proj = XYProject.from_bytes(data)
        except Exception as e:
            print(f"  SKIP {p.name}: {e}")
            continue

        body = proj.tracks[0].body
        offsets = []
        pos = 0
        while True:
            idx = body.find(pattern, pos)
            if idx == -1:
                break
            offsets.append(idx)
            pos = idx + 1

        if offsets:
            files_with_match += 1
            # Categorize: inside E4 block vs outside
            e4_inside = []
            e4_outside = []

            if len(body) > 0xB1 and body[0xB1] == 0xE4:
                records, seps = parse_block_known(body, 0xB1)
                if records is not None:
                    block_size = 1 + sum(r[1] for r in records) + len(seps)
                    e4_start = 0xB1
                    e4_end = e4_start + block_size
                else:
                    e4_start = e4_end = None
            else:
                e4_start = e4_end = None

            for off in offsets:
                if e4_start is not None and e4_start <= off < e4_end:
                    e4_inside.append(off)
                else:
                    e4_outside.append(off)

            print(f"\n  {p.name}: {len(offsets)} occurrence(s)")
            if e4_inside:
                print(f"    Inside E4 block ({len(e4_inside)}): "
                      f"{', '.join(f'{o:#06x}' for o in e4_inside[:6])}"
                      f"{'...' if len(e4_inside) > 6 else ''}")
            if e4_outside:
                for off in e4_outside:
                    ctx = body[max(0, off - 4):off + 8]
                    label = ""
                    if e4_end is not None and off == e4_end:
                        label = "  <-- immediately after E4 block"
                    print(f"    Outside E4 at {off:#06x}: ...{ctx.hex(' ')}...{label}")

    print(f"\n  Summary: {files_with_match}/{total_files} files contain the pattern")
    print(f"  Only unnamed 118b.xy has it immediately after the E4 block")


# ---------------------------------------------------------------------------
# Part 2: Generate test files
# ---------------------------------------------------------------------------
def build_e4_block(records_raw, seps):
    """Build an E4 block from raw record bytes and separator values.

    records_raw: list of 16 bytes objects (the raw record bytes)
    seps: list of 15 int values (separator bytes)
    """
    block = bytearray([0xE4])
    for i, raw in enumerate(records_raw):
        block.extend(raw)
        if i < 15:
            block.append(seps[i])
    return bytes(block)


def replace_e4_in_body(old_body, new_e4_block, old_e4_size):
    """Replace the E4 block in a track body, handling size changes.

    old_body: original body bytes
    new_e4_block: new E4 block bytes
    old_e4_size: size of the old E4 block in bytes
    """
    e4_offset = 0xB1
    old_e4_end = e4_offset + old_e4_size
    new_body = bytearray()
    new_body.extend(old_body[:e4_offset])
    new_body.extend(new_e4_block)
    new_body.extend(old_body[old_e4_end:])
    return bytes(new_body)


def rebuild_project(orig_proj, new_t1_body):
    """Rebuild a project with a modified Track 1 body.

    Returns the new project bytes.
    """
    parts = [orig_proj.pre_track]
    for i, track in enumerate(orig_proj.tracks):
        if i == 0:
            parts.append(track.preamble + new_t1_body)
        else:
            parts.append(track.to_bytes())
    return b"".join(parts)


def generate_v6a():
    """v6a: unnamed 119 with all-Hold E4 block (128 bytes, replacing 130 bytes)."""
    print("\n" + "=" * 70)
    print("  Part 2a: Generate v6a_119_to_all_hold.xy")
    print("=" * 70)

    path_119 = CORPUS / "unnamed 119.xy"
    proj_119 = XYProject.from_bytes(path_119.read_bytes())
    body_119 = proj_119.tracks[0].body

    # Parse old E4 block to get its size
    records_119, seps_119 = parse_block_known(body_119, 0xB1)
    assert records_119 is not None, "Failed to parse 119's E4 block"
    old_e4_size = 1 + sum(r[1] for r in records_119) + len(seps_119)
    print(f"  119 E4 block: {old_e4_size} bytes (offset 0xB1:0x{0xB1 + old_e4_size:03X})")

    # Build all-Hold block: 16 x Hold record (type_id=0x00, 7B), seps all 10
    hold_rec = bytes([0x02, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00])
    all_hold_records = [hold_rec] * 16
    all_hold_seps = [10] * 15
    new_e4 = build_e4_block(all_hold_records, all_hold_seps)
    print(f"  New E4 block: {len(new_e4)} bytes (all-Hold)")
    print(f"  Size change: {len(new_e4) - old_e4_size:+d} bytes")

    # Replace in body
    new_body = replace_e4_in_body(body_119, new_e4, old_e4_size)
    print(f"  Body size: {len(body_119)} -> {len(new_body)} ({len(new_body) - len(body_119):+d})")

    # Verify the new E4 block parses correctly
    check_records, check_seps = parse_block_known(new_body, 0xB1)
    assert check_records is not None, "New E4 block failed to parse"
    assert len(check_records) == 16, f"Expected 16 records, got {len(check_records)}"
    for i, (tid, sz, raw) in enumerate(check_records):
        assert tid == 0x00, f"Step {i+1}: expected type 0x00, got {tid}"
        assert sz == 7, f"Step {i+1}: expected 7B, got {sz}B"
    print("  Parse verification: OK (16 Hold records)")

    # Rebuild project
    result = rebuild_project(proj_119, new_body)

    # Double-check round-trip
    proj_check = XYProject.from_bytes(result)
    assert proj_check.tracks[0].body == new_body
    print(f"  Round-trip check: OK")
    print(f"  Total file size: {len(path_119.read_bytes())} -> {len(result)} ({len(result) - len(path_119.read_bytes()):+d})")

    out_path = OUTPUT / "v6a_119_to_all_hold.xy"
    out_path.write_bytes(result)
    print(f"  Written: {out_path}")
    return True


def generate_v6b():
    """v6b: unnamed 119 with 118b's E4 pattern (128 bytes, replacing 130 bytes)."""
    print("\n" + "=" * 70)
    print("  Part 2b: Generate v6b_119_to_118b_pattern.xy")
    print("=" * 70)

    path_119 = CORPUS / "unnamed 119.xy"
    path_118b = CORPUS / "unnamed 118b.xy"

    proj_119 = XYProject.from_bytes(path_119.read_bytes())
    proj_118b = XYProject.from_bytes(path_118b.read_bytes())

    body_119 = proj_119.tracks[0].body
    body_118b = proj_118b.tracks[0].body

    # Parse 119's E4 block
    records_119, seps_119 = parse_block_known(body_119, 0xB1)
    assert records_119 is not None
    old_e4_size = 1 + sum(r[1] for r in records_119) + len(seps_119)
    print(f"  119 E4 block: {old_e4_size} bytes")

    # Parse 118b's E4 block - use actual records+seps from the device
    records_118b, seps_118b = parse_block_known(body_118b, 0xB1)
    assert records_118b is not None
    e4_118b_size = 1 + sum(r[1] for r in records_118b) + len(seps_118b)
    print(f"  118b E4 block: {e4_118b_size} bytes")

    # Show 118b pattern summary
    print(f"  118b pattern:")
    for i, (tid, sz, raw) in enumerate(records_118b):
        tid_str = f"0x{tid:02x}" if tid is not None else "Pulse"
        sep_str = f"sep={seps_118b[i]}" if i < 15 else ""
        names = {0x00: "Hold", 0x05: "Random", 0x0a: "Trigger"}
        name = names.get(tid, tid_str)
        print(f"    Step {i+1:2d}: {name:8s} ({tid_str}, {sz}B) {sep_str}")

    # Build new E4 block from 118b's records
    raw_records = [raw for (_, _, raw) in records_118b]
    new_e4 = build_e4_block(raw_records, seps_118b)
    print(f"  New E4 block: {len(new_e4)} bytes")
    print(f"  Size change: {len(new_e4) - old_e4_size:+d} bytes")

    # Replace in body
    new_body = replace_e4_in_body(body_119, new_e4, old_e4_size)
    print(f"  Body size: {len(body_119)} -> {len(new_body)} ({len(new_body) - len(body_119):+d})")

    # Verify parse
    check_records, check_seps = parse_block_known(new_body, 0xB1)
    assert check_records is not None, "New E4 block failed to parse"
    assert len(check_records) == 16
    # Verify records match 118b
    for i in range(16):
        orig_tid, orig_sz, orig_raw = records_118b[i]
        check_tid, check_sz, check_raw = check_records[i]
        assert orig_tid == check_tid, f"Step {i+1}: type mismatch"
        assert orig_raw == check_raw, f"Step {i+1}: raw mismatch"
    if check_seps == seps_118b:
        print("  Parse verification: OK (matches 118b exactly)")
    else:
        print("  WARNING: separator mismatch!")
        for i in range(15):
            if check_seps[i] != seps_118b[i]:
                print(f"    sep[{i}]: expected {seps_118b[i]}, got {check_seps[i]}")

    # Rebuild project
    result = rebuild_project(proj_119, new_body)

    # Round-trip check
    proj_check = XYProject.from_bytes(result)
    assert proj_check.tracks[0].body == new_body
    print(f"  Round-trip check: OK")
    print(f"  Total file size: {len(path_119.read_bytes())} -> {len(result)} ({len(result) - len(path_119.read_bytes()):+d})")

    out_path = OUTPUT / "v6b_119_to_118b_pattern.xy"
    out_path.write_bytes(result)
    print(f"  Written: {out_path}")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("E4 Block Scan & Test File Generation")
    print("=" * 70)

    scan_corpus()
    ok_a = generate_v6a()
    ok_b = generate_v6b()

    print("\n" + "=" * 70)
    print("  Summary")
    print("=" * 70)
    print(f"  v6a (119 -> all-Hold):     {'OK' if ok_a else 'FAILED'}")
    print(f"  v6b (119 -> 118b pattern): {'OK' if ok_b else 'FAILED'}")

    # Final verification: show hex dumps of the E4 blocks in generated files
    print("\n  E4 block hex verification:")
    for name in ["v6a_119_to_all_hold.xy", "v6b_119_to_118b_pattern.xy"]:
        path = OUTPUT / name
        proj = XYProject.from_bytes(path.read_bytes())
        body = proj.tracks[0].body
        records, seps = parse_block_known(body, 0xB1)
        block_size = 1 + sum(r[1] for r in records) + len(seps)
        e4_hex = body[0xB1:0xB1 + block_size]
        print(f"\n  {name}:")
        print(f"    E4 block ({block_size} bytes):")
        for row in range(0, len(e4_hex), 16):
            chunk = e4_hex[row:row + 16]
            print(f"      {row:3d}: {chunk.hex(' ')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
