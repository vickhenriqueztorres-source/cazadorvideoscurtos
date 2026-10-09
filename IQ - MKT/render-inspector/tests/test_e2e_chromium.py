from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

import pytest
from aiohttp import web

from render_inspector.browser.cdp import CDPConnection
from render_inspector.browser.discovery import locate_browser
from render_inspector.browser.lifecycle import launch_browser
from render_inspector.browser.targets import TargetManager
from render_inspector.events import EventBus
from render_inspector.inspector.instrumentation import InstrumentationManager

ROOT = Path(__file__).resolve().parents[1]


async def wait_for_event(bus: EventBus, event_type: str, timeout: float = 10) -> None:
    try:
        async with asyncio.timeout(timeout):
            while not any(event.type == event_type for event in bus.recent):
                await asyncio.sleep(0.05)
    except TimeoutError as exc:
        raise AssertionError(
            f"missing {event_type}; received {[event.type for event in bus.recent]}"
        ) from exc


@pytest.mark.asyncio
async def test_real_chromium_bootstrap_canvas_webgl_and_worker(tmp_path: Path) -> None:
    app = web.Application()
    app.router.add_static("/", ROOT / "test-pages", show_index=True)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    sockets = site._server.sockets  # type: ignore[union-attr]
    port = int(sockets[0].getsockname()[1])

    browser = await launch_browser(locate_browser(), tmp_path / "profile", headless=True)
    cdp = CDPConnection(browser.websocket_url)
    await cdp.open()
    bus = EventBus()
    instrumentation = InstrumentationManager(cdp, ROOT / "hooks", "normal", 10)
    targets = TargetManager(cdp, instrumentation, bus)
    try:
        await targets.start()
        page = next(target for target in targets.targets.values() if target.type == "page")
        session_id = targets.sessions[page.target_id]

        await cdp.command(
            "Page.navigate",
            {"url": f"http://127.0.0.1:{port}/canvas2d.html"},
            session_id=session_id,
        )
        await wait_for_event(bus, "CANVAS2D_TEXT")
        result = await cdp.command(
            "Runtime.evaluate",
            {"expression": "window.fixtureHookPrecededScript", "returnByValue": True},
            session_id=session_id,
        )
        assert result["result"]["value"] is True
        text_event = next(event for event in bus.recent if event.type == "CANVAS2D_TEXT")
        assert text_event.payload["text"] == "Saldo: R$ 500"
        assert text_event.payload["fillStyle"] == "#ffffff"

        armed = await instrumentation.arm_selector([session_id])
        assert armed == [session_id]
        for event_type in ("mouseMoved", "mousePressed", "mouseReleased"):
            params: dict[str, object] = {"type": event_type, "x": 150, "y": 95}
            if event_type != "mouseMoved":
                params.update(button="left", clickCount=1)
            await cdp.command("Input.dispatchMouseEvent", params, session_id=session_id)
        await wait_for_event(bus, "TARGET_SELECTED")
        selected = next(event for event in bus.recent if event.type == "TARGET_SELECTED")
        assert selected.payload["elements"][0]["tag"] == "canvas"
        screenshot = await cdp.command(
            "Page.captureScreenshot",
            {"format": "png", "fromSurface": True},
            session_id=session_id,
        )
        evidence = ROOT / "workspace" / "evidence" / "phase3"
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "target_full.png").write_bytes(base64.b64decode(screenshot["data"]))
        (evidence / "selection.json").write_text(
            json.dumps(selected.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

        canvas_count = sum(event.type == "CANVAS2D_TEXT" for event in bus.recent)
        await cdp.command(
            "Page.navigate",
            {"url": f"http://127.0.0.1:{port}/nested-parent.html"},
            session_id=session_id,
        )
        async with asyncio.timeout(10):
            while sum(event.type == "CANVAS2D_TEXT" for event in bus.recent) <= canvas_count:
                await asyncio.sleep(0.05)
        nested_text = [event for event in bus.recent if event.type == "CANVAS2D_TEXT"][-1]
        assert nested_text.payload.get("frameId")
        nested_frame = targets.frames[nested_text.payload["frameId"]]
        assert nested_frame.parent_frame_id is not None
        parent_frame = targets.frames[nested_frame.parent_frame_id]
        assert parent_frame.parent_frame_id is not None

        await cdp.command(
            "Page.navigate",
            {"url": f"http://127.0.0.1:{port}/webgl.html"},
            session_id=session_id,
        )
        await wait_for_event(bus, "WEBGL_DRAW")
        assert any(event.type == "WEBGL_SHADER_SOURCE" for event in bus.recent)
        assert any(event.type == "WEBGL_PROGRAM_LINKED" for event in bus.recent)
        assert any(event.type == "WEBGL_UNIFORM_UPDATED" for event in bus.recent)

        await cdp.command(
            "Page.navigate",
            {"url": f"http://127.0.0.1:{port}/worker.html"},
            session_id=session_id,
        )
        try:
            async with asyncio.timeout(10):
                while not any(
                    event.type == "TARGET_ATTACHED" and event.payload.get("targetType") == "worker"
                    for event in bus.recent
                ):
                    await asyncio.sleep(0.05)
        except TimeoutError as exc:
            raise AssertionError(
                [(event.type, event.payload) for event in bus.recent if "HOOK" in event.type]
            ) from exc
        worker_ids = {
            target.target_id for target in targets.targets.values() if target.type == "worker"
        }
        async with asyncio.timeout(10):
            while not any(
                event.type == "CANVAS_CONTEXT_CREATED" and event.target_id in worker_ids
                for event in bus.recent
            ):
                await asyncio.sleep(0.05)
    finally:
        await cdp.close()
        await browser.close()
        await runner.cleanup()
