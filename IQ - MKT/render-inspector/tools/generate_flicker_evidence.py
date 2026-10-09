"""Generate controlled before/after flicker evidence with real Chromium frames."""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from aiohttp import web

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from render_inspector.browser.cdp import CDPConnection  # noqa: E402
from render_inspector.browser.discovery import locate_browser  # noqa: E402
from render_inspector.browser.lifecycle import launch_browser  # noqa: E402
from render_inspector.browser.targets import TargetManager  # noqa: E402
from render_inspector.events import EventBus  # noqa: E402
from render_inspector.inspector.flicker import (  # noqa: E402
    analyze_flicker_trace,
    render_flicker_report,
)
from render_inspector.inspector.instrumentation import InstrumentationManager  # noqa: E402


async def wait_ready(cdp: CDPConnection, session_id: str) -> None:
    async with asyncio.timeout(10):
        while True:
            response = await cdp.command(
                "Runtime.evaluate",
                {"expression": "globalThis.fixtureReady===true", "returnByValue": True},
                session_id=session_id,
            )
            if response["result"].get("value"):
                return
            await asyncio.sleep(0.05)


async def capture(
    cdp: CDPConnection,
    session_id: str,
    url: str,
    output: Path,
    title: str,
    frames: int,
) -> dict:
    await cdp.command("Page.navigate", {"url": url}, session_id=session_id)
    await wait_ready(cdp, session_id)
    await cdp.command(
        "Runtime.evaluate",
        {
            "expression": f"globalThis.__riFlickerTrace.arm({{label:{json.dumps(title)},maxFrames:{frames + 5}}})"
        },
        session_id=session_id,
    )
    burst = await cdp.command(
        "Runtime.evaluate",
        {
            "expression": f"runFlickerBurst({frames})",
            "awaitPromise": True,
            "returnByValue": True,
        },
        session_id=session_id,
        timeout=max(15, frames // 3),
    )
    trace_result = await cdp.command(
        "Runtime.evaluate",
        {"expression": "globalThis.__riFlickerTrace.stop()", "returnByValue": True},
        session_id=session_id,
    )
    trace = trace_result["result"]["value"]
    analysis = analyze_flicker_trace(trace)
    analysis["pixelBurst"] = burst["result"]["value"]
    output.mkdir(parents=True, exist_ok=True)
    (output / "trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    (output / "metrics.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    (output / "report.md").write_text(
        render_flicker_report(title, analysis), encoding="utf-8"
    )
    return analysis


async def main() -> None:
    app = web.Application()
    app.router.add_static("/", ROOT / "test-pages")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = int(site._server.sockets[0].getsockname()[1])  # type: ignore[union-attr]
    with tempfile.TemporaryDirectory(prefix="render-inspector-flicker-") as profile:
        browser = await launch_browser(locate_browser(), Path(profile), headless=True)
        cdp = CDPConnection(browser.websocket_url)
        await cdp.open()
        bus = EventBus()
        instrumentation = InstrumentationManager(cdp, ROOT / "hooks", "normal", 10)
        targets = TargetManager(cdp, instrumentation, bus)
        try:
            await targets.start()
            page = next(target for target in targets.targets.values() if target.type == "page")
            session = targets.sessions[page.target_id]
            evidence = ROOT / "workspace" / "evidence"
            before = await capture(
                cdp,
                session,
                f"http://127.0.0.1:{port}/flicker-post-render.html",
                evidence / "flicker-before",
                "FLICKER BEFORE FIX",
                120,
            )
            after = await capture(
                cdp,
                session,
                f"http://127.0.0.1:{port}/flicker-prerender.html",
                evidence / "flicker-after",
                "FLICKER AFTER FIX",
                120,
            )
            print(json.dumps({"before": before, "after": after}, indent=2))
        finally:
            await cdp.close()
            await browser.close()
            await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
