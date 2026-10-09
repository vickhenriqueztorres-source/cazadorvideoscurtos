from __future__ import annotations

from typing import Any

from render_inspector.events import InspectorEvent
from render_inspector.models import AnalysisCandidate, EvidenceStatus


def point_in_polygon(x: float, y: float, polygon: list[dict[str, float]]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i, point in enumerate(polygon):
        xi, yi = point["x"], point["y"]
        xj, yj = polygon[j]["x"], polygon[j]["y"]
        intersects = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def classify_dom(elements: list[dict[str, Any]]) -> AnalysisCandidate | None:
    if not elements:
        return None
    top = elements[0]
    tag = top.get("tag")
    if tag in {"canvas", "iframe", "html", "body"}:
        return None
    renderer = str(top.get("renderer") or "DOM")
    return AnalysisCandidate(
        kind=renderer,
        status=EvidenceStatus.CONFIRMED,
        score=1.0,
        evidence=["elementFromPoint returned a concrete visual element"],
        data=top,
    )


def correlate_canvas(
    x: float, y: float, frame_id: str | None, events: list[InspectorEvent]
) -> list[AnalysisCandidate]:
    candidates: list[AnalysisCandidate] = []
    for event in reversed(events):
        if event.type != "CANVAS2D_TEXT" or (frame_id and event.payload.get("frameId") != frame_id):
            continue
        polygon = event.payload.get("bbox", [])
        if len(polygon) == 4 and point_in_polygon(x, y, polygon):
            candidates.append(
                AnalysisCandidate(
                    kind="Canvas2D",
                    status=EvidenceStatus.CONFIRMED,
                    score=1.0,
                    evidence=[
                        "same frame",
                        "selected coordinate is inside transformed TextMetrics polygon",
                    ],
                    data=event.payload,
                )
            )
            break
    return candidates


def webgl_candidate(
    events: list[InspectorEvent],
    frame_id: str | None,
    canvas_id: str | None,
    selected_at: float,
) -> AnalysisCandidate | None:
    draws = [
        event
        for event in events
        if event.type == "WEBGL_DRAW"
        and (not frame_id or event.payload.get("frameId") == frame_id)
        and (not canvas_id or event.payload.get("canvasId") == canvas_id)
        and selected_at - 2_000 <= float(event.payload.get("timestamp") or 0) <= selected_at + 5
    ]
    if not draws:
        return None
    programs = sorted({str(event.payload.get("programId")) for event in draws})
    textures = sorted(
        {str(texture) for event in draws for texture in event.payload.get("textures", [])}
    )
    return AnalysisCandidate(
        kind="WebGL draw window",
        status=EvidenceStatus.INCONCLUSIVE,
        score=None,
        evidence=[
            f"{len(draws)} draws occurred on the selected canvas in the preceding two seconds",
            "the exact draw owning the selected pixel was not spatially or differentially confirmed",
        ],
        data={
            "canvasId": canvas_id,
            "candidateCount": len(draws),
            "programs": programs,
            "textures": textures,
            "windowStart": selected_at - 2_000,
            "windowEnd": selected_at + 5,
        },
    )
