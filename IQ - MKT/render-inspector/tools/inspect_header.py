"""Capture original rendering and measure complete button borders, without guessing draws."""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

import websockets
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def measure_buttons(image: Image.Image) -> list[dict[str, int]]:
    image = image.convert("RGB")
    width, height = image.size
    candidates = []

    def green(x: int, y: int) -> bool:
        r, g, b = image.getpixel((x, y))
        return g > 95 and g > r * 1.4 and g > b * 1.4

    # Detect complete horizontal borders, then require both vertical sides and bottom.
    for y in range(min(100, height)):
        x = max(0, width - 450)
        while x < width:
            if not green(x, y):
                x += 1
                continue
            start = x
            while x < width and green(x, y):
                x += 1
            if not 100 <= x - start <= 260:
                continue
            for bottom in range(y + 35, min(y + 65, height)):
                if sum(green(xx, bottom) for xx in range(start, x)) < (x - start) * 0.95:
                    continue
                sides = []
                for expected in (start, x - 1):
                    found = [
                        xx
                        for xx in range(max(0, expected - 3), min(width, expected + 4))
                        if all(green(xx, yy) for yy in range(y + 4, bottom - 3))
                    ]
                    if not found:
                        break
                    sides.append(min(found, key=lambda xx: abs(xx - expected)))
                if len(sides) == 2:
                    candidates.append(
                        {
                            "left": sides[0],
                            "top": y,
                            "width": sides[1] - sides[0] + 1,
                            "height": bottom - y + 1,
                        }
                    )
                    break
    return candidates


async def main() -> None:
    port = (ROOT / "workspace/browser-profile/DevToolsActivePort").read_text().splitlines()[0]
    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        targets = json.load(response)
    target = next(
        t
        for t in targets
        if t.get("type") == "page" and t.get("url", "").startswith("https://iqoption.com/traderoom")
    )
    directory = (
        ROOT / "workspace/evidence/header-inspection" / datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    directory.mkdir(parents=True, exist_ok=True)
    async with websockets.connect(target["webSocketDebuggerUrl"], max_size=20_000_000) as ws:
        sequence = 0

        async def call(method: str, params: dict | None = None) -> dict:
            nonlocal sequence
            sequence += 1
            await ws.send(json.dumps({"id": sequence, "method": method, "params": params or {}}))
            async with asyncio.timeout(20):
                while True:
                    result = json.loads(await ws.recv())
                    if result.get("id") == sequence:
                        if "error" in result:
                            raise RuntimeError(result["error"])
                        return result["result"]

        # Retire obsolete visual filters and prevent old resize callbacks restoring them.
        cleanup = """(() => {
          const state=globalThis.__renderInspectorVisual;
          state?.observer?.disconnect();
          if(state) { state.removeAll?.(); state.roots.clear(); }
          for(const c of document.querySelectorAll('canvas#glcanvas')) c.style.removeProperty('filter');
          return {url:location.href, dpr:devicePixelRatio,
            viewport:{width:innerWidth,height:innerHeight},
            canvases:[...document.querySelectorAll('canvas')].map(c=>({id:c.id,width:c.width,height:c.height,rect:c.getBoundingClientRect().toJSON()})),
            depositDom:[...document.querySelectorAll('button,[role=button]')].filter(e=>/depositar/i.test(e.textContent)).map(e=>({tag:e.tagName,text:e.textContent,rect:e.getBoundingClientRect().toJSON()}))};
        })()"""
        await call("Runtime.runIfWaitingForDebugger")
        result = await call("Runtime.evaluate", {"expression": cleanup, "returnByValue": True})
        report = result["result"]["value"]
        screenshot = await call("Page.captureScreenshot", {"format": "png"})
        path = directory / "original.png"
        path.write_bytes(base64.b64decode(screenshot["data"]))
        with Image.open(path) as image:
            report["buttonCandidates"] = measure_buttons(image)
            image.crop((max(0, image.width - 600), 0, image.width, min(100, image.height))).save(
                directory / "header.png"
            )
        report["drawAttribution"] = (
            "UNRESOLVED: pixel geometry is not a semantic component or an exact WebGL draw."
        )
        report["patchStatus"] = "disabled; original rendering restored"
        (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"evidence": str(directory), "report": report}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
