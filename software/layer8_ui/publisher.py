"""In-process pub/sub for Layer 8 websocket streaming."""

from __future__ import annotations

import asyncio
from typing import Any


class BackendPublisher:
    """Fan-out publisher that broadcasts dict events to websocket subscribers."""

    def __init__(self, *, queue_maxsize: int = 200) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._queue_maxsize = queue_maxsize

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._queue_maxsize)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(q)

    def publish(self, event: dict[str, Any]) -> None:
        for q in tuple(self._subscribers):
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                continue

    def subscriber_count(self) -> int:
        return len(self._subscribers)
