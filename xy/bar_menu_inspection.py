"""Read Bar-menu track/pattern defaults from decoded project images."""

from __future__ import annotations

from dataclasses import dataclass

from .image_writer import ImageProject
from .rle import decode_project

TRACK_BASE0 = 0x0D79
TRACK_STRIDE = 0x45D4
TRACK_DEFAULT_STEP_LENGTH_OFFSET = 0x02
TRACK_QUANTIZATION_OFFSET = 0x07
TRACK_GROOVE_OFFSET = 0x08
TRACK_PLOCK_SHAPE_OFFSET = 0x3056


@dataclass(frozen=True)
class TrackBarMenu:
    track: int
    default_step_length_ticks: int
    quantization_raw: int
    groove_raw: int
    plock_shape_raw: int

    @property
    def default_step_length_ui(self) -> int:
        """Approximate device UI percent for the 0..480 tick length range."""
        return round(self.default_step_length_ticks * 100 / 480)

    @property
    def quantization_ui_approx(self) -> int:
        """Approximate UI percent; BAR probes pin the byte but not full scaling."""
        return round(self.quantization_raw * 100 / 255)

    @property
    def groove_signed_raw(self) -> int:
        if self.groove_raw >= 0x80:
            return self.groove_raw - 0x100
        return self.groove_raw

    @property
    def plock_shape_signed_raw(self) -> int:
        if self.plock_shape_raw >= 0x80:
            return self.plock_shape_raw - 0x100
        return self.plock_shape_raw


def read_track_bar_menu(project: ImageProject, track: int) -> TrackBarMenu:
    if not 1 <= track <= 16:
        raise ValueError("track must be 1..16")
    image = project.image
    # These BAR fields sit inside the byte range historically used as the track
    # signature, so signature scanning can miss edited tracks. BAR probes use
    # the fixed baseline-shape decoded image; use the canonical base/stride.
    base = TRACK_BASE0 + (track - 1) * TRACK_STRIDE
    return TrackBarMenu(
        track=track,
        default_step_length_ticks=int.from_bytes(
            image[
                base
                + TRACK_DEFAULT_STEP_LENGTH_OFFSET : base
                + TRACK_DEFAULT_STEP_LENGTH_OFFSET
                + 2
            ],
            "little",
        ),
        quantization_raw=image[base + TRACK_QUANTIZATION_OFFSET],
        groove_raw=image[base + TRACK_GROOVE_OFFSET],
        plock_shape_raw=image[base + TRACK_PLOCK_SHAPE_OFFSET],
    )


def inspect_bar_menu_bytes(data: bytes, *, tracks: int = 8) -> tuple[TrackBarMenu, ...]:
    header, image = decode_project(data)
    project = ImageProject(header, bytearray(image))
    project._rescan()
    return tuple(read_track_bar_menu(project, track) for track in range(1, tracks + 1))
