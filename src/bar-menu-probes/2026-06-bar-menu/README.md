# Bar menu probe (Scene 1 · Track 1 · Pattern 1)

> **Status:** todo · Firmware **1.1.4**
> **ID:** BAR · checklist §4 gaps (quantization, default length, per-track groove, p-lock shape)
> **Baseline:** `bar0.xy` — fresh project (`hdr0` / `prjconf0` equivalent)

## Scope

**First pass:** Scene **1**, Track **1**, Pattern **1** only. Open the **Bar** menu for T1 while P1 is active.

**Skip (already mapped):** number of bars (`track+0x01`), track scale (`track+0x06`).

**Do not add pattern notes** unless you need them to reach the bar page (blank pattern is fine).

## Checklist targets

| Row | UI control | Default | Files |
| --- | --- | --- | --- |
| `[ ]` Per-track quantization | Quantization 0–100 | **100** | `bar-q-*` |
| `[ ]` Default step length | Length 0–100 | **50** | `bar-l-*` |
| `[ ]` Per-track groove override | Groove −99…+99 | **0** | `bar-g*` (full LUT) |
| `[ ]` P-lock smoothing/shape | Interpolation (no numeric UI) | mid unknown | `bar-s-*` |

## Rules

1. Every file starts as a copy of **`bar0.xy`**; on device: open → change **one** bar-menu field → **Save** (overwrite).
2. Stay on **Scene 1 / T1 / P1** for all Phase A captures.
3. Re-copy **`bar0.xy` from PC** before each isolated row (same workflow as PCFG/HDR).
4. Do **not** change bars count, track scale, tempo, or project-config fields.
5. Record **UI values** (and encoder click counts for `bar-s-*`) in **Results** — append only.

## Workflow

1. MTP all `bar*.xy` to device.
2. Recommended order: **`bar0`** → quantization → length → groove LUT → p-lock shape.
3. Groove LUT is large — batch MTP in alphabetical chunks if needed.

---

## Capture procedure — baseline

| PC / device name | Bar menu state |
| --- | --- |
| `bar0` | Quantization **100**, Length **50**, Groove **0**, p-lock shape **factory default** |

---

## Capture procedure — Quantization

Bar menu → **Quantization**. Default **100** on `bar0`. Re-copy `bar0` before each row.

| PC filename | Procedure |
| --- | --- |
| `bar-q-min.xy` | Turn to **minimum (0)** |
| `bar-q-minp1.xy` | From min: **+1 click** |
| `bar-q-minp2.xy` | From min: **+2 clicks** |
| `bar-q-max.xy` | Turn to **maximum (100)** |
| `bar-q-maxm1.xy` | From max: **−1 click** |
| `bar-q-maxm2.xy` | From max: **−2 clicks** |

---

## Capture procedure — Length (default step length)

Bar menu → **Length**. Default **50** on `bar0`. Re-copy `bar0` before each row.

| PC filename | Procedure |
| --- | --- |
| `bar-l-l1.xy` | From 50: **1 click left** |
| `bar-l-l2.xy` | From 50: **2 clicks left** |
| `bar-l-r1.xy` | From 50: **1 click right** |
| `bar-l-r2.xy` | From 50: **2 clicks right** |
| `bar-l-min.xy` | Turn to **minimum (0)** |
| `bar-l-minp1.xy` | From min: **+1 click** |
| `bar-l-minp2.xy` | From min: **+2 clicks** |
| `bar-l-max.xy` | Turn to **maximum (100)** |
| `bar-l-maxm1.xy` | From max: **−1 click** |
| `bar-l-maxm2.xy` | From max: **−2 clicks** |

---

## Capture procedure — Per-track groove (full UI LUT)

Bar menu → **Groove** (per-track swing override — **not** global tempo groove type @ `0x03`).

Default **0** on `bar0`. UI uses a **non-uniform** step table (not linear). Capture **every** listed value; negatives mirror positives.

### Positive values (43 steps + zero)

| PC filename | Set groove UI to |
| --- | --- |
| `bar-g0.xy` | **0** (same as `bar0` — optional confirm save) |
| `bar-gpXXX.xy` | Set groove UI to **+XXX** |
| `bar-gnXXX.xy` | Set groove UI to **-XXX** |

i did a limited sweep, since doing everything is too cumbersome.

The exact range of values attainable on the device is
```
ids = [2,4,7,9,11,14,16,18,21,23,25,28,30,32,35,37,39,42,44,46,49,51,53,56,58,60,63,65,67,70,72,75,77,79,82,84,86,89,91,93,96,98,99]
```
those, and zero ("-"), and all negative counterparts.

---

## Capture procedure — P-lock interpolation shape

Bar menu → **p-lock interpolation / shape** (no numeric readout). Re-copy `bar0` before each row. Count **encoder clicks from default**.

| PC filename | Procedure |
| --- | --- |
| `bar-s-min.xy` | Turn shape to **minimum** (count clicks from default) |
| `bar-s-minp1.xy` | From min: **+1 click** |
| `bar-s-minp2.xy` | From min: **+2 clicks** |
| `bar-s-max.xy` | Turn shape to **maximum** |
| `bar-s-maxm1.xy` | From max: **−1 click** |
| `bar-s-maxm2.xy` | From max: **−2 clicks** |

Record click counts and any visible icon/curve change in Results.

---

## Phase B — cross-context spot checks (later)

After T1/P1 decode, add **separate** files (do not block Phase A):

| Probe | Intent |
| --- | --- |
| Scene 2, T1, P1 — set groove **+14** | Same byte as `bar-gp014`? |
| Scene 1, T2, P1 — set length **0** | Per-track length storage |
| Scene 1, T1, P2 — set quantization **0** | Per-pattern vs per-track |

