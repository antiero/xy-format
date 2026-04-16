#!/usr/bin/env python3
"""Verify the multi-step separator formula against unnamed 118 and 119.

Formula:
  sep[0] = 11 if step 1 is Pulse (no type_id), else 10
  sep[i] (i >= 1) = sep[i-1]          if step(i+1) same (type_id, size) as step(i+2)
                  = max(sep[i-1]-1,0)  otherwise
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject

CORPUS = Path("src/one-off-changes-from-default")


def parse_multistep_block(body, offset=0xB1):
    """Parse the 16-step multi-step block starting at body[offset].

    Returns list of (type_id_or_None, record_bytes) and list of separator values.
    """
    pos = offset
    header = body[pos]
    assert header == 0xE4, f"Expected 0xE4 header, got {header:#04x}"
    pos += 1

    records = []
    seps = []

    for step_idx in range(16):
        # Determine record size by examining the record
        # Pulse: 5B — starts with bitmask, then 00, param, 00, 00
        #   Pulse detection: byte[3] is NOT a valid type_id pattern
        #   Actually, Pulse has no type_id field. Format: [bm][00][param][00][00]
        #   Standard 7B: [bm][00][00][type_id][data][00][00]
        #
        # We need to figure out record size. The challenge is that records are
        # variable-length. Let's use the known structure:
        #
        # For standard records: byte[1]=00, byte[2]=00, byte[3]=type_id
        # For Pulse: byte[1]=00, byte[2]=param (could be 00), byte[3]=00, byte[4]=00
        #
        # Key insight: in standard records, byte[3] is the type_id (0x00-0x0A).
        # In Pulse, byte[3] is always 0x00 and byte[4] is always 0x00.
        # But Hold also has type_id=0x00! So we can't distinguish by byte[3] alone.
        #
        # Better approach: Pulse has byte[1]=0x00, byte[2]=param (0x00-0x04 observed),
        # and byte[3]=0x00, byte[4]=0x00. Standard has byte[1]=0x00, byte[2]=0x00.
        # So byte[2] != 0x00 indicates Pulse with a non-zero param.
        # But byte[2]=0x00 could be either Pulse(param=0) or Standard.
        #
        # Actually, let's use a different approach. We know the sizes from the type system:
        # - If we can identify Pulse vs Standard, we know the size.
        #
        # From unnamed 119, the block has known structure. Let me just parse it
        # by trying each possible size and seeing what makes the separators land correctly.
        #
        # SIMPLEST APPROACH: use the fact that separators are single bytes with values
        # 0x00-0x0B, and records have specific patterns. Parse greedily.

        rec_start = pos

        # Look at bytes to determine record type and size
        bm = body[pos]
        b1 = body[pos + 1]
        b2 = body[pos + 2]
        b3 = body[pos + 3]
        b4 = body[pos + 4]

        # Pulse detection: 5B record where byte[2] is the param and bytes[3:5] = 00 00
        # But we need a reliable way to distinguish 5B Pulse from 7B Standard.
        #
        # Key: in Standard 7B, the layout is [bm][00][00][type_id][data...][00][00]
        # So byte[1]=0x00 and byte[2]=0x00 always for Standard.
        # In Pulse 5B, layout is [bm][00][param][00][00]
        # So byte[1]=0x00, byte[2]=param.
        #
        # If byte[2] != 0x00 → Pulse (param != 0)
        # If byte[2] == 0x00 → could be Standard OR Pulse(param=0)
        #
        # For Pulse(param=0): [bm][00][00][00][00] = 5B
        # For Standard(Hold): [bm][00][00][00][data][00][00] = 7B
        #
        # We can check byte[4]: in Pulse, it's always 0x00 (last byte).
        # In Standard Hold, byte[4] is the first data byte (typically 0x01-0x08).
        # But what if Standard Hold has data byte 0x00? That seems unlikely but possible.
        #
        # Alternative: check if byte at pos+5 (which would be byte[5] of a 7B record
        # or a separator after a 5B record) looks like a separator (0x00-0x0B).
        #
        # This is getting complicated. Let me use a known-structure approach for the
        # two specimen files.
        pass

    # Instead of the complex parsing above, let me parse using known offsets
    # from the hex dumps analyzed in previous sessions.
    return None, None


def parse_block_known(body, offset=0xB1):
    """Parse multi-step block using backtracking with type-aware size constraints.

    Type_id → valid sizes:
      Pulse (no type_id): 5B
      0x00-0x06: 7B only
      0x07: 7B (Tonality) or 9B (Jump)
      0x08: 8B (Parameter)
      0x09: 9B (Conditional)
      0x0a: 7B or 8B (Trigger variants)
    """
    assert body[offset] == 0xE4, f"Expected 0xE4, got {body[offset]:#04x}"
    start = offset + 1

    TYPE_SIZES = {
        0x00: [7], 0x01: [7], 0x02: [7], 0x03: [7], 0x04: [7],
        0x05: [7], 0x06: [7], 0x07: [7, 9], 0x08: [8], 0x09: [9],
        0x0a: [7, 8],
    }
    VALID_SEP = set(range(12))  # 0x00-0x0B

    def solve(step, pos):
        """Recursively parse step records with backtracking."""
        if step == 16:
            return [], []

        candidates = []

        # Check Pulse (5B): [bm][00][param][00][00]
        if (pos + 5 <= len(body) and
            body[pos + 1] == 0x00 and
            body[pos + 3] == 0x00 and
            body[pos + 4] == 0x00):
            candidates.append((None, 5))

        # Check Standard: [bm][00][00][type_id][...][00...]
        if (pos + 7 <= len(body) and
            body[pos + 1] == 0x00 and
            body[pos + 2] == 0x00):
            type_id = body[pos + 3]
            if type_id <= 0x0A:
                for size in TYPE_SIZES.get(type_id, [7]):
                    if pos + size <= len(body):
                        candidates.append((type_id, size))

        for type_id, size in candidates:
            rec = body[pos:pos + size]

            if step < 15:
                if pos + size >= len(body):
                    continue
                sep = body[pos + size]
                if sep not in VALID_SEP:
                    continue
                result = solve(step + 1, pos + size + 1)
                if result is not None:
                    recs, seps = result
                    recs.insert(0, (type_id, size, rec))
                    seps.insert(0, sep)
                    return recs, seps
            else:
                # Last step — no separator after
                return [(type_id, size, rec)], []

        return None

    result = solve(0, start)
    return result if result else (None, None)


def compute_seps(records):
    """Compute predicted separator values using our formula.

    records: list of (type_id_or_None, size, raw_bytes)
    Returns: list of 15 predicted separator values
    """
    pred = []

    # sep[0]: 11 if step 1 is Pulse, 10 if standard
    if records[0][0] is None:  # Pulse
        pred.append(11)
    else:
        pred.append(10)

    # sep[i] for i >= 1
    for i in range(1, 15):
        left = records[i]      # step i+1 (1-indexed)
        right = records[i + 1]  # step i+2 (1-indexed)

        left_type, left_size = left[0], left[1]
        right_type, right_size = right[0], right[1]

        if left_type == right_type and left_size == right_size:
            pred.append(pred[-1])  # hold
        else:
            pred.append(max(pred[-1] - 1, 0))  # decrement

    return pred


def analyze_file(name, path):
    """Analyze a single .xy file's multi-step block."""
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    data = path.read_bytes()
    proj = XYProject.from_bytes(data)
    body = proj.tracks[0].body

    # Check for multi-step block header
    if body[0xB1] != 0xE4:
        print(f"  No multi-step block (header={body[0xB1]:#04x})")
        return False

    records, actual_seps = parse_block_known(body)
    if records is None:
        return False

    print(f"\n  Step  Type  Size  Record Hex                        Sep")
    print(f"  {'─'*70}")
    for i, (type_id, size, raw) in enumerate(records):
        type_str = f"0x{type_id:02x}" if type_id is not None else "Pulse"
        sep_str = f"{actual_seps[i]:3d}" if i < 15 else "  -"
        print(f"  {i+1:3d}   {type_str:5s}  {size}B   {raw.hex(' '):<36s}  {sep_str}")

    # Compute predicted separators
    pred_seps = compute_seps(records)

    print(f"\n  Separator Comparison:")
    print(f"  {'Sep':>5s}  {'Actual':>6s}  {'Pred':>6s}  {'Match':>5s}  Rule")
    print(f"  {'─'*55}")

    matches = 0
    for i in range(15):
        match = "✓" if actual_seps[i] == pred_seps[i] else "✗"
        if actual_seps[i] == pred_seps[i]:
            matches += 1

        # Explain the rule
        if i == 0:
            type_id = records[0][0]
            rule = f"11 - (1 if std else 0) = {pred_seps[i]} [step 1 {'Pulse' if type_id is None else 'standard'}]"
        else:
            lt, ls = records[i][0], records[i][1]
            rt, rs = records[i+1][0], records[i+1][1]
            lt_str = f"0x{lt:02x}" if lt is not None else "Pulse"
            rt_str = f"0x{rt:02x}" if rt is not None else "Pulse"
            same = lt == rt and ls == rs
            if same:
                rule = f"HOLD ({lt_str},{ls}B) = ({rt_str},{rs}B)"
            else:
                diff_parts = []
                if lt != rt:
                    diff_parts.append(f"type {lt_str}≠{rt_str}")
                if ls != rs:
                    diff_parts.append(f"size {ls}≠{rs}")
                rule = f"DEC  {', '.join(diff_parts)}"

        print(f"  [{i:2d}]  {actual_seps[i]:6d}  {pred_seps[i]:6d}  {match:>5s}  {rule}")

    print(f"\n  Result: {matches}/15 separators match")
    return matches == 15


def main():
    print("=" * 60)
    print("  Multi-Step Separator Formula Verification")
    print("=" * 60)
    print()
    print("Formula:")
    print("  sep[0] = 11 if step 1 is Pulse, 10 if standard")
    print("  sep[i] = sep[i-1]          if step(i+1) matches step(i+2)")
    print("         = max(sep[i-1]-1,0) otherwise")
    print("  Match = same type_id AND same record size")

    results = {}

    for num in [118, 119]:
        path = CORPUS / f"unnamed {num}.xy"
        if path.exists():
            ok = analyze_file(f"unnamed {num}", path)
            results[num] = ok
        else:
            print(f"\n  WARNING: {path} not found")

    # Also verify generated test files
    test_dir = Path("output/multistep")
    for path in sorted(test_dir.glob("ms_t*.xy")):
        ok = analyze_file(path.stem, path)
        results[path.stem] = ok

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    for num, ok in results.items():
        print(f"  unnamed {num}: {'PASS (15/15)' if ok else 'FAIL'}")

    all_pass = all(results.values())
    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
