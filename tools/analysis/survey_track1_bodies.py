#!/usr/bin/env python3
"""Survey structural regions of Track 1 bodies across the full corpus."""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from xy.container import XYProject


CORPUS = Path(__file__).resolve().parent.parent / "src" / "one-off-changes-from-default"


def load_all():
    """Load every .xy file and return list of (filename, project, track1_body)."""
    results = []
    for f in sorted(CORPUS.glob("*.xy")):
        try:
            data = f.read_bytes()
            proj = XYProject.from_bytes(data)
            t1 = proj.tracks[0]
            results.append((f.name, proj, t1))
        except Exception as e:
            print(f"  SKIP {f.name}: {e}")
    return results


def analysis_a(entries):
    """Body size distribution."""
    print("=" * 80)
    print("ANALYSIS A: Body Size Distribution")
    print("=" * 80)

    size_groups = defaultdict(list)
    for name, proj, t1 in entries:
        size_groups[len(t1.body)].append(name)

    for size in sorted(size_groups.keys()):
        files = size_groups[size]
        print(f"\n  Size {size} (0x{size:04X}) -- {len(files)} file(s):")
        for f in files:
            print(f"    {f}")

    # Identify baseline
    most_common_size = max(size_groups, key=lambda s: len(size_groups[s]))
    print(f"\n  BASELINE SIZE: {most_common_size} (0x{most_common_size:04X}) "
          f"-- {len(size_groups[most_common_size])} files")
    return most_common_size


def find_ff_00_00_runs(body):
    """Find runs of FF 00 00 pattern in body. Returns list of (offset, count)."""
    runs = []
    i = 0
    while i < len(body) - 2:
        if body[i] == 0xFF and body[i+1] == 0x00 and body[i+2] == 0x00:
            start = i
            count = 0
            while i < len(body) - 2 and body[i] == 0xFF and body[i+1] == 0x00 and body[i+2] == 0x00:
                count += 1
                i += 3
            runs.append((start, count))
        else:
            i += 1
    return runs


def analysis_b(entries, baseline_size):
    """FF 00 00 sentinel table region."""
    print("\n" + "=" * 80)
    print("ANALYSIS B: FF 00 00 Sentinel Table Region")
    print("=" * 80)

    # First, detailed look at baseline (unnamed 1.xy)
    baseline_entry = None
    for name, proj, t1 in entries:
        if name == "unnamed 1.xy":
            baseline_entry = (name, proj, t1)
            break

    if baseline_entry:
        name, proj, t1 = baseline_entry
        body = t1.body
        runs = find_ff_00_00_runs(body)
        print(f"\n  Baseline ({name}), body size={len(body)}:")
        for offset, count in runs:
            print(f"    FF 00 00 run at offset 0x{offset:04X}, count={count} "
                  f"(spans 0x{offset:04X}--0x{offset + count*3 - 1:04X})")

    # Now check interesting file groups
    groups = {
        "Single-step (59-78)": [n for n, _, _ in entries if any(
            n == f"unnamed {i}.xy" for i in range(59, 79))],
        "Multi-step (118, 118b, 119)": ["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"],
        "Non-baseline size": [n for n, _, t1 in entries if len(t1.body) != baseline_size],
    }

    for group_name, filenames in groups.items():
        print(f"\n  --- {group_name} ---")
        for name, proj, t1 in entries:
            if name in filenames:
                runs = find_ff_00_00_runs(t1.body)
                run_summary = "; ".join(
                    f"@0x{off:04X} x{cnt}" for off, cnt in runs
                ) if runs else "NONE"
                print(f"    {name}: body={len(t1.body)}, FF runs: {run_summary}")


def hex_dump_region(body, start, length):
    """Return hex dump string for a region of body."""
    end = min(start + length, len(body))
    chunk = body[start:end]
    hex_str = " ".join(f"{b:02X}" for b in chunk)
    return hex_str


