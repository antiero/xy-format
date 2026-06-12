# Scene track mute inspection (P2-E)

**Date:** 2026-06-12  
**Firmware:** 1.1.4  
**Fixtures:** `src/app-scene-probes/2026-06-track-mutes/`  
**Operator README:** `user_probes/2026-06-track-mutes/README.md`

## Summary

Per-scene track mutes are **not** stored with mixer volumes on track structs.
They live in the **33-byte scene slot** mute region (`slot + 16 .. slot + 31`),
separate from P2-D volume bytes (`track+0x38FE`).

On a **single-scene** project, Scene 1 mutes are written to **slot 0**
(`GLOBAL+0x95`). Muted tracks use byte value **`0x02`**; unmuted = `0x00`.
This matches `build_arrangement` / `tests/test_image_writer.py`.

## Slot layout (recap)

| Offset in slot | Field |
| --- | --- |
| `+0..15` | pattern sel per track |
| `+16..31` | mute per track |
| `+32` | flags |

## Scene 1 captures

| File | Muted tracks | Diffs vs baseline |
| --- | --- | --- |
| `mute-#-#-#-#.xy` | — | — |
| `mute-1-3-6-7.xy` | 1,3,6,7 | slot0 mute bytes only (+ M4 session noise on T9+) |
| `mute-2-7-8-#.xy` | 2,7,8 | **3** bytes in mute region only |
| `mute-3-4-5-6.xy` | 3,4,5,6 | slot0 mute bytes only |

## API

`xy/scene_volume_inspection.py`:

- `read_scene_slot_mute_bytes(project, scene_slot)`
- `read_scene_muted_tracks(project, scene_slot)` → 1-based track numbers

## Open

- **Scene 2+ slot index** — hypothesis: scene *N* on multi-scene project uses
  slot *N* (slot 1 = pattern row for scene 1 in `s0b`). Awaiting `mute2-*`
  captures.

## Related

- P2-D scene volumes: `docs/logs/2026-06-12_scene_volume_inspection.md`
- Writer: `xy/image_writer.py` (`SCENE_MUTE_VALUE = 2` in arrangement builder)
