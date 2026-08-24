from xy.image_writer import ImageProject
from xy.song_footer_inspection import inspect_song_footer


def test_inspects_all_device_song_slots_without_losing_raw_footer_bytes() -> None:
    project = ImageProject.from_file(
        "src/one-off-changes-from-default/unnamed 155.xy"
    )

    slots = inspect_song_footer(project)

    assert len(slots) == 14
    assert slots[1].scene_chain == (1, 2, 3)
    assert slots[1].loop
    assert slots[1].loop_raw == 0
    assert slots[1].reserved == 0
