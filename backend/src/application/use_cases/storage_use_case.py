# backend/src/application/use_cases/storage_use_case.py
import asyncio
import os
import tempfile

from src.domain.ports.storage_port import StorageEntry, StoragePort

_CONVERTIBLE_EXTENSIONS = ("pptx", "ppt", "odp")


class StorageUseCase:
    def __init__(self, storage: StoragePort) -> None:
        self._storage = storage

    def list_entries(self, folder: str) -> list[StorageEntry]:
        return self._storage.list_entries(folder)

    def create_folder(self, folder: str, name: str) -> None:
        self._storage.create_folder(folder, name)

    def delete_folder(self, folder: str, name: str) -> None:
        self._storage.delete_folder(folder, name)

    async def upload_file(
        self, folder: str, filename: str, data: bytes, overwrite: bool = False
    ) -> StorageEntry:
        safe_name = filename.strip() or "upload"
        if not overwrite and self._storage.file_exists(folder, safe_name):
            raise FileExistsError(f"File already exists: {safe_name}")
        return await self._storage.save_file(folder, safe_name, data)

    def file_exists(self, folder: str, name: str) -> bool:
        return self._storage.file_exists(folder, name)

    def get_file_path(self, folder: str, name: str) -> str:
        if not self._storage.file_exists(folder, name):
            raise FileNotFoundError(f"File not found: {name}")
        return self._storage.resolve_path(folder, name)

    def delete_file(self, folder: str, name: str) -> None:
        self._storage.delete_file(folder, name)

    def get_mime_type(self, folder: str, name: str) -> str:
        return self._storage.get_mime_type(folder, name)

    def is_convertible(self, name: str) -> bool:
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        return ext in _CONVERTIBLE_EXTENSIONS

    async def convert_to_pdf(self, folder: str, name: str) -> bytes:
        src_path = self.get_file_path(folder, name)
        with tempfile.TemporaryDirectory() as tmpdir:
            proc = await asyncio.create_subprocess_exec(
                "libreoffice", "--headless", "--norestore",
                "--convert-to", "pdf",
                "--outdir", tmpdir,
                src_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            if proc.returncode != 0:
                raise RuntimeError(f"LibreOffice conversion failed: {stderr.decode()}")
            base = os.path.splitext(os.path.basename(src_path))[0]
            pdf_path = os.path.join(tmpdir, base + ".pdf")
            if not os.path.exists(pdf_path):
                raise RuntimeError("Converted PDF not found")
            with open(pdf_path, "rb") as f:
                return f.read()
