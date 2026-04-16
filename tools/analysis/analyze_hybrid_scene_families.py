#!/usr/bin/env python3
"""Analyze hybrid matrix-scene families from the indexed corpus.

This mines the existing `corpus_lab` SQLite DB for `matrix_records` files whose
scene regions are only partially decoded (`hybrid_matrix=1`). The goal is to
surface repeated branch structure from the current corpus without needing new
device captures.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "output" / "corpus_lab.sqlite"


@dataclass(frozen=True)
class RecordRow:
    ordinal: int
    record_kind: str
    raw: bytes
    patterns: tuple[int, ...]


@dataclass(frozen=True)
class HybridFile:
    name: str
    source: str
    scene_region_sha1: str
    corpus_count: int
    scene_record_count: int
    matrix_vector_count: int
    records: tuple[RecordRow, ...]


def _parse_hex_bytes(raw_hex: str) -> bytes:
    if not raw_hex:
        return b""
    return bytes.fromhex(raw_hex)


def _parse_patterns(raw: str) -> tuple[int, ...]:
    if not raw:
        return ()
    return tuple(int(part) for part in raw.split(",") if part)


def _load_hybrid_files(conn: sqlite3.Connection) -> list[HybridFile]:
    hash_counts = {
        str(row["scene_region_sha1"]): int(row["n"])
        for row in conn.execute(
            """
            SELECT scene_region_sha1, COUNT(*) AS n
            FROM files
            WHERE parse_ok = 1
              AND scene_format = 'matrix_records'
              AND hybrid_matrix = 1
            GROUP BY scene_region_sha1
            """
        )
    }
    rows = conn.execute(
        """
        SELECT
          f.id,
          f.name,
          f.source,
          f.scene_region_sha1,
          f.scene_record_count,
          f.matrix_vector_count,
          sr.ordinal,
          sr.record_kind,
          sr.raw_hex,
          sr.patterns
        FROM files f
        JOIN scene_records sr ON sr.file_id = f.id
        WHERE f.parse_ok = 1
          AND f.scene_format = 'matrix_records'
          AND f.hybrid_matrix = 1
        ORDER BY f.name, sr.ordinal
        """
    ).fetchall()
    grouped: dict[int, list[sqlite3.Row]] = defaultdict(list)
    meta: dict[int, sqlite3.Row] = {}
    for row in rows:
        grouped[int(row["id"])].append(row)
        meta[int(row["id"])] = row

    out: list[HybridFile] = []
    for file_id, file_rows in grouped.items():
        first = meta[file_id]
        records = tuple(
            RecordRow(
                ordinal=int(row["ordinal"]),
                record_kind=str(row["record_kind"]),
                raw=_parse_hex_bytes(str(row["raw_hex"])),
                patterns=_parse_patterns(str(row["patterns"] or "")),
            )
            for row in file_rows
        )
        out.append(
            HybridFile(
                name=str(first["name"]),
                source=str(first["source"]),
                scene_region_sha1=str(first["scene_region_sha1"]),
                corpus_count=hash_counts[str(first["scene_region_sha1"])],
                scene_record_count=int(first["scene_record_count"]),
                matrix_vector_count=int(first["matrix_vector_count"]),
                records=records,
            )
        )
    return out


def _dedupe_by_scene_hash(files: Sequence[HybridFile]) -> list[HybridFile]:
    chosen: dict[str, HybridFile] = {}
    for file in sorted(files, key=lambda item: (item.scene_region_sha1, item.source, item.name)):
        current = chosen.get(file.scene_region_sha1)
        if current is None:
            chosen[file.scene_region_sha1] = file
            continue
        current_rank = (0 if current.source == "src" else 1, current.name)
        candidate_rank = (0 if file.source == "src" else 1, file.name)
        if candidate_rank < current_rank:
            chosen[file.scene_region_sha1] = file
    return list(chosen.values())


def _layout_key(file: HybridFile) -> tuple[str, ...]:
    return tuple(record.record_kind for record in file.records)


def _fmt_bytes(data: bytes) -> str:
    return data.hex(" ") if data else "(none)"


def _fmt_positions(values: Iterable[int]) -> str:
    return ", ".join(str(v) for v in values)


def _fmt_patterns(patterns: Sequence[int]) -> str:
    return ",".join(f"P{value}" for value in patterns) if patterns else "(none)"


def _varying_opaque_byte_indexes(records: Sequence[RecordRow]) -> tuple[int, ...]:
    if not records:
        return ()
    max_len = max(len(record.raw) for record in records)
    out: list[int] = []
    for idx in range(max_len):
        vals = {
            record.raw[idx]
            for record in records
            if idx < len(record.raw)
        }
        if len(vals) > 1:
            out.append(idx)
    return tuple(out)


def _varying_vector_track_indexes(records: Sequence[RecordRow]) -> tuple[int, ...]:
    vectors = [record.patterns for record in records if record.patterns]
    if not vectors or not all(len(vector) == 8 for vector in vectors):
        return ()
    out: list[int] = []
    for track_idx in range(8):
        vals = {vector[track_idx] for vector in vectors}
        if len(vals) > 1:
            out.append(track_idx + 1)
    return tuple(out)


def _analyze_opaque(records: Sequence[RecordRow]) -> list[str]:
    if not records:
        return ["    no records"]
    max_len = max(len(record.raw) for record in records)
    varying_positions: list[str] = []
    for idx in range(max_len):
        vals = Counter(
            record.raw[idx]
            for record in records
            if idx < len(record.raw)
        )
        if len(vals) <= 1:
            continue
        parts = ", ".join(f"{value:02x}:{count}" for value, count in sorted(vals.items()))
        varying_positions.append(f"    byte[{idx}] -> {parts}")
    if not varying_positions:
        return ["    all bytes invariant"]
    return varying_positions


def _analyze_matrix_vectors(records: Sequence[RecordRow]) -> list[str]:
    vectors = [record.patterns for record in records if record.patterns]
    if not vectors:
        return ["    no decoded vectors"]
    if not all(len(vector) == 8 for vector in vectors):
        return ["    inconsistent decoded vector lengths"]

    lines: list[str] = []
    for track_idx in range(8):
        vals = Counter(vector[track_idx] for vector in vectors)
        if len(vals) <= 1:
            continue
        pretty = ", ".join(f"P{value}:{count}" for value, count in sorted(vals.items()))
        lines.append(f"    T{track_idx + 1} varies -> {pretty}")
    if not lines:
        return ["    all decoded track lanes invariant"]
    return lines


def _common_raw(records: Sequence[RecordRow]) -> tuple[bytes, int] | None:
    if not records:
        return None
    counter = Counter(record.raw for record in records)
    raw, n = counter.most_common(1)[0]
    return raw, n


def _cross_axis_lines(group: Sequence[HybridFile]) -> list[str]:
    if not group:
        return []

    ordinal_groups: dict[int, list[RecordRow]] = defaultdict(list)
    for file in group:
        for record in file.records:
            ordinal_groups[record.ordinal].append(record)

    opaque_ordinals = [
        ordinal for ordinal, rows in sorted(ordinal_groups.items())
        if rows and rows[0].record_kind == "opaque"
    ]
    vector_ordinals = [
        ordinal for ordinal, rows in sorted(ordinal_groups.items())
        if rows and rows[0].record_kind == "matrix_vector"
    ]
    if not opaque_ordinals or not vector_ordinals:
        return []

    opaque_ordinal = opaque_ordinals[-1]
    vector_ordinal = vector_ordinals[-1]
    by_vector: dict[tuple[int, ...], set[bytes]] = defaultdict(set)
    by_opaque: dict[bytes, set[tuple[int, ...]]] = defaultdict(set)
    for file in group:
        by_ord = {record.ordinal: record for record in file.records}
        opaque = by_ord.get(opaque_ordinal)
        vector = by_ord.get(vector_ordinal)
        if opaque is None or vector is None or not vector.patterns:
            continue
        by_vector[vector.patterns].add(opaque.raw)
        by_opaque[opaque.raw].add(vector.patterns)

    vector_variants = sorted(
        (
            patterns,
            len(opaques),
            len(group),
        )
        for patterns, opaques in by_vector.items()
        if len(opaques) > 1
    )
    opaque_variants = sorted(
        (
            raw,
            len(vectors),
            len(group),
        )
        for raw, vectors in by_opaque.items()
        if len(vectors) > 1
    )
    if not vector_variants and not opaque_variants:
        return []

    lines = ["  cross-axis evidence:"]
    for patterns, n_opaques, _ in sorted(vector_variants, key=lambda item: (-item[1], item[0]))[:3]:
        lines.append(
            f"    vector {_fmt_patterns(patterns)} pairs with {n_opaques} opaque forms"
        )
    for raw, n_vectors, _ in sorted(opaque_variants, key=lambda item: (-item[1], item[0]))[:3]:
        lines.append(
            f"    opaque {_fmt_bytes(raw)} pairs with {n_vectors} decoded vectors"
        )
    return lines


def _family_focus_lines(group: Sequence[HybridFile]) -> list[str]:
    if not group:
        return []

    ordinal_groups: dict[int, list[RecordRow]] = defaultdict(list)
    for file in group:
        for record in file.records:
            ordinal_groups[record.ordinal].append(record)

    opaque_ordinals = [
        ordinal for ordinal, rows in sorted(ordinal_groups.items())
        if rows and rows[0].record_kind == "opaque"
    ]
    vector_ordinals = [
        ordinal for ordinal, rows in sorted(ordinal_groups.items())
        if rows and rows[0].record_kind == "matrix_vector"
    ]
    if not opaque_ordinals or not vector_ordinals:
        return []

    opaque_ordinal = opaque_ordinals[-1]
    vector_ordinal = vector_ordinals[-1]
    by_vector: dict[tuple[int, ...], list[tuple[str, RecordRow]]] = defaultdict(list)
    by_opaque: dict[bytes, list[tuple[str, RecordRow]]] = defaultdict(list)

    for file in group:
        by_ord = {record.ordinal: record for record in file.records}
        opaque = by_ord.get(opaque_ordinal)
        vector = by_ord.get(vector_ordinal)
        if opaque is None or vector is None or not vector.patterns:
            continue
        by_vector[vector.patterns].append((file.name, opaque))
        by_opaque[opaque.raw].append((file.name, vector))

    lines: list[str] = []
    top_vectors = [
        (patterns, items)
        for patterns, items in sorted(
            by_vector.items(),
            key=lambda item: (-len({record.raw for _, record in item[1]}), item[0]),
        )
        if len({record.raw for _, record in items}) > 1
    ][:3]
    if top_vectors:
        lines.append("  fixed-vector families:")
        for patterns, items in top_vectors:
            records = [record for _, record in items]
            examples = ", ".join(name for name, _ in sorted(items)[:4])
            varying = _varying_opaque_byte_indexes(records)
            lines.append(
                "    "
                f"{_fmt_patterns(patterns)} -> {len({record.raw for record in records})} opaque forms; "
                f"varying opaque bytes: {_fmt_positions(varying) or '(none)'}; "
                f"examples: {examples}"
            )

    top_opaques = [
        (raw, items)
        for raw, items in sorted(
            by_opaque.items(),
            key=lambda item: (-len({record.patterns for _, record in item[1]}), item[0]),
        )
        if len({record.patterns for _, record in items}) > 1
    ][:3]
    if top_opaques:
        lines.append("  fixed-opaque families:")
        for raw, items in top_opaques:
            records = [record for _, record in items]
            examples = ", ".join(name for name, _ in sorted(items)[:4])
            varying = _varying_vector_track_indexes(records)
            varying_tracks = ", ".join(f"T{track}" for track in varying) or "(none)"
            lines.append(
                "    "
                f"{_fmt_bytes(raw)} -> {len({record.patterns for record in records})} vectors; "
                f"varying lanes: {varying_tracks}; "
                f"examples: {examples}"
            )
    return lines


def print_report(files: Sequence[HybridFile]) -> None:
    layout_groups: dict[tuple[str, ...], list[HybridFile]] = defaultdict(list)
    for file in files:
        layout_groups[_layout_key(file)].append(file)

    print(f"hybrid files analyzed: {len(files)}")
    print("top repeated families in corpus:")
    seen_hashes = set()
    for file in sorted(files, key=lambda item: (-item.corpus_count, item.scene_region_sha1, item.name))[:8]:
        if file.scene_region_sha1 in seen_hashes:
            continue
        seen_hashes.add(file.scene_region_sha1)
        print(
            f"  {file.scene_region_sha1}  corpus_files={file.corpus_count:2d}  representative={file.name}"
        )
    print("layouts:")
    for layout, group in sorted(layout_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        layout_desc = " -> ".join(layout)
        counts = Counter(file.scene_record_count for file in group)
        count_desc = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
        print(f"  {layout_desc:<36} files={len(group):2d}  scene_record_count={count_desc}")

    for layout, group in sorted(layout_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        print("")
        print(f"layout: {' -> '.join(layout)}")
        examples = ", ".join(file.name for file in sorted(group, key=lambda item: item.name)[:6])
        print(f"  examples: {examples}")
        for line in _cross_axis_lines(group):
            print(line)
        for line in _family_focus_lines(group):
            print(line)
        ordinal_groups: dict[int, list[RecordRow]] = defaultdict(list)
        for file in group:
            for record in file.records:
                ordinal_groups[record.ordinal].append(record)

        for ordinal in sorted(ordinal_groups):
            record_rows = ordinal_groups[ordinal]
            kind = record_rows[0].record_kind
            common = _common_raw(record_rows)
            print(f"  ordinal {ordinal}: {kind}  n={len(record_rows)}")
            if common is not None:
                raw, n = common
                print(f"    most common raw ({n}): {_fmt_bytes(raw)}")
            if kind == "opaque":
                for line in _analyze_opaque(record_rows):
                    print(line)
            elif kind == "matrix_vector":
                for line in _analyze_matrix_vectors(record_rows):
                    print(line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help="Path to corpus_lab sqlite db",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Do not dedupe files that share the same scene_region_sha1",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    files = _load_hybrid_files(conn)
    if not files:
        print("No hybrid matrix-scene files found.")
        return 1
    if not args.no_dedupe:
        files = _dedupe_by_scene_hash(files)
    print_report(files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
