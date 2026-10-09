"""Dump the live header WebGL draw attribution exposed by webgl-editor."""

from __future__ import annotations

import asyncio
import base64
import json
import sys
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from render_inspector.browser.cdp import CDPConnection  # noqa: E402


async def main() -> None:
    port = (ROOT / "workspace/browser-profile/DevToolsActivePort").read_text().splitlines()[0]
    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        targets = json.load(response)
    target = next(
        item
        for item in targets
        if item.get("type") == "page"
        and item.get("url", "").startswith("https://iqoption.com/traderoom")
    )
    cdp = CDPConnection(target["webSocketDebuggerUrl"])
    await cdp.open()
    try:
        result = await cdp.command(
            "Runtime.evaluate",
            {
                "expression": "({origin:globalThis.__riOriginPatches||null,viewport:[innerWidth,innerHeight],accountMode:globalThis.__riAccountShiftMode||null,depositMode:globalThis.__riDepositGeometryMode||null,hasAccountPixels:Boolean(globalThis.__riAccountPixels),control:globalThis.__riVisualControl?.state?.()||null,overlays:[...document.querySelectorAll('[data-render-inspector-overlay]')].map(root=>({id:root.dataset.renderInspectorOverlay,children:[...root.children].map(node=>({tag:node.tagName,display:getComputedStyle(node).display,width:node.getBoundingClientRect().width,height:node.getBoundingClientRect().height}))}))})",
                "returnByValue": True,
            },
        )
        print(json.dumps(result["result"]["value"], indent=2))
        screenshot = await cdp.command("Page.captureScreenshot", {"format": "png"})
        image = Image.open(BytesIO(base64.b64decode(screenshot["data"])))
        image.save(ROOT / "workspace/reference-remap-final.png")
        image.crop((max(0, image.width - 600), 0, image.width, min(100, image.height))).save(
            ROOT / "workspace/reference-remap-header.png"
        )
    finally:
        await cdp.close()


if __name__ == "__main__":
    asyncio.run(main())
