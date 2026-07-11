# backend/src/presentation/api/v1/storage.py
import urllib.parse
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from src.application.use_cases.storage_use_case import StorageUseCase
from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.jwt_service import get_jwt_service
from src.presentation.api.v1.deps import get_storage_use_case
from src.shared.audit_helper import get_client_ip
from src.shared.audit_logger import get_audit_logger

router = APIRouter(prefix="/storage", tags=["storage"])
preview_router = APIRouter(prefix="/storage", tags=["storage"])
_audit = get_audit_logger()

CHUNK_SIZE = 1024 * 1024  # 1MB


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


class QuotaResponse(BaseModel):
    used: int
    limit: int
    available: int
    percent: float


class ChunkInitRequest(BaseModel):
    folder: str = ""
    filename: str
    total_size: int | None = None
    overwrite: bool = False


class ChunkInitResponse(BaseModel):
    upload_id: str


class ChunkCompleteRequest(BaseModel):
    upload_id: str
    total_chunks: int


class ChunkAbortRequest(BaseModel):
    upload_id: str


def _decode(value: str) -> str:
    return urllib.parse.unquote(value)


def _verify_preview_token(token: str | None) -> None:
    settings = get_settings()
    if not settings.login:
        return
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        get_jwt_service().decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    return uc.get_quota()


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
    request: Request,
    body: FolderCreateRequest,
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    try:
        uc.create_folder(body.folder, body.name)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Already exists")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    ip = get_client_ip(request)
    _audit.audit("FOLDER_CREATE | ip=%s | path=%s/%s", ip, body.folder, body.name)
    return {"name": body.name}


@router.delete("/folders")
async def delete_folder(
    request: Request,
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
    ip = get_client_ip(request)
    _audit.audit("FOLDER_DELETE | ip=%s | path=%s/%s", ip, folder, name)


@router.post("/upload", response_model=StorageFileInfo, status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile,
    folder: str = Query(default=""),
    overwrite: bool = Query(default=False),
    file_size: int | None = Query(default=None),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    filename = file.filename or "upload"
    try:
        entry = await uc.upload_file_streaming(
            folder, filename, file,
            overwrite=overwrite,
            file_size=file_size,
        )
    except FileExistsError:
        raise HTTPException(status_code=409, detail="File already exists")
    except ValueError as e:
        msg = str(e)
        if msg.startswith("QUOTA_EXCEEDED:"):
            _, available, needed = msg.split(":")
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "available": int(available),
                    "needed": int(needed),
                },
            )
        raise HTTPException(status_code=400, detail="Invalid path")
    ip = get_client_ip(request)
    _audit.audit("FILE_UPLOAD | ip=%s | path=%s/%s | size=%d | overwrite=%s", ip, folder, filename, entry.size, overwrite)
    return StorageFileInfo(**entry.__dict__)


@router.post("/upload/init", response_model=ChunkInitResponse, status_code=201)
async def chunked_upload_init(
    request: Request,
    body: ChunkInitRequest,
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    upload_id = str(uuid.uuid4())
    try:
        uc.init_chunked_upload(
            upload_id,
            body.folder,
            body.filename,
            total_size=body.total_size,
            overwrite=body.overwrite,
        )
    except FileExistsError:
        raise HTTPException(status_code=409, detail="File already exists")
    except ValueError as e:
        msg = str(e)
        if msg.startswith("QUOTA_EXCEEDED:"):
            _, available, needed = msg.split(":")
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "available": int(available),
                    "needed": int(needed),
                },
            )
        raise HTTPException(status_code=400, detail="Invalid request")
    ip = get_client_ip(request)
    _audit.audit("CHUNKED_INIT | ip=%s | upload_id=%s | file=%s/%s", ip, upload_id, body.folder, body.filename)
    return ChunkInitResponse(upload_id=upload_id)


@router.post("/upload/chunk", status_code=204)
async def chunked_upload_chunk(
    upload_id: str = Query(...),
    chunk_index: int = Query(...),
    file: UploadFile = ...,
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    data = await file.read()
    try:
        await uc.upload_chunk(upload_id, chunk_index, data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Upload session not found")
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))


@router.post("/upload/complete", response_model=StorageFileInfo)
async def chunked_upload_complete(
    request: Request,
    body: ChunkCompleteRequest,
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    try:
        entry = uc.complete_chunked_upload(body.upload_id, body.total_chunks)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Upload session not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ip = get_client_ip(request)
    _audit.audit("CHUNKED_COMPLETE | ip=%s | upload_id=%s | size=%d", ip, body.upload_id, entry.size)
    return StorageFileInfo(**entry.__dict__)


@router.delete("/upload/abort", status_code=204)
async def chunked_upload_abort(
    request: Request,
    upload_id: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    uc.abort_chunked_upload(upload_id)
    ip = get_client_ip(request)
    _audit.audit("CHUNKED_ABORT | ip=%s | upload_id=%s", ip, upload_id)


@preview_router.get("/preview")
async def preview_file(
    folder: str = Query(default=""),
    name: str = Query(...),
    _t: str | None = Query(default=None),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    _verify_preview_token(_t)
    folder, name = _decode(folder), _decode(name)
    try:
        path = uc.get_file_path(folder, name)
        mime = uc.get_mime_type(folder, name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="File not found")
    safe_name = urllib.parse.quote(name, safe="")
    return FileResponse(
        path=path,
        media_type=mime,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{safe_name}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        },
    )


@preview_router.get("/preview-converted")
async def preview_converted(
    folder: str = Query(default=""),
    name: str = Query(...),
    _t: str | None = Query(default=None),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    _verify_preview_token(_t)
    folder, name = _decode(folder), _decode(name)
    if not uc.is_convertible(name):
        raise HTTPException(status_code=400, detail="Unsupported format for conversion")
    try:
        pdf_bytes = await uc.convert_to_pdf(folder, name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Conversion timed out")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


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
    safe_name = urllib.parse.quote(name, safe="")
    return FileResponse(
        path=path,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}",
        },
    )


@router.delete("/files")
async def delete_file(
    request: Request,
    folder: str = Query(default=""),
    name: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    folder = _decode(folder)
    name = _decode(name)
    try:
        uc.delete_file(folder, name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="File not found")
    ip = get_client_ip(request)
    _audit.audit("FILE_DELETE | ip=%s | path=%s/%s", ip, folder, name)
