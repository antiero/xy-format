#!/usr/bin/env python3
"""Step Component Diagnostic — generates .xy files for device name verification.

Each file places a single step component on step 9 of T1 (Drum) or T3 (Prism),
along with a note on step 9 so the component effect is audible. Load on the
OP-XY, navigate to the step component view for step 9, and check what the device
displays.

PROPOSED mapping (from cross-referencing corpus hex with device UI changelog):

  BANK 1 (step_byte 0x63 for step 9):
    #01  bit 0  Pulse      (3B)         unnamed 59  repeat 1x
    #02  bit 0  Pulse Max  (1B)         unnamed 60  random repeats
    #03  bit 1  Hold       (5B id=00)   unnamed 61  minimum
    #04  bit 2  Multiply   (5B id=01)   unnamed 66  /4
    #05  bit 3  Velocity   (1B)         unnamed 67  random
    #06  bit 4  Ramp Up    (5B id=03)   unnamed 68  amount 8
    #07  bit 5  Ramp Down  (5B id=04)   unnamed 69  amount 2
    #08  bit 6  Random     (5B id=05)   unnamed 70  amount 3
    #09  bit 7  Portamento (5B id=06)   unnamed 71  70%

  BANK 2 (step_byte 0x64 for step 9):
    #10  bit 0  Bend        (5B id=06)  unnamed 72  amount 1
    #11  bit 1  Tonality    (5B id=07)  unnamed 73  amount 4
    #12  bit 2  Jump        (5B id=08)  unnamed 74  step 4
    #13  bit 3  Parameter   (5B id=09)  unnamed 75  amount 4
    #14  bit 4  Conditional (5B id=0a)  unnamed 76  skip 2
    #15  bit 5  Type14(?)   (5B id=0b)  unnamed 77  param 9

What our code CURRENTLY maps (WRONG for most types):
    Code "VELOCITY"    (bit 1) = proposed "Hold"
    Code "BEND"        (bit 3) = proposed "Velocity"
    Code "TONALITY"    (bit 4) = proposed "Ramp Up"
    Code "JUMP"        (bit 5) = proposed "Ramp Down"
    Code "PARAMETER"   (bit 6) = proposed "Random"
    Code "COMPONENT"   (bit 7) = proposed "Portamento"
    Code has NO bank 2 support.

Usage:
    python tools/write_step_comp_diag.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xy.container import XYProject, TrackBlock
from xy.note_events import Note, build_event, event_type_for_track
from xy.project_builder import _activate_body, append_notes_to_tracks

TEMPLATE = Path("src/one-off-changes-from-default/unnamed 1.xy")
CORPUS = Path("src/one-off-changes-from-default")
OUTPUT_DIR = Path("output/sc_diag")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Component definitions ─────────────────────────────────────────────
# (name, bank, bitpos, payload_size, type_id, param, description, corpus_file)
COMPONENTS = [
    # Bank 1 (step_byte nibble=3 for step 9)
    ("01_pulse",      1, 0, 3, -1,   0x01, "Pulse: 1x repeat",             59),
    ("02_pulse_max",  1, 0, 1, -1,   0x00, "Pulse Max: random repeats",    60),
    ("03_hold",       1, 1, 5, 0x00, 0x01, "Hold: minimum",                61),
    ("04_multiply",   1, 2, 5, 0x01, 0x04, "Multiply: /4",                 66),
    ("05_velocity",   1, 3, 1, -1,   0x00, "Velocity: random",             67),
    ("06_ramp_up",    1, 4, 5, 0x03, 0x08, "Ramp Up: amount 8",            68),
    ("07_ramp_down",  1, 5, 5, 0x04, 0x02, "Ramp Down: amount 2",          69),
    ("08_random",     1, 6, 5, 0x05, 0x03, "Random: amount 3",             70),
    ("09_portamento", 1, 7, 5, 0x06, 0x07, "Portamento: 70%",              71),
    # Bank 2 (step_byte nibble=4 for step 9)
    ("10_bend",        2, 0, 5, 0x06, 0x01, "Bend: amount 1",              72),
    ("11_tonality",    2, 1, 5, 0x07, 0x04, "Tonality: amount 4",          73),
    ("12_jump",        2, 2, 5, 0x08, 0x04, "Jump: step 4",                74),
    ("13_parameter",   2, 3, 5, 0x09, 0x04, "Parameter: amount 4",         75),
    ("14_conditional", 2, 4, 5, 0x0a, 0x02, "Conditional: skip 2",         76),
    ("15_type14",      2, 5, 5, 0x0b, 0x09, "Type14(?): param 9",          77),
]

# Extra param variations for subsetting verification
PARAM_VARIANTS = [
    # (name, bank, bitpos, payload_size, type_id, param, description)
    ("01_pulse_p3",       1, 0, 3, -1,   0x03, "Pulse: 3x repeats"),
    ("01_pulse_p7",       1, 0, 3, -1,   0x07, "Pulse: 7x repeats"),
    ("04_multiply_p2",    1, 2, 5, 0x01, 0x02, "Multiply: /2"),
    ("04_multiply_p8",    1, 2, 5, 0x01, 0x08, "Multiply: /8"),
    ("14_conditional_p1", 2, 4, 5, 0x0a, 0x01, "Conditional: param 1"),
    ("14_conditional_p4", 2, 4, 5, 0x0a, 0x04, "Conditional: param 4"),
    ("09_portamento_p3",  1, 7, 5, 0x06, 0x03, "Portamento: 30%"),
]

# Engine configs for track testing
ENGINE_BASELINE_ALLOC = {
    0x03: 0xDF,  # Drum
    0x12: 0xDE,  # Prism
}
TABLE_START = {
    0x03: 0x0024,  # Drum
    0x12: 0x0024,  # Prism (same as Drum)
}


# ── Raw byte construction (bypasses broken step_components.py) ─────────

def build_raw_component_data(bank, bitpos, payload_size, type_id, param):
    """Build raw step component bytes for step 9.

    Returns bytes that REPLACE the 3-byte ff 00 00 slot entry.
    Layout: header(3B) + payload(1/3/5B) + sentinels((slot_idx-5)*3B).
    """
    step_0 = 8  # step 9 → 0-indexed = 8
    nibble = 3 if bank == 1 else 4
    step_byte = ((0xE - step_0) << 4) | nibble
    bitmask = 1 << bitpos

    header = bytes([step_byte, bitmask, 0x00])

    if payload_size == 1:
        payload = bytes([param & 0xFF])
    elif payload_size == 3:
        payload = bytes([param & 0xFF, 0x00, 0x00])
    elif payload_size == 5:
        payload = bytes([0x00, type_id & 0xFF, param & 0xFF, 0x00, 0x00])
    else:
        raise ValueError(f"unexpected payload_size {payload_size}")

    # Step 9 → slot_index=6, so 1 trailing sentinel
    sentinels = b'\xff\x00\x00'

    return header + payload + sentinels


def compute_raw_alloc_byte(bank, bitpos, payload_size, engine_id):
    """Compute the alloc marker byte value.

    5B/3B: 0x77 - abs_bit  where abs_bit = (bank-1)*8 + bitpos
    1B:    0x79
    Adjusted by engine offset (0xDF - engine_baseline_alloc).
    """
    if payload_size == 1:
        base = 0x79
    else:
        abs_bit = (bank - 1) * 8 + bitpos
        base = 0x77 - abs_bit
    engine_baseline = ENGINE_BASELINE_ALLOC.get(engine_id, 0xDF)
    offset = 0xDF - engine_baseline
    return (base - offset) & 0xFF


def insert_component_raw(project, track_num, bank, bitpos, payload_size,
                         type_id, param):
    """Insert a raw step component on step 9 of the given track."""
    idx = track_num - 1
    tracks = list(project.tracks)
    target = tracks[idx]
    engine_id = target.engine_id

    new_body = _activate_body(target.body)

    table_start = TABLE_START.get(engine_id, 0x0024)
    slot_abs = 42 + 6  # step_comp_slot_offset + slot_index(step 9)
    replace_offset = table_start + slot_abs * 3

    data = build_raw_component_data(bank, bitpos, payload_size, type_id, param)
    new_body[replace_offset:replace_offset + 3] = data
    net_growth = len(data) - 3

    alloc_baseline_offset = table_start + 55 * 3
    alloc_offset = alloc_baseline_offset + net_growth
    alloc_byte = compute_raw_alloc_byte(bank, bitpos, payload_size, engine_id)
    if alloc_offset < len(new_body):
        new_body[alloc_offset] = alloc_byte

    tracks[idx] = TrackBlock(
        index=target.index,
        preamble=target.preamble,
        body=bytes(new_body),
    )
    return XYProject(pre_track=project.pre_track, tracks=tracks)


# ── Corpus verification ───────────────────────────────────────────────

def verify_corpus():
    """Verify raw byte construction against corpus specimens."""
    baseline = XYProject.from_bytes(TEMPLATE.read_bytes())
    print("=" * 70)
    print("  CORPUS VERIFICATION (component-only, no notes)")
    print("=" * 70)

    pass_count = 0
    fail_count = 0
    skip_count = 0

    for name, bank, bitpos, payload_size, type_id, param, desc, corpus_num in COMPONENTS:
        corpus_file = CORPUS / f"unnamed {corpus_num}.xy"
        if not corpus_file.exists():
            print(f"  SKIP  {name:22s}  unnamed {corpus_num} not found")
            skip_count += 1
            continue

        # Generate component-only file
        proj = insert_component_raw(baseline, 1, bank, bitpos, payload_size,
                                    type_id, param)
        generated = proj.to_bytes()
        specimen = corpus_file.read_bytes()

        if generated == specimen:
            print(f"  PASS  {name:22s}  byte-perfect vs unnamed {corpus_num}")
            pass_count += 1
        else:
            diff_size = len(generated) - len(specimen)
            print(f"  FAIL  {name:22s}  unnamed {corpus_num}  "
                  f"(gen={len(generated)}, spec={len(specimen)}, "
                  f"delta={diff_size:+d})")
            fail_count += 1

    print(f"\n  Results: {pass_count} PASS, {fail_count} FAIL, {skip_count} SKIP")
    return fail_count == 0


# ── Diagnostic file generation ────────────────────────────────────────

def generate_diagnostic_files(baseline):
    """Generate .xy files with note + component for device testing."""
    KICK = 48   # C3 drum kick
    SNARE = 50  # Snare
    C4 = 60     # C4 for synth
    E4 = 64     # E4 for synth

    # Notes on BOTH step 1 and step 9 — the event format requires
    # the first note at tick 0 (flag 0x02). A single note at step 9
    # puts a non-zero tick as the first entry, which the firmware skips.
    track_configs = [
        (1, "t1", [Note(step=1, note=KICK, velocity=80),
                   Note(step=9, note=SNARE, velocity=100)]),
        (3, "t3", [Note(step=1, note=C4, velocity=80),
                   Note(step=9, note=E4, velocity=100)]),
    ]

    manifest = []

    # Main components (one per type per track)
    for name, bank, bitpos, payload_size, type_id, param, desc, _ in COMPONENTS:
        for track_num, track_label, notes in track_configs:
            # Step 1: insert component into baseline
            proj = insert_component_raw(baseline, track_num, bank, bitpos,
                                        payload_size, type_id, param)
            # Step 2: append note on step 9
            proj = append_notes_to_tracks(proj, {track_num: notes})

            fname = f"sc_{name}_{track_label}.xy"
            data = proj.to_bytes()
            (OUTPUT_DIR / fname).write_bytes(data)
            manifest.append((fname, track_label.upper(), desc))

    # Param variations (T1 only, to keep count manageable)
    for name, bank, bitpos, payload_size, type_id, param, desc in PARAM_VARIANTS:
        track_num = 1
        notes = [Note(step=1, note=KICK, velocity=80),
                 Note(step=9, note=SNARE, velocity=100)]
        proj = insert_component_raw(baseline, track_num, bank, bitpos,
                                    payload_size, type_id, param)
        proj = append_notes_to_tracks(proj, {track_num: notes})

        fname = f"sc_{name}_t1.xy"
        data = proj.to_bytes()
        (OUTPUT_DIR / fname).write_bytes(data)
        manifest.append((fname, "T1", f"{desc} [param variant]"))

    # Control files (note only, no component)
    for track_num, track_label, notes in track_configs:
        proj = append_notes_to_tracks(baseline, {track_num: notes})
        fname = f"sc_00_control_{track_label}.xy"
        data = proj.to_bytes()
        (OUTPUT_DIR / fname).write_bytes(data)
        manifest.append((fname, track_label.upper(), "Control: note only"))

    return manifest


def main():
    baseline = XYProject.from_bytes(TEMPLATE.read_bytes())

    # Corpus verification
    all_pass = verify_corpus()
    print()

    if not all_pass:
        print("  WARNING: Not all corpus specimens matched.")
        print("  Generating diagnostic files anyway (bytes may differ for Multiply).")
        print()

    # Generate diagnostic files
    print("=" * 70)
    print("  DIAGNOSTIC FILE GENERATION")
    print("=" * 70)
    manifest = generate_diagnostic_files(baseline)
    print(f"\n  Generated {len(manifest)} files in {OUTPUT_DIR}/\n")

    # Print manifest grouped by priority
    print("=" * 70)
    print("  VERIFICATION MANIFEST")
    print("=" * 70)
    print()

    # Group: T1 Bank 1 (highest confidence, matches corpus)
    print("  --- T1 Bank 1 (corpus-verified bytes, verify NAMES) ---")
    print(f"  {'File':42s} {'Track':6s} Device should show:")
    print(f"  {'─'*42} {'─'*6} {'─'*40}")
    for fname, track, desc in manifest:
        if track == "T1" and "_t1" in fname and not any(
            x in fname for x in ["10_", "11_", "12_", "13_", "14_", "15_"]
        ) and "control" not in fname and "variant" not in desc:
            print(f"  {fname:42s} {track:6s} {desc}")

    print()
    print("  --- T1 Bank 2 (NEW, untested encoding) ---")
    print(f"  {'File':42s} {'Track':6s} Device should show:")
    print(f"  {'─'*42} {'─'*6} {'─'*40}")
    for fname, track, desc in manifest:
        if track == "T1" and "_t1" in fname and any(
            x in fname for x in ["10_", "11_", "12_", "13_", "14_", "15_"]
        ) and "variant" not in desc:
            print(f"  {fname:42s} {track:6s} {desc}")

    print()
    print("  --- T1 Param Variants (subsetting verification) ---")
    print(f"  {'File':42s} {'Track':6s} Device should show:")
    print(f"  {'─'*42} {'─'*6} {'─'*40}")
    for fname, track, desc in manifest:
        if "variant" in desc:
            print(f"  {fname:42s} {track:6s} {desc}")

    print()
    print("  --- T3 (TONAL, may crash — test after T1 works) ---")
    print(f"  {'File':42s} {'Track':6s} Device should show:")
    print(f"  {'─'*42} {'─'*6} {'─'*40}")
    for fname, track, desc in manifest:
        if track == "T3":
            print(f"  {fname:42s} {track:6s} {desc}")

    print()
    print("  --- Controls ---")
    print(f"  {'File':42s} {'Track':6s} Device should show:")
    print(f"  {'─'*42} {'─'*6} {'─'*40}")
    for fname, track, desc in manifest:
        if "control" in fname:
            print(f"  {fname:42s} {track:6s} {desc}")

    print(f"""
{"="*70}
  TESTING INSTRUCTIONS
{"="*70}

  1. Copy {OUTPUT_DIR}/ folder to OP-XY USB drive
  2. Load each project file
  3. Select the indicated track (T1 or T3)
  4. Press STEP COMPONENT button to enter step component view
  5. Navigate to step 9
  6. Note what component TYPE and PARAMETER the device displays
  7. Compare with "Device should show" column above

  PRIORITY ORDER:
    a. sc_00_control_t1.xy — loads? Has note on step 9? (baseline sanity)
    b. T1 Bank 1 files — these use corpus-verified bytes; verify the NAMES
    c. T1 Bank 2 files — test bank 2 encoding (may crash if bank 2 wrong)
    d. T1 Param variants — verify subsetting param display matches
    e. T3 files — test tonal track step components (may crash)

  IF A FILE CRASHES:
    - T3 crash: step components don't work on tonal tracks (expected risk)
    - T1 bank 2 crash: bank 2 encoding is wrong (step_byte nibble issue)
    - T1 bank 1 crash: unexpected — should match corpus specimens exactly

  WHAT TO REPORT:
    For each file, note: LOADS/CRASHES and the displayed component name.
    e.g. "sc_03_hold_t1 → LOADS, shows Hold, param=minimum"
         "sc_10_bend_t1 → CRASHES"

  NOTE: unnamed 66 (Multiply) has 5 extra bytes in the corpus specimen
  that we don't reproduce. If Multiply crashes, that's the likely cause.
""")


if __name__ == "__main__":
    main()
