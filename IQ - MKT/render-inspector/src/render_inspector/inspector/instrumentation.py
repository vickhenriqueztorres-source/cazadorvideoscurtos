from __future__ import annotations

import asyncio
import json
from pathlib import Path

from render_inspector.browser.cdp import CDPConnection, CDPError


class InstrumentationManager:
    def __init__(
        self, cdp: CDPConnection, hooks_dir: Path, capture_level: str, batch_ms: int
    ) -> None:
        self.cdp = cdp
        self.hooks_dir = hooks_dir
        self.capture_level = capture_level
        self.batch_ms = batch_ms
        self.source = self._load_source()
        self.selector_source = (hooks_dir / "target-selector.js").read_text(encoding="utf-8")

    def _load_source(self) -> str:
        ordered = [
            "flicker-trace.js",
            "canvas2d.js",
            "webgl-editor.js",
            "webgl-overlay.js",
            "webgl-frame.js",
            "webgl.js",
            "runtime-core.js",
        ]
        source = "\n".join((self.hooks_dir / name).read_text(encoding="utf-8") for name in ordered)
        edits_path = self.hooks_dir.parent / "workspace" / "visual-edits.json"
        edits = json.loads(edits_path.read_text(encoding="utf-8")) if edits_path.exists() else []
        return (
            source.replace("__CAPTURE_LEVEL__", self.capture_level)
            .replace("__BATCH_MS__", str(self.batch_ms))
            .replace("__VISUAL_EDITS__", json.dumps(edits, separators=(",", ":")))
        )

    async def install_page(self, session_id: str) -> None:
        await self.cdp.command("Page.enable", session_id=session_id)
        await self.cdp.command("Runtime.enable", session_id=session_id)
        try:
            await self.cdp.command(
                "Runtime.addBinding", {"name": "__renderInspectorEmit"}, session_id=session_id
            )
        except CDPError as exc:
            if "already exists" not in str(exc).lower():
                raise
        await self.cdp.command(
            "Page.addScriptToEvaluateOnNewDocument", {"source": self.source}, session_id=session_id
        )
        await self.cdp.command(
            "Runtime.evaluate",
            {"expression": self.source, "awaitPromise": False, "returnByValue": False},
            session_id=session_id,
        )

    async def install_worker(self, session_id: str, *, waiting_for_debugger: bool) -> None:
        await self.cdp.command("Runtime.enable", session_id=session_id)
        try:
            await self.cdp.command(
                "Runtime.addBinding", {"name": "__renderInspectorEmit"}, session_id=session_id
            )
        except CDPError as exc:
            if "already exists" not in str(exc).lower():
                raise
        if not waiting_for_debugger:
            await self.cdp.command(
                "Runtime.evaluate",
                {"expression": self.source, "awaitPromise": False},
                session_id=session_id,
            )
            return
        paused: asyncio.Future[dict[str, object]] = asyncio.get_running_loop().create_future()

        async def on_paused(message: dict[str, object]) -> None:
            if message.get("sessionId") == session_id and not paused.done():
                paused.set_result(message)

        self.cdp.on("Debugger.paused", on_paused)
        try:
            await self.cdp.command("Debugger.enable", session_id=session_id)
            breakpoint = await self.cdp.command(
                "Debugger.setInstrumentationBreakpoint",
                {"instrumentation": "beforeScriptExecution"},
                session_id=session_id,
            )
            await self.cdp.command("Runtime.runIfWaitingForDebugger", session_id=session_id)
            message = await asyncio.wait_for(paused, timeout=5)
            params = message.get("params", {})
            assert isinstance(params, dict)
            frames = params.get("callFrames", [])
            assert isinstance(frames, list) and frames
            frame = frames[0]
            assert isinstance(frame, dict)
            await self.cdp.command(
                "Debugger.evaluateOnCallFrame",
                {"callFrameId": frame["callFrameId"], "expression": self.source},
                session_id=session_id,
            )
            await self.cdp.command(
                "Debugger.removeBreakpoint",
                {"breakpointId": breakpoint["breakpointId"]},
                session_id=session_id,
            )
            await self.cdp.command("Debugger.resume", session_id=session_id)
        finally:
            self.cdp.off("Debugger.paused", on_paused)

    async def arm_selector(self, session_ids: list[str]) -> list[str]:
        armed: list[str] = []
        for session_id in session_ids:
            try:
                await self.cdp.command(
                    "Runtime.evaluate",
                    {"expression": self.selector_source, "includeCommandLineAPI": False},
                    session_id=session_id,
                )
                armed.append(session_id)
            except CDPError:
                continue
        return armed

    async def disarm_selector(self, session_ids: list[str]) -> None:
        for session_id in session_ids:
            try:
                await self.cdp.command(
                    "Runtime.evaluate",
                    {"expression": "globalThis.__riSelectorCleanup?.()"},
                    session_id=session_id,
                )
            except CDPError:
                continue
