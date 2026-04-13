"""In-process pub/sub for Layer 8 websocket streaming."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class _Subscriber:
    queue: asyncio.Queue[dict[str, Any]]
    loop: asyncio.AbstractEventLoop | None


class BackendPublisher:
    """Fan-out publisher that broadcasts dict events to websocket subscribers."""

    def __init__(self, *, queue_maxsize: int = 200) -> None:
        self._subscribers: dict[asyncio.Queue[dict[str, Any]], _Subscriber] = {}
        self._queue_maxsize = queue_maxsize
        self._lock = threading.Lock()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._queue_maxsize)
        with self._lock:
            self._subscribers[q] = _Subscriber(queue=q, loop=loop)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.pop(q, None)

    @staticmethod
    def _enqueue(q: asyncio.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
        if q.full():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            return

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            subscribers = tuple(self._subscribers.values())

        for subscriber in subscribers:
            if subscriber.loop is None:
                self._enqueue(subscriber.queue, event)
            else:
                subscriber.loop.call_soon_threadsafe(self._enqueue, subscriber.queue, event)

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)
