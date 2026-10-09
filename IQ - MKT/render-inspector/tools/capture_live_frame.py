"""Validate frame capture on the owned browser without clicking platform controls."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from render_inspector.artifacts import ArtifactStore  # noqa: E402
from render_inspector.browser.cdp import CDPConnection  # noqa: E402
from render_inspector.inspector.webgl_geometry import analyze_webgl_frame  # noqa: E402


async def run(x: float, y: float) -> None:
    port = (ROOT / "workspace/browser-profile/DevToolsActivePort").read_text().splitlines()[0]
    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        targets = json.load(response)
    target = next(
        t
        for t in targets
        if t.get("type") == "page" and t.get("url", "").startswith("https://iqoption.com/traderoom")
    )
    cdp = CDPConnection(target["webSocketDebuggerUrl"])
    await cdp.open()
    try:
        await cdp.command("Page.bringToFront")
        hook = (ROOT / "hooks/webgl-frame.js").read_text(encoding="utf-8")
        install = (
            hook
            + """; (() => {
          const c=document.querySelector('canvas#glcanvas');
          const gl=c?.getContext('webgl2')||c?.getContext('webgl')||c?.getContext('experimental-webgl');
          if(!gl)throw new Error('WebGL context unavailable');
          globalThis.__riInstallFrameCapture(gl,c);
          return globalThis.__renderInspector.id('canvas',c);
        })()"""
        )
        response = await cdp.command(
            "Runtime.evaluate", {"expression": install, "returnByValue": True}
        )
        if response.get("exceptionDetails"):
            raise RuntimeError(response["exceptionDetails"])
        canvas_id = response["result"]["value"]
        await cdp.command(
            "Runtime.evaluate",
            {
                "expression": f"globalThis.__riPendingCapture=globalThis.__renderInspector.frameCaptures.get({json.dumps(canvas_id)})({x},{y})",
                "returnByValue": False,
                "awaitPromise": False,
            },
        )
        await cdp.command("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})
        await cdp.command("Runtime.evaluate", {"expression": "dispatchEvent(new Event('resize'))"})
        result = await cdp.command(
            "Runtime.evaluate",
            {
                "expression": "globalThis.__riPendingCapture",
                "returnByValue": True,
                "awaitPromise": True,
            },
            timeout=15,
        )
        if result.get("exceptionDetails"):
            raise RuntimeError(result["exceptionDetails"])
        frame = result["result"]["value"]
        evidence = ArtifactStore(ROOT / "workspace/evidence/spatial-validation")
        analysis_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        evidence.write_json(analysis_id, "webgl-frame.json", frame)
        summary = analyze_webgl_frame(frame)
        artifact = evidence.write_json(
            analysis_id, "spatial-analysis.json", summary.model_dump(mode="json")
        )
        shot = await cdp.command("Page.captureScreenshot", {"format": "png"})
        evidence.save_screenshot(
            analysis_id, shot["data"], (round(x) - 80, round(y) - 60, 160, 120)
        )
        print(
            json.dumps(
                {
                    "summary": artifact.path,
                    "status": summary.status,
                    "evidence": summary.evidence,
                    "unsupportedReasons": sorted(
                        {d["reason"] for d in summary.data["unsupportedDraws"]}
                    ),
                    "byteCount": frame.get("byteCount"),
                    "limitations": frame.get("limitations"),
                },
                indent=2,
            )
        )
    finally:
        await cdp.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--x", type=float, required=True)
    parser.add_argument("--y", type=float, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.x, args.y))
