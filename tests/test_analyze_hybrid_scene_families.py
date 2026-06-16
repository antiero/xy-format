"""Regressions for hybrid scene family mining helpers."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.analysis.analyze_hybrid_scene_families import (
    HybridFile,
    RecordRow,
    _analyze_opaque,
    _cross_axis_lines,
    _dedupe_by_scene_hash,
    _family_focus_lines,
)


def _hybrid_file(
    *,
    name: str,
    source: str,
    sha1: str,
    corpus_count: int,
    opaque_ord1: bytes,
    patterns_ord2: tuple[int, ...],
) -> HybridFile:
    return HybridFile(
        name=name,
        source=source,
        scene_region_sha1=sha1,
        corpus_count=corpus_count,
        scene_record_count=3,
        matrix_vector_count=1,
        records=(
            RecordRow(0, "opaque", bytes.fromhex("08 08 06 00 00 16 01"), ()),
            RecordRow(1, "opaque", opaque_ord1, ()),
            RecordRow(2, "matrix_vector", bytes.fromhex("08 08 01 00 00 00 08 08 01 00 00 16 01"), patterns_ord2),
        ),
    )


def test_dedupe_by_scene_hash_prefers_src_variant() -> None:
    src_file = _hybrid_file(
        name="src_copy.xy",
        source="src",
        sha1="abc",
        corpus_count=4,
        opaque_ord1=bytes.fromhex("08 08 00 00 08 08 03 00 00 16 01"),
        patterns_ord2=(9, 9, 2, 1, 1, 9, 9, 2),
    )
    output_file = _hybrid_file(
        name="output_copy.xy",
        source="output",
        sha1="abc",
        corpus_count=4,
        opaque_ord1=bytes.fromhex("08 08 00 00 08 08 03 00 00 16 01"),
        patterns_ord2=(9, 9, 2, 1, 1, 9, 9, 2),
    )

    deduped = _dedupe_by_scene_hash([output_file, src_file])
    assert deduped == [src_file]


def test_analyze_opaque_reports_varying_positions() -> None:
    rows = [
        RecordRow(1, "opaque", bytes.fromhex("08 08 00 00 08 08 03 00 00 16 01"), ()),
        RecordRow(1, "opaque", bytes.fromhex("08 08 00 02 08 08 03 00 00 16 01"), ()),
    ]

    assert _analyze_opaque(rows) == ["    byte[3] -> 00:1, 02:1"]


def test_cross_axis_lines_detects_independent_opaque_and_vector_axes() -> None:
    group = [
        _hybrid_file(
            name="a.xy",
            source="src",
            sha1="a",
            corpus_count=1,
            opaque_ord1=bytes.fromhex("08 08 00 00 08 08 03 00 00 16 01"),
            patterns_ord2=(9, 9, 2, 1, 1, 9, 9, 2),
        ),
        _hybrid_file(
            name="b.xy",
            source="src",
            sha1="b",
            corpus_count=1,
            opaque_ord1=bytes.fromhex("08 08 00 01 08 08 03 00 00 16 01"),
            patterns_ord2=(9, 9, 2, 1, 1, 9, 9, 2),
        ),
        _hybrid_file(
            name="c.xy",
            source="src",
            sha1="c",
            corpus_count=1,
            opaque_ord1=bytes.fromhex("08 08 00 00 08 08 03 00 00 16 01"),
            patterns_ord2=(9, 9, 2, 1, 1, 9, 1, 9),
        ),
    ]

    assert _cross_axis_lines(group) == [
        "  cross-axis evidence:",
        "    vector P9,P9,P2,P1,P1,P9,P9,P2 pairs with 2 opaque forms",
        "    opaque 08 08 00 00 08 08 03 00 00 16 01 pairs with 2 decoded vectors",
    ]


def test_family_focus_lines_summarizes_fixed_vector_and_fixed_opaque_families() -> None:
    group = [
        _hybrid_file(
            name="a.xy",
            source="src",
            sha1="a",
            corpus_count=1,
            opaque_ord1=bytes.fromhex("08 08 00 00 08 08 03 00 00 16 01"),
            patterns_ord2=(9, 9, 2, 1, 1, 9, 9, 2),
        ),
        _hybrid_file(
            name="b.xy",
            source="src",
            sha1="b",
            corpus_count=1,
            opaque_ord1=bytes.fromhex("08 08 00 01 08 08 03 00 00 16 01"),
            patterns_ord2=(9, 9, 2, 1, 1, 9, 9, 2),
        ),
        _hybrid_file(
            name="c.xy",
            source="src",
            sha1="c",
            corpus_count=1,
            opaque_ord1=bytes.fromhex("08 08 00 00 08 08 03 00 00 16 01"),
            patterns_ord2=(9, 9, 2, 1, 1, 9, 1, 9),
        ),
    ]

    assert _family_focus_lines(group) == [
        "  fixed-vector families:",
        "    P9,P9,P2,P1,P1,P9,P9,P2 -> 2 opaque forms; varying opaque bytes: 3; examples: a.xy, b.xy",
        "  fixed-opaque families:",
        "    08 08 00 00 08 08 03 00 00 16 01 -> 2 vectors; varying lanes: T7, T8; examples: a.xy, c.xy",
    ]
