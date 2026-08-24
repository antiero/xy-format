# Next Device Captures — OS 1.1.25

Use a fresh project for each independent A/B unless the row says to continue
from the previous file. Keep these exact short names so alphabetical order is
the test order. Save on OP-XY OS 1.1.25, then download with XYBuddy.

| Order / filename | Starting state | Exact saved change | Comparison / purpose |
| --- | --- | --- | --- |
| `01_fw125_base.xy` | New project | Save without edits. | Firmware-1.1.25 baseline for every later diff. |
| `02_fw125_scale_x3.xy` | Reopen `01` | T1 Bar page: set track scale to x3; save. | Confirms track `+0x06 == 0x06`. |
| `03_fw125_scale_x5.xy` | Reopen `01` | T1 Bar page: set track scale to x5; save. | Confirms track `+0x06 == 0x08`. |
| `04_fw125_scale_x6.xy` | Reopen `01` | T1 Bar page: set track scale to x6; save. | Confirms track `+0x06 == 0x09`. |
| `05_fw125_scale_x7.xy` | Reopen `01` | T1 Bar page: set track scale to x7; save. | Confirms track `+0x06 == 0x0A`. |
| `06_fw125_multi_x0.xy` | New project | T1: load one audible factory multisample, set global transpose 0, play middle C to confirm audio, save. | Fresh multisampler project-state baseline. |
| `07_fw125_multi_x12.xy` | Reopen `06` | Set global transpose +12; do not touch the preset; save. | Isolates 1.1.25 multisample/global-transpose state. |
| `08_fw125_arp_p1.xy` | New project | T1: enable Arpeggio player with its defaults on Pattern 1; save. | Locates player enable/type and default Arp block. |
| `09_fw125_arp_p2.xy` | Continue from `08` | Add Pattern 2 without changing player type; save while P2 is selected. | Tests 1.1.25 player-type inheritance across patterns. |
| `10_fw125_hold_p1.xy` | New project | T1: enable Hold player with defaults; save. | Locates Hold type/state for the new note-off behavior surface. |

For each downloaded file:

```sh
python tools/corpus_lab.py record <file.xy> pass --note "OS 1.1.25 device save"
python tools/analysis/decoded_diff.py 01_fw125_base.xy <file.xy>
```

If any authored probe crashes, stop the batch and follow
[`crash_capture.md`](crash_capture.md); do not continue testing later files.
