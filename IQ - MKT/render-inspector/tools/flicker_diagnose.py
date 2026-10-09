"""Arm FlickerTrace in the owned live browser and save an offline diagnosis."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from render_inspector.browser.cdp import CDPConnection  # noqa: E402
from render_inspector.inspector.flicker import (  # noqa: E402
    analyze_flicker_trace,
    render_flicker_report,
)


async def run(frames: int, timeout_seconds: float, output: Path) -> None:
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
        arm = await cdp.command(
            "Runtime.evaluate",
            {
                "expression": f"""(() => {{
                  const trace=globalThis.__riFlickerTrace;
                  if(!trace)throw new Error('FlickerTrace unavailable; restart the inspector');
                  trace.arm({{label:'live-header-after',maxFrames:{frames + 10},maxEvents:100000}});
                  const visible=[...document.querySelectorAll('[data-render-inspector-overlay]')].flatMap(root=>[...root.children]).filter(node=>{{
                    const style=getComputedStyle(node),rect=node.getBoundingClientRect();
                    return style.display!=='none'&&style.visibility!=='hidden'&&rect.width>0&&rect.height>0&&(node.tagName==='CANVAS'||style.backgroundColor!=='rgba(0, 0, 0, 0)');
                  }});
                  if(visible.length)trace.record('OVERLAY_PRESENT',{{count:visible.length}});
                  return trace.snapshot();
                }})()""",
                "returnByValue": True,
            },
        )
        if arm.get("exceptionDetails"):
            raise RuntimeError(str(arm["exceptionDetails"]))
        expression = f"""new Promise(resolve=>{{
          const started=performance.now();
          const poll=()=>{{
            const value=globalThis.__riFlickerTrace.snapshot();
            if(value.observedFrames>={frames}||performance.now()-started>{timeout_seconds * 1000})resolve(globalThis.__riFlickerTrace.stop());
            else setTimeout(poll,50);
          }};poll();
        }})"""
        response = await cdp.command(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": True, "returnByValue": True},
            timeout=timeout_seconds + 5,
        )
        if response.get("exceptionDetails"):
            raise RuntimeError(str(response["exceptionDetails"]))
        trace = response["result"]["value"]
        analysis = analyze_flicker_trace(trace)
        output.mkdir(parents=True, exist_ok=True)
        (output / "trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
        (output / "metrics.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
        (output / "report.md").write_text(
            render_flicker_report("LIVE HEADER FLICKER TRACE", analysis), encoding="utf-8"
        )
        print(json.dumps({"output": str(output), "analysis": analysis}, indent=2))
    finally:
        await cdp.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="FLICKER DIAGNOSE")
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "workspace/evidence/flicker-live-after"
    )
    args = parser.parse_args()
    asyncio.run(run(max(1, args.frames), max(1.0, args.timeout), args.output))


if __name__ == "__main__":
    main()
