# P-lock rotation carry-curve capture — 2026-08-26

## Question

Why did a generated Param 1 lock display as `-12.00` after sequence rotation,
even though the source lock displayed at its intended value?

## Device evidence

- Device: connected OP-XY
- Firmware: 1.1.25
- Transport: macOS MTP
- Captures: `pr24-p1-native.xy`, `pr24-p2-manual.xy`, and
  `pr24-p2-native.xy`

The device-generated Step 7 `+9.00` lock had two non-zero Param 1 value cells:
Step 6 contained `0x6FFF` and the armed Step 7 contained `0x7000`. After the
native sequence-left operation, the device image contained:

- Step 5: `0x6FFF`
- Step 6: `0x7000`, armed
- Step 7: `0x7000`, retained but unarmed

The step component moved from Step 7 to Step 6 and the Param 1 UI
current-value cache was cleared. A separate native right shift showed the same
copy-without-source-clearing behavior around a Step 1 lock.

This demonstrates that p-lock value cells form a sparse carry/cache curve.
The per-step activation row determines where the lock applies; a native shift
does not circularly rotate and clear the value rows.

## Implementation and regression

`ImageProject.set_plock()` now seeds an empty, unarmed predecessor cell with
`value - 1`. `ImageProject.rotate_pattern()` copies non-zero value cells into
their shifted destinations without clearing source cells, rotates the
activation and step-component rows normally, and clears the affected UI cache.

The generated verification pair `e_rot_fixed_src.xy` and
`f_rot_fixed_expected.xy` was copied to the same OP-XY, read back byte-for-byte,
and checked from the front panel. The source locks displayed `-9.00` and
`+9.00`; after rotation both retained those values at the expected destination
steps, with Multiply ×3 and Hold ×2 moving alongside their notes.
