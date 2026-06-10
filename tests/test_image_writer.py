"""Image-writer validation: byte-exact replication of device-saved files.

The standard: building from the decoded baseline with semantic edits must
reproduce real device captures byte-for-byte. No scaffolds, transplants,
event types, or preamble rules involved.
"""
from __future__ import annotations

import pytest

from xy.image_writer import ImageProject

BASE = "src/one-off-changes-from-default/unnamed 1.xy"


def build(edits):
    p = ImageProject.from_file(BASE)
    edits(p)
    return p.to_bytes()


def real(name: str) -> bytes:
    return open(f"src/one-off-changes-from-default/{name}", "rb").read()


def test_replicates_unnamed_2_single_note_step1():
    out = build(lambda p: p.add_note(1, step=1, note=60))
    assert out == real("unnamed 2.xy")


def test_replicates_unnamed_81_single_note_step9():
    out = build(lambda p: p.add_note(1, step=9, note=60))
    assert out == real("unnamed 81.xy")


def test_replicates_unnamed_19_bar_count():
    out = build(lambda p: p.set_bars(1, 4))
    assert out == real("unnamed 19.xy")


def test_replicates_unnamed_92_notes_with_gates():
    def edits(p):
        p.add_note(3, step=1, note=48, gate=960)
        p.add_note(3, step=5, note=50, gate=1920)
        p.add_note(3, step=11, note=53, gate=2880)
    assert build(edits) == real("unnamed 92.xy")


def test_note_equals_velocity_emits_escaped_pair():
    out = build(lambda p: p.add_note(1, step=1, note=60, velocity=60))
    # the equal pair must carry its RLE extension byte
    assert b"\x3c\x3c\x00" in out


def test_note_limit_enforced():
    p = ImageProject.from_file(BASE)
    for i in range(120):
        p.add_note(1, tick=i * 10, note=60)
    with pytest.raises(ValueError):
        p.add_note(1, tick=2000, note=61)
