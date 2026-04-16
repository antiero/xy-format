"""Smoke tests for the musical showcase pack generator."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.analysis.write_music_showcase_pack import build_showcase_payloads
from xy.container import XYProject
from xy.json_build_spec import build_xy_bytes, parse_build_spec


def test_showcase_payloads_build_and_roundtrip(tmp_path: Path) -> None:
    payloads = build_showcase_payloads(output_dir=tmp_path)
    assert [piece.slug for piece, _ in payloads] == [
        "01_neon_rain_runner",
        "02_dustlight_cascade",
        "03_voltage_meridian",
    ]

    for piece, payload in payloads:
        spec = parse_build_spec(payload, base_dir=REPO_ROOT)
        assert spec.topology_policy == "bootstrap_t1_t8_p9"
        assert spec.scene_assignments == {}
        assert spec.song_arrangement == []
        assert len(spec.multi_tracks) == 8
        assert all(len(track.patterns) == 9 for track in spec.multi_tracks)
        raw = build_xy_bytes(spec)
        project = XYProject.from_bytes(raw)
        assert len(project.tracks) == 16
        assert len(piece.patterns) == 9
