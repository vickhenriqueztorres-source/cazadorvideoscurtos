from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rect:
    x: float
    y: float
    width: float
    height: float


def viewport_to_canvas(
    x: float,
    y: float,
    rect: Rect,
    backing_width: float,
    backing_height: float,
) -> tuple[float, float]:
    if rect.width <= 0 or rect.height <= 0:
        raise ValueError("canvas CSS dimensions must be positive")
    return (
        (x - rect.x) * backing_width / rect.width,
        (y - rect.y) * backing_height / rect.height,
    )


def nested_frame_point(
    root_x: float,
    root_y: float,
    frame_rects: list[Rect],
) -> tuple[float, float]:
    x, y = root_x, root_y
    for rect in frame_rects:
        x -= rect.x
        y -= rect.y
    return x, y


def css_to_device(value: float, dpr: float, zoom: float = 1.0) -> int:
    if dpr <= 0 or zoom <= 0:
        raise ValueError("DPR and zoom must be positive")
    return round(value * dpr * zoom)
