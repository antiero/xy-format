"""LEGACY (pre-RLE model) — superseded by xy/image_writer.py.
New authoring should use the decoded-image path
(docs/engineering/authoring.md). Retained for its validated scopes.

High-level scene patching for OP-XY .xy files.

Follows the project_builder.py pattern: immutable XYProject in → new XYProject out.
Coordinates all four regions that must be updated together for scene operations:

1. Pre-track scene record region (insert/remove/rewrite)
2. Pre-track ordinal byte (pre[0x0F])
3. Track 1 preamble byte[0] (scene-coupled)
4. Track 16 scene list (count + IDs at body offset 0x6E7)

Usage:
    project = XYProject.from_bytes(data)
    new_project = patch_add_scene(project, scene_id=3, overrides=[(3, 1)])
    new_data = new_project.to_bytes()
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Sequence, Tuple

from .container import TrackBlock, XYProject
from .scene_records import (
    SCENE_FORMAT_MATRIX_RECORDS,
    T16_SCENE_COUNT_OFFSET,
    T16_SCENE_IDS_OFFSET,
    decode_scene_region,
    decode_matrix_scene_vectors,
    detect_scene_region_format,
    encode_matrix_scene_vector,
    encode_scene_record,
    encode_scene_record_general,
    find_scene_region,
    read_scene_assignments,
    t1_preamble_for_record_count,
    write_t16_scene_list,
)


# ── Scene ordinal ────────────────────────────────────────────────────

ORDINAL_OFFSET = 0x0F


def _read_ordinal(pre_track: bytes) -> int:
    return pre_track[ORDINAL_OFFSET]


# ── Add scene ─────────────────────────────────────────────────────────

def patch_add_scene(
    project: XYProject,
    scene_id: int,
    overrides: Sequence[Tuple[int, int]],
) -> XYProject:
    """Add a new scene to the project.

    Coordinates all four regions:
      1. Insert scene record(s) before handle table
      2. Increment ordinal at pre[0x0F]
      3. Recompute T1 preamble[0] from new record count
      4. Increment T16 scene count and append scene_id

    Args:
        project: Source project (not modified).
        scene_id: 0-based scene ID to add (e.g., 3 for Scene 4).
        overrides: List of (track_1based, pattern_0based) tuples.
            Each must reference a pattern that exists on the target track.
            Only corpus-validated combinations are accepted.

    Returns:
        New XYProject with the scene added.

    Raises:
        ValueError: If override combination is not corpus-validated.
    """
    pre = bytearray(project.pre_track)

    # 1. Insert scene record(s) before handle table
    _, ht_start = find_scene_region(project.pre_track)
    record_bytes = b""
    for track, pattern in overrides:
        record_bytes += encode_scene_record(track, pattern)
    new_pre = bytes(pre[:ht_start]) + record_bytes + bytes(pre[ht_start:])

    # 2. Increment ordinal
    new_pre = bytearray(new_pre)
    old_ordinal = new_pre[ORDINAL_OFFSET]
    new_ordinal = old_ordinal + 1
    new_pre[ORDINAL_OFFSET] = new_ordinal
    new_pre = bytes(new_pre)

    # 3. T1 preamble: recompute from new record count
    #    T1p = 0xD6 - (record_count + 1) * 0x21 (file 14 confirmed)
    t1 = project.tracks[0]
    old_records = decode_scene_region(project.pre_track)
    new_record_count = len(old_records) + len(overrides)
    new_t1_byte0 = t1_preamble_for_record_count(new_record_count)
    if new_t1_byte0 < 0:
        raise ValueError(
            f"T1 preamble underflow for {new_record_count} records: "
            f"0x{new_t1_byte0 & 0xFF:02X}"
        )
    new_t1 = TrackBlock(
        index=0,
        preamble=bytes([new_t1_byte0]) + t1.preamble[1:],
        body=t1.body,
    )

    # 4. T16: increment count, append scene_id
    t16 = project.tracks[15]
    t16_body = bytearray(t16.body)
    old_count = t16_body[T16_SCENE_COUNT_OFFSET]
    t16_body[T16_SCENE_COUNT_OFFSET] = old_count + 1
    insert_pos = T16_SCENE_IDS_OFFSET + old_count
    new_t16_body = (
        bytes(t16_body[:insert_pos])
        + bytes([scene_id])
        + bytes(t16_body[insert_pos:])
    )
    new_t16 = TrackBlock(
        index=15, preamble=t16.preamble, body=new_t16_body
    )

    # Rebuild tracks
    new_tracks = [new_t1] + list(project.tracks[1:15]) + [new_t16]
    return XYProject(new_pre, new_tracks)


# ── Remove scene ──────────────────────────────────────────────────────

def patch_remove_scene(
    project: XYProject,
    record_start: int,
    record_end: int,
    scene_id: int,
) -> XYProject:
    """Remove a scene from the project.

    Inverse of patch_add_scene. Requires knowing the exact byte offsets
    of the record to remove (use find_scene_region + decode_scene_region
    to locate records).

    Args:
        project: Source project (not modified).
        record_start: Byte offset in pre_track where the record starts.
        record_end: Byte offset in pre_track where the record ends.
        scene_id: 0-based scene ID to remove from T16 list.

    Returns:
        New XYProject with the scene removed.
    """
    pre = project.pre_track

    # 1. Remove record bytes
    new_pre = bytearray(pre[:record_start] + pre[record_end:])

    # 2. Decrement ordinal
    old_ordinal = new_pre[ORDINAL_OFFSET]
    if old_ordinal <= 0:
        raise ValueError(f"ordinal already 0, cannot decrement")
    new_pre[ORDINAL_OFFSET] = old_ordinal - 1
    new_pre = bytes(new_pre)

    # 3. T1 preamble: recompute from new record count
    #    After removing one record, count decreases by 1
    t1 = project.tracks[0]
    old_records = decode_scene_region(project.pre_track)
    new_record_count = len(old_records) - 1
    if new_record_count < 0:
        new_record_count = 0
    new_t1_byte0 = t1_preamble_for_record_count(new_record_count)
    new_t1 = TrackBlock(
        index=0,
        preamble=bytes([new_t1_byte0]) + t1.preamble[1:],
        body=t1.body,
    )

    # 4. T16: decrement count, remove scene_id
    t16 = project.tracks[15]
    t16_body = bytearray(t16.body)
    old_count = t16_body[T16_SCENE_COUNT_OFFSET]
    t16_body[T16_SCENE_COUNT_OFFSET] = old_count - 1
    # Find and remove the scene_id byte
    ids_start = T16_SCENE_IDS_OFFSET
    ids_end = ids_start + old_count
    ids = list(t16_body[ids_start:ids_end])
    if scene_id not in ids:
        raise ValueError(f"scene_id {scene_id} not in T16 list: {ids}")
    idx = ids.index(scene_id)
    remove_pos = ids_start + idx
    new_t16_body = (
        bytes(t16_body[:remove_pos]) + bytes(t16_body[remove_pos + 1 :])
    )
    new_t16 = TrackBlock(
        index=15, preamble=t16.preamble, body=new_t16_body
    )

    new_tracks = [new_t1] + list(project.tracks[1:15]) + [new_t16]
    return XYProject(new_pre, new_tracks)


# ── Modify scene record ──────────────────────────────────────────────

def patch_modify_scene_record(
    project: XYProject,
    record_start: int,
    record_end: int,
    new_record: bytes,
) -> XYProject:
    """Replace a scene record's bytes in the pre-track region.

    Only modifies the record bytes; does not change ordinal, T1 preamble,
    or T16 scene list. Use this for record-only rewrites (e.g., changing
    which track/pattern a scene overrides).

    Args:
        project: Source project (not modified).
        record_start: Byte offset in pre_track where the old record starts.
        record_end: Byte offset in pre_track where the old record ends.
        new_record: New record bytes to insert.

    Returns:
        New XYProject with the record replaced.
    """
    pre = project.pre_track
    new_pre = pre[:record_start] + new_record + pre[record_end:]
    return XYProject(new_pre, project.tracks)


# ── Batch scene addition ──────────────────────────────────────────────

def patch_add_scenes(
    project: XYProject,
    scenes: Sequence[Tuple[int, List[Tuple[int, int]]]],
) -> XYProject:
    """Add multiple scenes to the project in one operation.

    Uses the generalized encoder (encode_scene_record_general) to support
    any T1-T8 × P2-P9 combination. Coordinates all four regions:
      1. Insert scene record(s) before handle table
      2. Increment ordinal at pre[0x0F] for each scene
      3. Recompute T1 preamble[0] from new total record count
      4. Update T16 scene list with new scene IDs

    Args:
        project: Source project (not modified).
        scenes: List of (scene_id, overrides) tuples where:
            - scene_id: 0-based scene ID
            - overrides: List of (track_1based, pattern_0based) tuples

    Returns:
        New XYProject with all scenes added.

    Example:
        patch_add_scenes(project, [
            (3, [(4, 1)]),          # Scene 4: T4→P2
            (4, [(3, 1), (4, 2)]),  # Scene 5: T3→P2 + T4→P3
        ])
    """
    pre = bytearray(project.pre_track)

    # Count existing records
    old_records = decode_scene_region(project.pre_track)
    existing_record_count = len(old_records)

    # 1. Build all new record bytes
    _, ht_start = find_scene_region(project.pre_track)
    new_record_bytes = b""
    total_new_records = 0
    for scene_id, overrides in scenes:
        for i, (track, pattern) in enumerate(overrides):
            # First record overall in the region uses compact form (is_first=True)
            # only if there are NO existing records AND this is the first override
            # of the first scene being added.
            is_first = (existing_record_count == 0 and total_new_records == 0)
            new_record_bytes += encode_scene_record_general(
                track, pattern, is_first=is_first
            )
            total_new_records += 1

    # Insert before handle table
    new_pre = bytes(pre[:ht_start]) + new_record_bytes + bytes(pre[ht_start:])

    # 2. Increment ordinal for each scene added
    new_pre = bytearray(new_pre)
    old_ordinal = new_pre[ORDINAL_OFFSET]
    new_pre[ORDINAL_OFFSET] = old_ordinal + len(scenes)
    new_pre = bytes(new_pre)

    # 3. T1 preamble: recompute from new total record count
    new_record_count = existing_record_count + total_new_records
    new_t1_byte0 = t1_preamble_for_record_count(new_record_count)
    if new_t1_byte0 < 0:
        raise ValueError(
            f"T1 preamble underflow for {new_record_count} records: "
            f"0x{new_t1_byte0 & 0xFF:02X}"
        )
    t1 = project.tracks[0]
    new_t1 = TrackBlock(
        index=0,
        preamble=bytes([new_t1_byte0]) + t1.preamble[1:],
        body=t1.body,
    )

    # 4. T16: update scene list
    t16 = project.tracks[15]
    old_count, old_ids = (
        t16.body[T16_SCENE_COUNT_OFFSET],
        list(t16.body[T16_SCENE_IDS_OFFSET : T16_SCENE_IDS_OFFSET + t16.body[T16_SCENE_COUNT_OFFSET]]),
    )
    new_ids = old_ids + [sid for sid, _ in scenes]
    new_t16_body = write_t16_scene_list(t16.body, new_ids)
    new_t16 = TrackBlock(
        index=15, preamble=t16.preamble, body=new_t16_body
    )

    # Rebuild tracks
    new_tracks = [new_t1] + list(project.tracks[1:15]) + [new_t16]
    return XYProject(new_pre, new_tracks)


def _normalize_scene_assignments(
    assignments: Mapping[int, Mapping[int, int]],
) -> Dict[int, Dict[int, int]]:
    if not assignments:
        raise ValueError("scene assignments cannot be empty")

    scene_ids = sorted(assignments)
    expected = list(range(1, len(scene_ids) + 1))
    if scene_ids != expected:
        raise ValueError(
            f"scene ids must be contiguous 1..N, got {scene_ids}"
        )

    normalized: Dict[int, Dict[int, int]] = {}
    for scene_id in scene_ids:
        row = assignments[scene_id]
        tracks = sorted(row)
        if tracks != list(range(1, 9)):
            raise ValueError(
                f"scene {scene_id} must contain tracks 1..8, got {tracks}"
            )
        normalized_row: Dict[int, int] = {}
        for track in tracks:
            pattern = int(row[track])
            if not 1 <= pattern <= 9:
                raise ValueError(
                    f"scene {scene_id} track {track}: pattern must be 1..9, got {pattern}"
                )
            normalized_row[track] = pattern
        normalized[scene_id] = normalized_row
    return normalized


def patch_set_scene_assignments(
    project: XYProject,
    assignments: Mapping[int, Mapping[int, int]],
) -> XYProject:
    """Rewrite all existing scene pattern assignments from a full scene map.

    `assignments` is keyed by 1-based scene number and track number:
      {scene: {track: pattern_1based}}

    Current constraints:
    - Scene count must match the existing project (no add/remove in this API).
    - Matrix-family files (`unnamed 156` style) are rewritten in matrix form.
    - Tag-record files are rewritten as sparse overrides relative to Scene 1.
    """
    desired = _normalize_scene_assignments(assignments)
    current = read_scene_assignments(project)
    if not current:
        raise ValueError(
            "scene assignments unavailable for this encoding family; "
            "current parser supports tag-record and matrix-record families"
        )

    if sorted(current) != sorted(desired):
        raise ValueError(
            f"scene ids must match existing file exactly; existing={sorted(current)} requested={sorted(desired)}"
        )

    fmt = detect_scene_region_format(project.pre_track)
    start, end = find_scene_region(project.pre_track)
    pre = project.pre_track

    if fmt == SCENE_FORMAT_MATRIX_RECORDS:
        vectors, trailing = decode_matrix_scene_vectors(project.pre_track)
        if len(vectors) != len(desired):
            raise ValueError(
                f"matrix scene count mismatch: existing={len(vectors)} requested={len(desired)}"
            )

        new_records: List[bytes] = []
        for scene_id in range(1, len(vectors) + 1):
            patterns_0based = [desired[scene_id][track] - 1 for track in range(1, 9)]
            new_records.append(
                encode_matrix_scene_vector(
                    patterns_0based,
                    widths_hint=vectors[scene_id - 1].widths,
                )
            )
        new_region = b"".join(new_records) + trailing
        new_pre = pre[:start] + new_region + pre[end:]
        return XYProject(new_pre, project.tracks)

    # Tag-record family: encode sparse overrides vs Scene 1 base.
    region = pre[start:end]
    old_records = decode_scene_region(pre)
    consumed = sum(len(record.raw) for record in old_records)
    trailing = region[consumed:]

    base = desired[1]
    new_record_bytes = b""
    record_count = 0
    for scene_id in range(2, len(desired) + 1):
        row = desired[scene_id]
        for track in range(1, 9):
            target_pattern = row[track]
            base_pattern = base[track]
            if target_pattern == base_pattern:
                continue
            if target_pattern == 1 and base_pattern != 1:
                raise ValueError(
                    f"scene {scene_id} track {track}: explicit P1 override is not encodable in tag-record form"
                )
            if target_pattern == 1:
                continue
            is_first = record_count == 0
            new_record_bytes += encode_scene_record_general(
                track, target_pattern - 1, is_first=is_first
            )
            record_count += 1

    new_region = new_record_bytes + trailing
    new_pre = pre[:start] + new_region + pre[end:]

    t1 = project.tracks[0]
    new_t1_byte0 = t1_preamble_for_record_count(record_count)
    new_t1 = TrackBlock(
        index=0,
        preamble=bytes([new_t1_byte0]) + t1.preamble[1:],
        body=t1.body,
    )
    new_tracks = [new_t1] + list(project.tracks[1:])
    return XYProject(new_pre, new_tracks)
