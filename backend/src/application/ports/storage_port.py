# backend/src/application/ports/storage_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol


class AsyncBinaryReader(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True)
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
    def move_entry(self, source_folder: str, name: str, destination_folder: str) -> None: ...

    @abstractmethod
    async def save_file(self, folder: str, filename: str, data: bytes) -> StorageEntry: ...

    @abstractmethod
    async def save_file_streaming(
        self,
        folder: str,
        filename: str,
        source: AsyncBinaryReader,
    ) -> StorageEntry: ...

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

    @abstractmethod
    def init_chunked_upload(self, upload_id: str, folder: str, filename: str) -> None: ...

    @abstractmethod
    async def save_chunk(self, upload_id: str, chunk_index: int, data: bytes) -> None: ...

    @abstractmethod
    def complete_chunked_upload(self, upload_id: str, total_chunks: int) -> StorageEntry: ...

    @abstractmethod
    def abort_chunked_upload(self, upload_id: str) -> None: ...
