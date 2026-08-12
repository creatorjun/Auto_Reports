# backend/src/application/use_cases/storage_use_case.py
import asyncio

from src.application.ports.document_converter_port import DocumentConverterPort
from src.application.ports.storage_port import AsyncBinaryReader, StorageEntry, StoragePort

STORAGE_LIMIT_BYTES = 2 * 1024**4
MAX_CHUNK_SIZE = 32 * 1024 * 1024


class StorageUseCase:
    def __init__(
        self,
        storage: StoragePort,
        converter: DocumentConverterPort,
    ) -> None:
        self._storage = storage
        self._converter = converter

    async def list_entries(self, folder: str) -> list[StorageEntry]:
        return await asyncio.to_thread(self._storage.list_entries, folder)

    async def file_exists(self, folder: str, name: str) -> bool:
        return await asyncio.to_thread(self._storage.file_exists, folder, name)

    async def create_folder(self, folder: str, name: str) -> None:
        await asyncio.to_thread(self._storage.create_folder, folder, name)

    async def delete_folder(self, folder: str, name: str) -> None:
        await asyncio.to_thread(self._storage.delete_folder, folder, name)

    async def get_quota(self) -> dict:
        used = await asyncio.to_thread(self._storage.get_total_size)
        limit = STORAGE_LIMIT_BYTES
        return {
            "used": used,
            "limit": limit,
            "available": max(0, limit - used),
            "percent": round(used / limit * 100, 2),
        }

    async def upload_file(self, folder: str, filename: str, data: bytes, overwrite: bool = False) -> StorageEntry:
        if not overwrite and await self.file_exists(folder, filename):
            raise FileExistsError(filename)
        return await self._storage.save_file(folder, filename, data)

    async def upload_file_streaming(
        self,
        folder: str,
        filename: str,
        upload: AsyncBinaryReader,
        overwrite: bool = False,
        file_size: int | None = None,
    ) -> StorageEntry:
        if not overwrite and await self.file_exists(folder, filename):
            raise FileExistsError(filename)
        if file_size is not None:
            quota = await self.get_quota()
            if file_size > quota["available"]:
                raise ValueError(f"QUOTA_EXCEEDED:{quota['available']}:{file_size}")
        return await self._storage.save_file_streaming(folder, filename, upload)

    async def init_chunked_upload(
        self,
        upload_id: str,
        folder: str,
        filename: str,
        total_size: int | None = None,
        overwrite: bool = False,
    ) -> None:
        if not overwrite and await self.file_exists(folder, filename):
            raise FileExistsError(filename)
        if total_size is not None:
            quota = await self.get_quota()
            if total_size > quota["available"]:
                raise ValueError(f"QUOTA_EXCEEDED:{quota['available']}:{total_size}")
        await asyncio.to_thread(
            self._storage.init_chunked_upload,
            upload_id,
            folder,
            filename,
        )

    async def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        data: bytes,
    ) -> None:
        if len(data) > MAX_CHUNK_SIZE:
            raise ValueError(f"Chunk too large: {len(data)} > {MAX_CHUNK_SIZE}")
        await self._storage.save_chunk(upload_id, chunk_index, data)

    async def complete_chunked_upload(self, upload_id: str, total_chunks: int) -> StorageEntry:
        return await asyncio.to_thread(
            self._storage.complete_chunked_upload,
            upload_id,
            total_chunks,
        )

    async def abort_chunked_upload(self, upload_id: str) -> None:
        await asyncio.to_thread(self._storage.abort_chunked_upload, upload_id)

    async def get_file_path(self, folder: str, name: str) -> str:
        if not await self.file_exists(folder, name):
            raise FileNotFoundError(name)
        return self._storage.resolve_path(folder, name)

    def get_mime_type(self, folder: str, name: str) -> str:
        return self._storage.get_mime_type(folder, name)

    async def delete_file(self, folder: str, name: str) -> None:
        await asyncio.to_thread(self._storage.delete_file, folder, name)

    def is_convertible(self, filename: str) -> bool:
        return self._converter.supports(filename)

    async def convert_to_pdf(self, folder: str, name: str) -> bytes:
        return await self._converter.convert_to_pdf(
            await self.get_file_path(folder, name)
        )
