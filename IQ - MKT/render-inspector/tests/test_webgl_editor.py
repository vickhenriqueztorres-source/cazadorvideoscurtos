from __future__ import annotations

import asyncio
import base64
import io
from pathlib import Path

import pytest
from aiohttp import web
from PIL import Image

from render_inspector.browser.cdp import CDPConnection
from render_inspector.browser.discovery import locate_browser
from render_inspector.browser.lifecycle import launch_browser
from render_inspector.browser.targets import TargetManager
from render_inspector.events import EventBus
from render_inspector.inspector.flicker import analyze_flicker_trace
from render_inspector.inspector.instrumentation import InstrumentationManager

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_editor_changes_webgl_vertices_without_resampling(tmp_path: Path) -> None:
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
        page = next(t for t in targets.targets.values() if t.type == "page")
        session = targets.sessions[page.target_id]
        await cdp.command(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1920, "height": 200, "deviceScaleFactor": 1, "mobile": False},
            session_id=session,
        )
        await cdp.command(
            "Page.navigate",
            {"url": f"http://127.0.0.1:{port}/webgl-editor.html"},
            session_id=session,
        )
        async with asyncio.timeout(10):
            while True:
                result = await cdp.command(
                    "Runtime.evaluate",
                    {"expression": "window.fixtureReady===true", "returnByValue": True},
                    session_id=session,
                )
                if result["result"].get("value"):
                    break
                await asyncio.sleep(0.05)
        await cdp.command(
            "Runtime.evaluate",
            {"expression": "globalThis.__riFlickerTrace.arm({label:'vertex-remap',maxFrames:10})"},
            session_id=session,
        )
        await cdp.command(
            "Runtime.evaluate",
            {"expression": "refreshFixture();refreshFixture();refreshFixture()"},
            session_id=session,
        )
        trace = await cdp.command(
            "Runtime.evaluate",
            {"expression": "globalThis.__riFlickerTrace.stop()", "returnByValue": True},
            session_id=session,
        )
        shot = await cdp.command(
            "Page.captureScreenshot", {"format": "png", "fromSurface": True}, session_id=session
        )
        stats = await cdp.command(
            "Runtime.evaluate",
            {
                "expression": "({stats:globalThis.__riEditorLast,origin:globalThis.__riOriginPatches,shiftMode:globalThis.__riAccountShiftMode,depositMode:globalThis.__riDepositGeometryMode,hasAccountPixels:Boolean(globalThis.__riAccountPixels)})",
                "returnByValue": True,
            },
            session_id=session,
        )
        stats = stats["result"].get("value")
        assert stats["shiftMode"] == "vertices"
        assert stats["depositMode"] == "vertices"
        assert stats["hasAccountPixels"] is False
        assert stats["origin"]["interceptedWrites"] >= 1
        flicker = analyze_flicker_trace(trace["result"]["value"])
        assert flicker["status"] == "PASS", flicker
        assert flicker["incorrectStateFrames"] == 0
        assert flicker["referenceTargetMaxDeltaPx"] == 0
        image = Image.open(io.BytesIO(base64.b64decode(shot["data"]))).convert("RGB")
        assert image.getpixel((1540, 35)) == (25, 21, 18)  # original avatar area cleared
        assert image.getpixel((1561, 35)) == (128, 128, 128)  # avatar shifted once
        assert image.getpixel((1609, 35)) == (128, 128, 128)  # width remains exactly 50 px
        assert image.getpixel((1610, 35)) == (25, 21, 18)  # no cumulative deformation
        assert image.getpixel((1620, 35)) == (25, 21, 18)  # old balance position cleared
        assert image.getpixel((1689, 35)) == (27, 161, 54)  # native account green
        assert image.getpixel((1790, 35)) == (25, 21, 18), stats  # icon center removed
        assert image.getpixel((1755, 14)) == (25, 21, 18)  # old left border removed
        old_inner = [image.getpixel((x, 55)) for x in range(1759, 1765)]
        assert old_inner == [(25, 21, 18)] * 6, old_inner  # old inner edge removed
        assert image.getpixel((1775, 35)) == (81, 168, 93)  # native left border moved
        moved_inner = [image.getpixel((x, 55)) for x in range(1781, 1785)]
        assert (81, 168, 93) in moved_inner, moved_inner  # inner edge follows as one component
        assert image.getpixel((1800, 14)) == (81, 168, 93)  # native top border preserved
        assert image.getpixel((1815, 35)) == (81, 168, 93)  # button text shifted left
        assert image.getpixel((1880, 35)) == (25, 21, 18)  # old text tail cleared
        await cdp.command(
            "Runtime.evaluate",
            {"expression": "globalThis.__riVisualControl.disable();refreshFixture()"},
            session_id=session,
        )
        disabled_shot = await cdp.command(
            "Page.captureScreenshot", {"format": "png", "fromSurface": True}, session_id=session
        )
        disabled = Image.open(
            io.BytesIO(base64.b64decode(disabled_shot["data"]))
        ).convert("RGB")
        assert disabled.getpixel((1540, 35)) == (128, 128, 128)  # native geometry restored
        assert disabled.getpixel((1650, 35)) == (232, 101, 2)  # native source color restored
        assert disabled.getpixel((1790, 35)) == (81, 168, 93)  # native icon restored
        assert disabled.getpixel((1815, 35)) == (25, 21, 18)  # native text position restored
        await cdp.command(
            "Runtime.evaluate",
            {"expression": "globalThis.__riVisualControl.enable();refreshFixture()"},
            session_id=session,
        )
        enabled_shot = await cdp.command(
            "Page.captureScreenshot", {"format": "png", "fromSurface": True}, session_id=session
        )
        enabled = Image.open(io.BytesIO(base64.b64decode(enabled_shot["data"]))).convert("RGB")
        assert enabled.getpixel((1689, 35)) == (27, 161, 54)
        assert enabled.getpixel((1790, 35)) == (25, 21, 18)
        errors = [e.payload for e in bus.recent if e.type == "HOOK_ERROR"]
        assert not errors, errors
    finally:
        await cdp.close()
        await browser.close()
        await runner.cleanup()

