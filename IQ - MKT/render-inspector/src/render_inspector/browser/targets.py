from __future__ import annotations

import asyncio
import json
from typing import Any

from render_inspector.browser.cdp import CDPConnection, CDPError
from render_inspector.events import EventBus, InspectorEvent
from render_inspector.inspector.instrumentation import InstrumentationManager
from render_inspector.models import BrowserTarget, ExecutionContextInfo, FrameInfo


class TargetManager:
    ATTACH_TYPES = {"page", "iframe", "worker", "shared_worker", "service_worker"}

    def __init__(
        self, cdp: CDPConnection, instrumentation: InstrumentationManager, bus: EventBus
    ) -> None:
        self.cdp = cdp
        self.instrumentation = instrumentation
        self.bus = bus
        self.targets: dict[str, BrowserTarget] = {}
        self.sessions: dict[str, str] = {}
        self.session_targets: dict[str, str] = {}
        self.frames: dict[str, FrameInfo] = {}
        self.contexts: dict[int, ExecutionContextInfo] = {}
        self.instrumented_sessions: set[str] = set()
        self._instrument_tasks: set[asyncio.Task[None]] = set()
        cdp.on("Target.targetCreated", self._target_created)
        cdp.on("Target.targetInfoChanged", self._target_changed)
        cdp.on("Target.attachedToTarget", self._attached)
        cdp.on("Target.detachedFromTarget", self._detached)
        cdp.on("Page.frameNavigated", self._frame_navigated)
        cdp.on("Runtime.executionContextCreated", self._context_created)
        cdp.on("Runtime.executionContextDestroyed", self._context_destroyed)
        cdp.on("Runtime.bindingCalled", self._binding_called)

    async def start(self) -> None:
        await self.cdp.command("Target.setDiscoverTargets", {"discover": True})
        await self.cdp.command(
            "Target.setAutoAttach",
            {
                "autoAttach": True,
                "waitForDebuggerOnStart": True,
                "flatten": True,
                "filter": [{"type": kind, "exclude": False} for kind in self.ATTACH_TYPES],
            },
        )
        result = await self.cdp.command("Target.getTargets")
        for info in result.get("targetInfos", []):
            await self._upsert(info)
            if info.get("type") in self.ATTACH_TYPES and not info.get("attached"):
                try:
                    attached = await self.cdp.command(
                        "Target.attachToTarget", {"targetId": info["targetId"], "flatten": True}
                    )
                    await self._instrument(attached["sessionId"], info, waiting_for_debugger=False)
                except CDPError:
                    pass
        for _ in range(200):
            if any(
                session in self.instrumented_sessions
                for target_id, session in self.sessions.items()
                if self.targets.get(target_id) and self.targets[target_id].type == "page"
            ):
                return
            await asyncio.sleep(0.025)
        raise TimeoutError("no page target completed instrumentation")

    async def _target_created(self, message: dict[str, Any]) -> None:
        await self._upsert(message["params"]["targetInfo"])

    async def _target_changed(self, message: dict[str, Any]) -> None:
        await self._upsert(message["params"]["targetInfo"])

    async def _upsert(self, info: dict[str, Any]) -> None:
        target = BrowserTarget(
            target_id=info["targetId"],
            type=info["type"],
            title=info.get("title", ""),
            url=info.get("url", ""),
            attached=info.get("attached", False),
            opener_id=info.get("openerId"),
            session_id=self.sessions.get(info["targetId"]),
        )
        self.targets[target.target_id] = target
        await self.bus.publish(
            InspectorEvent("TARGET_DISCOVERED", target.model_dump(mode="json"), target.target_id)
        )

    async def _attached(self, message: dict[str, Any]) -> None:
        params = message["params"]
        await self._instrument(
            params["sessionId"],
            params["targetInfo"],
            waiting_for_debugger=bool(params.get("waitingForDebugger")),
        )

    async def _instrument(
        self, session_id: str, info: dict[str, Any], *, waiting_for_debugger: bool
    ) -> None:
        target_id, target_type = info["targetId"], info["type"]
        if self.sessions.get(target_id) == session_id:
            return
        self.sessions[target_id] = session_id
        self.session_targets[session_id] = target_id
        await self._upsert({**info, "attached": True})
        try:
            if target_type in {"page", "iframe"}:
                await self.instrumentation.install_page(session_id)
                await self.cdp.command(
                    "Target.setAutoAttach",
                    {
                        "autoAttach": True,
                        "waitForDebuggerOnStart": True,
                        "flatten": True,
                        "filter": [
                            {"type": "worker", "exclude": False},
                            {"type": "shared_worker", "exclude": False},
                            {"type": "service_worker", "exclude": False},
                        ],
                    },
                    session_id=session_id,
                )
            elif target_type in {"worker", "shared_worker", "service_worker"}:
                await self.instrumentation.install_worker(
                    session_id, waiting_for_debugger=waiting_for_debugger
                )
            await self.bus.publish(
                InspectorEvent(
                    "TARGET_ATTACHED", {"targetType": target_type}, target_id, session_id
                )
            )
            self.instrumented_sessions.add(session_id)
        except Exception as exc:
            await self.bus.publish(
                InspectorEvent("HOOK_FAILED", {"error": repr(exc)}, target_id, session_id)
            )
        finally:
            try:
                await self.cdp.command("Runtime.runIfWaitingForDebugger", session_id=session_id)
            except CDPError:
                pass

    async def _detached(self, message: dict[str, Any]) -> None:
        session_id = message["params"]["sessionId"]
        target_id = self.session_targets.pop(session_id, None)
        if target_id:
            self.sessions.pop(target_id, None)
            self.instrumented_sessions.discard(session_id)
            await self.bus.publish(InspectorEvent("TARGET_DETACHED", {}, target_id, session_id))

    async def _frame_navigated(self, message: dict[str, Any]) -> None:
        data = message["params"]["frame"]
        target_id = self.session_targets.get(message.get("sessionId", ""), "")
        frame = FrameInfo(
            frame_id=data["id"],
            target_id=target_id,
            parent_frame_id=data.get("parentId"),
            url=data.get("url", ""),
            name=data.get("name", ""),
        )
        self.frames[frame.frame_id] = frame
        await self.bus.publish(
            InspectorEvent(
                "FRAME_NAVIGATED",
                frame.model_dump(mode="json"),
                target_id,
                message.get("sessionId"),
            )
        )

    async def _context_created(self, message: dict[str, Any]) -> None:
        data = message["params"]["context"]
        aux = data.get("auxData", {})
        target_id = self.session_targets.get(message.get("sessionId", ""), "")
        context = ExecutionContextInfo(
            context_id=data["id"],
            target_id=target_id,
            frame_id=aux.get("frameId"),
            origin=data.get("origin", ""),
            name=data.get("name", ""),
        )
        self.contexts[context.context_id] = context
        await self.bus.publish(
            InspectorEvent(
                "CONTEXT_CREATED",
                context.model_dump(mode="json"),
                target_id,
                message.get("sessionId"),
                context.context_id,
            )
        )

    async def _context_destroyed(self, message: dict[str, Any]) -> None:
        self.contexts.pop(message["params"]["executionContextId"], None)

    async def _binding_called(self, message: dict[str, Any]) -> None:
        params = message["params"]
        if params.get("name") != "__renderInspectorEmit":
            return
        session_id = message.get("sessionId")
        target_id = self.session_targets.get(session_id or "")
        context_id = params.get("executionContextId")
        try:
            packet = json.loads(params["payload"])
            events = packet.get("events", [packet]) if isinstance(packet, dict) else []
            for item in events:
                payload = item.get("payload", {})
                payload["jsTimestamp"] = item.get("jsTimestamp")
                context = self.contexts.get(context_id)
                if context and context.frame_id:
                    payload.setdefault("frameId", context.frame_id)
                await self.bus.publish(
                    InspectorEvent(
                        item.get("type", "UNKNOWN"), payload, target_id, session_id, context_id
                    )
                )
        except Exception as exc:
            await self.bus.publish(
                InspectorEvent(
                    "BRIDGE_DECODE_FAILED", {"error": repr(exc)}, target_id, session_id, context_id
                )
            )

    @property
    def page_sessions(self) -> list[str]:
        return [
            session
            for target, session in self.sessions.items()
            if self.targets.get(target)
            and self.targets[target].type in {"page", "iframe"}
            and not self.targets[target].url.startswith("http://127.0.0.1:8765")
        ]

    def snapshot(self) -> dict[str, Any]:
        return {
            "targets": [target.model_dump(mode="json") for target in self.targets.values()],
            "frames": [frame.model_dump(mode="json") for frame in self.frames.values()],
            "contexts": [context.model_dump(mode="json") for context in self.contexts.values()],
        }
