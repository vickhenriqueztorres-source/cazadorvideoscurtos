from __future__ import annotations

from collections import defaultdict
from statistics import fmean
from typing import Any

CAUSES = {
    "POST_RENDER_OVERRIDE",
    "ONE_FRAME_LATE_TRACKING",
    "MUTATION_OBSERVER_DELAY",
    "TIMER_DELAY",
    "RAF_ORDERING_PROBLEM",
    "DOUBLE_RAF_DELAY",
    "WORKER_MAIN_THREAD_DESYNC",
    "CANVAS_REDRAW_OVERWRITES_PATCH",
    "WEBGL_UNIFORM_APPLIED_AFTER_DRAW",
    "WEBGL_TEXTURE_APPLIED_AFTER_DRAW",
    "OVERLAY_COMPOSITION_DELAY",
    "MULTIPLE_CANVAS_LAYER_DESYNC",
    "REFERENCE_TARGET_CLOCK_DESYNC",
    "UNKNOWN",
}


def _round(value: float) -> float:
    return round(value, 4)


def analyze_flicker_trace(trace: dict[str, Any]) -> dict[str, Any]:
    events = [item for item in trace.get("events", []) if isinstance(item, dict)]
    by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_frame[int(event.get("frameSequence") or 0)].append(event)

    operation_starts: dict[tuple[str, int], float] = {}
    override_durations: list[float] = []
    draw_durations: list[float] = []
    for event in events:
        event_type = str(event.get("type", ""))
        payload = event.get("payload") or {}
        operation_id = int(payload.get("operationId") or 0)
        timestamp = float(event.get("timestamp") or 0)
        if event_type.endswith("_BEGIN") and operation_id:
            operation_starts[(event_type.removesuffix("_BEGIN"), operation_id)] = timestamp
        elif event_type.endswith("_END") and operation_id:
            name = event_type.removesuffix("_END")
            start = operation_starts.get((name, operation_id))
            if start is None:
                continue
            duration = max(0.0, timestamp - start)
            if name == "OUR_OVERRIDE":
                override_durations.append(duration)
            elif name in {"WEBGL_DRAW", "CANVAS_DRAW"}:
                draw_durations.append(duration)

    incorrect_frames: set[int] = set()
    motion_deltas: list[float] = []
    post_render_frames: set[int] = set()
    for frame, frame_events in by_frame.items():
        draw_begins = [
            item
            for item in frame_events
            if item.get("type") in {"WEBGL_DRAW_BEGIN", "CANVAS_DRAW_BEGIN"}
        ]
        draw_ends = [
            item
            for item in frame_events
            if item.get("type") in {"WEBGL_DRAW_END", "CANVAS_DRAW_END"}
        ]
        for override in (item for item in frame_events if item.get("type") == "OUR_OVERRIDE_BEGIN"):
            override_time = float(override.get("timestamp") or 0)
            override_payload = override.get("payload") or {}
            override_canvas = override_payload.get("canvasId")
            if override_payload.get("phase") == "post-render":
                post_render_frames.add(frame)
                continue
            matching_begins = [
                float(item.get("timestamp") or 0)
                for item in draw_begins
                if (item.get("payload") or {}).get("canvasId") == override_canvas
                and float(item.get("timestamp") or 0) >= override_time
            ]
            if matching_begins:
                continue
            matching_ends = [
                float(item.get("timestamp") or 0)
                for item in draw_ends
                if (item.get("payload") or {}).get("canvasId") == override_canvas
                and float(item.get("timestamp") or 0) <= override_time
            ]
            if matching_ends:
                post_render_frames.add(frame)
        for event in frame_events:
            payload = event.get("payload") or {}
            if int(payload.get("incorrectStateVertices") or 0) > 0 or payload.get(
                "incorrectStateVisible"
            ):
                incorrect_frames.add(frame)
            if "motionDeltaPx" in payload:
                motion_deltas.append(abs(float(payload["motionDeltaPx"])))

    raf_times: list[float] = []
    seen_raf_frames: set[int] = set()
    for event in events:
        if event.get("type") != "REQUEST_ANIMATION_FRAME_BEGIN":
            continue
        frame = int(event.get("frameSequence") or 0)
        if frame in seen_raf_frames:
            continue
        seen_raf_frames.add(frame)
        raf_times.append(float(event.get("timestamp") or 0))
    frame_intervals = [
        b - a for a, b in zip(raf_times, raf_times[1:], strict=False) if b >= a
    ]

    event_types = {str(item.get("type", "")) for item in events}
    classifications: list[str] = []
    if post_render_frames:
        classifications.append("POST_RENDER_OVERRIDE")
    explicit_map = {
        "MUTATION_OBSERVER_CALLBACK": "MUTATION_OBSERVER_DELAY",
        "TIMER_CALLBACK": "TIMER_DELAY",
        "DOUBLE_RAF_DETECTED": "DOUBLE_RAF_DELAY",
        "WORKER_MAIN_THREAD_SYNC": "WORKER_MAIN_THREAD_DESYNC",
        "CANVAS_PATCH_OVERWRITTEN": "CANVAS_REDRAW_OVERWRITES_PATCH",
        "WEBGL_UNIFORM_AFTER_DRAW": "WEBGL_UNIFORM_APPLIED_AFTER_DRAW",
        "WEBGL_TEXTURE_AFTER_DRAW": "WEBGL_TEXTURE_APPLIED_AFTER_DRAW",
        "OVERLAY_PRESENT": "OVERLAY_COMPOSITION_DELAY",
        "MULTIPLE_CANVAS_LAYER_SYNC": "MULTIPLE_CANVAS_LAYER_DESYNC",
        "REFERENCE_TARGET_CLOCK_MISMATCH": "REFERENCE_TARGET_CLOCK_DESYNC",
        "ONE_FRAME_LATE": "ONE_FRAME_LATE_TRACKING",
        "RAF_ORDERING_MISMATCH": "RAF_ORDERING_PROBLEM",
    }
    for event_type, classification in explicit_map.items():
        if event_type in event_types and classification not in classifications:
            classifications.append(classification)
    maximum_motion_delta = max(motion_deltas, default=0.0)
    if maximum_motion_delta > 0.01 and "REFERENCE_TARGET_CLOCK_DESYNC" not in classifications:
        classifications.append("REFERENCE_TARGET_CLOCK_DESYNC")
    if incorrect_frames and not classifications:
        classifications.append("UNKNOWN")

    if "POST_RENDER_OVERRIDE" in classifications:
        root_cause = "The visual override begins after a renderer draw in the same observable frame."
        recommendation = "Move the remap into the state update or immediately before the native draw."
        grade = "E"
    elif "OVERLAY_COMPOSITION_DELAY" in classifications:
        root_cause = "A compositor overlay is updated independently from the renderer output."
        recommendation = "Replace the overlay with a renderer-local pre-draw remap where possible."
        grade = "D"
    elif incorrect_frames:
        root_cause = "Incorrect target state reached at least one observed draw."
        recommendation = "Use the recorded call context to intercept the target before its native draw."
        grade = "C"
    else:
        root_cause = "No incorrect target state reached an observed renderer draw."
        recommendation = "Keep the renderer-local hook and re-run the trace after renderer changes."
        grade = "B"

    observed_frames = int(trace.get("observedFrames") or len(by_frame))
    status = (
        "PASS"
        if not incorrect_frames and not post_render_frames and maximum_motion_delta <= 0.01
        else "FAIL"
    )
    return {
        "renderer": "WebGL" if any("WEBGL" in kind for kind in event_types) else "UNKNOWN",
        "status": status,
        "grade": grade,
        "classifications": classifications,
        "observedFrames": observed_frames,
        "incorrectStateFrames": len(incorrect_frames),
        "incorrectStateFrameIds": sorted(incorrect_frames),
        "postRenderOverrideFrames": len(post_render_frames),
        "referenceTargetMaxDeltaPx": _round(maximum_motion_delta),
        "averageOverrideDurationMs": _round(fmean(override_durations))
        if override_durations
        else 0.0,
        "maximumOverrideDurationMs": _round(max(override_durations, default=0.0)),
        "averageDrawDurationMs": _round(fmean(draw_durations)) if draw_durations else 0.0,
        "averageFrameIntervalMs": _round(fmean(frame_intervals)) if frame_intervals else 0.0,
        "maximumFrameIntervalMs": _round(max(frame_intervals, default=0.0)),
        "droppedFrameEstimate": sum(1 for value in frame_intervals if value > 25.0),
        "eventCount": len(events),
        "droppedTraceEvents": int(trace.get("droppedEvents") or 0),
        "rootCause": root_cause,
        "recommendedFix": recommendation,
    }


def render_flicker_report(title: str, analysis: dict[str, Any]) -> str:
    classifications = analysis.get("classifications") or ["NONE_DETECTED"]
    return "\n".join(
        [
            f"# {title}",
            "",
            f"- Renderer: {analysis['renderer']}",
            f"- Status: {analysis['status']}",
            f"- Solution grade: {analysis['grade']}",
            f"- Classification: {', '.join(classifications)}",
            f"- Observed frames: {analysis['observedFrames']}",
            f"- Incorrect state frames: {analysis['incorrectStateFrames']}",
            f"- Post-render override frames: {analysis['postRenderOverrideFrames']}",
            f"- Reference/target maximum delta: {analysis['referenceTargetMaxDeltaPx']} px",
            f"- Average override duration: {analysis['averageOverrideDurationMs']} ms",
            f"- Maximum override duration: {analysis['maximumOverrideDurationMs']} ms",
            f"- Average frame interval: {analysis['averageFrameIntervalMs']} ms",
            f"- Dropped-frame estimate: {analysis['droppedFrameEstimate']}",
            "",
            "## Root cause",
            "",
            str(analysis["rootCause"]),
            "",
            "## Recommended fix",
            "",
            str(analysis["recommendedFix"]),
            "",
        ]
    )
