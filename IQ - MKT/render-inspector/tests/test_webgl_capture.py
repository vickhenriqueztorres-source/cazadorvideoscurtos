from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from aiohttp import web

from render_inspector.artifacts import ArtifactStore
from render_inspector.browser.cdp import CDPConnection
from render_inspector.browser.discovery import locate_browser
from render_inspector.browser.lifecycle import launch_browser
from render_inspector.browser.targets import TargetManager
from render_inspector.coordinator import InspectorCoordinator
from render_inspector.events import EventBus
from render_inspector.inspector.instrumentation import InstrumentationManager
from render_inspector.models import EvidenceStatus, SessionInfo
from render_inspector.storage import SessionStore

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_selected_pixel_capture_in_real_chromium(tmp_path: Path) -> None:
    app = web.Application()
    app.router.add_static("/", ROOT / "test-pages")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = int(site._server.sockets[0].getsockname()[1])  # type: ignore[union-attr]
    browser = await launch_browser(locate_browser(), tmp_path / "profile", headless=True)
    cdp = CDPConnection(browser.websocket_url)
    await cdp.open()
    bus = EventBus()
    store = SessionStore(tmp_path / "session")
    await store.open(SessionInfo(session_id="spatial-test", status="RUNNING"))
    instrumentation = InstrumentationManager(cdp, ROOT / "hooks", "normal", 10)
    targets = TargetManager(cdp, instrumentation, bus)
    coordinator = InspectorCoordinator(
        cdp, targets, bus, store, ArtifactStore(tmp_path / "session")
    )
    try:
        await coordinator.start()
        page = next(t for t in targets.targets.values() if t.type == "page")
        session = targets.sessions[page.target_id]
        await cdp.command(
            "Page.navigate",
            {"url": f"http://127.0.0.1:{port}/webgl-spatial.html"},
            session_id=session,
        )
        async with asyncio.timeout(10):
            while not any(e.type == "WEBGL_DRAW" for e in bus.recent):
                await asyncio.sleep(0.05)
        await coordinator.arm_selector()
        for kind in ("mousePressed", "mouseReleased"):
            await cdp.command(
                "Input.dispatchMouseEvent",
                {"type": kind, "x": 320, "y": 240, "button": "left", "clickCount": 1},
                session_id=session,
            )
        async with asyncio.timeout(15):
            while coordinator.last_analysis is None:
                failures = [e.payload for e in bus.recent if e.type == "ANALYSIS_FAILED"]
                assert not failures, failures
                await asyncio.sleep(0.05)
        analysis = coordinator.last_analysis
        assert analysis.renderer == "WebGL"
        assert analysis.status is EvidenceStatus.PROBABLE
        candidate = analysis.candidates[0]
        assert candidate.kind == "WebGL frame / spatial evidence"
        assert candidate.data["point"] == {"x": 160, "y": 119}
        matches = candidate.data["spatialMatches"]
        assert len(matches) == 1, candidate.model_dump()
        assert matches[0]["hits"][0]["vertexIndices"] == [0, 1, 2]
        assert matches[0]["pixelChanged"] is True
        assert not candidate.data["unsupportedDraws"]
        frame_path = next(
            Path(a.path) for a in analysis.artifacts if a.path.endswith("webgl-frame.json")
        )
        frame = json.loads(frame_path.read_text())
        assert len(frame["buffers"]) == 2
        assert len(frame["draws"]) == 3  # clear + red triangle + scissored triangle
        assert frame["draws"][1]["after"] == [255, 0, 0, 255]
        assert frame["draws"][2]["before"] == frame["draws"][2]["after"]
        result = await cdp.command(
            "Runtime.evaluate",
            {"expression": "gl.getError()", "returnByValue": True},
            session_id=session,
        )
        assert result["result"]["value"] == 0
    finally:
        await coordinator.close()
        await cdp.close()
        await browser.close()
        await store.close()
        await runner.cleanup()
