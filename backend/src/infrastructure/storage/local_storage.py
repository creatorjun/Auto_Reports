# backend/src/infrastructure/storage/local_storage.py
import asyncio
import mimetypes
import os
import shutil
from datetime import datetime, timezone
from functools import lru_cache

import aiofiles
from fastapi import UploadFile

from src.domain.ports.storage_port import StorageEntry, StoragePort
from src.infrastructure.config.settings import get_settings

CHUNK_SIZE = 1024 * 1024  # 1MB
_TEMP_PREFIX = ".chunked_"


class LocalStorageAdapter(StoragePort):
    def __init__(self, base_dir: str) -> None:
        self._base = os.path.realpath(base_dir)
        os.makedirs(self._base, exist_ok=True)
        self._path_locks: dict[str, asyncio.Lock] = {}
        self._meta_lock = asyncio.Lock()

    def _resolve(self, folder: str, name: str = "") -> str:
        target = os.path.realpath(os.path.join(self._base, folder.lstrip("/"), name))
        if not target.startswith(self._base + os.sep) and target != self._base:
            raise ValueError("Invalid path")
        if name:
            basename = os.path.basename(target)
            if not basename:
                raise ValueError("Invalid name")
        return target

    def _temp_dir(self, upload_id: str) -> str:
        safe_id = upload_id.replace("/", "").replace("..", "")
        return os.path.join(self._base, f"{_TEMP_PREFIX}{safe_id}")

    async def _get_path_lock(self, dest: str) -> asyncio.Lock:
        async with self._meta_lock:
            if dest not in self._path_locks:
                self._path_locks[dest] = asyncio.Lock()
            return self._path_locks[dest]

    def list_entries(self, folder: str) -> list[StorageEntry]:
        dir_path = self._resolve(folder)
        if not os.path.isdir(dir_path):
            raise FileNotFoundError(f"Folder not found: {folder}")
        result: list[StorageEntry] = []
        for entry in sorted(os.scandir(dir_path), key=lambda e: (e.is_file(), e.name.lower())):
            stat = entry.stat()
            result.append(StorageEntry(
                name=entry.name,
                size=stat.st_size if entry.is_file() else 0,
                uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                is_dir=entry.is_dir(),
            ))
        return result

    def get_total_size(self) -> int:
        total = 0
        for dirpath, dirnames, filenames in os.walk(self._base):
            dirnames[:] = [d for d in dirnames if not d.startswith(_TEMP_PREFIX)]
            for filename in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, filename))
                except OSError:
                    pass
        return total

    def create_folder(self, folder: str, name: str) -> None:
        path = self._resolve(folder, name)
        if os.path.exists(path):
            raise FileExistsError(f"Already exists: {name}")
        os.makedirs(path)

    def delete_folder(self, folder: str, name: str) -> None:
        path = self._resolve(folder, name)
        if not os.path.isdir(path):
            raise FileNotFoundError(f"Folder not found: {name}")
        shutil.rmtree(path)

    async def save_file(self, folder: str, filename: str, data: bytes) -> StorageEntry:
        dest = self._resolve(folder, filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        path_lock = await self._get_path_lock(dest)
        async with path_lock:
            async with aiofiles.open(dest, "wb") as f:
                await f.write(data)
            stat = os.stat(dest)
        return StorageEntry(
            name=os.path.basename(dest),
            size=stat.st_size,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            is_dir=False,
        )

    async def save_file_streaming(self, folder: str, filename: str, upload: UploadFile) -> StorageEntry:
        dest = self._resolve(folder, filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        path_lock = await self._get_path_lock(dest)
        async with path_lock:
            async with aiofiles.open(dest, "wb") as f:
                while chunk := await upload.read(CHUNK_SIZE):
                    await f.write(chunk)
            stat = os.stat(dest)
        return StorageEntry(
            name=os.path.basename(dest),
            size=stat.st_size,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            is_dir=False,
        )

    def init_chunked_upload(self, upload_id: str, folder: str, filename: str) -> None:
        temp_dir = self._temp_dir(upload_id)
        if os.path.exists(temp_dir):
            raise FileExistsError(f"Upload already initialized: {upload_id}")
        os.makedirs(temp_dir)
        meta_path = os.path.join(temp_dir, "_meta")
        with open(meta_path, "w") as f:
            f.write(f"{folder}\n{filename}")

    async def save_chunk(self, upload_id: str, chunk_index: int, data: bytes) -> None:
        temp_dir = self._temp_dir(upload_id)
        if not os.path.isdir(temp_dir):
            raise FileNotFoundError(f"Upload not initialized: {upload_id}")
        chunk_path = os.path.join(temp_dir, f"{chunk_index:08d}")
        async with aiofiles.open(chunk_path, "wb") as f:
            await f.write(data)

    def complete_chunked_upload(self, upload_id: str, total_chunks: int) -> StorageEntry:
        temp_dir = self._temp_dir(upload_id)
        if not os.path.isdir(temp_dir):
            raise FileNotFoundError(f"Upload not initialized: {upload_id}")
        meta_path = os.path.join(temp_dir, "_meta")
        with open(meta_path) as f:
            lines = f.read().splitlines()
        folder, filename = lines[0], lines[1]
        dest = self._resolve(folder, filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as out:
            for i in range(total_chunks):
                chunk_path = os.path.join(temp_dir, f"{i:08d}")
                if not os.path.isfile(chunk_path):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    raise ValueError(f"Missing chunk {i}")
                with open(chunk_path, "rb") as cf:
                    shutil.copyfileobj(cf, out)
        shutil.rmtree(temp_dir, ignore_errors=True)
        stat = os.stat(dest)
        return StorageEntry(
            name=os.path.basename(dest),
            size=stat.st_size,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            is_dir=False,
        )

    def abort_chunked_upload(self, upload_id: str) -> None:
        temp_dir = self._temp_dir(upload_id)
        shutil.rmtree(temp_dir, ignore_errors=True)

    def resolve_path(self, folder: str, name: str) -> str:
        return self._resolve(folder, name)

    def file_exists(self, folder: str, name: str) -> bool:
        try:
            return os.path.isfile(self._resolve(folder, name))
        except ValueError:
            return False

    def delete_file(self, folder: str, name: str) -> None:
        path = self._resolve(folder, name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {name}")
        os.remove(path)

    def get_mime_type(self, folder: str, name: str) -> str:
        path = self._resolve(folder, name)
        mime, _ = mimetypes.guess_type(path)
        return mime or "application/octet-stream"


@lru_cache
def get_local_storage_adapter() -> LocalStorageAdapter:
    return LocalStorageAdapter(get_settings().storage_dir)
