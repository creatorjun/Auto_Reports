# backend/src/application/use_cases/storage_use_case.py
import asyncio
import subprocess
from pathlib import Path

from fastapi import UploadFile

from src.domain.ports.storage_port import StorageEntry, StoragePort

CONVERTIBLE_EXTENSIONS = {".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".hwp", ".hwpx"}


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

    async def upload_file(self, folder: str, filename: str, data: bytes, overwrite: bool = False) -> StorageEntry:
        if not overwrite and self._adapter.file_exists(folder, filename):
            raise FileExistsError(filename)
        return await self._adapter.save_file(folder, filename, data)

    async def upload_file_streaming(self, folder: str, filename: str, upload: UploadFile, overwrite: bool = False) -> StorageEntry:
        if not overwrite and self._adapter.file_exists(folder, filename):
            raise FileExistsError(filename)
        return await self._adapter.save_file_streaming(folder, filename, upload)

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
