# backend/src/application/ports/service_desk_port.py
from abc import ABC, abstractmethod


class ServiceDeskPort(ABC):
    @abstractmethod
    async def get_organizations(self) -> list[dict]: ...

    @abstractmethod
    async def get_members(self, org_id: str) -> list[dict]: ...

    @abstractmethod
    async def resolve_org_name(self, org_id: str) -> str: ...

    @abstractmethod
    async def aclose(self) -> None: ...
