#!/usr/bin/env python3
"""Analyze binary deltas between consecutive scene-chain .xy files.

Usage:
    python tools/analyze_scene_delta.py <before.xy> <after.xy>
    python tools/analyze_scene_delta.py --chain src/one-off-changes-from-default/0*_scene_*.xy

Fast mode (default) is linear and avoids expensive LCS-style matching:
  - File/pre-track/scene-region changed-byte counts
  - First N changed offsets
  - Size/pre-track/preamble/scene-format/T16 deltas

Deep mode (`--deep`) enables expensive structured decode paths and pre-track
SequenceMatcher opcodes for detailed forensic analysis.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from difflib import SequenceMatcher
from statistics import mean
import sys
from time import perf_counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from xy.container import XYProject
from xy.scene_records import (
    decode_matrix_scene_vectors,
    decode_scene_region,
    detect_scene_region_format,
    describe_record as structured_describe_record,
    find_scene_region,
    read_scene_assignments,
    read_t16_scene_list,
)


@dataclass(frozen=True)
class ExtractOptions:
    deep: bool = False
    decode_assignments: bool = False
    use_cache: bool = True


_EXTRACT_CACHE: Dict[Tuple[str, int, int, bool, bool], dict] = {}


def _cache_key(path: Path, options: ExtractOptions) -> Tuple[str, int, int, bool, bool]:
    st = path.stat()
    return (
        str(path.resolve()),
        st.st_mtime_ns,
        st.st_size,
        options.deep,
        options.decode_assignments,
    )


def extract_scene_info(filepath: str, *, options: ExtractOptions) -> dict:
    path = Path(filepath)
    key: Optional[Tuple[str, int, int, bool, bool]] = None
    if options.use_cache:
        key = _cache_key(path, options)
        cached = _EXTRACT_CACHE.get(key)
        if cached is not None:
            return cached

    info = _extract_scene_info_uncached(
        path,
        deep=options.deep,
        decode_assignments=options.decode_assignments,
    )
    if key is not None:
        _EXTRACT_CACHE[key] = info
    return info


def _extract_scene_info_uncached(
    filepath: Path,
    *,
    deep: bool,
    decode_assignments: bool,
) -> dict:
    """Extract scene-relevant fields from an .xy file."""
    data = filepath.read_bytes()
    p = XYProject.from_bytes(data)
    pre = p.pre_track

    scene_format = detect_scene_region_format(pre)
    scene_start, scene_end = find_scene_region(pre)
    scene_region = pre[scene_start:scene_end]

    # Descriptor only exists in the tag-record family.
    desc_start = None
    desc_bytes = b""
    if scene_format == "tag_records" and scene_start >= 4:
        candidate = scene_start - 4
        if pre[candidate] == 0x1E:
            desc_start = candidate
            desc_bytes = pre[desc_start:scene_start]

    decode_error = None
    parsed_records = []
    records = []
    matrix_vectors = []
    matrix_trailing = b""

    if deep:
        try:
            parsed_records = decode_scene_region(pre)
            records = [record.raw for record in parsed_records]
        except Exception as exc:
            decode_error = str(exc)

        try:
            matrix_vectors, matrix_trailing = decode_matrix_scene_vectors(pre)
        except Exception:
            # Keep report generation resilient even if matrix decode evolves.
            pass

    scene_assignments = {}
    if decode_assignments:
        try:
            scene_assignments = read_scene_assignments(p)
        except Exception:
            # Keep extraction resilient for partially decoded branches.
            pass

    scene_slot_hint = pre[0x0F] + 1 if len(pre) > 0x0F else 0
    matrix_raw_record_count = len(parsed_records) if scene_format == "matrix_records" else 0
    matrix_decoded_record_count = (
        sum(1 for rec in parsed_records if rec.overrides)
        if scene_format == "matrix_records"
        else 0
    )
    matrix_partial_decode = (
        scene_format == "matrix_records"
        and matrix_raw_record_count > 0
        and matrix_decoded_record_count < matrix_raw_record_count
    )

    # T16 scene list
    t16_body = p.tracks[15].body
    scene_count_raw, scene_ids_raw = read_t16_scene_list(t16_body)
    t16_scene_list_valid = (
        0 < scene_count_raw <= 96
        and len(scene_ids_raw) == scene_count_raw
        and all(0 <= scene_id <= 98 for scene_id in scene_ids_raw)
    )
    scene_count = scene_count_raw if t16_scene_list_valid else 0
    scene_ids = scene_ids_raw if t16_scene_list_valid else []

    return {
        "filepath": str(filepath),
        "filename": filepath.name,
        "file_size": len(data),
        "pre_track_len": len(pre),
        "pre_0f_12": pre[0x0F:0x12],
        "scene_format": scene_format,
        "scene_start": scene_start,
        "scene_end": scene_end,
        "descriptor": desc_bytes,
        "desc_offset": desc_start,
        "scene_region": scene_region,
        "scene_decode_error": decode_error,
        "scene_records_struct": parsed_records,
        "scene_records": records,
        "scene_assignments": scene_assignments,
        "scene_slot_hint": scene_slot_hint,
        "matrix_vector_count": len(matrix_vectors),
        "matrix_raw_record_count": matrix_raw_record_count,
        "matrix_decoded_record_count": matrix_decoded_record_count,
        "matrix_partial_decode": matrix_partial_decode,
        "matrix_trailing": matrix_trailing,
        "t1_preamble_0": p.tracks[0].preamble[0],
        "track_preambles": tuple(track.preamble for track in p.tracks),
        "track_body_lens": tuple(len(track.body) for track in p.tracks),
        "t16_body_len": len(t16_body),
        "t16_scene_count_raw": scene_count_raw,
        "t16_scene_ids_raw": scene_ids_raw,
        "t16_scene_list_valid": t16_scene_list_valid,
        "t16_scene_count": scene_count,
        "t16_scene_ids": scene_ids,
        "data": data,
        "pre_track": pre,
    }


def format_hex(data: bytes, sep: str = " ") -> str:
    return sep.join(f"{b:02x}" for b in data)


TRACK_TAG_MAP = {
    0x1D: "T1",
    0x1C: "T2",
    0x1B: "T3",
    0x1A: "T4",
    0x19: "T5",
    0x18: "T6",
    0x17: "T7",
    0x16: "T8",
}


def describe_record(record: bytes) -> str:
    """Attempt to describe a scene record's content."""
    hex_str = format_hex(record)
    # Look for track tag bytes
    tags_found = []
    for i, b in enumerate(record):
        if b in TRACK_TAG_MAP:
            tags_found.append(f"{TRACK_TAG_MAP[b]}(@{i})")
    tag_info = f" tags=[{', '.join(tags_found)}]" if tags_found else ""
    return f"[{hex_str}]{tag_info}"


