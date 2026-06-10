"""Author .xy files by editing the decoded RAM image (the firmware's way).

Strategy (see docs/format/decoded_image_map.md): decode a known-good file
to its RAM image, apply edits exactly as the firmware would (set fields,
splice count-prefixed vector elements, maintain invariants), then
RLE-encode canonically. No scaffolds, no byte transplants, no "event
types" — the legacy type bytes were zero-run extension counts.

Validation standard: byte-exact replication of device-saved corpus files
(see tests/test_image_writer.py).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from xy.rle import decode_project, encode_project

SIG_RE = re.compile(rb"\x00\x00\x00[\x00-\x0f]\xff\x00\xfc\x00", re.S)

# track-struct relative offsets (docs/format/decoded_image_map.md)
OFF_BARS = 0x01
OFF_SCALE = 0x06
OFF_PRISTINE = 0x11   # u16: 8 = factory, 0 = edited (sticky)
OFF_NOTE_COUNT = 0x456F
NOTE_SIZE = 12

STEP_TICKS = 480


@dataclass
class ImageProject:
    header: bytes
    image: bytearray
    _starts: list[int] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str) -> "ImageProject":
        header, image = decode_project(open(path, "rb").read())
        p = cls(header, bytearray(image))
        p._rescan()
        return p

    def _rescan(self) -> None:
        self._starts = [m.start() - 3 for m in SIG_RE.finditer(self.image)]

    def track_start(self, track: int) -> int:
        """1-based track number -> struct base offset (header byte 0)."""
        return self._starts[track - 1]

    # --- field edits -----------------------------------------------------
    def mark_edited(self, track: int) -> None:
        s = self.track_start(track)
        self.image[s + OFF_PRISTINE : s + OFF_PRISTINE + 2] = b"\x00\x00"

    def set_bars(self, track: int, bars: int) -> None:
        s = self.track_start(track)
        self.image[s + OFF_BARS] = (bars & 0xF) << 4
        self.mark_edited(track)

    # --- note vector -----------------------------------------------------
    def note_count(self, track: int) -> int:
        return self.image[self.track_start(track) + OFF_NOTE_COUNT]

    def add_note(
        self,
        track: int,
        *,
        step: int | None = None,
        tick: int | None = None,
        note: int,
        velocity: int = 100,
        gate: int = 240,
    ) -> None:
        """Append a note record (firmware order: ascending tick, appended
        after existing records). ``step`` is 1-based grid position."""
        if tick is None:
            if step is None:
                raise ValueError("need step or tick")
            tick = (step - 1) * STEP_TICKS
        s = self.track_start(track)
        cpos = s + OFF_NOTE_COUNT
        count = self.image[cpos]
        if count >= 120:
            raise ValueError("pattern note limit reached")
        rec = (
            tick.to_bytes(4, "little")
            + gate.to_bytes(4, "little")
            + bytes([note & 0x7F, velocity & 0x7F, 0, 0])
        )
        insert_at = cpos + 1 + count * NOTE_SIZE
        self.image[cpos] = count + 1
        self.image[insert_at:insert_at] = rec
        self.mark_edited(track)
        self._rescan()

    # --- output ----------------------------------------------------------
    def to_bytes(self) -> bytes:
        return encode_project(self.header, bytes(self.image))

    def save(self, path: str) -> None:
        open(path, "wb").write(self.to_bytes())
