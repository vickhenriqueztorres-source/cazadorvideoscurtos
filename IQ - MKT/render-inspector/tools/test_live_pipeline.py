"""Test renderer state and composited header pixels in the owned live browser."""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import sys
from pathlib import Path
from urllib.request import urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from render_inspector.browser.cdp import CDPConnection  # noqa: E402
from render_inspector.inspector.flicker import analyze_flicker_trace  # noqa: E402


def scan_header(raw: bytes) -> dict[str, int]:
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    width, height = image.size
    left, right, bottom = max(0, width - 430), max(0, width - 145), min(height, 76)
    orange = green = 0
    for red, channel_green, blue in image.crop((left, 0, right, bottom)).get_flattened_data():
        if red > 150 and red > channel_green * 1.55 and channel_green > 35 and blue < 65:
            orange += 1
        if channel_green > 95 and channel_green > red * 1.25 and channel_green > blue * 1.25:
            green += 1
    return {"orangePixels": orange, "greenPixels": green, "width": width, "height": height}


async def runtime_inventory(websocket_url: str) -> dict:
    cdp = CDPConnection(websocket_url)
    await cdp.open()
    try:
        response = await cdp.command(
            "Runtime.evaluate",
            {
                "expression": """(() => ({
                  scope:typeof document==='undefined'?'worker':'document',
                  url:globalThis.location?.href||'',
                  hookInstalled:Boolean(globalThis.__renderInspector),
                  contexts:[...(globalThis.__renderInspector?.contexts?.values?.()||[])],
                  serials:{...(globalThis.__renderInspector?.serials||{})},
                  canvases:typeof document==='undefined'?[]:[...document.querySelectorAll('canvas')].map(canvas=>({
                    id:canvas.id,width:canvas.width,height:canvas.height,
                    rect:canvas.getBoundingClientRect().toJSON(),
                    display:getComputedStyle(canvas).display,
                    visibility:getComputedStyle(canvas).visibility,
                    zIndex:getComputedStyle(canvas).zIndex
                  })),
                  overlays:typeof document==='undefined'?[]:[...document.querySelectorAll('[data-render-inspector-overlay]')].map(root=>({
                    id:root.dataset.renderInspectorOverlay,
                    visibleChildren:[...root.children].filter(node=>{const style=getComputedStyle(node),rect=node.getBoundingClientRect();return style.display!=='none'&&style.visibility!=='hidden'&&rect.width>0&&rect.height>0;}).map(node=>({tag:node.tagName,width:node.getBoundingClientRect().width,height:node.getBoundingClientRect().height,background:getComputedStyle(node).backgroundColor}))
                  })),
                  origin:globalThis.__riOriginPatches||null,
                  visualControl:globalThis.__riVisualControl?.state?.()||null
                }))()""",
                "returnByValue": True,
            },
        )
        if response.get("exceptionDetails"):
            return {"error": str(response["exceptionDetails"])}
        return response["result"].get("value") or {}
    except Exception as exc:
        return {"error": repr(exc)}
    finally:
        await cdp.close()


