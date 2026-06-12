from pathlib import Path

from xy.drum_sample_inspection import inspect_drum_samples_bytes


ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT / "src" / "app-sample-probes" / "2026-06-sample-paths"


def _track1_voices(path: Path):
    inspection = inspect_drum_samples_bytes(path.read_bytes())
    by_track = {track.track: track for track in inspection.tracks}
    assert 1 in by_track, f"expected drum track 1, got {sorted(by_track)}"
    return by_track[1].voices


def test_baseline_pp_kit_voice_paths() -> None:
    voices = _track1_voices(PROBES / "c0-baseline.xy")

    assert voices[0].path == "/fat32/presets/drum/pp.preset/unnamed-f#2-31.wav"
    assert voices[1].path == "/fat32/presets/drum/pp.preset/unnamed-g2-31.wav"
    assert voices[2].path == "/fat32/presets/drum/pp.preset/unnamed-g#2-31.wav"
    assert len(voices) == 24


def test_single_voice_swap_to_fx_sample_is_isolated() -> None:
    baseline = _track1_voices(PROBES / "c0-baseline.xy")
    cases = [
        ("c1-v23-fx-a2-3.xy", 23, "/fat32/presets/fx/nt-z-fx.preset/unnamed-a2-3.wav"),
        ("c2-v00-fx-a3-3.xy", 0, "/fat32/presets/fx/nt-z-fx.preset/unnamed-a3-3.wav"),
        ("c3-v01-fx-b2-4.xy", 1, "/fat32/presets/fx/nt-z-fx.preset/unnamed-b2-4.wav"),
    ]

    for filename, voice, expected_path in cases:
        voices = _track1_voices(PROBES / filename)
        assert voices[voice].path == expected_path
        for other_voice, before, after in zip(range(24), baseline, voices):
            if other_voice == voice:
                continue
            assert after.path == before.path, f"{filename} voice {other_voice} drifted"
