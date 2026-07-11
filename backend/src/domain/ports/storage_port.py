# backend/src/domain/ports/storage_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StorageEntry:
    name: str
    size: int
    uploaded_at: str
    is_dir: bool = False


class StoragePort(ABC):
    @abstractmethod
    def list_entries(self, folder: str) -> list[StorageEntry]: ...

    @abstractmethod
    def create_folder(self, folder: str, name: str) -> None: ...

    @abstractmethod
    def delete_folder(self, folder: str, name: str) -> None: ...

    @abstractmethod
    async def save_file(self, folder: str, filename: str, data: bytes) -> StorageEntry: ...

    @abstractmethod
    def resolve_path(self, folder: str, name: str) -> str: ...

    @abstractmethod
    def file_exists(self, folder: str, name: str) -> bool: ...

    @abstractmethod
    def delete_file(self, folder: str, name: str) -> None: ...

    @abstractmethod
    def get_mime_type(self, folder: str, name: str) -> str: ...

    @abstractmethod
    def get_total_size(self) -> int: ...