def analysis_c(entries, baseline_size):
    """Bytes at body offsets 0x0131-0x0140."""
    print("\n" + "=" * 80)
    print("ANALYSIS C: Hex Dump of Body Offsets 0x0131--0x0140")
    print("=" * 80)

    target_files = set()
    # Baseline
    target_files.add("unnamed 1.xy")
    # Single-step (59-78)
    for i in range(59, 79):
        target_files.add(f"unnamed {i}.xy")
    # Multi-step
    target_files.update(["unnamed 118.xy", "unnamed 118b.xy", "unnamed 119.xy"])
    # Non-baseline size
    for name, proj, t1 in entries:
        if len(t1.body) != baseline_size:
            target_files.add(name)

    print(f"\n  {'Filename':<30s} {'Size':>6s}  Bytes at 0x0131--0x0140")
    print(f"  {'-'*30} {'-'*6}  {'-'*47}")
    for name, proj, t1 in entries:
        if name in target_files:
            body = t1.body
            if len(body) > 0x0131:
                dump = hex_dump_region(body, 0x0131, 16)
            else:
                dump = "(body too short)"
            print(f"  {name:<30s} {len(body):>6d}  {dump}")


def analysis_d(entries):
    """Sample metadata byte near offset 0x0675 for drum tracks."""
    print("\n" + "=" * 80)
    print("ANALYSIS D: Byte Near 0x0675 for Drum Track Files (engine=0x03)")
    print("=" * 80)

    drum_entries = []
    for name, proj, t1 in entries:
        try:
            eid = t1.engine_id
        except Exception:
            eid = -1
        if eid == 0x03:
            drum_entries.append((name, proj, t1))

    if not drum_entries:
        print("  No drum track files found (engine 0x03)")
        return

    print(f"\n  Found {len(drum_entries)} files with engine 0x03 on Track 1")
    print(f"\n  {'Filename':<30s} {'Size':>6s} {'Type':>4s}  "
          f"0x0673  0x0674  0x0675  0x0676  0x0677  context (0x0670--0x067F)")
    print(f"  {'-'*30} {'-'*6} {'-'*4}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*47}")

    for name, proj, t1 in drum_entries:
        body = t1.body
        sz = len(body)
        tb = t1.type_byte

        if sz > 0x067F:
            vals = [f"  0x{body[off]:02X}" for off in [0x0673, 0x0674, 0x0675, 0x0676, 0x0677]]
            ctx = hex_dump_region(body, 0x0670, 16)
        else:
            vals = ["  N/A "] * 5
            ctx = "(body too short)"

        print(f"  {name:<30s} {sz:>6d}   0x{tb:02X}  {''.join(vals)}  {ctx}")


def analysis_e(entries, baseline_size):
    """Body size vs component activation for single-step files."""
    print("\n" + "=" * 80)
    print("ANALYSIS E: Body Size vs Component Activation (unnamed 59--78)")
    print("=" * 80)

    print(f"\n  Baseline body size: {baseline_size} (0x{baseline_size:04X})")
    print(f"\n  {'Filename':<30s} {'Size':>6s} {'Delta':>6s}  Type  Engine")
    print(f"  {'-'*30} {'-'*6} {'-'*6}  {'-'*4}  {'-'*6}")

    for name, proj, t1 in entries:
        if any(name == f"unnamed {i}.xy" for i in range(59, 79)):
            body = t1.body
            sz = len(body)
            delta = sz - baseline_size
            try:
                eid = t1.engine_id
            except Exception:
                eid = -1
            print(f"  {name:<30s} {sz:>6d} {delta:>+6d}  0x{t1.type_byte:02X}  0x{eid:02X}")

    # Also show baseline for reference
    for name, proj, t1 in entries:
        if name == "unnamed 1.xy":
            body = t1.body
            try:
                eid = t1.engine_id
            except Exception:
                eid = -1
            print(f"\n  {'unnamed 1.xy (baseline)':<30s} {len(body):>6d}     +0  0x{t1.type_byte:02X}  0x{eid:02X}")


def main():
    print("Loading corpus...")
    entries = load_all()
    print(f"Loaded {len(entries)} files\n")

    # Print overview table
    print("=" * 80)
    print("OVERVIEW: All Track 1 Bodies")
    print("=" * 80)
    print(f"\n  {'Filename':<30s} {'BodySize':>8s}  Type  Engine")
    print(f"  {'-'*30} {'-'*8}  {'-'*4}  {'-'*6}")
    for name, proj, t1 in entries:
        try:
            eid = t1.engine_id
        except Exception:
            eid = -1
        print(f"  {name:<30s} {len(t1.body):>8d}  0x{t1.type_byte:02X}  0x{eid:02X}")

    baseline_size = analysis_a(entries)
    analysis_b(entries, baseline_size)
    analysis_c(entries, baseline_size)
    analysis_d(entries)
    analysis_e(entries, baseline_size)


if __name__ == "__main__":
    main()
