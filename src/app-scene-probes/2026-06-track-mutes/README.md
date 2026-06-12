# P2-E — Scene track mute fixtures

> **Status:** partial — scene 1 only

**Capture procedure:**
[`user_probes/2026-06-track-mutes/README.md`](../../../../user_probes/2026-06-track-mutes/README.md)

4 files (scene 1, single-scene project). Scene 2+ pending operator capture.

| File | Muted tracks (slot 0) |
| --- | --- |
| `mute-#-#-#-#.xy` | none |
| `mute-1-3-6-7.xy` | T1, T3, T6, T7 |
| `mute-2-7-8-#.xy` | T2, T7, T8 |
| `mute-3-4-5-6.xy` | T3–T6 |

Log: `docs/logs/2026-06-12_scene_track_mute_inspection.md`  
Tests: `tests/test_scene_track_mute_inspection.py`  
API: `xy/scene_volume_inspection.py` (`read_scene_muted_tracks`)
