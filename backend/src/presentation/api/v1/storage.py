# backend/src/presentation/api/v1/storage.py
import urllib.parse
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from src.application.ports.audit_port import AuditPort
from src.application.services.auth_service import AuthService
from src.application.use_cases.storage_use_case import StorageUseCase
from src.presentation.api.deps import get_audit, get_auth, get_storage_use_case
from src.presentation.http.client_ip import get_client_ip

router = APIRouter(prefix="/storage", tags=["storage"])
preview_router = APIRouter(prefix="/storage", tags=["storage"])

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


def _verify_preview_token(auth: AuthService, token: str | None) -> None:
    if not auth.enabled:
        return
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        auth.decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _make_content_disposition(disposition: str, filename: str) -> str:
    try:
        filename.encode("ascii")
        ascii_name = filename
    except UnicodeEncodeError:
        ascii_name = "download"
    encoded_name = urllib.parse.quote(filename, safe="")
    return f'{disposition}; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}'


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    return await uc.get_quota()


@router.get("/items", response_model=list[StorageFileInfo])
async def list_items(
    folder: str = Query(default=""),
    uc: StorageUseCase = Depends(get_storage_use_case),
):
    try:
        entries = await uc.list_entries(folder)
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
    exists = await uc.file_exists(folder, name)
    return FileExistsResponse(exists=exists)


@router.post("/folders", status_code=201)
async def create_folder(
    request: Request,
    body: FolderCreateRequest,
    uc: StorageUseCase = Depends(get_storage_use_case),
    audit: AuditPort = Depends(get_audit),
):
    try:
        await uc.create_folder(body.folder, body.name)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Already exists")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    ip = get_client_ip(request)
    audit.record("FOLDER_CREATE", ip=ip, path=f"{body.folder}/{body.name}")
    return {"name": body.name}


@router.delete("/folders")
async def delete_folder(
    request: Request,
    folder: str = Query(default=""),
    name: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
    audit: AuditPort = Depends(get_audit),
):
    try:
        await uc.delete_folder(folder, name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Folder not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    ip = get_client_ip(request)
    audit.record("FOLDER_DELETE", ip=ip, path=f"{folder}/{name}")


@router.post("/upload", response_model=StorageFileInfo, status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile,
    folder: str = Query(default=""),
    overwrite: bool = Query(default=False),
    file_size: int | None = Query(default=None),
    uc: StorageUseCase = Depends(get_storage_use_case),
    audit: AuditPort = Depends(get_audit),
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
    audit.record(
        "FILE_UPLOAD",
        ip=ip,
        path=f"{folder}/{filename}",
        size=entry.size,
        overwrite=overwrite,
    )
    return StorageFileInfo(**entry.__dict__)


@router.post("/upload/init", response_model=ChunkInitResponse, status_code=201)
async def chunked_upload_init(
    request: Request,
    body: ChunkInitRequest,
    uc: StorageUseCase = Depends(get_storage_use_case),
    audit: AuditPort = Depends(get_audit),
):
    upload_id = str(uuid.uuid4())
    try:
        await uc.init_chunked_upload(
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
    audit.record(
        "CHUNKED_INIT",
        ip=ip,
        upload_id=upload_id,
        file=f"{body.folder}/{body.filename}",
    )
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
    audit: AuditPort = Depends(get_audit),
):
    try:
        entry = await uc.complete_chunked_upload(body.upload_id, body.total_chunks)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Upload session not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ip = get_client_ip(request)
    audit.record(
        "CHUNKED_COMPLETE",
        ip=ip,
        upload_id=body.upload_id,
        size=entry.size,
    )
    return StorageFileInfo(**entry.__dict__)


@router.delete("/upload/abort", status_code=204)
async def chunked_upload_abort(
    request: Request,
    upload_id: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
    audit: AuditPort = Depends(get_audit),
):
    await uc.abort_chunked_upload(upload_id)
    ip = get_client_ip(request)
    audit.record("CHUNKED_ABORT", ip=ip, upload_id=upload_id)


@preview_router.get("/preview")
async def preview_file(
    request: Request,
    folder: str = Query(default=""),
    name: str = Query(...),
    _t: str | None = Query(default=None),
    uc: StorageUseCase = Depends(get_storage_use_case),
    auth: AuthService = Depends(get_auth),
):
    _verify_preview_token(auth, _t)
    folder, name = _decode(folder), _decode(name)
    try:
        path = await uc.get_file_path(folder, name)
        mime = uc.get_mime_type(folder, name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=path,
        media_type=mime,
        headers={
            "Content-Disposition": _make_content_disposition("inline", name),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        },
    )


@preview_router.get("/preview-converted")
async def preview_converted(
    request: Request,
    folder: str = Query(default=""),
    name: str = Query(...),
    _t: str | None = Query(default=None),
    uc: StorageUseCase = Depends(get_storage_use_case),
    auth: AuthService = Depends(get_auth),
):
    _verify_preview_token(auth, _t)
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


@preview_router.get("/download")
async def download_file(
    request: Request,
    folder: str = Query(default=""),
    name: str = Query(...),
    _t: str | None = Query(default=None),
    uc: StorageUseCase = Depends(get_storage_use_case),
    auth: AuthService = Depends(get_auth),
):
    _verify_preview_token(auth, _t)
    folder, name = _decode(folder), _decode(name)
    try:
        path = await uc.get_file_path(folder, name)
        mime = uc.get_mime_type(folder, name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=path,
        media_type=mime,
        headers={
            "Content-Disposition": _make_content_disposition("attachment", name),
            "X-Content-Type-Options": "nosniff",
            "X-Download-Options": "noopen",
            "Cache-Control": "no-store",
        },
    )


@router.delete("/files")
async def delete_file(
    request: Request,
    folder: str = Query(default=""),
    name: str = Query(...),
    uc: StorageUseCase = Depends(get_storage_use_case),
    audit: AuditPort = Depends(get_audit),
):
    folder = _decode(folder)
    name = _decode(name)
    try:
        await uc.delete_file(folder, name)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="File not found")
    ip = get_client_ip(request)
    audit.record("FILE_DELETE", ip=ip, path=f"{folder}/{name}")
