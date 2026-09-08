# backend/src/infrastructure/storage/document_converter.py
import asyncio
import logging
import os
from pathlib import Path
import signal
from tempfile import TemporaryDirectory

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
_IS_POSIX = os.name == "posix"
_log = logging.getLogger(__name__)


class LibreOfficeDocumentConverter(DocumentConverterPort):
    def supports(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in _CONVERTIBLE_EXTENSIONS

    async def convert_to_pdf(self, source_path: str) -> bytes:
        source = Path(source_path).resolve()
        with TemporaryDirectory(prefix="auto-reports-conversion-") as temp_dir:
            workspace = Path(temp_dir).resolve()
            output_dir = workspace / "output"
            output_dir.mkdir()
            profile_uri = (workspace / "profile").as_uri()
            try:
                process = await asyncio.create_subprocess_exec(
                    "libreoffice",
                    f"-env:UserInstallation={profile_uri}",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_dir),
                    str(source),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    start_new_session=_IS_POSIX,
                )
            except FileNotFoundError as exc:
                _log.error("libreoffice executable was not found")
                raise RuntimeError(
                    "PDF conversion unavailable: LibreOffice executable not found"
                ) from exc
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=_CONVERSION_TIMEOUT_SECONDS,
                )
            except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
                if _IS_POSIX:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                elif process.returncode is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                await process.communicate()
                if isinstance(exc, asyncio.CancelledError):
                    raise
                _log.error("libreoffice conversion timed out")
                raise TimeoutError("PDF conversion timed out") from exc
            diagnostics = "\n".join(
                output.decode(errors="replace").strip()
                for output in (stdout, stderr)
                if output and output.strip()
            )
            if process.returncode != 0:
                _log.error(
                    "libreoffice conversion failed (rc=%d): %s",
                    process.returncode,
                    diagnostics,
                )
                raise RuntimeError(
                    f"PDF conversion failed (rc={process.returncode}): {diagnostics}"
                )
            converted = output_dir / source.with_suffix(".pdf").name
            if not converted.is_file():
                _log.error("libreoffice exited 0 but pdf not found: %s", diagnostics)
                raise RuntimeError(
                    f"PDF conversion failed: output file not found. {diagnostics}".rstrip()
                )
            content = await asyncio.to_thread(converted.read_bytes)
            _log.debug("libreoffice conversion completed (%d bytes)", len(content))
            return content
