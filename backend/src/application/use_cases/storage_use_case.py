# backend/src/application/use_cases/storage_use_case.py
from src.domain.ports.storage_port import StorageEntry, StoragePort


class StorageUseCase:
    def __init__(self, storage: StoragePort) -> None:
        self._storage = storage

    def list_entries(self, folder: str) -> list[StorageEntry]:
        return self._storage.list_entries(folder)

    def create_folder(self, folder: str, name: str) -> None:
        self._storage.create_folder(folder, name)

    def delete_folder(self, folder: str, name: str) -> None:
        self._storage.delete_folder(folder, name)

    def upload_file(self, folder: str, filename: str, data: bytes, overwrite: bool = False) -> StorageEntry:
        safe_name = filename.strip() or "upload"
        if not overwrite and self._storage.file_exists(folder, safe_name):
            raise FileExistsError(f"File already exists: {safe_name}")
        return self._storage.save_file(folder, safe_name, data)

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
