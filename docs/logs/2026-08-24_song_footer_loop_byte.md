# Song Footer Loop Byte

**Date:** 2026-08-24  
**Fixtures:** `unnamed 150.xy`, `unnamed 154.xy`, `unnamed 155.xy`

Decoded song slots are variable-length records:

```text
[scene count][scene IDs...][loop][reserved 00]
```

The loop field is one byte: `0` is on and `1` is off. The final byte remains
zero. `unnamed 155.xy` is the operator-confirmed Song 2 loop-on capture and its
Song 2 slot ends `00 00`; `unnamed 154.xy` is loop-off and ends `01 00`.

The browser reader previously required `00 01` for loop-on, a raw/RLE-era
interpretation that made real decoded projects display loop-off. Python and
XYBuddy now share the decoded rule, emit canonical `[loop][00]`, and can parse
or rewrite any of the 14 serialized song slots.

## Production verification

Commit `c6d5867` deployed successfully. A production browser session loaded
`unnamed 155.xy`: Song 1 displayed **loop on**, Next Song displayed Song 2 with
**loop on** and chain `1 → 2 → 3`, and the console reported zero errors and
zero warnings.
