from __future__ import annotations

import asyncio
import itertools
import json
from typing import Any

from render_inspector.artifacts import ArtifactStore
from render_inspector.browser.cdp import CDPConnection
from render_inspector.browser.targets import TargetManager
from render_inspector.events import EventBus, InspectorEvent
from render_inspector.inspector.analysis import classify_dom, correlate_canvas, webgl_candidate
from render_inspector.inspector.webgl_geometry import analyze_webgl_frame
from render_inspector.models import AnalysisResult, EvidenceStatus, TargetSelection
from render_inspector.state import InspectorState, StateMachine
from render_inspector.storage import SessionStore


class InspectorCoordinator:
    def __init__(
        self,
        cdp: CDPConnection,
        targets: TargetManager,
        bus: EventBus,
        store: SessionStore,
        artifacts: ArtifactStore,
    ) -> None:
        self.cdp, self.targets, self.bus, self.store, self.artifacts = (
            cdp,
            targets,
            bus,
            store,
            artifacts,
        )
        self.state = StateMachine()
        self.state.current = InspectorState.BROWSER_CONNECTED
        self.last_analysis: AnalysisResult | None = None
        self._analysis_serial = itertools.count(1)
        self._consumer: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.state.transition(InspectorState.INSTRUMENTING)
        self._consumer = asyncio.create_task(self._consume(), name="event-consumer")
        await self.targets.start()
        self.state.transition(InspectorState.READY)
        await self.bus.publish(InspectorEvent("STATE_CHANGED", {"state": self.state.current}))

    async def _consume(self) -> None:
        async for event in self.bus.subscribe():
            await self.store.save_event(event)
            if event.type == "TARGET_SELECTED":
                try:
                    await self._analyze(event)
                except Exception as exc:
                    self.state.current = InspectorState.FAILED
                    await self.bus.publish(
                        InspectorEvent(
                            "ANALYSIS_FAILED",
                            {"error": repr(exc)},
                            event.target_id,
                            event.session_id,
                            event.context_id,
                        )
                    )

    async def arm_selector(self) -> int:
        if self.state.current in {InspectorState.COMPLETE, InspectorState.FAILED}:
            self.state.transition(InspectorState.READY)
        self.state.transition(InspectorState.TARGET_SELECTION_ARMED)
        armed = await self.targets.instrumentation.arm_selector(self.targets.page_sessions)
        await self.bus.publish(
            InspectorEvent(
                "STATE_CHANGED", {"state": self.state.current, "armedContexts": len(armed)}
            )
        )
        return len(armed)

    async def _analyze(self, event: InspectorEvent) -> None:
        await self.targets.instrumentation.disarm_selector(self.targets.page_sessions)
        self.state.transition(InspectorState.TARGET_CAPTURED)
        p = event.payload
        selection = TargetSelection(
            target_id=event.target_id or "",
            frame_id=p.get("frameId"),
            execution_context_id=event.context_id,
            client_x=p["clientX"],
            client_y=p["clientY"],
            page_x=p["pageX"],
            page_y=p["pageY"],
            screen_x=p["screenX"],
            screen_y=p["screenY"],
            device_pixel_ratio=p["devicePixelRatio"],
            viewport_width=p["viewportWidth"],
            viewport_height=p["viewportHeight"],
            scroll_x=p["scrollX"],
            scroll_y=p["scrollY"],
            frame_url=p["frameUrl"],
            timestamp=float(p.get("jsTimestamp") or 0),
            elements=p.get("elements", []),
        )
        analysis_id = f"analysis_{next(self._analysis_serial):06d}"
        self.state.transition(InspectorState.ANALYZING_DOM)
        artifacts = []
        capture_limitations: list[str] = []
        candidates = []
        dom = classify_dom(selection.elements)
        if dom:
            candidates.append(dom)
            renderer, status = dom.kind, EvidenceStatus.CONFIRMED
        else:
            self.state.transition(InspectorState.ANALYZING_CANVAS)
            top = selection.elements[0] if selection.elements else {}
            rect = top.get("rect") or {
                "x": 0,
                "y": 0,
                "width": selection.viewport_width,
                "height": selection.viewport_height,
            }
            canvas_width = top.get("canvasWidth") or rect["width"] or 1
            canvas_height = top.get("canvasHeight") or rect["height"] or 1
            canvas_x = (selection.client_x - rect["x"]) * canvas_width / (rect["width"] or 1)
            canvas_y = (selection.client_y - rect["y"]) * canvas_height / (rect["height"] or 1)
            candidates.extend(
                correlate_canvas(canvas_x, canvas_y, selection.frame_id, list(self.bus.recent))
            )
            if candidates:
                renderer, status = "Canvas2D", EvidenceStatus.CONFIRMED
            else:
                self.state.transition(InspectorState.ANALYZING_WEBGL)
                frame: dict[str, Any] | None = None
                if event.session_id and top.get("canvasId"):
                    try:
                        canvas_id = json.dumps(top["canvasId"])
                        params: dict[str, Any] = {
                            "expression": f"(async () => {{ const capture = globalThis.__renderInspector?.frameCaptures?.get({canvas_id}); return capture ? await capture({selection.client_x}, {selection.client_y}) : {{error:'Frame capture hook unavailable; reload with current inspector'}}; }})()",
                            "awaitPromise": True,
                            "returnByValue": True,
                        }
                        if event.context_id:
                            params["contextId"] = event.context_id
                        response = await self.cdp.command(
                            "Runtime.evaluate", params, session_id=event.session_id, timeout=8
                        )
                        if response.get("exceptionDetails"):
                            raise RuntimeError(str(response["exceptionDetails"]))
                        frame = response.get("result", {}).get("value")
                        if not isinstance(frame, dict):
                            raise RuntimeError("Frame capture returned no serialized result")
                        artifacts.append(
                            self.artifacts.write_json(analysis_id, "webgl-frame.json", frame)
                        )
                        capture_limitations.extend(frame.get("limitations", []))
                        if frame.get("error"):
                            capture_limitations.append(str(frame["error"]))
                    except Exception as exc:
                        capture_limitations.append(f"WebGL frame capture failed: {exc}")
                candidate = (
                    analyze_webgl_frame(frame)
                    if frame and not frame.get("error")
                    else webgl_candidate(
                        list(self.bus.recent),
                        selection.frame_id,
                        top.get("canvasId"),
                        selection.timestamp,
                    )
                )
                if candidate is None and frame is not None:
                    candidate = analyze_webgl_frame(frame)
                if candidate:
                    candidates.append(candidate)
                    renderer, status = "WebGL", candidate.status
                elif top.get("tag") == "canvas":
                    renderer, status = "Canvas (context unresolved)", EvidenceStatus.INCONCLUSIVE
                else:
                    renderer, status = "UNKNOWN", EvidenceStatus.INCONCLUSIVE
                self.state.transition(InspectorState.CORRELATING)
        if event.session_id:
            shot = await self.cdp.command(
                "Page.captureScreenshot",
                {"format": "png", "fromSurface": True},
                session_id=event.session_id,
            )
            dpr = selection.device_pixel_ratio
            artifacts.extend(
                self.artifacts.save_screenshot(
                    analysis_id,
                    shot["data"],
                    (
                        round(selection.client_x * dpr) - 80,
                        round(selection.client_y * dpr) - 60,
                        160,
                        120,
                    ),
                )
            )
        result = AnalysisResult(
            analysis_id=analysis_id,
            status=status,
            renderer=renderer,
            selection=selection,
            candidates=candidates,
            artifacts=artifacts,
            limitations=[]
            if status == EvidenceStatus.CONFIRMED
            else capture_limitations
            + ["Specific draw and color require differential evidence before confirmation."],
        )
        result_artifact = self.artifacts.write_json(
            analysis_id, "analysis.json", result.model_dump(mode="json")
        )
        result.artifacts.append(result_artifact)
        await self.store.save_analysis(result)
        self.last_analysis = result
        self.state.current = InspectorState.COMPLETE
        await self.bus.publish(
            InspectorEvent(
                "ANALYSIS_COMPLETED",
                result.model_dump(mode="json"),
                event.target_id,
                event.session_id,
                event.context_id,
            )
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state.current,
            **self.targets.snapshot(),
            "lastAnalysis": self.last_analysis.model_dump(mode="json")
            if self.last_analysis
            else None,
            "eventCount": len(self.bus.recent),
        }

    async def close(self) -> None:
        if self._consumer:
            self._consumer.cancel()
            try:
                await self._consumer
            except asyncio.CancelledError:
                pass
