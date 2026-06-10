#!/usr/bin/env python3
"""Pre-track scene-record decoder (record-boundary reframe, 2026-06-09).

DECODED MODEL (validated 245/246 corpus files; the one failure is
``bleez34.xy`` — the known device-crashing file, which the firmware also
rejects):

    pre_track := fixed_header  rle_stream(n * 33 values)  00 00
                 handle_table(36B)  tail(1B)

    n    = (0xD6 - tail) / 0x21        ; the loader's record count
    tail = 0xD6 - 0x21 * n             ; serialized pool-allocator state

Each 33-byte record is a SCENE struct:

    struct Scene {
        u8 selected_pattern[16];   // 0-based pattern index per track
        u8 mute[16];               // 0 = unmuted, 2 = muted (T1=idx16 .. T16=idx31)
        u8 flags;                  // 0x01 normally, 0x00 on blank/placeholder rows
    };

The first record is the live/current selection state (what older docs
called the multi-pattern "descriptor"; Schemes A/B, v56/v57, tokens and
"collapse triggers" are all artifacts of this RLE over selection state).
Subsequent records are scenes in order.

RLE rule (one continuous stream across all records; runs may span record
boundaries): after two consecutive equal bytes, an extension count byte
follows (that many additional repeats). The old "track tag = 0x1E - track"
formula was the trailing zero-run's extension count.

The fixed header end is anchored by ``cd cc cc 00 0c 00 00 01 40``.
NOTE: the 4th track-signature byte is the TRACK SCALE (0x03 = 1x default,
0x05 = 2x, 0x0E = 16x, 0x01 = 1/2x — unnamed 20/21/22), so signature
matching must wildcard it.
"""
from __future__ import annotations

import glob
import re
import sys
from dataclasses import dataclass

SIG_RE = re.compile(rb"\x00\x00\x01[\x00-\x0f]\xff\x00\xfc\x00", re.S)
ANCHOR = bytes.fromhex("cdcccc000c00000140")
RECORD_SIZE = 33


def rle_decode(buf: bytes, start: int, n: int) -> tuple[list[int] | None, int]:
    """Decode ``n`` values; two consecutive equal bytes are followed by an
    extension count (additional repeats)."""
    out: list[int] = []
    i = start
    while len(out) < n and i < len(buf):
        v = buf[i]
        i += 1
        out.append(v)
        if len(out) >= 2 and out[-1] == out[-2] and len(out) < n:
            if i >= len(buf):
                return None, i
            out.extend([v] * buf[i])
            i += 1
    return (out if len(out) == n else None), i


@dataclass
class SceneRecord:
    selected_pattern: list[int]  # 16 entries
    mute: list[int]              # 16 entries
    flags: int

    @classmethod
    def from_values(cls, vals: list[int]) -> "SceneRecord":
        return cls(vals[0:16], vals[16:32], vals[32])

    def describe(self) -> str:
        sel = ",".join(f"T{t+1}=P{p+1}" for t, p in enumerate(self.selected_pattern) if p)
        mut = ",".join(f"T{t+1}" for t, m in enumerate(self.mute) if m)
        bits = []
        if sel:
            bits.append(f"sel[{sel}]")
        if mut:
            bits.append(f"mute[{mut}]")
        bits.append(f"flags={self.flags:#x}")
        return " ".join(bits)


@dataclass
class PretrackParse:
    tail: int
    n_records: int
    records: list[SceneRecord]
    terminator_ok: bool
    error: str | None = None


def parse_pretrack(data: bytes) -> PretrackParse | None:
    m = SIG_RE.search(data)
    if m is None:
        return None
    j = m.start()
    hl = 3 if 1 <= data[j - 3] <= 9 else 2
    tail_pos = j - hl - 1
    pre = data[:tail_pos]
    tail = data[tail_pos]

    a = pre.rfind(ANCHOR)
    if a < 0:
        return None
    region = pre[a + len(ANCHOR) : -36]

    diff = 0xD6 - tail
    if diff % 0x21:
        return PretrackParse(tail, -1, [], False, "tail not on 0x21 grid")
    n = diff // 0x21

    vals, i = rle_decode(region, 0, n * RECORD_SIZE)
    if vals is None:
        return PretrackParse(tail, n, [], False, f"RLE decode failed at region+{i}")
    records = [
        SceneRecord.from_values(vals[r * RECORD_SIZE : (r + 1) * RECORD_SIZE])
        for r in range(n)
    ]
    term_ok = region[i:] == b"\x00\x00"
    err = None if term_ok else f"unexpected trailing bytes: {region[i:].hex(' ')}"
    return PretrackParse(tail, n, records, term_ok, err)


def main(patterns: list[str]) -> int:
    files: list[str] = []
    for pat in patterns:
        files.extend(sorted(glob.glob(pat)))
    ok = bad = 0
    for f in files:
        data = open(f, "rb").read()
        if data[:4] != bytes.fromhex("ddccbbaa"):
            continue
        p = parse_pretrack(data)
        name = f.split("/")[-1]
        if p is None:
            print(f"!! {name}: no anchor/signature")
            bad += 1
            continue
        if p.error:
            print(f"BAD {name:<42} tail=0x{p.tail:02x} n={p.n_records}: {p.error}")
            bad += 1
            continue
        ok += 1
        desc = "; ".join(r.describe() for r in p.records) or "no records"
        print(f"OK  {name:<42} tail=0x{p.tail:02x} n={p.n_records}  {desc}")
    print(f"\nok={ok} bad={bad}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:] or [
        "src/one-off-changes-from-default/*.xy",
        "src/bleez*.xy",
        "src/unnamed*.xy",
    ]
    raise SystemExit(main(args))
