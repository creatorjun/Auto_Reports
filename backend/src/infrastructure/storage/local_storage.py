# backend/src/infrastructure/storage/local_storage.py
import asyncio
import mimetypes
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from functools import lru_cache

import aiofiles
from src.application.ports.storage_port import AsyncBinaryReader, StorageEntry, StoragePort
from src.infrastructure.config.settings import get_settings

CHUNK_SIZE = 1024 * 1024
_TEMP_PREFIX = ".chunked_"
_ARCHIVE_DIR_NAME = f"{_TEMP_PREFIX}archives"


class LocalStorageAdapter(StoragePort):
    def __init__(self, base_dir: str) -> None:
        self._base = os.path.realpath(base_dir)
        os.makedirs(self._base, exist_ok=True)
        self._path_locks: dict[str, asyncio.Lock] = {}
        self._meta_lock = asyncio.Lock()
        self._archive_dir = os.path.join(self._base, _ARCHIVE_DIR_NAME)
        shutil.rmtree(self._archive_dir, ignore_errors=True)
        os.makedirs(self._archive_dir)

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

    @staticmethod
    def _validate_entry_name(name: str) -> None:
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("Invalid name")

    def _resolve_entries(self, folder: str, names: list[str]) -> list[tuple[str, str]]:
        if not names or len(names) > 200:
            raise ValueError("Invalid selection")
        entries: list[tuple[str, str]] = []
        seen: set[str] = set()
        for name in names:
            self._validate_entry_name(name)
            if name in seen:
                continue
            seen.add(name)
            path = self._resolve(folder, name)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Entry not found: {name}")
            entries.append((name, path))
        return entries

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
        visible_entries = (
            entry
            for entry in os.scandir(dir_path)
            if not entry.name.startswith(_TEMP_PREFIX)
        )
        for entry in sorted(visible_entries, key=lambda e: (e.is_file(), e.name.lower())):
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

    def move_entry(self, source_folder: str, name: str, destination_folder: str) -> None:
        self._validate_entry_name(name)
        source = self._resolve(source_folder, name)
        destination_dir = self._resolve(destination_folder)
        destination = self._resolve(destination_folder, name)
        if not os.path.exists(source):
            raise FileNotFoundError(f"Entry not found: {name}")
        if not os.path.isdir(destination_dir):
            raise FileNotFoundError(f"Folder not found: {destination_folder}")
        source_key = os.path.normcase(source)
        destination_key = os.path.normcase(destination)
        if source_key == destination_key:
            raise ValueError("Source and destination are the same")
        if os.path.exists(destination):
            raise FileExistsError(f"Already exists: {name}")
        if os.path.isdir(source):
            destination_dir_key = os.path.normcase(destination_dir)
            if os.path.commonpath((source_key, destination_dir_key)) == source_key:
                raise ValueError("Cannot move a folder into itself")
        shutil.move(source, destination)

    def create_archive(self, folder: str, names: list[str]) -> str:
        entries = self._resolve_entries(folder, names)
        archive_path = os.path.join(self._archive_dir, f"{uuid.uuid4().hex}.zip")
        try:
            with zipfile.ZipFile(
                archive_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                allowZip64=True,
            ) as archive:
                for name, path in entries:
                    if os.path.isdir(path):
                        for root, directories, filenames in os.walk(path):
                            directories[:] = [
                                directory
                                for directory in directories
                                if not os.path.islink(os.path.join(root, directory))
                            ]
                            relative = os.path.relpath(root, path)
                            archive_root = name if relative == "." else f"{name}/{relative.replace(os.sep, '/')}"
                            archive.write(root, archive_root)
                            for filename in filenames:
                                source = os.path.join(root, filename)
                                if os.path.islink(source):
                                    continue
                                archive.write(source, f"{archive_root}/{filename}")
                    else:
                        archive.write(path, name)
            return archive_path
        except Exception:
            if os.path.exists(archive_path):
                os.remove(archive_path)
            raise

    def delete_archive(self, path: str) -> None:
        archive_path = os.path.realpath(path)
        archive_root = os.path.realpath(self._archive_dir)
        if os.path.commonpath((archive_root, archive_path)) != archive_root:
            raise ValueError("Invalid archive path")
        try:
            os.remove(archive_path)
        except FileNotFoundError:
            pass

    def delete_entries(self, folder: str, names: list[str]) -> None:
        entries = self._resolve_entries(folder, names)
        for _, path in entries:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

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

    async def save_file_streaming(self, folder: str, filename: str, upload: AsyncBinaryReader) -> StorageEntry:
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
