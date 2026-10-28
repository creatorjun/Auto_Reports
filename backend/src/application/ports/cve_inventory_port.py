# backend/src/application/ports/cve_inventory_port.py
from abc import ABC, abstractmethod

from src.domain.entities.cve_inventory import CveFinding, CveInventory, CveInventoryPackage, CveStoredSnapshot


class CveInventoryLoaderPort(ABC):
    @abstractmethod
    async def load(self) -> CveInventory:
        raise NotImplementedError


class CvePackageSourcePort(ABC):
    async def configure(self, packages: tuple[CveInventoryPackage, ...]) -> None:
        return None

    @abstractmethod
    async def fetch(self, package: CveInventoryPackage) -> tuple[CveFinding, ...]:
        raise NotImplementedError

    async def begin_refresh(self) -> frozenset[str] | None:
        return None

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError


class CveInventorySnapshotPort(ABC):
    @abstractmethod
    async def load(self) -> CveStoredSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, snapshot: CveStoredSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
