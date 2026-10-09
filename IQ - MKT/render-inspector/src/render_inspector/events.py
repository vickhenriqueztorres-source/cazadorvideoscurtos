from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class InspectorEvent:
    type: str
    payload: dict[str, Any]
    target_id: str | None = None
    session_id: str | None = None
    context_id: int | None = None
    received_at: str = ""

    def __post_init__(self) -> None:
        if not self.received_at:
            self.received_at = datetime.now(UTC).isoformat()

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "payload": self.payload,
            "targetId": self.target_id,
            "sessionId": self.session_id,
            "contextId": self.context_id,
            "receivedAt": self.received_at,
        }


class EventBus:
    def __init__(self, capacity: int = 20_000) -> None:
        self.recent: deque[InspectorEvent] = deque(maxlen=capacity)
        self._subscribers: set[asyncio.Queue[InspectorEvent]] = set()

    async def publish(self, event: InspectorEvent) -> None:
        self.recent.append(event)
        for queue in tuple(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(event)

    async def subscribe(self) -> AsyncIterator[InspectorEvent]:
        queue: asyncio.Queue[InspectorEvent] = asyncio.Queue(maxsize=1000)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)
