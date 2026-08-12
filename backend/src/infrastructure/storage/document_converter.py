# backend/src/infrastructure/storage/document_converter.py
import asyncio
import logging
from pathlib import Path

from src.application.ports.document_converter_port import DocumentConverterPort

_CONVERTIBLE_EXTENSIONS = {
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    ".hwp",
    ".hwpx",
}
_CONVERSION_TIMEOUT_SECONDS = 120
_log = logging.getLogger(__name__)


class LibreOfficeDocumentConverter(DocumentConverterPort):
    def supports(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in _CONVERTIBLE_EXTENSIONS

    async def convert_to_pdf(self, source_path: str) -> bytes:
        source = Path(source_path)
        process = await asyncio.create_subprocess_exec(
            "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(source.parent),
            str(source),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=_CONVERSION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise TimeoutError("PDF conversion timed out") from exc
        error_text = stderr.decode(errors="replace").strip() if stderr else ""
        if process.returncode != 0:
            _log.error(
                "libreoffice conversion failed (rc=%d): %s",
                process.returncode,
                error_text,
            )
            raise RuntimeError(
                f"PDF conversion failed (rc={process.returncode}): {error_text}"
            )
        converted = source.with_suffix(".pdf")
        if not converted.exists():
            _log.error("libreoffice exited 0 but pdf not found: %s", error_text)
            raise RuntimeError("PDF conversion failed: output file not found")
        try:
            return converted.read_bytes()
        finally:
            converted.unlink(missing_ok=True)
