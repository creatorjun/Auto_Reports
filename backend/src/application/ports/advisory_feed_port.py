# backend/src/application/ports/advisory_feed_port.py
from datetime import date, datetime
from typing import Protocol

from src.domain.entities.advisory_feed import AdvisorySnapshot, DataT, FeedClaim, FeedHistory


class AdvisorySnapshotPort(Protocol[DataT]):
    async def load(self, target: str, feed: str) -> FeedHistory[DataT]: ...

    async def claim(self, target: str, feed: str, day: date, owner: str, now: datetime) -> FeedClaim: ...

    async def finish(self, target: str, feed: str, owner: str, snapshot: AdvisorySnapshot[DataT] | None, error: str | None) -> bool: ...

    async def abandon(self, target: str, feed: str, owner: str) -> None: ...
