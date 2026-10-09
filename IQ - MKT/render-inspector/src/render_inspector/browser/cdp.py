from __future__ import annotations

import asyncio
import contextlib
import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from websockets.asyncio.client import ClientConnection, connect

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class CDPError(RuntimeError):
    pass


class CDPConnection:
    def __init__(self, websocket_url: str, *, debug: bool = False) -> None:
        self.websocket_url = websocket_url
        self.debug = debug
        self._ws: ClientConnection | None = None
        self._reader: asyncio.Task[None] | None = None
        self._next_id = 0
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._handlers: defaultdict[str, list[EventHandler]] = defaultdict(list)

    async def open(self) -> None:
        self._ws = await connect(self.websocket_url, max_size=32 * 1024 * 1024)
        self._reader = asyncio.create_task(self._read_loop(), name="cdp-reader")

    def on(self, method: str, handler: EventHandler) -> None:
        self._handlers[method].append(handler)

    def off(self, method: str, handler: EventHandler) -> None:
        if handler in self._handlers.get(method, []):
            self._handlers[method].remove(handler)

    async def command(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        session_id: str | None = None,
        timeout: float = 15,
    ) -> dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("CDP connection is closed")
        self._next_id += 1
        message: dict[str, Any] = {"id": self._next_id, "method": method, "params": params or {}}
        if session_id:
            message["sessionId"] = session_id
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[self._next_id] = future
        await self._ws.send(json.dumps(message, separators=(",", ":")))
        response = await asyncio.wait_for(future, timeout)
        if "error" in response:
            error = response["error"]
            raise CDPError(f"{method}: {error.get('message')} ({error.get('code')})")
        return dict(response.get("result", {}))

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                message = json.loads(raw)
                if "id" in message:
                    future = self._pending.pop(int(message["id"]), None)
                    if future and not future.done():
                        future.set_result(message)
                    continue
                method = message.get("method", "")
                for handler in tuple(self._handlers.get(method, [])):
                    asyncio.ensure_future(handler(message))
        except Exception as exc:
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(exc)
            self._pending.clear()

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
        if self._reader:
            self._reader.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader
        self._ws = None
