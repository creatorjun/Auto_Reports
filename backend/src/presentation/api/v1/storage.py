# backend/src/presentation/api/v1/storage.py
import os
import urllib.parse
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

STORAGE_DIR = os.environ.get("STORAGE_DIR", "/app/storage")

router = APIRouter(prefix="/storage", tags=["storage"])


class StorageFileInfo(BaseModel):
    name: str
    size: int
    uploaded_at: str


def _ensure_dir() -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)


def _safe_path(filename: str) -> str:
    basename = os.path.basename(filename)
    if not basename or basename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return os.path.join(STORAGE_DIR, basename)


@router.get("/", response_model=list[StorageFileInfo])
async def list_files():
    _ensure_dir()
    result: list[StorageFileInfo] = []
    for entry in sorted(os.scandir(STORAGE_DIR), key=lambda e: e.stat().st_mtime, reverse=True):
        if entry.is_file():
            stat = entry.stat()
            result.append(StorageFileInfo(
                name=entry.name,
                size=stat.st_size,
                uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            ))
    return result


@router.post("/", response_model=StorageFileInfo, status_code=201)
async def upload_file(file: UploadFile):
    _ensure_dir()
    dest = _safe_path(file.filename or "upload")
    contents = await file.read()
    with open(dest, "wb") as f:
        f.write(contents)
    stat = os.stat(dest)
    return StorageFileInfo(
        name=os.path.basename(dest),
        size=stat.st_size,
        uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    )


@router.get("/download/{filename}")
async def download_file(filename: str):
    decoded = urllib.parse.unquote(filename)
    path = _safe_path(decoded)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=path,
        filename=decoded,
        media_type="application/octet-stream",
    )


@router.delete("/{filename}", status_code=204)
async def delete_file(filename: str):
    decoded = urllib.parse.unquote(filename)
    path = _safe_path(decoded)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(path)