def print_info(
    info: dict,
    *,
    deep: bool = False,
    decode: bool = False,
    decode_assignments: bool = False,
) -> None:
    """Print a summary of scene-relevant fields."""
    print(f"  File: {info['filename']}")
    print(f"  Size: {info['file_size']} bytes, pre-track: {info['pre_track_len']} bytes")
    print(f"  pre[0x0F:0x12] = {format_hex(info['pre_0f_12'])}")
    print(
        f"  Scene format: {info['scene_format']} "
        f"(region 0x{info['scene_start']:02x}-0x{info['scene_end']:02x}, "
        f"len={len(info['scene_region'])})"
    )
    if info["scene_format"] in {"matrix_records", "alt_records"}:
        print(f"  Scene slot hint (pre[0x0F]+1): {info['scene_slot_hint']}")
    if info["desc_offset"] is None:
        print("  Descriptor: (none in this scene family)")
    else:
        print(f"  Descriptor: {format_hex(info['descriptor'])} @ 0x{info['desc_offset']:02x}")
    print(f"  T1 preamble[0] = 0x{info['t1_preamble_0']:02x}")
    if info["t16_scene_list_valid"]:
        print(f"  T16 scene count = {info['t16_scene_count']}, IDs = {info['t16_scene_ids']}")
    else:
        preview = info["t16_scene_ids_raw"][:8]
        print(
            "  T16 scene list: invalid/non-scene payload at canonical offsets "
            f"(raw_count={info['t16_scene_count_raw']}, raw_ids_head={preview})"
        )

    if not deep:
        print("  Scene decode: skipped in fast mode (use --deep)")
    elif info["scene_decode_error"]:
        print(f"  Scene decode: partial (error: {info['scene_decode_error']})")

    if deep and decode and info["scene_records_struct"]:
        print(f"  Scene records ({len(info['scene_records_struct'])}) [decoded]:")
        for i, rec in enumerate(info["scene_records_struct"]):
            print(f"    [{i}] {structured_describe_record(rec)}")
    elif deep and info["scene_records"]:
        print(f"  Scene records ({len(info['scene_records'])}):")
        for i, rec in enumerate(info["scene_records"]):
            print(f"    [{i}] {describe_record(rec)}")
    else:
        if deep:
            print("  Scene records: (none)")

    if deep and (info["matrix_vector_count"] or info["scene_format"] == "matrix_records"):
        print(
            f"  Matrix vectors: {info['matrix_vector_count']}, "
            f"trailing={format_hex(info['matrix_trailing']) or '(none)'}"
        )
        if info["scene_format"] == "matrix_records":
            print(
                f"  Matrix decode coverage: {info['matrix_decoded_record_count']}/"
                f"{info['matrix_raw_record_count']} records"
            )
            if info["matrix_partial_decode"]:
                print(
                    "  Matrix decode warning: hybrid/mixed record family; "
                    "per-track decode is provisional. Confirm on device."
                )
            if decode_assignments and info["scene_assignments"]:
                print(
                    f"  Assignment map (decoded): {len(info['scene_assignments'])} scene(s)"
                )
            elif decode_assignments:
                print("  Assignment map: unavailable for this branch (partial decode)")


