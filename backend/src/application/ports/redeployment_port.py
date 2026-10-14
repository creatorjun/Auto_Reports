# backend/src/application/ports/redeployment_port.py
from datetime import datetime
from typing import Protocol

from src.domain.entities.redeployment_report import RedeploymentReport, RedeploymentTicket


class RedeploymentSourcePort(Protocol):
    async def fetch(self, as_of: datetime) -> tuple[str, tuple[RedeploymentTicket, ...], tuple[str, ...]]: ...


class RedeploymentRepository(Protocol):
    async def try_generation_lock(self) -> bool: ...

    async def get_latest(self) -> RedeploymentReport | None: ...

    async def save(self, report: RedeploymentReport) -> RedeploymentReport: ...
