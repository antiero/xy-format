#!/usr/bin/env python3
"""Deep structural analysis of pre-track descriptor bytes across multi-pattern specimens.

Decodes topology, activation state, and descriptor structure for each specimen,
then attempts to find correlations between state and descriptor encoding.

Usage:
  python tools/analyze_descriptors_deep.py src/one-off-changes-from-default/*.xy
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xy.container import XYProject


def _find_ff_table_start(pre_track: bytes) -> int | None:
    """Return first offset where eight consecutive `ff 00 00` entries begin."""
    for i in range(0x56, len(pre_track) - 24):
        if all(pre_track[i + k * 3 : i + k * 3 + 3] == b"\xff\x00\x00" for k in range(8)):
            return i
    return None


def _hex(data: bytes) -> str:
    return data.hex(" ") if data else "(empty)"


def analyze_file(path: Path) -> dict | None:
    """Extract multi-pattern metadata from a single .xy file."""
    raw = path.read_bytes()
    proj = XYProject.from_bytes(raw)
    pre = proj.pre_track

    # Find FF table and extract var region
    ff_start = _find_ff_table_start(pre)
    if ff_start is None:
        return None

    var_region = pre[0x56:ff_start]
    if not var_region or var_region == b"\x00\x00":
        return None  # no multi-pattern data

    # Analyze each block
    blocks = []
    for idx, track in enumerate(proj.tracks):
        p = track.preamble
        pat_count = p[1] if p[1] > 0 else 1
        is_leader = pat_count > 1 and p[0] != 0x00
        is_clone = p[0] == 0x00 and (p[1] == 0x64 or p[1] == 0x8a or p[1] == 0x86
                                      or p[1] == 0x2e or p[1] == 0x00)
        activated = track.type_byte == 0x07

        # Infer owner track for clones by looking backward
        blocks.append({
            "slot": idx,
            "preamble": p.hex(" "),
            "p0": p[0],
            "p1": p[1],
            "type_byte": track.type_byte,
            "body_len": len(track.body),
            "activated": activated,
            "pat_count": pat_count if is_leader else None,
            "is_leader": is_leader,
            "is_clone_like": p[0] == 0x00,
        })

    # Identify multi-pattern tracks and their patterns
    multi_tracks = {}  # owner_track_1based -> {patterns: int, leader_activated: bool, clone_activated: list}
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if b["pat_count"] is not None and b["pat_count"] > 1:
            owner = i  # 0-based slot of leader
            pat_count = b["pat_count"]
            leader_activated = b["activated"]
            clone_states = []
            for j in range(1, pat_count):
                if i + j < len(blocks):
                    clone_states.append(blocks[i + j]["activated"])
            # Map to 1-based track index (leader's slot position in original layout)
            # For now, use the leader's preamble byte[0] to identify original track
            multi_tracks[i] = {
                "patterns": pat_count,
                "leader_slot": i,
                "leader_p0": b["p0"],
                "leader_activated": leader_activated,
                "clone_activated": clone_states,
            }
            i += pat_count
        else:
            i += 1

    # Determine which original tracks are multi-pattern
    # Use preamble byte[0] to identify: 0xB5=T1, 0x8A=T2, 0x86=T3, etc.
    PREAMBLE_TO_TRACK = {
        0xB5: 1,
        0x8A: 2,
        0x86: 3,  # also T3 in some contexts
        # T4-T8 vary; need to infer from position
    }

    return {
        "path": str(path.name),
        "file_size": len(raw),
        "pre_track_len": len(pre),
        "ff_table_start": ff_start,
        "var_0x56": var_region,
        "var_hex": _hex(var_region),
        "byte_0x56": pre[0x56],
        "byte_0x57": pre[0x57],
        "blocks": blocks,
        "multi_tracks": multi_tracks,
    }


def print_analysis(results: list[dict]) -> None:
    """Print comparative analysis of all specimens."""
    print("=" * 100)
    print("MULTI-PATTERN DESCRIPTOR ANALYSIS")
    print("=" * 100)

    for r in results:
        print(f"\n{'─' * 80}")
        print(f"  {r['path']}")
        print(f"  file={r['file_size']}B  pre_track={r['pre_track_len']}B  "
              f"ff_table=0x{r['ff_table_start']:02x}")
        print(f"  0x56=0x{r['byte_0x56']:02x}  0x57=0x{r['byte_0x57']:02x}")
        print(f"  var_0x56: {r['var_hex']}")

        # Show descriptor split: prefix | body | terminator
        var = r["var_0x56"]
        if len(var) >= 2:
            # Last 2 bytes are always 00 00 (baseline pushed right)
            if var[-2:] == b"\x00\x00":
                core = var[:-2]
                print(f"  core (minus 00 00 tail): {_hex(core)}")
            else:
                print(f"  (no 00 00 tail!)")

        # Show multi-pattern blocks
        for leader_slot, info in r["multi_tracks"].items():
            act_str = "ACTIVE" if info["leader_activated"] else "blank"
            clone_strs = ["ACTIVE" if a else "blank" for a in info["clone_activated"]]
            print(f"  Track @slot{leader_slot} (p0=0x{info['leader_p0']:02x}): "
                  f"{info['patterns']} patterns  "
                  f"leader={act_str}  clones=[{', '.join(clone_strs)}]")

        # Show all blocks with non-default preambles
        print(f"  Blocks:")
        for b in r["blocks"]:
            flags = []
            if b["pat_count"] and b["pat_count"] > 1:
                flags.append(f"LEADER({b['pat_count']}pat)")
            if b["is_clone_like"] and b["slot"] > 0:
                flags.append("CLONE?")
            if b["activated"]:
                flags.append("*ACT*")
            flag_str = f"  [{' '.join(flags)}]" if flags else ""
            print(f"    B{b['slot']+1:02d}: pre={b['preamble']}  "
                  f"type=0x{b['type_byte']:02x}  body={b['body_len']}{flag_str}")

    # Comparative table
    print(f"\n{'=' * 100}")
    print("DESCRIPTOR COMPARISON TABLE")
    print("=" * 100)
    print(f"{'File':<35} {'Topology':<25} {'State':<25} {'Descriptor Core'}")
    print(f"{'─'*35} {'─'*25} {'─'*25} {'─'*40}")

    for r in results:
        # Build topology string
        topo_parts = []
        states = []
        for leader_slot, info in r["multi_tracks"].items():
            p0 = info["leader_p0"]
            # Try to identify track
            if p0 == 0xB5:
                tname = "T1"
            elif p0 == 0x8A:
                tname = "T2"
            elif p0 == 0x86:
                tname = f"T?(0x{p0:02x})"
            elif p0 == 0x64:
                tname = f"T?(0x64)"
            else:
                tname = f"T?(0x{p0:02x})"
            topo_parts.append(f"{tname}×{info['patterns']}")

            # State
            l = "L" if info["leader_activated"] else "l"
            cs = "".join("C" if a else "c" for a in info["clone_activated"])
            states.append(f"{tname}:{l}{cs}")

        topo = " + ".join(topo_parts) if topo_parts else "?"
        state = " ".join(states) if states else "?"

        var = r["var_0x56"]
        core = _hex(var[:-2]) if var[-2:] == b"\x00\x00" else _hex(var)

        print(f"{r['path']:<35} {topo:<25} {state:<25} {core}")

    # Token analysis
    print(f"\n{'=' * 100}")
    print("TOKEN ANALYSIS")
    print("=" * 100)
    print("Looking for track tokens (0x1E - track_1_based) in descriptor cores:")
    print()

    TRACK_TOKENS = {0x1E - i: f"T{i}" for i in range(1, 17)}

    for r in results:
        var = r["var_0x56"]
        core = var[:-2] if var[-2:] == b"\x00\x00" else var
        found_tokens = []
        for i, b in enumerate(core):
            if b in TRACK_TOKENS:
                found_tokens.append(f"  byte[{i}]=0x{b:02x} → {TRACK_TOKENS[b]} token")
        if found_tokens:
            print(f"{r['path']}:")
            for ft in found_tokens:
                print(f"  {ft}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    expanded: list[Path] = []
    for pat in args.files:
        matches = sorted(Path(".").glob(pat))
        if matches:
            expanded.extend(matches)
        else:
            expanded.append(Path(pat))

    results = []
    for path in expanded:
        try:
            r = analyze_file(path)
            if r is not None:
                results.append(r)
        except Exception as e:
            print(f"SKIP {path}: {e}", file=sys.stderr)

    if results:
        print_analysis(results)
    else:
        print("No multi-pattern files found.")


if __name__ == "__main__":
    main()
