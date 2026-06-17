# 2026-06 T9 Brain Probe Plan

> **Status:** captured/analyzed · Firmware **1.1.4**
> **Baseline source:** `src/bar-menu-probes/2026-06-bar-menu/bar0.xy`
> **Probe vehicle:** Track **9** (Brain).

Goal: isolate Brain track settings, routing, linked-track state, and any
recorded Brain sequence storage.

## Planned Captures

| File | Device action | Notes |
| --- | --- |
| `t09-brain-mode-manual.xy` | Set Brain mode to manual. | Manual - c major |
| `t09-brain-mode-auto.xy` | Set Brain mode to auto. | Auto - same as default. also detects as c major. |
| `t09-brain-key-d.xy` | Set key/root to D | manual - key d major. expect increment of 2 semitones from c major.|
| `t09-brain-scale-minor.xy` | Set scale to minor. | manual - scale C minor (index 6). |
| `t09-brain-link-t1.xy` | Link T1. | default is not linked |
| `t09-brain-link-t2.xy` | Link T2. | default is not linked |
| `t09-brain-link-t3.xy` | Link T3. | default is not linked |
| `t09-brain-link-t4.xy` | Link T4. | default is not linked |
| `t09-brain-link-t5.xy` | Link T5. | default is not linked |
| `t09-brain-link-t6.xy` | Link T6. | default is not linked |
| `t09-brain-link-t7.xy` | Link T7. | default is not linked |
| `t09-brain-link-t8.xy` | Link T8. | default is not linked |
| `t09-brain-route-t1-t8.xy` | Link/control T1 through T8. | |
| `t09-brain-route-none.xy` | Route output to none. | |
| `t09-brain-route-t1-only.xy` | Route output to T1 only. | |
| `t09-brain-route-t2-only.xy` | Route output to T2 only. | |
| `t09-brain-route-t3-only.xy` | Route output to T3 only. | |
| `t09-brain-route-t4-only.xy` | Route output to T4 only. | |
| `t09-brain-route-t5-only.xy` | Route output to T5 only. | |
| `t09-brain-route-t6-only.xy` | Route output to T6 only. | |
| `t09-brain-route-t7-only.xy` | Route output to T7 only. | |
| `t09-brain-route-t8-only.xy` | Route output to T8 only. | |
| `t09-brain-seq-two-notes.xy` | Record the smallest useful Brain sequence, e.g. two notes/chords. | C on step 1, G on step 9. All "normal" sequencer stuff is available (number of bars, bar scale, etc.) so in all likelyhood this is encoded in exactly the same way as for tracks 1-8. I chose these notes so the auto brain still detects it as c major = default. same goes for the LFO settings (M4). filter (M3) is unavailable for brain (understandable since it doesnt produce sound itself)|

## Notes

Use one-variable captures first. If the UI requires changing both mode and
route before a field is visible, record that dependency in this README.

Important difference between link and route: link is singular selection / off. Route is on/off per track.

I expect route to be a 1 byte mask, which would make default (every track except 1 and 2, because those are drums):
0b00111111, or 0b11111100 is the endianness is the other way around. If these are not found, try the complements
route-t1-t8 should then be 0b11111111, and
route-t1-only should be 0b10000000, under that same hypothesis.

i dont exactly understand link semantics. Guide (section 15.1) says:
"""
rotate the white knob to link any of the instrument tracks to the brain track, this allows you to riff over your song, while transposing it live.
"""

The link state needs quite a lot of encoder clicks to change. I suspect under the hood it is a full byte and
the device is doing the floor after division trick to get out 9 distinct indices. Other evidence for this is that it if you rotate a few clicks backwards just after it changes, it changes back quickly,
but if you rotate back more clicks, it also takes more forward rotations to change it.
This is only a hypothesis however. But likely if the values found are confusing. (since the floor trick
causes many values to map to off/1/.../8, and my device authored files will have random values out of those ranges)

i counted it out: it seems like rougly 12 encoder clicks per value -> 9 values -> 108 clicks. So maybe a half byte?
It also seems inconsistent which aligns with the flooring trick.

as for the selectable scales, there are 7, its the modes of major, so
1 - major
2 - dorian
3 - phrygian
4 - lydian
5 - mixolydian
6 - minor
7 - locrian
Not sure if that is the natural order, but that is the order displayed in the UI.

## Analysis Results

Route is decoded as a T1-low bitmask at T9 track-relative `+0x09`:
`0x00` none, `0x01` T1, `0x02` T2, ..., `0x80` T8, `0xFF` all.
The baseline/default route is `0xFC`, i.e. T3-T8.

Brain key/root appears at T9 `+0x385B`. Device-authored detents are consistent
with the 12 displayed key names C, C#, D, D#, E, F, F#, G, G#, A, A#, B, but
the exact raw boundary formula is not confirmed.

Brain scale appears at T9 `+0x385F`. Device-authored detents are consistent
with the 7 displayed scale names major, dorian, phrygian, lydian, mixolydian,
minor, locrian, but the exact raw boundary formula is not confirmed.

Recorded Brain notes use the generic note vector at T9 `+0x456F`.
`t09-brain-seq-two-notes.xy` decodes as C4 on step 1 and G4 on step 9.

Link selection is located at T9 `+0x3863`, but the current captures show
encoder-bucket jitter; treat it as raw until a tighter probe isolates the
off/T1-T8 bucket boundaries.