def _preview_hex(data: bytes, *, max_bytes: int = 12) -> str:
    if not data:
        return "(none)"
    if len(data) <= max_bytes:
        return format_hex(data)
    return f"{format_hex(data[:max_bytes])} ... (+{len(data) - max_bytes}B)"


def _linear_diff_metrics(a: bytes, b: bytes, *, max_offsets: int) -> dict:
    min_len = min(len(a), len(b))
    changed = 0
    samples: List[Tuple[int, Optional[int], Optional[int]]] = []

    for idx in range(min_len):
        if a[idx] != b[idx]:
            changed += 1
            if len(samples) < max_offsets:
                samples.append((idx, a[idx], b[idx]))

    if len(a) != len(b):
        changed += abs(len(a) - len(b))
        extra_start = min_len
        extra_bytes = b[extra_start:] if len(b) > len(a) else a[extra_start:]
        is_insert = len(b) > len(a)
        for rel_idx, value in enumerate(extra_bytes):
            if len(samples) >= max_offsets:
                break
            if is_insert:
                samples.append((extra_start + rel_idx, None, value))
            else:
                samples.append((extra_start + rel_idx, value, None))

    return {
        "changed": changed,
        "total": max(len(a), len(b)),
        "tail_delta": len(b) - len(a),
        "samples": samples,
    }


def _format_sample(sample: Tuple[int, Optional[int], Optional[int]]) -> str:
    offset, old, new = sample
    old_s = "(absent)" if old is None else f"{old:02x}"
    new_s = "(absent)" if new is None else f"{new:02x}"
    return f"@0x{offset:04x}:{old_s}->{new_s}"