Create new filenames when ready (e.g. `bar-x-s2-gp014.xy`).

---

## File count

| Block | Files |
| --- | ---: |
| Baseline `bar0` | 1 |
| Quantization sweep | 10 |
| Length sweep | 10 |
| Groove LUT (0 + 43 + 43) | 87 |
| P-lock shape | 6 |
| **Total** | **114** |

(`bar-g0` duplicates `bar0` defaults — included for LUT completeness; you may skip re-saving if identical to `bar0`.)

---

## Results

### Baseline (`bar0`)

| Field | UI | Byte(s) @ track offset | Status |
| --- | --- | --- | --- |
| Quantization | 100 | `+0x07 = FF` | raw byte pinned; UI scaling partial |
| Length | 50 | `+0x02 = F0 00` (`240` ticks) | decoded |
| Groove | 0 | `+0x08 = 00` | raw/LUT byte pinned; partial sweep |
| P-lock shape | default | `+0x3056 = 00` | decoded raw storage |

### Groove LUT decode

`TRACK+0x08` stores the per-track groove override as a raw signed/LUT byte.
The limited sweep suggests most positive values follow the same 3-unit raw
ladder as the negative captures, but `bar-gp002.xy` stores `0x09`, matching
`bar-gp007.xy`; treat that capture as anomalous until re-probed.

| PC filename | UI groove | Stored raw | Signed raw |
| --- | --- | --- | --- |
| `bar-g0.xy` | 0 | `00` | 0 |
| `bar-gn002.xy` | -2 | `FD` | -3 |
| `bar-gn004.xy` | -4 | `FA` | -6 |
| `bar-gn007.xy` | -7 | `F7` | -9 |
| `bar-gn009.xy` | -9 | `F4` | -12 |
| `bar-gn011.xy` | -11 | `F1` | -15 |
| `bar-gp002.xy` | +2 | `09` | +9 |
| `bar-gp004.xy` | +4 | `06` | +6 |
| `bar-gp007.xy` | +7 | `09` | +9 |
| `bar-gp009.xy` | +9 | `0C` | +12 |
| `bar-gp011.xy` | +11 | `0F` | +15 |
| `bar-gp014.xy` | +14 | `12` | +18 |
| `bar-gp016.xy` | +16 | `15` | +21 |
| `bar-gp018.xy` | +18 | `18` | +24 |
| `bar-gp051.xy` | +51 | `42` | +66 |
| `bar-gp053.xy` | +53 | `45` | +69 |
| `bar-gp056.xy` | +56 | `48` | +72 |
| `bar-gp058.xy` | +58 | `4B` | +75 |
| `bar-gp060.xy` | +60 | `4E` | +78 |

### Quant / length / shape

| PC filename | Status | UI | Decoded |
| --- | --- | --- | --- |
| `bar-q-min.xy` | decoded | quant 0 | `+0x07 = 00` |
| `bar-q-minp1.xy` | decoded | near min +1 | `+0x07 = 04` |
| `bar-q-minp2.xy` | decoded | near min +2 | `+0x07 = 07` |
| `bar-q-maxm2.xy` | decoded | near max -2 | `+0x07 = FC` |
| `bar-q-maxm1.xy` | decoded | near max -1 | `+0x07 = FE` |
| `bar-q-max.xy` | anomalous | max/default | quant stayed `FF`; length changed to `244` ticks |
| `bar-l-min.xy` | decoded | length 0/min | `+0x02 = 04 00` (`4` ticks) |
| `bar-l-minp1.xy` | decoded | min +1 | `+0x02 = 08 00` (`8`) |
| `bar-l-minp2.xy` | decoded | min +2 | `+0x02 = 0C 00` (`12`) |
| `bar-l-l2.xy` | decoded | 50 -2 clicks | `+0x02 = E8 00` (`232`) |
| `bar-l-l1.xy` | decoded | 50 -1 click | `+0x02 = EC 00` (`236`) |
| `bar-l-r1.xy` | decoded | 50 +1 click | `+0x02 = F8 00` (`248`) |
| `bar-l-r2.xy` | decoded | 50 +2 clicks | `+0x02 = FC 00` (`252`) |
| `bar-l-maxm2.xy` | decoded | max -2 | `+0x02 = D8 01` (`472`) |
| `bar-l-maxm1.xy` | decoded | max -1 | `+0x02 = DC 01` (`476`) |
| `bar-l-max.xy` | decoded | max | `+0x02 = E0 01` (`480`) |
| `bar-s-min.xy` | decoded | min/default | `+0x3056 = 00` |
| `bar-s-minp1.xy` | decoded | min +1 | `+0x3056 = 04` |
| `bar-s-minp2.xy` | decoded | min +2 | `+0x3056 = 08` |
| `bar-s-maxm2.xy` | decoded | max -2 | `+0x3056 = F7` |
| `bar-s-maxm1.xy` | decoded | max -1 | `+0x3056 = FB` |
| `bar-s-max.xy` | decoded | max | `+0x3056 = FF` |

Most non-shape edits also flip the T1 pristine flag at `+0x11` from `08 00` to
`00 00`. Repeated T9-T16 `+0x38F2/+0x38F6` changes from `00` to `40` are the
same save-side noise seen in PCFG/HDR probes.

Implementation note: BAR offsets mutate the old signature range used by
`ImageProject._rescan()`, so `xy/bar_menu_inspection.py` reads these baseline
shape probes by canonical decoded-image track base/stride.

---

## After capture

Promoted to `xy-format-fork/src/bar-menu-probes/2026-06-bar-menu/`. Log:
`docs/logs/2026-06-13_bar_menu_inspection.md`.
