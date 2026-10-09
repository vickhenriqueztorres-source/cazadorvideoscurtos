from render_inspector.events import InspectorEvent
from render_inspector.inspector.analysis import classify_dom, correlate_canvas, webgl_candidate
from render_inspector.models import EvidenceStatus


def test_dom_is_confirmed_only_for_concrete_element() -> None:
    candidate = classify_dom([{"tag": "span", "renderer": "DOM", "text": "Saldo"}])
    assert candidate and candidate.status is EvidenceStatus.CONFIRMED
    assert classify_dom([{"tag": "canvas"}]) is None


def test_canvas_text_requires_point_inside_bbox_and_frame() -> None:
    event = InspectorEvent(
        "CANVAS2D_TEXT",
        {
            "frameId": "f1",
            "bbox": [
                {"x": 10, "y": 10},
                {"x": 110, "y": 10},
                {"x": 110, "y": 40},
                {"x": 10, "y": 40},
            ],
            "text": "85%",
        },
    )
    assert correlate_canvas(50, 20, "f1", [event])[0].status is EvidenceStatus.CONFIRMED
    assert correlate_canvas(150, 20, "f1", [event]) == []
    assert correlate_canvas(50, 20, "f2", [event]) == []


def test_webgl_window_is_fail_closed_and_excludes_future_draws() -> None:
    valid = InspectorEvent(
        "WEBGL_DRAW",
        {
            "frameId": "f1",
            "canvasId": "canvas_1",
            "timestamp": 9_900,
            "programId": "program_1",
            "textures": ["texture_1"],
        },
    )
    future = InspectorEvent(
        "WEBGL_DRAW",
        {
            "frameId": "f1",
            "canvasId": "canvas_1",
            "timestamp": 10_100,
            "programId": "program_future",
            "textures": [],
        },
    )
    candidate = webgl_candidate([valid, future], "f1", "canvas_1", 10_000)
    assert candidate and candidate.status is EvidenceStatus.INCONCLUSIVE
    assert candidate.data["candidateCount"] == 1
    assert candidate.data["programs"] == ["program_1"]