def _print_linear_diff(label: str, a: bytes, b: bytes, *, max_offsets: int) -> None:
    m = _linear_diff_metrics(a, b, max_offsets=max_offsets)
    if m["total"] == 0:
        pct = 0.0
    else:
        pct = 100.0 * m["changed"] / m["total"]
    print(
        f"  {label}: {m['changed']}/{m['total']} bytes changed "
        f"({pct:.2f}%)"
    )
    if m["samples"]:
        samples = ", ".join(_format_sample(s) for s in m["samples"])
        print(f"    first changes: {samples}")
    if m["tail_delta"] > 0:
        print(f"    size tail: +{m['tail_delta']}B in right-hand file")
    elif m["tail_delta"] < 0:
        print(f"    size tail: {m['tail_delta']}B in right-hand file")


def _iter_non_equal_ops(
    a: bytes,
    b: bytes,
    *,
    max_ops: int,
) -> Tuple[List[Tuple[str, int, int, int, int]], int]:
    matcher = SequenceMatcher(a=a, b=b, autojunk=False)
    ops: List[Tuple[str, int, int, int, int]] = []
    total = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        total += 1
        if len(ops) < max_ops:
            ops.append((tag, i1, i2, j1, j2))
    return ops, total


def _print_fast_delta(before: dict, after: dict, *, max_offsets: int) -> None:
    size_delta = after["file_size"] - before["file_size"]
    pre_delta = after["pre_track_len"] - before["pre_track_len"]
    scene_region_delta = len(after["scene_region"]) - len(before["scene_region"])
    print(f"\n  File size: {before['file_size']} → {after['file_size']} ({size_delta:+d})")
    print(f"  Pre-track: {before['pre_track_len']} → {after['pre_track_len']} ({pre_delta:+d})")
    print(
        f"  Scene region len: {len(before['scene_region'])} → {len(after['scene_region'])} "
        f"({scene_region_delta:+d})"
    )

    if before["pre_0f_12"] != after["pre_0f_12"]:
        print(
            f"  pre[0x0F:0x12]: {format_hex(before['pre_0f_12'])} → "
            f"{format_hex(after['pre_0f_12'])} *** CHANGED"
        )
    else:
        print(f"  pre[0x0F:0x12]: {format_hex(after['pre_0f_12'])} (unchanged)")

    if before["scene_format"] != after["scene_format"]:
        print(f"  Scene format: {before['scene_format']} → {after['scene_format']} *** CHANGED")
    else:
        print(f"  Scene format: {after['scene_format']} (unchanged)")

    if before["t1_preamble_0"] != after["t1_preamble_0"]:
        delta = after["t1_preamble_0"] - before["t1_preamble_0"]
        print(
            f"  T1 preamble[0]: 0x{before['t1_preamble_0']:02x} → "
            f"0x{after['t1_preamble_0']:02x} (delta={delta:+d} = {delta:+#x}) *** CHANGED"
        )
    else:
        print(f"  T1 preamble[0]: 0x{after['t1_preamble_0']:02x} (unchanged)")

    _print_linear_diff("Full blob byte diff", before["data"], after["data"], max_offsets=max_offsets)
    _print_linear_diff("Pre-track byte diff", before["pre_track"], after["pre_track"], max_offsets=max_offsets)
    _print_linear_diff(
        "Scene-region byte diff",
        before["scene_region"],
        after["scene_region"],
        max_offsets=max_offsets,
    )

    if (
        before["t16_scene_list_valid"] != after["t16_scene_list_valid"]
        or before["t16_scene_count"] != after["t16_scene_count"]
        or before["t16_scene_ids"] != after["t16_scene_ids"]
    ):
        print(
            f"\n  T16 scene list: CHANGED"
            f"\n    valid: {before['t16_scene_list_valid']} → {after['t16_scene_list_valid']}"
            f"\n    count: {before['t16_scene_count']} → {after['t16_scene_count']}"
            f"\n    IDs: {before['t16_scene_ids']} → {after['t16_scene_ids']}"
        )
        if not before["t16_scene_list_valid"] or not after["t16_scene_list_valid"]:
            print(
                "    raw head: "
                f"{before['t16_scene_count_raw']}:{before['t16_scene_ids_raw'][:8]} → "
                f"{after['t16_scene_count_raw']}:{after['t16_scene_ids_raw'][:8]}"
            )
    else:
        print(
            f"\n  T16 scene list: unchanged (count={after['t16_scene_count']}, IDs={after['t16_scene_ids']})"
        )

    if before["t16_body_len"] != after["t16_body_len"]:
        t16_delta = after["t16_body_len"] - before["t16_body_len"]
        print(
            f"  T16 body: {before['t16_body_len']} → {after['t16_body_len']} ({t16_delta:+d})"
        )

    preamble_changes: List[str] = []
    for i in range(16):
        pb = before["track_preambles"][i]
        pa = after["track_preambles"][i]
        if pb != pa:
            preamble_changes.append(f"T{i+1}: {format_hex(pb)} → {format_hex(pa)}")
    if preamble_changes:
        head = ", ".join(preamble_changes[:6])
        suffix = "" if len(preamble_changes) <= 6 else f", ... (+{len(preamble_changes) - 6} more)"
        print(f"\n  Preamble changes ({len(preamble_changes)}): {head}{suffix}")

    body_changes = []
    for i in range(16):
        lb = before["track_body_lens"][i]
        la = after["track_body_lens"][i]
        if lb != la:
            body_changes.append(f"T{i+1}: {lb}→{la} ({la-lb:+d})")
    if body_changes:
        print(f"\n  Body size changes: {', '.join(body_changes)}")


