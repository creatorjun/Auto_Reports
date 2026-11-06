# backend/src/domain/entities/advisory_feed.py
from dataclasses import dataclass
from datetime import date, datetime
from typing import Generic, Literal, Protocol, TypeVar


AdvisoryStatus = Literal["pending", "ready", "partial", "stale", "error"]
AdvisorySeverity = Literal["critical", "high", "medium", "low", "unknown"]
SEVERITIES: tuple[AdvisorySeverity, ...] = ("critical", "high", "medium", "low", "unknown")


class FeedPayload(Protocol):
    @property
    def complete(self) -> bool: ...

    @property
    def note(self) -> str: ...


DataT = TypeVar("DataT", bound=FeedPayload)


@dataclass(frozen=True)
class AdvisorySnapshot(Generic[DataT]):
    data: DataT
    refreshed_at: datetime


@dataclass(frozen=True)
class FeedHistory(Generic[DataT]):
    snapshot: AdvisorySnapshot[DataT] | None
    completed_day: date | None
    error: str | None


@dataclass(frozen=True)
class FeedClaim:
    acquired: bool
    lease_until: datetime | None = None
