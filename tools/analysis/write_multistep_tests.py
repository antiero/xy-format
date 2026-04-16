#!/usr/bin/env python3
"""Multi-step device tests — files with correctly computed separator bytes.

Uses the verified separator formula to create mixed-type multi-step blocks
from the unnamed 118 baseline (all-Hold). Each test modifies step records
AND recomputes all separators to match.

Separator formula (verified 30/30 on unnamed 118 + 119):
  sep[0] = 11 if step 1 is Pulse, 10 if standard
  sep[i] = sep[i-1]          if step(i+1) matches step(i+2) in (type_id, size)
         = max(sep[i-1]-1, 0) otherwise
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject, TrackBlock

TEMPLATE = Path("src/one-off-changes-from-default/unnamed 118.xy")
OUTPUT_DIR = Path("output/multistep")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load unnamed 118 — known-working all-Hold multi-step project
source = XYProject.from_bytes(TEMPLATE.read_bytes())
source_body = source.tracks[0].body

BLOCK_START = 0x00B1

# Record templates for each type
# Format: (type_id_or_None, size, bytes)
# bitmask will be filled in per-step
RECORDS = {
    "Pulse":       (None, 5,  bytes([0x00, 0x00, 0x04, 0x00, 0x00])),
    "Hold":        (0x00, 7,  bytes([0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00])),
    "Multiply":    (0x01, 7,  bytes([0x00, 0x00, 0x00, 0x01, 0x02, 0x00, 0x00])),
    "Velocity":    (0x02, 7,  bytes([0x00, 0x00, 0x00, 0x02, 0x05, 0x00, 0x00])),
    "RampUp":      (0x03, 7,  bytes([0x00, 0x00, 0x00, 0x03, 0x04, 0x00, 0x00])),
    "RampDown":    (0x04, 7,  bytes([0x00, 0x00, 0x00, 0x04, 0x04, 0x00, 0x00])),
    "Random":      (0x05, 7,  bytes([0x00, 0x00, 0x00, 0x05, 0x04, 0x00, 0x00])),
    "Portamento":  (0x06, 7,  bytes([0x00, 0x00, 0x00, 0x06, 0x04, 0x00, 0x00])),
    "Bend":        (0x06, 7,  bytes([0x00, 0x00, 0x00, 0x06, 0x01, 0x00, 0x00])),
    "Tonality":    (0x07, 7,  bytes([0x00, 0x00, 0x00, 0x07, 0x04, 0x00, 0x00])),
    "Jump":        (0x07, 9,  bytes([0x00, 0x00, 0x00, 0x07, 0x04, 0x04, 0x00, 0x00, 0x00])),
    "Parameter":   (0x08, 8,  bytes([0x00, 0x00, 0x00, 0x08, 0x04, 0x02, 0x00, 0x00])),
    "Conditional": (0x09, 9,  bytes([0x00, 0x00, 0x00, 0x09, 0x02, 0x02, 0x00, 0x00, 0x00])),
    "TriggerA":    (0x0a, 7,  bytes([0x00, 0x00, 0x00, 0x0a, 0x02, 0x02, 0x00])),
    "TriggerB":    (0x0a, 8,  bytes([0x00, 0x00, 0x00, 0x0a, 0x02, 0x02, 0x00, 0x01])),
}

# Step bitmasks: step 1-8 use bits 0-7, step 9-16 repeat bits 0-7
STEP_BITMASK = [1 << (i % 8) for i in range(16)]


def compute_separators(steps):
    """Compute separator bytes for a list of 16 step records.

    steps: list of (type_id_or_None, size) tuples
    Returns: list of 15 separator values
    """
    seps = []

    # sep[0]: 11 if Pulse, 10 if standard
    if steps[0][0] is None:
        seps.append(11)
    else:
        seps.append(10)

    # sep[i] for i >= 1
    for i in range(1, 15):
        left_type, left_size = steps[i]
        right_type, right_size = steps[i + 1]

        if left_type == right_type and left_size == right_size:
            seps.append(seps[-1])  # HOLD
        else:
            seps.append(max(seps[-1] - 1, 0))  # DECREMENT

    return seps


def build_block(step_names):
    """Build a multi-step block from a list of 16 step type names.

    Returns the full block bytes (0xE4 header + records + separators).
    """
    assert len(step_names) == 16

    # Resolve records
    steps = []
    for i, name in enumerate(step_names):
        type_id, size, template = RECORDS[name]
        rec = bytearray(template)
        rec[0] = STEP_BITMASK[i]  # set bitmask
        steps.append((type_id, size, bytes(rec)))

    # Compute separators
    step_sigs = [(type_id, size) for type_id, size, _ in steps]
    seps = compute_separators(step_sigs)

    # Assemble block
    block = bytearray([0xE4])
    for i, (_, _, rec) in enumerate(steps):
        block.extend(rec)
        if i < 15:
            block.append(seps[i])

    return bytes(block), seps


def make_test(name, desc, step_names):
    """Create a test file with the given step configuration."""
    block, seps = build_block(step_names)

    # The original block region in the body
    # unnamed 118 block: E4 + 16*7B + 15 seps = 1 + 112 + 15 = 128 bytes
    orig_block_start = BLOCK_START
    orig_block_size = 1 + 16 * 7 + 15  # 128 bytes for all-7B

    # New block might be different size due to variable-length records
    new_block = block

    # Replace the block in the body
    body = bytearray(source_body)
    body[orig_block_start:orig_block_start + orig_block_size] = new_block

    # Rebuild project
    tracks = list(source.tracks)
    tracks[0] = TrackBlock(
        index=tracks[0].index,
        preamble=tracks[0].preamble,
        body=bytes(body),
    )
    proj = XYProject(pre_track=source.pre_track, tracks=tracks)
    data = proj.to_bytes()
    outpath = OUTPUT_DIR / f"{name}.xy"
    outpath.write_bytes(data)

    # Print summary
    print(f"\n  {outpath.name} ({len(data)}B)")
    print(f"  {desc}")
    for i, sname in enumerate(step_names):
        type_id, size, _ = RECORDS[sname]
        type_str = f"0x{type_id:02x}" if type_id is not None else "---"
        sep_str = f"sep={seps[i]:2d}" if i < 15 else "     "
        print(f"    Step {i+1:2d}: {sname:12s} type={type_str} {size}B  {sep_str}")


def main():
    print("=" * 60)
    print("  Multi-Step Device Tests (formula-computed separators)")
    print("=" * 60)

    # Test 1: Single Random on step 5 (simplest mixed case)
    steps = ["Hold"] * 16
    steps[4] = "Random"
    make_test("ms_t1_random_s5", "Single Random on step 5, rest Hold", steps)

    # Test 2: Two different types (Random s5, Multiply s10)
    steps = ["Hold"] * 16
    steps[4] = "Random"
    steps[9] = "Multiply"
    make_test("ms_t2_two_types", "Random(s5) + Multiply(s10), rest Hold", steps)

    # Test 3: Pulse on step 1 (changes sep[0] from 10 to 11)
    steps = ["Hold"] * 16
    steps[0] = "Pulse"
    make_test("ms_t3_pulse_s1", "Pulse on step 1, rest Hold", steps)

    # Test 4: Adjacent different types (tests consecutive decrements)
    steps = ["Hold"] * 16
    steps[0] = "Pulse"
    steps[1] = "Multiply"
    steps[2] = "Velocity"
    steps[3] = "RampUp"
    make_test("ms_t4_four_diff", "Pulse+Multiply+Velocity+RampUp on s1-4", steps)

    # Test 5: Two adjacent same types (tests HOLD rule)
    steps = ["Hold"] * 16
    steps[4] = "Random"
    steps[5] = "Random"
    make_test("ms_t5_hold_test", "Two adjacent Random (s5+s6), should HOLD sep", steps)

    # Test 6: Reproduce unnamed 119 exactly (gold standard)
    steps_119 = [
        "Pulse", "Hold", "Multiply", "Velocity",
        "RampUp", "RampDown", "Random", "Portamento",
        "Bend", "Tonality", "Jump", "Parameter",
        "Conditional", "TriggerB", "TriggerA", "Pulse",
    ]
    make_test("ms_t6_all_types", "All 14 UI types (reproduces unnamed 119 structure)", steps_119)

    print(f"\n{'='*60}")
    print(f"  Test Priority:")
    print(f"    ms_t1 — simplest mixed (1 type change)")
    print(f"    ms_t3 — Pulse on step 1 (sep[0]=11)")
    print(f"    ms_t5 — HOLD rule (adjacent same types)")
    print(f"    ms_t2 — two different types")
    print(f"    ms_t4 — consecutive decrements")
    print(f"    ms_t6 — all 14 types (full validation)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
