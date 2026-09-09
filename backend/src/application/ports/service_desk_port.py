# backend/src/application/ports/service_desk_port.py
from abc import ABC, abstractmethod

from src.domain.entities.partner import PartnerMember, PartnerOrganization


class ServiceDeskPort(ABC):
    @abstractmethod
    async def get_organizations(self) -> list[PartnerOrganization]: ...

    @abstractmethod
    async def get_members(self, org_id: str) -> list[PartnerMember]: ...

    @abstractmethod
    async def resolve_org_name(self, org_id: str) -> str: ...

    @abstractmethod
    async def aclose(self) -> None: ...
