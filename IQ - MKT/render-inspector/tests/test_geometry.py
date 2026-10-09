from render_inspector.geometry import Rect, css_to_device, nested_frame_point, viewport_to_canvas


def test_dpr_and_zoom_are_deterministic() -> None:
    assert [css_to_device(100, dpr) for dpr in (1, 1.25, 1.5, 2)] == [100, 125, 150, 200]
    assert css_to_device(80, 1.25, 1.2) == 120


def test_scaled_canvas_coordinates() -> None:
    assert viewport_to_canvas(150, 100, Rect(50, 50, 200, 100), 800, 400) == (400, 200)


def test_nested_frame_offsets() -> None:
    assert nested_frame_point(400, 300, [Rect(50, 40, 700, 300), Rect(30, 20, 600, 250)]) == (
        320,
        240,
    )
