#!/usr/bin/env python3
"""Compare each delta_m*.xy against unnamed 118 and verify exact byte diffs.

For each file in output/multistep/delta_m*.xy:
1. Load it and unnamed 118 via XYProject
2. Extract Track 1 body (tracks[0].body)
3. Byte-by-byte diff
4. Classify each diff as bitmask, type_id, separator, or UNKNOWN
5. Confirm delta_m0_identity has ZERO diffs
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject

TEMPLATE = Path("src/one-off-changes-from-default/unnamed 118.xy")
DELTA_DIR = Path("output/multistep")

BLOCK_START = 0x00B1

def rec_offset(step_0based):
    """Body offset of record byte[0] for given step (0-based)."""
    return BLOCK_START + 1 + step_0based * 8

def sep_offset(sep_index):
    """Body offset of separator[i] (between record[i] and record[i+1])."""
    return BLOCK_START + 8 + sep_index * 8


def classify_offset(off):
    """Classify a body offset into bitmask, type_id, separator, or UNKNOWN."""
    # Check if it's a record bitmask (byte 0 of a record)
    for step in range(16):
        r = rec_offset(step)
        if off == r:
            return f"bitmask(step={step+1})"
        if off == r + 3:
            return f"type_id(step={step+1})"
        # Check other record bytes (1,2,4,5,6) as record fields
        if r < off < r + 7 and off != r + 3:
            field_off = off - r
            return f"rec_field(step={step+1},+{field_off})"

    # Check if it's a separator
    for i in range(15):
        s = sep_offset(i)
        if off == s:
            return f"separator(i={i})"

    return f"UNKNOWN(off={off:#06x})"


def main():
    # Load reference
    ref_data = TEMPLATE.read_bytes()
    ref_proj = XYProject.from_bytes(ref_data)
    ref_body = ref_proj.tracks[0].body

    # Find all delta_m*.xy files
    delta_files = sorted(DELTA_DIR.glob("delta_m*.xy"))
    if not delta_files:
        print("ERROR: No delta_m*.xy files found in", DELTA_DIR)
        sys.exit(1)

    print(f"Reference: {TEMPLATE} (Track 1 body = {len(ref_body)} bytes)")
    print(f"Found {len(delta_files)} delta test files\n")
    print("=" * 80)

    all_pass = True

    for fpath in delta_files:
        fname = fpath.name
        data = fpath.read_bytes()
        proj = XYProject.from_bytes(data)
        body = proj.tracks[0].body

        # Also check that non-track-1 data is identical
        # (preamble, other tracks, pre_track)
        other_diffs = []
        if proj.pre_track != ref_proj.pre_track:
            other_diffs.append("pre_track differs!")
        for i in range(16):
            if i == 0:
                # Check preamble only for track 0
                if proj.tracks[i].preamble != ref_proj.tracks[i].preamble:
                    other_diffs.append(f"track[{i}].preamble differs!")
            else:
                if proj.tracks[i].preamble != ref_proj.tracks[i].preamble:
                    other_diffs.append(f"track[{i}].preamble differs!")
                if proj.tracks[i].body != ref_proj.tracks[i].body:
                    other_diffs.append(f"track[{i}].body differs!")

        # Byte-by-byte diff of Track 1 body
        diffs = []
        if len(body) != len(ref_body):
            print(f"\n--- {fname} ---")
            print(f"  LENGTH MISMATCH: ref={len(ref_body)}, test={len(body)}")
            all_pass = False
            continue

        for offset in range(len(body)):
            if body[offset] != ref_body[offset]:
                classification = classify_offset(offset)
                diffs.append((offset, ref_body[offset], body[offset], classification))

        # Print results
        print(f"\n--- {fname} ---")
        print(f"  Total Track 1 body diffs: {len(diffs)}")

        if other_diffs:
            for od in other_diffs:
                print(f"  WARNING: {od}")

        if diffs:
            # Group by classification type
            bitmask_count = sum(1 for _, _, _, c in diffs if c.startswith("bitmask"))
            type_id_count = sum(1 for _, _, _, c in diffs if c.startswith("type_id"))
            sep_count = sum(1 for _, _, _, c in diffs if c.startswith("separator"))
            rec_field_count = sum(1 for _, _, _, c in diffs if c.startswith("rec_field"))
            unknown_count = sum(1 for _, _, _, c in diffs if c.startswith("UNKNOWN"))

            print(f"  Breakdown: {bitmask_count} bitmask, {type_id_count} type_id, "
                  f"{sep_count} separator, {rec_field_count} rec_field, {unknown_count} UNKNOWN")
            print()

            for offset, old_val, new_val, classification in diffs:
                print(f"    [{offset:#06x}] {old_val:#04x} -> {new_val:#04x}  {classification}")
        else:
            print("  (no diffs - byte-identical to unnamed 118)")

    # --- Verification summary ---
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    # Expected diffs per file (from write_delta_tests_v2.py logic)
    expected = {
        "delta_m0_identity.xy": {
            "total": 0,
            "bitmask": 0,
            "type_id": 0,
            "separator": 0,
        },
        "delta_m1_type_and_seps.xy": {
            "total": 1 + 12,  # 1 type_id + 12 sep changes (seps 3-14 where != 10)
            "type_id": 1,
            # formula_seps = [10,10,10,9,8,8,8,8,8,8,8,8,8,8,8] -> 12 non-10 values at i=3..14
            "separator": 12,
            "bitmask": 0,
        },
        "delta_m2_all_bitmasks.xy": {
            # STEP_BITMASK = [1<<(i%8) for i in range(16)] = [1,2,4,8,16,32,64,128,1,2,4,8,16,32,64,128]
            # unnamed 118 uses 0x02 for all; step 1 (idx 9): 0x02 != 0x01 YES
            # step 2: 0x02 == 0x02 NO ... so 14 steps differ
            "total": 14,
            "bitmask": 14,
            "type_id": 0,
            "separator": 0,
        },
        "delta_m3_s16_type_and_sep.xy": {
            "total": 2,  # 1 type_id + 1 sep
            "type_id": 1,
            "separator": 1,
            "bitmask": 0,
        },
        "delta_m4_s16_type_only.xy": {
            "total": 1,
            "type_id": 1,
            "separator": 0,
            "bitmask": 0,
        },
        "delta_m5_full_formula.xy": {
            # 1 bitmask + 1 type_id + 12 seps
            "total": 1 + 1 + 12,
            "bitmask": 1,
            "type_id": 1,
            "separator": 12,
        },
        "delta_m6_seps_after_only.xy": {
            # 1 bitmask + 1 type_id + 11 seps (i=4..14)
            "total": 1 + 1 + 11,
            "bitmask": 1,
            "type_id": 1,
            "separator": 11,
        },
        "delta_m7_flanking_seps.xy": {
            # 1 type_id + 2 seps
            "total": 3,
            "type_id": 1,
            "separator": 2,
            "bitmask": 0,
        },
    }

    for fpath in delta_files:
        fname = fpath.name
        data = fpath.read_bytes()
        proj = XYProject.from_bytes(data)
        body = proj.tracks[0].body

        diffs = []
        for offset in range(len(body)):
            if body[offset] != ref_body[offset]:
                classification = classify_offset(offset)
                diffs.append((offset, ref_body[offset], body[offset], classification))

        bitmask_count = sum(1 for _, _, _, c in diffs if c.startswith("bitmask"))
        type_id_count = sum(1 for _, _, _, c in diffs if c.startswith("type_id"))
        sep_count = sum(1 for _, _, _, c in diffs if c.startswith("separator"))
        unknown_count = sum(1 for _, _, _, c in diffs if c.startswith("UNKNOWN"))
        rec_field_count = sum(1 for _, _, _, c in diffs if c.startswith("rec_field"))

        if fname in expected:
            exp = expected[fname]
            checks = []
            ok = True

            if len(diffs) != exp["total"]:
                checks.append(f"total: expected {exp['total']}, got {len(diffs)}")
                ok = False
            if bitmask_count != exp["bitmask"]:
                checks.append(f"bitmask: expected {exp['bitmask']}, got {bitmask_count}")
                ok = False
            if type_id_count != exp["type_id"]:
                checks.append(f"type_id: expected {exp['type_id']}, got {type_id_count}")
                ok = False
            if sep_count != exp["separator"]:
                checks.append(f"separator: expected {exp['separator']}, got {sep_count}")
                ok = False
            if unknown_count > 0:
                checks.append(f"UNKNOWN diffs: {unknown_count}")
                ok = False
            if rec_field_count > 0:
                checks.append(f"rec_field diffs: {rec_field_count}")
                ok = False

            status = "PASS" if ok else "FAIL"
            if not ok:
                all_pass = False
            print(f"  {fname:40s} [{status}]", end="")
            if checks:
                print(f"  -- {'; '.join(checks)}")
            else:
                print()
        else:
            print(f"  {fname:40s} [NO EXPECTED DATA]")

    print()
    if all_pass:
        print("ALL TESTS PASSED - every delta file has exactly the expected changes.")
    else:
        print("SOME TESTS FAILED - see details above.")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
