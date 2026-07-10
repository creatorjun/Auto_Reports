# backend/src/infrastructure/storage/local_storage.py
import mimetypes
import os
import shutil
from datetime import datetime, timezone

from src.domain.ports.storage_port import StorageEntry, StoragePort
from src.infrastructure.config.settings import get_settings


class LocalStorageAdapter(StoragePort):
    def __init__(self) -> None:
        self._base = os.path.realpath(
            os.environ.get("STORAGE_DIR", get_settings().__dict__.get("storage_dir", "/app/storage"))
        )
        os.makedirs(self._base, exist_ok=True)

    def _resolve(self, folder: str, name: str = "") -> str:
        target = os.path.realpath(os.path.join(self._base, folder.lstrip("/"), name))
        if not target.startswith(self._base + os.sep) and target != self._base:
            raise ValueError("Invalid path")
        if name:
            basename = os.path.basename(target)
            if not basename or basename.startswith("."):
                raise ValueError("Invalid name")
        return target

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

    def save_file(self, folder: str, filename: str, data: bytes) -> StorageEntry:
        dest = self._resolve(folder, filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        stat = os.stat(dest)
        return StorageEntry(
            name=os.path.basename(dest),
            size=stat.st_size,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            is_dir=False,
        )

    def resolve_path(self, folder: str, name: str) -> str:
        return self._resolve(folder, name)

    def file_exists(self, folder: str, name: str) -> bool:
        try:
            path = self._resolve(folder, name)
            return os.path.isfile(path)
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
