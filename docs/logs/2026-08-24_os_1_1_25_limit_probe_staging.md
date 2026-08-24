# OS 1.1.25 Limit-Probe Staging

**Device:** OP-XY serial `XXYVP11X`  
**Firmware:** 1.1.25  
**Transport:** XYBuddy `xybuddy-mtp` helper on macOS

The ordered projects from `tools/build_limit_probes.py` were uploaded to
`/projects/templates` without changing `/projects/workspace.xy` or any user
project. A new download of each MTP object matched its local SHA-256 exactly:

| Object | Template | SHA-256 |
| ---: | --- | --- |
| 311 | `01_scenes99.xy` | `8b6e614cca30dc4f840228cf13115ff0bcf4cc1e60796ba094186af68caf6347` |
| 312 | `02_song96.xy` | `c4b93e39a2bc87c1377a8cf29e58656bd8a3a63e644e95707b44b3da6177c9b3` |
| 313 | `03_patterns16.xy` | `3a801a7351ccad350aba424d0a5574d6dd1242a24ce3b63985cc4157557e9a35` |
| 314 | `04_notes120.xy` | `8e081e5650df976dcba5993ef0464ef4ca6f8ca822b44d4ed44b074265b8fe31` |

This proves current-firmware MTP compatibility and transfer integrity only.
The roadmap boxes remain open until an operator selects the last scene/song
entry or pattern and observes the 120-note project load/play on the device.

## Production XYBuddy check

After commit `a358dcc` deployed successfully, a headed browser session loaded
the device-authored `unnamed 155.xy` fixture from `https://xybuddy.xyz/`.
Song Mode showed Song 1's one-scene chain; **Next Song** selected Song 2 and
showed the captured `1 → 2 → 3` chain. The browser console reported zero errors
and zero warnings. This covers the deployed reader and song navigation; the
MTP hashes above cover the native helper/device boundary.

## Post-upstream-sync revalidation

After merging `kmorrill/main` and adding the firmware-layout reader follow-up
at `2b557ae`, the connected device still enumerated as VID `0x2367`, PID
`0x0021`. A fresh `/projects/templates` listing returned the same four object
IDs and sizes. Each object was downloaded again and checked with:

```bash
python tools/build_limit_probes.py --verify-dir /tmp/xybuddy-cert-WrTRx1
```

All four copies remained byte-identical to freshly generated output and passed
generated-project preflight. Each retained one expected warning inherited from
the baseline's T8 Multisampler: zone boundaries/root keys remain opaque and
are preserved but cannot yet be preflighted. No front-panel acceptance claim
is inferred from these MTP-only checks.
