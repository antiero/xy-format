from xy.image_writer import ImageProject
from xy.song_footer_inspection import inspect_song_footer


FIXTURE = "src/one-off-changes-from-default/unnamed 155.xy"


def test_inspects_all_fourteen_song_slots() -> None:
    slots = inspect_song_footer(ImageProject.from_file(FIXTURE))

    assert len(slots) == 14
    assert slots[1].song == 2
    assert slots[1].scene_chain == (1, 2, 3)
    assert slots[1].loop
    assert slots[1].loop_raw == 0
    assert slots[1].reserved == 0