def _print_deep_delta(before: dict, after: dict, *, decode: bool, deep_max_opcodes: int) -> None:
    print("\n  Deep decode details:")
    if before["scene_region"] != after["scene_region"]:
        print(
            f"    Scene records changed: {len(before['scene_records'])} → "
            f"{len(after['scene_records'])}"
        )
    else:
        print(f"    Scene records unchanged: {len(after['scene_records'])}")

    if decode:
        if before["scene_records_struct"]:
            print("    Before decoded records:")
            for idx, rec in enumerate(before["scene_records_struct"]):
                print(f"      [{idx}] {structured_describe_record(rec)}")
        if after["scene_records_struct"]:
            print("    After decoded records:")
            for idx, rec in enumerate(after["scene_records_struct"]):
                print(f"      [{idx}] {structured_describe_record(rec)}")

    if before["scene_records"] and after["scene_records"]:
        shared = min(len(before["scene_records"]), len(after["scene_records"]))
        for idx in range(shared):
            rb = before["scene_records"][idx]
            ra = after["scene_records"][idx]
            if rb != ra:
                print(f"    Record[{idx}] changed:")
                print(f"      before: {_preview_hex(rb)}")
                print(f"      after:  {_preview_hex(ra)}")
                break

    ops, total = _iter_non_equal_ops(
        before["pre_track"],
        after["pre_track"],
        max_ops=deep_max_opcodes,
    )
    print(f"    pre-track opcodes (SequenceMatcher): {total}")
    for tag, i1, i2, j1, j2 in ops:
        left = before["pre_track"][i1:i2]
        right = after["pre_track"][j1:j2]
        print(
            f"      {tag:<7} pre[0x{i1:02x}:0x{i2:02x}] {_preview_hex(left)} "
            f"-> pre'[0x{j1:02x}:0x{j2:02x}] {_preview_hex(right)}"
        )
    if total > len(ops):
        print(f"      ... truncated {total - len(ops)} opcode(s)")


def print_delta(
    before: dict,
    after: dict,
    *,
    deep: bool,
    decode: bool,
    max_offsets: int,
    deep_max_opcodes: int,
) -> None:
    """Print the delta between two consecutive files."""
    print(f"\n{'='*70}")
    print(f"DELTA: {before['filename']} → {after['filename']}")
    print(f"{'='*70}")
    _print_fast_delta(before, after, max_offsets=max_offsets)
    if deep:
        _print_deep_delta(before, after, decode=decode, deep_max_opcodes=deep_max_opcodes)