async def run(frames: int, timeout_seconds: float) -> None:
    evidence = ROOT / "workspace/evidence/live-pipeline-test"
    evidence.mkdir(parents=True, exist_ok=True)
    port = (ROOT / "workspace/browser-profile/DevToolsActivePort").read_text().splitlines()[0]
    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        targets = json.load(response)
    page = next(
        item
        for item in targets
        if item.get("type") == "page"
        and item.get("url", "").startswith("https://iqoption.com/traderoom")
    )

    cdp = CDPConnection(page["webSocketDebuggerUrl"])
    await cdp.open()
    frame_rows: list[dict[str, int]] = []
    suspicious: bytes | None = None
    maximum_orange = -1
    completed = asyncio.Event()

    async def screencast(message: dict) -> None:
        nonlocal suspicious, maximum_orange
        params = message.get("params", {})
        raw = base64.b64decode(params.get("data", ""))
        row = scan_header(raw)
        row["sequence"] = len(frame_rows) + 1
        frame_rows.append(row)
        if row["orangePixels"] > maximum_orange:
            maximum_orange = row["orangePixels"]
            suspicious = raw
        await cdp.command("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        if len(frame_rows) >= frames:
            completed.set()

    cdp.on("Page.screencastFrame", screencast)
    try:
        inventory_before = await runtime_inventory(page["webSocketDebuggerUrl"])
        armed = await cdp.command(
            "Runtime.evaluate",
            {
                "expression": f"globalThis.__riFlickerTrace.arm({{label:'live-presented-pixels',maxFrames:{frames + 20},maxEvents:200000}})",
                "returnByValue": True,
            },
        )
        if armed.get("exceptionDetails"):
            raise RuntimeError(str(armed["exceptionDetails"]))
        await cdp.command(
            "Page.startScreencast",
            {"format": "png", "quality": 100, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1},
        )
        try:
            await asyncio.wait_for(completed.wait(), timeout=timeout_seconds)
        except TimeoutError:
            pass
        await cdp.command("Page.stopScreencast")
        trace_result = await cdp.command(
            "Runtime.evaluate",
            {"expression": "globalThis.__riFlickerTrace.stop()", "returnByValue": True},
        )
        trace = trace_result["result"]["value"]
        trace_analysis = analyze_flicker_trace(trace)
        inventory_after = await runtime_inventory(page["webSocketDebuggerUrl"])
    finally:
        cdp.off("Page.screencastFrame", screencast)
        await cdp.close()

    target_inventory = []
    for target in targets:
        row = {key: target.get(key) for key in ("id", "type", "title", "url")}
        websocket_url = target.get("webSocketDebuggerUrl")
        if websocket_url and target.get("type") in {"page", "iframe", "worker", "shared_worker", "service_worker"}:
            row["runtime"] = await runtime_inventory(websocket_url)
        target_inventory.append(row)

    presented = len(frame_rows)
    orange_frames = sum(row["orangePixels"] > 3 for row in frame_rows)
    green_frames = sum(row["greenPixels"] > 3 for row in frame_rows)
    contexts = inventory_after.get("contexts", [])
    unhooked_webgl = [
        context
        for context in contexts
        if context.get("contextType") in {"webgl", "webgl2", "experimental-webgl"}
        and not context.get("webglHook")
    ]
    if orange_frames and trace_analysis["incorrectStateFrames"] == 0:
        conclusion = "PRESENTED_PIXEL_MISMATCH: another layer/context or compositor path escapes the current target hook"
    elif orange_frames:
        conclusion = "SOURCE_STATE_REACHED_DRAW: current remap missed at least one renderer draw"
    elif unhooked_webgl:
        conclusion = "NO_ORANGE_OBSERVED_BUT_UNHOOKED_WEBGL_CONTEXT_EXISTS"
    else:
        conclusion = "NO_FLICKER_OBSERVED_AND_ALL_DISCOVERED_WEBGL_CONTEXTS_HOOKED"

    metrics = {
        "requestedPresentedFrames": frames,
        "capturedPresentedFrames": presented,
        "framesWithOrangePixels": orange_frames,
        "framesWithGreenPixels": green_frames,
        "maximumOrangePixels": max((row["orangePixels"] for row in frame_rows), default=0),
        "minimumGreenPixels": min((row["greenPixels"] for row in frame_rows), default=0),
        "trace": trace_analysis,
        "discoveredContexts": len(contexts),
        "unhookedWebGLContexts": unhooked_webgl,
        "conclusion": conclusion,
    }
    (evidence / "presented-frames.json").write_text(
        json.dumps(frame_rows, indent=2), encoding="utf-8"
    )
    (evidence / "trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    (evidence / "inventory-before.json").write_text(
        json.dumps(inventory_before, indent=2), encoding="utf-8"
    )
    (evidence / "inventory-after.json").write_text(
        json.dumps(inventory_after, indent=2), encoding="utf-8"
    )
    (evidence / "targets.json").write_text(
        json.dumps(target_inventory, indent=2), encoding="utf-8"
    )
    (evidence / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    if suspicious:
        (evidence / "maximum-orange-frame.png").write_bytes(suspicious)
    print(json.dumps({"evidence": str(evidence), **metrics}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    asyncio.run(run(max(1, args.frames), max(1.0, args.timeout)))


if __name__ == "__main__":
    main()
