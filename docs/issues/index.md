# Issues Index

## Active
- Crash handling protocol and artifacts: `docs/workflows/crash_capture.md`

## Resolved by the 2026-06-09 serialization-model breakthrough
See `docs/state_of_understanding.md` and `docs/format/record_structure.md`.
- **Sparse multi-pattern topology crash**: `docs/issues/sparse_topology_stability.md`
  — incoherent writer state, not sparseness; device-confirmed fix.
- Pointer-tail / pointer-21 and preamble state-machine issues were removed as
  standalone docs; both are now historical wrong-model entries in
  `docs/state_of_understanding.md` and old logs.
- Writer type/padding misalignment (`0x05`/`0x07`) — was the `+0x11`
  pristine flag's RLE shadow.
- Multi-track preamble propagation / `num_patterns > 0` crashes — RLE/
  state-coherence artifacts.

## Cleanup / Follow-up Candidates
- Keep active issues focused on decoded-image behavior, not old raw-byte
  grammar hypotheses.
