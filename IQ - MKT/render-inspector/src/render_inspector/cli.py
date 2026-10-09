from __future__ import annotations

import argparse
import asyncio
import logging
import secrets
import signal
from datetime import datetime
from pathlib import Path

from render_inspector.artifacts import ArtifactStore
from render_inspector.browser.cdp import CDPConnection
from render_inspector.browser.discovery import locate_browser
from render_inspector.browser.lifecycle import OwnedBrowser, launch_browser
from render_inspector.browser.targets import TargetManager
from render_inspector.config import InspectorConfig
from render_inspector.coordinator import InspectorCoordinator
from render_inspector.events import EventBus
from render_inspector.inspector.instrumentation import InstrumentationManager
from render_inspector.models import SessionInfo
from render_inspector.server import LocalServer
from render_inspector.storage import SessionStore


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Inspect the origin of browser rendering via direct CDP"
    )
    value.add_argument("--url", default="https://iqoption.com/traderoom")
    value.add_argument(
        "--capture", choices=("discovery", "normal", "target", "deep"), default="normal"
    )
    value.add_argument("--debug", action="store_true")
    value.add_argument("--headless", action="store_true", help=argparse.SUPPRESS)
    return value


async def run(args: argparse.Namespace) -> None:
    root = Path(__file__).resolve().parents[2]
    config = InspectorConfig(
        root=root, target_url=args.url, capture_level=args.capture, debug=args.debug
    )
    logging.basicConfig(
        level=logging.DEBUG if config.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("render-inspector")
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(3)
    session = SessionInfo(session_id=session_id, status="RUNNING")
    session_dir = config.sessions / session_id
    store = SessionStore(session_dir)
    await store.open(session)
    bus = EventBus(config.ring_events)
    server = LocalServer(config.host, config.port, root / "ui", root / "test-pages", bus)
    browser: OwnedBrowser | None = None
    cdp: CDPConnection | None = None
    coordinator: InspectorCoordinator | None = None
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, name):
            try:
                loop.add_signal_handler(getattr(signal, name), stop.set)
            except NotImplementedError:
                pass
    try:
        await server.start()
        executable = locate_browser()
        log.info("Browser: %s", executable)
        browser = await launch_browser(executable, config.profile, headless=args.headless)
        session.browser_pid = browser.process.pid
        cdp = CDPConnection(browser.websocket_url, debug=config.debug)
        await cdp.open()
        version = await cdp.command("Browser.getVersion")
        session.browser_version = version.get("product")
        session.cdp_version = version.get("protocolVersion")
        instrumentation = InstrumentationManager(
            cdp, root / "hooks", config.capture_level, config.batch_ms
        )
        targets = TargetManager(cdp, instrumentation, bus)
        coordinator = InspectorCoordinator(cdp, targets, bus, store, ArtifactStore(session_dir))
        server.attach(coordinator)
        await coordinator.start()
        page_targets = [
            target
            for target in targets.targets.values()
            if target.type == "page" and target.url in {"", "about:blank"}
        ]
        if not page_targets:
            created = await cdp.command("Target.createTarget", {"url": "about:blank"})
            for _ in range(50):
                await asyncio.sleep(0.05)
                if created["targetId"] in targets.sessions:
                    break
            target_id = created["targetId"]
        else:
            target_id = page_targets[0].target_id
        target_session = targets.sessions[target_id]
        await cdp.command("Page.navigate", {"url": config.target_url}, session_id=target_session)
        await cdp.command(
            "Target.createTarget", {"url": f"{config.panel_url}/?token={server.token}"}
        )
        await cdp.command("Target.activateTarget", {"targetId": target_id})
        log.info("Painel: %s/?token=%s", config.panel_url, server.token)
        log.info("Alvo: %s", config.target_url)
        await stop.wait()
    finally:
        log.info("Encerrando sessão %s", session_id)
        if coordinator:
            await coordinator.close()
        if cdp:
            await cdp.close()
        if browser:
            await browser.close()
        await server.close()
        await store.close()


def main() -> None:
    try:
        asyncio.run(run(parser().parse_args()))
    except KeyboardInterrupt:
        pass