def _expand_to_size(data: bytes, size: int) -> bytes:
    if size <= 0:
        return b""
    if not data:
        return bytes(size)
    if len(data) >= size:
        return data[:size]
    reps, rem = divmod(size, len(data))
    return data * reps + data[:rem]


def _percentile(values: Sequence[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int((len(ordered) - 1) * p)
    return ordered[idx]


def run_fast_micro_benchmark(
    before_path: str,
    after_path: str,
    *,
    runs: int,
    bench_size: int,
    target_ms: float,
) -> None:
    before_path_obj = Path(before_path)
    after_path_obj = Path(after_path)
    before_raw = before_path_obj.read_bytes()
    after_raw = after_path_obj.read_bytes()

    # End-to-end fast pipeline timing (uncached extraction + linear compare).
    pipeline_samples_ms: List[float] = []
    for _ in range(max(1, runs)):
        t0 = perf_counter()
        b = extract_scene_info(
            str(before_path_obj),
            options=ExtractOptions(deep=False, decode_assignments=False, use_cache=False),
        )
        a = extract_scene_info(
            str(after_path_obj),
            options=ExtractOptions(deep=False, decode_assignments=False, use_cache=False),
        )
        _linear_diff_metrics(b["data"], a["data"], max_offsets=0)
        _linear_diff_metrics(b["pre_track"], a["pre_track"], max_offsets=0)
        _linear_diff_metrics(b["scene_region"], a["scene_region"], max_offsets=0)
        pipeline_samples_ms.append((perf_counter() - t0) * 1000.0)

    # Synthetic 100KB+ linear diff timing for SLA tracking.
    bench_before = _expand_to_size(before_raw, bench_size)
    bench_after = _expand_to_size(after_raw, bench_size)
    diff_samples_ms: List[float] = []
    for _ in range(max(1, runs)):
        t0 = perf_counter()
        _linear_diff_metrics(bench_before, bench_after, max_offsets=0)
        diff_samples_ms.append((perf_counter() - t0) * 1000.0)

    pipeline_avg = mean(pipeline_samples_ms)
    pipeline_p95 = _percentile(pipeline_samples_ms, 0.95)
    diff_avg = mean(diff_samples_ms)
    diff_p95 = _percentile(diff_samples_ms, 0.95)
    sla = "PASS" if diff_avg < target_ms else "FAIL"

    print("\nFAST MICRO-BENCH")
    print(f"  Pair: {before_path_obj.name} -> {after_path_obj.name}")
    print(f"  Runs: {runs}")
    print(
        f"  Real pair sizes: {len(before_raw)}B / {len(after_raw)}B"
    )
    print(
        f"  Fast pipeline (uncached) avg={pipeline_avg:.3f} ms, p95={pipeline_p95:.3f} ms"
    )
    print(
        f"  Linear diff on {bench_size}B avg={diff_avg:.3f} ms, p95={diff_p95:.3f} ms"
    )
    print(f"  SLA target (<{target_ms:.1f} ms on {bench_size}B): {sla}")


def main():
    parser = argparse.ArgumentParser(description="Analyze scene deltas between .xy files")
    parser.add_argument("files", nargs="*", help="Two .xy files (before, after)")
    parser.add_argument(
        "--chain", action="store_true", help="Treat all files as a sequential chain"
    )
    parser.add_argument(
        "--summary", action="store_true", help="Print summary table only"
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Enable expensive deep compare (structured decode + pre-track opcodes)",
    )
    parser.add_argument(
        "--decode", action="store_true",
        help="Use structured scene_records decoder for record interpretation"
    )
    parser.add_argument(
        "--decode-assignments",
        action="store_true",
        help="Decode scene assignment map (off by default; can be expensive on heavy branches)",
    )
    parser.add_argument(
        "--max-offsets",
        type=int,
        default=12,
        help="Max changed-byte offsets to print for linear fast diffs (default: 12)",
    )
    parser.add_argument(
        "--deep-max-opcodes",
        type=int,
        default=16,
        help="Max pre-track SequenceMatcher opcode entries to print in --deep mode (default: 16)",
    )
    parser.add_argument(
        "--benchmark-fast",
        action="store_true",
        help="Run fast-mode micro-benchmark on the first pair and exit",
    )
    parser.add_argument(
        "--bench-runs",
        type=int,
        default=25,
        help="Benchmark iteration count for --benchmark-fast (default: 25)",
    )
    parser.add_argument(
        "--bench-size",
        type=int,
        default=100_000,
        help="Synthetic linear-diff byte size for --benchmark-fast (default: 100000)",
    )
    parser.add_argument(
        "--bench-target-ms",
        type=float,
        default=1000.0,
        help="SLA threshold in ms for synthetic diff benchmark (default: 1000.0)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable per-file extraction cache (cache key: path+mtime+size+mode)",
    )
    args = parser.parse_args()

    if not args.files:
        parser.error("Provide at least two .xy files")

    if args.benchmark_fast:
        if len(args.files) < 2:
            parser.error("--benchmark-fast requires at least two files")
        run_fast_micro_benchmark(
            args.files[0],
            args.files[1],
            runs=max(1, args.bench_runs),
            bench_size=max(1, args.bench_size),
            target_ms=max(0.0, args.bench_target_ms),
        )
        return

    deep_mode = args.deep or args.decode or args.decode_assignments
    files = sorted(args.files) if args.chain else list(args.files)
    options = ExtractOptions(
        deep=deep_mode,
        decode_assignments=args.decode_assignments,
        use_cache=not args.no_cache,
    )
    infos = [extract_scene_info(f, options=options) for f in files]

    if args.summary:
        print(
            f"{'File':34s} {'Fmt':12s} {'Size':>6s} {'PreTrk':>6s} {'pre0F':>8s} "
            f"{'T1p[0]':>6s} {'ScnCt':>5s} {'ScnIDs':>12s} {'Rec':>4s}"
        )
        print("-" * 115)
        for info in infos:
            rec_display = str(len(info["scene_records"])) if deep_mode else "-"
            print(
                f"{info['filename']:34s} {info['scene_format']:12s} "
                f"{info['file_size']:6d} {info['pre_track_len']:6d} "
                f"{format_hex(info['pre_0f_12']):>8s} "
                f"0x{info['t1_preamble_0']:02x}   "
                f"{info['t16_scene_count']:5d} {str(info['t16_scene_ids']):>12s} "
                f"{rec_display:>4s}"
            )
        return

    # Print info for each file
    for info in infos:
        print(f"\n{'─'*50}")
        print_info(
            info,
            deep=deep_mode,
            decode=args.decode,
            decode_assignments=args.decode_assignments,
        )

    # Print deltas
    if args.chain or len(files) == 2:
        for i in range(len(infos) - 1):
            print_delta(
                infos[i],
                infos[i + 1],
                deep=deep_mode,
                decode=args.decode,
                max_offsets=max(0, args.max_offsets),
                deep_max_opcodes=max(0, args.deep_max_opcodes),
            )
    else:
        # Just compare first two
        print_delta(
            infos[0],
            infos[1],
            deep=deep_mode,
            decode=args.decode,
            max_offsets=max(0, args.max_offsets),
            deep_max_opcodes=max(0, args.deep_max_opcodes),
        )

    # T1 preamble progression
    if len(infos) > 2:
        print(f"\n{'='*70}")
        print("T1 preamble[0] progression:")
        vals = [info["t1_preamble_0"] for info in infos]
        for i, (info, v) in enumerate(zip(infos, vals)):
            delta_str = ""
            if i > 0 and vals[i] != vals[i - 1]:
                d = vals[i] - vals[i - 1]
                delta_str = f" (delta={d:+d} = {d:+#06x})"
            print(f"  {info['filename']:40s} 0x{v:02x}{delta_str}")


if __name__ == "__main__":
    main()
