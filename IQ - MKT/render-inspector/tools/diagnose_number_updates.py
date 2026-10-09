"""Correlate live balance glyph source changes, composed pixels, and menu snapshot refreshes."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import io
import json
import sys
from pathlib import Path
from urllib.request import urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from render_inspector.browser.cdp import CDPConnection  # noqa: E402


def crop_hash(raw: bytes) -> tuple[str, bytes]:
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    width, height = image.size
    crop = image.crop((max(0, width - 280), 10, max(0, width - 145), min(height, 65)))
    output = io.BytesIO()
    crop.save(output, format="PNG")
    value = output.getvalue()
    return hashlib.sha256(value).hexdigest(), value


async def evaluate(cdp: CDPConnection, expression: str) -> dict:
    result = await cdp.command(
        "Runtime.evaluate", {"expression": expression, "returnByValue": True}
    )
    if result.get("exceptionDetails"):
        raise RuntimeError(str(result["exceptionDetails"]))
    return result["result"].get("value") or {}


async def menu_state(cdp: CDPConnection) -> dict:
    return await evaluate(
        cdp,
        """(() => {
          const pixels=globalThis.__riMenuPixels,data=pixels?.data;
          let hash=2166136261;
          if(data)for(let index=0;index<data.length;index+=17){hash^=data[index];hash=Math.imul(hash,16777619)>>>0;}
          return {
            hasPixels:Boolean(pixels),hash:data?hash:null,captureTime:globalThis.__riMenuCaptureTime||null,
            captureCount:globalThis.__riCaptureCounts?.menu||0,opening:Boolean(globalThis.__riMenuOpening),
            overlayVisible:Boolean(globalThis.__riMenuOverlayVisible),requested:globalThis.__riMenuRequested,
            cached:Boolean(globalThis.__riMenuCachedPixels),rendererDraws:globalThis.__renderInspector?.serials?.draw||0
          };
        })()""",
    )


async def click(cdp: CDPConnection, x: float, y: float) -> None:
    await cdp.command(
        "Input.dispatchMouseEvent",
        {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1},
    )
    await cdp.command(
        "Input.dispatchMouseEvent",
        {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1},
    )


async def run(frames: int, timeout_seconds: float) -> None:
    evidence = ROOT / "workspace/evidence/number-update-diagnostic"
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
    hashes: list[str] = []
    representative: dict[str, bytes] = {}
    complete = asyncio.Event()

    async def on_frame(message: dict) -> None:
        params = message.get("params", {})
        raw = base64.b64decode(params["data"])
        digest, crop = crop_hash(raw)
        hashes.append(digest)
        representative.setdefault(digest, crop)
        await cdp.command("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        if len(hashes) >= frames:
            complete.set()

    cdp.on("Page.screencastFrame", on_frame)
    try:
        await evaluate(cdp, "globalThis.__riNumberTelemetry={draws:0,changes:0,sources:{},samples:[]}")
        await cdp.command(
            "Page.startScreencast",
            {"format": "png", "quality": 100, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1},
        )
        try:
            await asyncio.wait_for(complete.wait(), timeout=timeout_seconds)
        except TimeoutError:
            pass
        await cdp.command("Page.stopScreencast")
        telemetry = await evaluate(cdp, "globalThis.__riNumberTelemetry||{}")

        viewport = await evaluate(cdp, "({width:innerWidth,height:innerHeight})")
        await click(cdp, viewport["width"] - 250, 35)
        for _ in range(40):
            await asyncio.sleep(0.1)
            opened = await menu_state(cdp)
            if opened.get("hasPixels") and not opened.get("opening"):
                break
        menu_first = await menu_state(cdp)
        await asyncio.sleep(2.5)
        menu_later = await menu_state(cdp)
        if menu_later.get("overlayVisible") or menu_later.get("opening"):
            await click(cdp, viewport["width"] - 250, 35)
        menu_closed = await menu_state(cdp)
    finally:
        cdp.off("Page.screencastFrame", on_frame)
        await cdp.close()

    unique = list(dict.fromkeys(hashes))
    for index, digest in enumerate(unique[:10], 1):
        (evidence / f"header-number-state-{index:02d}.png").write_bytes(representative[digest])
    menu_snapshot_frozen = (
        menu_first.get("hasPixels")
        and menu_later.get("hasPixels")
        and menu_first.get("hash") == menu_later.get("hash")
        and menu_first.get("captureTime") == menu_later.get("captureTime")
        and menu_first.get("captureCount") == menu_later.get("captureCount")
        and menu_later.get("rendererDraws", 0) > menu_first.get("rendererDraws", 0)
    )
    sources = telemetry.get("sources") or {}
    source_changes = sum(max(0, int(item.get("changes") or 0) - 1) for item in sources.values())
    presented_changes = max(0, len(unique) - 1)
    if source_changes <= 1:
        header_conclusion = "NO_NEW_SOURCE_VALUE_OBSERVED_DURING_WINDOW"
    elif presented_changes > 0:
        header_conclusion = "SOURCE_AND_PRESENTED_NUMBER_BOTH_UPDATED"
    else:
        header_conclusion = "SOURCE_CHANGED_BUT_PRESENTED_NUMBER_STAYED_STATIC"
    metrics = {
        "capturedPresentedFrames": len(hashes),
        "uniquePresentedNumberStates": len(unique),
        "presentedNumberChanges": presented_changes,
        "sourceTelemetry": telemetry,
        "sourceValueChangesAfterBaseline": source_changes,
        "headerConclusion": header_conclusion,
        "menuFirst": menu_first,
        "menuLater": menu_later,
        "menuClosed": menu_closed,
        "menuSnapshotFrozenWhileRendererContinued": bool(menu_snapshot_frozen),
        "rootCause": (
            "The account menu is rendered from a cached __riMenuPixels snapshot and is not recaptured while open."
            if menu_snapshot_frozen
            else "Menu snapshot freeze was not reproduced."
        ),
    }
    (evidence / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"evidence": str(evidence), **metrics}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    asyncio.run(run(max(1, args.frames), max(1.0, args.timeout)))


if __name__ == "__main__":
    main()
