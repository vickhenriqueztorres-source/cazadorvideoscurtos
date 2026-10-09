from __future__ import annotations

from render_inspector.inspector.flicker import CAUSES, analyze_flicker_trace


def event(sequence: int, kind: str, timestamp: float, frame: int, **payload: object) -> dict:
    return {
        "sequence": sequence,
        "type": kind,
        "timestamp": timestamp,
        "frameSequence": frame,
        "payload": payload,
    }


def test_post_render_override_is_classified() -> None:
    trace = {
        "observedFrames": 1,
        "events": [
            event(1, "WEBGL_DRAW_BEGIN", 1.0, 8, operationId=1, incorrectStateVertices=4),
            event(2, "WEBGL_DRAW_END", 1.2, 8, operationId=1, incorrectStateVertices=4),
            event(3, "OUR_OVERRIDE_BEGIN", 1.3, 8, operationId=2),
            event(4, "OUR_OVERRIDE_END", 1.5, 8, operationId=2),
        ],
    }
    result = analyze_flicker_trace(trace)
    assert result["status"] == "FAIL"
    assert result["incorrectStateFrames"] == 1
    assert result["postRenderOverrideFrames"] == 1
    assert "POST_RENDER_OVERRIDE" in result["classifications"]


def test_one_frame_late_and_all_required_causes_are_supported() -> None:
    trace = {
        "observedFrames": 2,
        "events": [
            event(1, "ONE_FRAME_LATE", 1.0, 2, motionDeltaPx=10),
            event(2, "OVERLAY_PRESENT", 1.1, 2),
        ],
    }
    result = analyze_flicker_trace(trace)
    assert "ONE_FRAME_LATE_TRACKING" in result["classifications"]
    assert "OVERLAY_COMPOSITION_DELAY" in result["classifications"]
    assert result["referenceTargetMaxDeltaPx"] == 10
    assert len(CAUSES) == 14


def test_pre_render_trace_passes() -> None:
    trace = {
        "observedFrames": 1,
        "events": [
            event(1, "OUR_OVERRIDE_BEGIN", 1.0, 3, operationId=1),
            event(2, "OUR_OVERRIDE_END", 1.1, 3, operationId=1, motionDeltaPx=0),
            event(3, "WEBGL_DRAW_BEGIN", 1.2, 3, operationId=2, incorrectStateVertices=0),
            event(4, "WEBGL_DRAW_END", 1.3, 3, operationId=2, incorrectStateVertices=0),
        ],
    }
    result = analyze_flicker_trace(trace)
    assert result["status"] == "PASS"
    assert result["incorrectStateFrames"] == 0
    assert result["classifications"] == []
