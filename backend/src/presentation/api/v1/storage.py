# backend/src/presentation/api/v1/storage.py
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.application.use_cases.storage_use_case import StorageUseCase
from src.presentation.api.v1.deps import get_storage_use_case

router = APIRouter(prefix="/storage", tags=["storage"])


class StorageFileInfo(BaseModel):
    name: str
    size: int
    uploaded_at: str
    is_dir: bool = False


class FolderCreateRequest(BaseModel):
    name: str
    folder: str = ""


class FileExistsResponse(BaseModel):
    exists: bool


def _decode(value: str) -> str:
    return urllib.parse.unquote(value)


@router.get("/items", response_model=list[StorageFileInfo])
async def list_items(
    folder: str = Query(default=""),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    try:
        entries = uc.list_entries(folder)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Folder not found")
    return [StorageFileInfo(**e.__dict__) for e in entries]


@router.get("/check", response_model=FileExistsResponse)
async def check_file_exists(
    folder: str = Query(default=""),
    name: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    folder, name = _decode(folder), _decode(name)
    exists = uc.file_exists(folder, name)
    return FileExistsResponse(exists=exists)


@router.post("/folders", status_code=201)
async def create_folder(
    body: FolderCreateRequest,
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    try:
        uc.create_folder(body.folder, body.name)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Already exists")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    return {"name": body.name}


@router.delete("/folders")
async def delete_folder(
    folder: str = Query(default=""),
    name: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    try:
        uc.delete_folder(folder, name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Folder not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")


@router.post("/upload", response_model=StorageFileInfo, status_code=201)
async def upload_file(
    file: UploadFile,
    folder: str = Query(default=""),
    overwrite: bool = Query(default=False),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    data = await file.read()
    filename = file.filename or "upload"
    try:
        entry = uc.upload_file(folder, filename, data, overwrite=overwrite)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="File already exists")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    return StorageFileInfo(**entry.__dict__)


@router.get("/preview")
async def preview_file(
    folder: str = Query(default=""),
    name: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    folder, name = _decode(folder), _decode(name)
    try:
        path = uc.get_file_path(folder, name)
        mime = uc.get_mime_type(folder, name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=path, media_type=mime, headers={"Content-Disposition": "inline"})


@router.get("/download")
async def download_file(
    folder: str = Query(default=""),
    name: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    folder, name = _decode(folder), _decode(name)
    try:
        path = uc.get_file_path(folder, name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=path, filename=name, media_type="application/octet-stream")


@router.delete("/files")
async def delete_file(
    folder: str = Query(default=""),
    name: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    folder, name = _decode(folder), _decode(name)
    try:
        uc.delete_file(folder, name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="File not found")
