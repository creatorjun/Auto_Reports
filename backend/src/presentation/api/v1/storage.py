# backend/src/presentation/api/v1/storage.py
import os
import shutil
import urllib.parse
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

STORAGE_DIR = os.environ.get("STORAGE_DIR", "/app/storage")

router = APIRouter(prefix="/storage", tags=["storage"])


class StorageFileInfo(BaseModel):
    name: str
    size: int
    uploaded_at: str
    is_dir: bool = False


class FolderCreateRequest(BaseModel):
    name: str
    folder: str = ""


def _resolve(folder: str, name: str = "") -> str:
    base = os.path.realpath(STORAGE_DIR)
    target = os.path.realpath(os.path.join(base, folder.lstrip("/"), name))
    if not target.startswith(base):
        raise HTTPException(status_code=400, detail="Invalid path")
    if name:
        basename = os.path.basename(target)
        if not basename or basename.startswith("."):
            raise HTTPException(status_code=400, detail="Invalid name")
    return target


def _ensure_storage() -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)


@router.get("/", response_model=list[StorageFileInfo])
async def list_items(folder: str = Query(default="")):
    _ensure_storage()
    dir_path = _resolve(folder)
    if not os.path.isdir(dir_path):
        raise HTTPException(status_code=404, detail="Folder not found")
    result: list[StorageFileInfo] = []
    for entry in sorted(os.scandir(dir_path), key=lambda e: (e.is_file(), e.name.lower())):
        stat = entry.stat()
        result.append(StorageFileInfo(
            name=entry.name,
            size=stat.st_size if entry.is_file() else 0,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            is_dir=entry.is_dir(),
        ))
    return result


@router.post("/folders", status_code=201)
async def create_folder(body: FolderCreateRequest):
    _ensure_storage()
    path = _resolve(body.folder, body.name)
    if os.path.exists(path):
        raise HTTPException(status_code=409, detail="Already exists")
    os.makedirs(path)
    return {"name": body.name}


@router.delete("/folders")
async def delete_folder(folder: str = Query(...), name: str = Query(...)):
    path = _resolve(folder, name)
    if not os.path.isdir(path):
        raise HTTPException(status_code=404, detail="Folder not found")
    shutil.rmtree(path)


@router.post("/", response_model=StorageFileInfo, status_code=201)
async def upload_file(file: UploadFile, folder: str = Query(default="")):
    _ensure_storage()
    dest = _resolve(folder, file.filename or "upload")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    contents = await file.read()
    with open(dest, "wb") as f:
        f.write(contents)
    stat = os.stat(dest)
    return StorageFileInfo(
        name=os.path.basename(dest),
        size=stat.st_size,
        uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        is_dir=False,
    )


@router.get("/download")
async def download_file(folder: str = Query(default=""), name: str = Query(...)):
    decoded_name = urllib.parse.unquote(name)
    decoded_folder = urllib.parse.unquote(folder)
    path = _resolve(decoded_folder, decoded_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=path,
        filename=decoded_name,
        media_type="application/octet-stream",
    )


@router.delete("/file")
async def delete_file(folder: str = Query(default=""), name: str = Query(...)):
    decoded_name = urllib.parse.unquote(name)
    decoded_folder = urllib.parse.unquote(folder)
    path = _resolve(decoded_folder, decoded_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(path)
