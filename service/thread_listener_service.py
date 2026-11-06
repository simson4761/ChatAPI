import asyncio
from collections import defaultdict


class ThreadListener:
    def __init__(self):
        self.queued: dict[str, set[asyncio.Event]] = defaultdict(set)

    def subscribe(self, thread_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self.queued[thread_id].add(event)
        return event

    def notify(self, thread_id: str):
        queued_events = list(self.queued.get(thread_id, ()))

        for event in queued_events:
            event.set()

    def unsubscribe(self, thread_id: str, event: asyncio.Event):
        events = self.queued.get(thread_id)
        if events is None:
            return
        events.discard(event)
        if not events:
            del self.queued[thread_id]
