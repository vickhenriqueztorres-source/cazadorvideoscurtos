from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from aiohttp import web

from render_inspector.browser.cdp import CDPConnection
from render_inspector.browser.discovery import locate_browser
from render_inspector.browser.lifecycle import launch_browser
from render_inspector.browser.targets import TargetManager
from render_inspector.events import EventBus
from render_inspector.inspector.flicker import analyze_flicker_trace
from render_inspector.inspector.instrumentation import InstrumentationManager

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_canvas_and_webgl_never_draw_source_color(tmp_path: Path) -> None:
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
    instrumentation = InstrumentationManager(cdp, ROOT / "hooks", "normal", 10)
    targets = TargetManager(cdp, instrumentation, bus)
    try:
        await targets.start()
        page = next(target for target in targets.targets.values() if target.type == "page")
        session = targets.sessions[page.target_id]
        await cdp.command(
            "Page.navigate",
            {"url": f"http://127.0.0.1:{port}/flicker-prerender.html"},
            session_id=session,
        )
        async with asyncio.timeout(10):
            while True:
                ready = await cdp.command(
                    "Runtime.evaluate",
                    {"expression": "globalThis.fixtureReady===true", "returnByValue": True},
                    session_id=session,
                )
                if ready["result"].get("value"):
                    break
                await asyncio.sleep(0.05)
        await cdp.command(
            "Runtime.evaluate",
            {"expression": "globalThis.__riFlickerTrace.arm({label:'pre-render-test',maxFrames:40})"},
            session_id=session,
        )
        burst = await cdp.command(
            "Runtime.evaluate",
            {"expression": "runFlickerBurst(30)", "awaitPromise": True, "returnByValue": True},
            session_id=session,
            timeout=10,
        )
        trace = await cdp.command(
            "Runtime.evaluate",
            {"expression": "globalThis.__riFlickerTrace.stop()", "returnByValue": True},
            session_id=session,
        )
        pixels = burst["result"]["value"]
        assert pixels["canvasOrangeFrames"] == 0
        assert pixels["webglOrangeFrames"] == 0
        assert pixels["canvasGreenFrames"] == 30
        assert pixels["webglGreenFrames"] == 30
        analysis = analyze_flicker_trace(trace["result"]["value"])
        assert analysis["status"] == "PASS", analysis
        assert analysis["incorrectStateFrames"] == 0
        assert analysis["referenceTargetMaxDeltaPx"] == 0
    finally:
        await cdp.close()
        await browser.close()
        await runner.cleanup()
