#!/usr/bin/env python3
"""Corpus-wide scene/pattern sweep with branch-aware decoding."""

from __future__ import annotations

import argparse
import glob
from collections import Counter
from pathlib import Path
import sys
from typing import Dict, Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xy.container import XYProject
from xy.scene_records import (
    decode_matrix_scene_vectors,
    decode_scene_region,
    detect_scene_region_format,
    find_scene_region,
    read_scene_assignments,
    read_t16_scene_list,
)

DEFAULT_GLOBS = [
    "src/**/*.xy",
    "src/*.xy",
    "output/**/*.xy",
    "output/*.xy",
]


def _collect_paths(patterns: Iterable[str]) -> List[Path]:
    paths: List[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for match in sorted(glob.glob(pattern, recursive=True)):
            p = Path(match)
            if not p.is_file():
                continue
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            paths.append(p)
    return paths


def _source_for_path(path: Path) -> str:
    s = str(path).replace("\\", "/")
    if s.startswith("src/one-off-changes-from-default/"):
        return "oneoff"
    if s.startswith("src/"):
        return "src"
    if s.startswith("output/"):
        return "output"
    return "other"


def _t16_scene_list_valid(count: int, ids: List[int]) -> bool:
    return (
        0 < count <= 96
        and len(ids) == count
        and all(0 <= scene_id <= 98 for scene_id in ids)
    )


def _max_pattern(assignments: Dict[int, Dict[int, int]]) -> int:
    if not assignments:
        return 0
    return max(pattern for tracks in assignments.values() for pattern in tracks.values())


def _analyze_file(path: Path) -> dict:
    raw = path.read_bytes()
    project = XYProject.from_bytes(raw)
    pre = project.pre_track

    scene_format = detect_scene_region_format(pre)
    scene_start, scene_end = find_scene_region(pre)
    region_len = scene_end - scene_start

    decode_error = ""
    try:
        scene_records = decode_scene_region(pre)
    except Exception as exc:  # pragma: no cover - defensive only
        scene_records = []
        decode_error = str(exc)
    scene_record_count = len(scene_records)

    matrix_error = ""
    try:
        matrix_vectors, matrix_trailing = decode_matrix_scene_vectors(pre)
    except Exception as exc:  # pragma: no cover - defensive only
        matrix_vectors = []
        matrix_trailing = b""
        matrix_error = str(exc)
    matrix_vector_count = len(matrix_vectors)
    matrix_trailing_len = len(matrix_trailing)

    t16_count_raw, t16_ids_raw = read_t16_scene_list(project.tracks[15].body)
    t16_valid = _t16_scene_list_valid(t16_count_raw, t16_ids_raw)

    assignments = read_scene_assignments(project)
    assignment_scene_count = len(assignments)
    assignment_max_pattern = _max_pattern(assignments)

    return {
        "path": str(path),
        "name": path.name,
        "source": _source_for_path(path),
        "file_size": len(raw),
        "pre_track_len": len(pre),
        "pre_0f_12": pre[0x0F:0x12].hex(" "),
        "scene_format": scene_format,
        "scene_start": scene_start,
        "scene_end": scene_end,
        "scene_region_len": region_len,
        "scene_record_count": scene_record_count,
        "scene_decode_error": decode_error,
        "matrix_vector_count": matrix_vector_count,
        "matrix_trailing_len": matrix_trailing_len,
        "matrix_decode_error": matrix_error,
        "t1_pre0": project.tracks[0].preamble[0],
        "t16_scene_count_raw": t16_count_raw,
        "t16_scene_list_valid": int(t16_valid),
        "t16_scene_ids_head": " ".join(str(v) for v in t16_ids_raw[:8]),
        "assignment_scene_count": assignment_scene_count,
        "assignment_max_pattern": assignment_max_pattern,
        "hybrid_matrix": int(
            scene_format == "matrix_records" and matrix_vector_count < scene_record_count
        ),
    }


def _write_csv(path: Path, rows: List[dict]) -> None:
    headers = [
        "path",
        "name",
        "source",
        "file_size",
        "pre_track_len",
        "pre_0f_12",
        "scene_format",
        "scene_start",
        "scene_end",
        "scene_region_len",
        "scene_record_count",
        "matrix_vector_count",
        "matrix_trailing_len",
        "t1_pre0",
        "t16_scene_count_raw",
        "t16_scene_list_valid",
        "t16_scene_ids_head",
        "assignment_scene_count",
        "assignment_max_pattern",
        "hybrid_matrix",
        "scene_decode_error",
        "matrix_decode_error",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for row in rows:
            vals = []
            for key in headers:
                value = str(row.get(key, ""))
                value = value.replace('"', '""')
                vals.append(f'"{value}"')
            f.write(",".join(vals) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--glob",
        action="append",
        default=DEFAULT_GLOBS.copy(),
        help="Input glob (repeatable)",
    )
    parser.add_argument(
        "--csv",
        default=str(REPO_ROOT / "output" / "scene_corpus_sweep_full.csv"),
        help="Output CSV path",
    )
    args = parser.parse_args()

    files = _collect_paths(args.glob)
    if not files:
        print("No files matched")
        return 1

    rows: List[dict] = []
    parse_errors: List[tuple[str, str]] = []
    for path in files:
        try:
            rows.append(_analyze_file(path))
        except Exception as exc:
            parse_errors.append((str(path), str(exc)))

    fmt_counts = Counter(row["scene_format"] for row in rows)
    source_fmt_counts = Counter((row["source"], row["scene_format"]) for row in rows)
    ctl_counts = Counter((row["scene_format"], row["pre_0f_12"]) for row in rows)
    hybrid = [row for row in rows if row["hybrid_matrix"]]

    scene_candidates = [
        row
        for row in rows
        if row["scene_record_count"] > 0
        or row["t16_scene_list_valid"]
        or row["pre_0f_12"] != "00 00 10"
    ]
    decoded_candidates = [
        row for row in scene_candidates if row["assignment_scene_count"] > 0
    ]

    print(f"files matched: {len(files)}")
    print(f"parsed: {len(rows)}  parse errors: {len(parse_errors)}")
    print("scene formats:")
    for fmt, n in fmt_counts.most_common():
        print(f"  {fmt:14s} {n}")

    print("source x scene format:")
    for (source, fmt), n in sorted(source_fmt_counts.items()):
        print(f"  {source:7s} {fmt:14s} {n}")

    print(
        "scene candidates:"
        f" {len(scene_candidates)}  decoded assignment maps: {len(decoded_candidates)}"
    )
    if scene_candidates:
        pct = 100.0 * len(decoded_candidates) / len(scene_candidates)
        print(f"decoded coverage: {pct:.1f}%")

    print("top control tuples by family:")
    for fmt in sorted(fmt_counts):
        print(f"  {fmt}")
        items = [(ctl, n) for (f, ctl), n in ctl_counts.items() if f == fmt]
        for ctl, n in sorted(items, key=lambda item: -item[1])[:8]:
            print(f"    {n:4d}  {ctl}")

    if hybrid:
        print("hybrid matrix-like files (matrix_records with partial vector decode):")
        for row in hybrid:
            print(
                "  "
                f"{row['path']} "
                f"(records={row['scene_record_count']}, vectors={row['matrix_vector_count']})"
            )

    if parse_errors:
        print("parse errors:")
        for path, err in parse_errors[:20]:
            print(f"  {path}: {err}")

    rows.sort(key=lambda row: (row["scene_format"], row["path"]))
    _write_csv(Path(args.csv), rows)
    print(f"wrote csv: {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
