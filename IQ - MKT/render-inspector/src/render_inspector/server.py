from __future__ import annotations

import asyncio
import secrets
from pathlib import Path

from aiohttp import WSMsgType, web

from render_inspector.coordinator import InspectorCoordinator
from render_inspector.events import EventBus


class LocalServer:
    def __init__(
        self, host: str, port: int, ui_dir: Path, fixtures_dir: Path, bus: EventBus
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("Render Inspector only binds to 127.0.0.1")
        self.host, self.port, self.ui_dir, self.fixtures_dir, self.bus = (
            host,
            port,
            ui_dir,
            fixtures_dir,
            bus,
        )
        self.token = secrets.token_urlsafe(32)
        self.coordinator: InspectorCoordinator | None = None
        self.app = web.Application(client_max_size=1024 * 1024)
        self.runner: web.AppRunner | None = None
        self.app.add_routes(
            [
                web.get("/", self.index),
                web.get("/app.js", self.asset),
                web.get("/style.css", self.asset),
                web.get("/ws", self.websocket),
                web.get("/api/state", self.state),
                web.post("/api/inspect", self.inspect),
                web.static("/fixtures", fixtures_dir),
            ]
        )

    def attach(self, coordinator: InspectorCoordinator) -> None:
        self.coordinator = coordinator

    def authorized(self, request: web.Request) -> bool:
        return secrets.compare_digest(request.query.get("token", ""), self.token)

    async def index(self, _request: web.Request) -> web.Response:
        text = (
            (self.ui_dir / "index.html")
            .read_text(encoding="utf-8")
            .replace("__TOKEN__", self.token)
        )
        return web.Response(text=text, content_type="text/html")

    async def asset(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(self.ui_dir / request.path.lstrip("/"))

    async def state(self, request: web.Request) -> web.Response:
        if not self.authorized(request):
            raise web.HTTPUnauthorized()
        assert self.coordinator
        return web.json_response(self.coordinator.snapshot())

    async def inspect(self, request: web.Request) -> web.Response:
        if not self.authorized(request):
            raise web.HTTPUnauthorized()
        assert self.coordinator
        count = await self.coordinator.arm_selector()
        return web.json_response({"armed": count})

    async def websocket(self, request: web.Request) -> web.WebSocketResponse:
        if not self.authorized(request):
            raise web.HTTPUnauthorized()
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        assert self.coordinator
        await ws.send_json({"type": "SNAPSHOT", "payload": self.coordinator.snapshot()})

        async def sender() -> None:
            async for event in self.bus.subscribe():
                await ws.send_json(event.as_dict())

        task = asyncio.create_task(sender())
        try:
            async for message in ws:
                if message.type == WSMsgType.TEXT and message.data == "ping":
                    await ws.send_str("pong")
        finally:
            task.cancel()
        return ws

    async def start(self) -> None:
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        await web.TCPSite(self.runner, self.host, self.port).start()

    async def close(self) -> None:
        if self.runner:
            await self.runner.cleanup()
