# backend/src/application/use_cases/storage_use_case.py
import asyncio
import subprocess
from pathlib import Path

from fastapi import UploadFile

from src.domain.ports.storage_port import StorageEntry, StoragePort

CONVERTIBLE_EXTENSIONS = {".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".hwp", ".hwpx"}

STORAGE_LIMIT_BYTES = 2 * 1024 ** 4  # 2TB
MAX_CHUNK_SIZE = 32 * 1024 * 1024    # 32MB per chunk


class StorageUseCase:
    def __init__(self, adapter: StoragePort):
        self._adapter = adapter

    def list_entries(self, folder: str) -> list[StorageEntry]:
        return self._adapter.list_entries(folder)

    def file_exists(self, folder: str, name: str) -> bool:
        return self._adapter.file_exists(folder, name)

    def create_folder(self, folder: str, name: str) -> None:
        self._adapter.create_folder(folder, name)

    def delete_folder(self, folder: str, name: str) -> None:
        self._adapter.delete_folder(folder, name)

    def get_quota(self) -> dict:
        used = self._adapter.get_total_size()
        limit = STORAGE_LIMIT_BYTES
        return {
            "used": used,
            "limit": limit,
            "available": max(0, limit - used),
            "percent": round(used / limit * 100, 2),
        }

    async def upload_file(self, folder: str, filename: str, data: bytes, overwrite: bool = False) -> StorageEntry:
        if not overwrite and self._adapter.file_exists(folder, filename):
            raise FileExistsError(filename)
        return await self._adapter.save_file(folder, filename, data)

    async def upload_file_streaming(
        self,
        folder: str,
        filename: str,
        upload: UploadFile,
        overwrite: bool = False,
        file_size: int | None = None,
    ) -> StorageEntry:
        if not overwrite and self._adapter.file_exists(folder, filename):
            raise FileExistsError(filename)
        if file_size is not None:
            quota = self.get_quota()
            if file_size > quota["available"]:
                raise ValueError(f"QUOTA_EXCEEDED:{quota['available']}:{file_size}")
        return await self._adapter.save_file_streaming(folder, filename, upload)

    def init_chunked_upload(
        self,
        upload_id: str,
        folder: str,
        filename: str,
        total_size: int | None = None,
        overwrite: bool = False,
    ) -> None:
        if not overwrite and self._adapter.file_exists(folder, filename):
            raise FileExistsError(filename)
        if total_size is not None:
            quota = self.get_quota()
            if total_size > quota["available"]:
                raise ValueError(f"QUOTA_EXCEEDED:{quota['available']}:{total_size}")
        self._adapter.init_chunked_upload(upload_id, folder, filename)

    async def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        data: bytes,
    ) -> None:
        if len(data) > MAX_CHUNK_SIZE:
            raise ValueError(f"Chunk too large: {len(data)} > {MAX_CHUNK_SIZE}")
        await self._adapter.save_chunk(upload_id, chunk_index, data)

    def complete_chunked_upload(self, upload_id: str, total_chunks: int) -> StorageEntry:
        return self._adapter.complete_chunked_upload(upload_id, total_chunks)

    def abort_chunked_upload(self, upload_id: str) -> None:
        self._adapter.abort_chunked_upload(upload_id)

    def get_file_path(self, folder: str, name: str) -> str:
        path = self._adapter.resolve_path(folder, name)
        if not Path(path).is_file():
            raise FileNotFoundError(name)
        return path

    def get_mime_type(self, folder: str, name: str) -> str:
        return self._adapter.get_mime_type(folder, name)

    def delete_file(self, folder: str, name: str) -> None:
        self._adapter.delete_file(folder, name)

    def is_convertible(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in CONVERTIBLE_EXTENSIONS

    async def convert_to_pdf(self, folder: str, name: str) -> bytes:
        path = self.get_file_path(folder, name)
        out_dir = str(Path(path).parent)
        proc = await asyncio.create_subprocess_exec(
            "libreoffice", "--headless", "--convert-to", "pdf",
            "--outdir", out_dir, path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError("PDF conversion timed out")
        pdf_path = Path(path).with_suffix(".pdf")
        if not pdf_path.exists():
            raise RuntimeError("PDF conversion failed")
        data = pdf_path.read_bytes()
        pdf_path.unlink(missing_ok=True)
        return data
