# backend/tests/test_document_converter.py
import asyncio
import os
from pathlib import Path
import signal
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrastructure.storage.document_converter import LibreOfficeDocumentConverter

_MODULE = "src.infrastructure.storage.document_converter"


class ConversionProcess:
    def __init__(
        self,
        output_path: Path | None = None,
        content: bytes = b"%PDF-converted",
        stdout: bytes = b"",
        stderr: bytes = b"",
        exit_code: int = 0,
        gate: asyncio.Event | None = None,
    ) -> None:
        self.output_path = output_path
        self.content = content
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.gate = gate
        self.started = asyncio.Event()
        self.returncode: int | None = None
        self.killed = False
        self.communicate_calls = 0
        self.pid = 12345

    async def communicate(self) -> tuple[bytes, bytes]:
        self.communicate_calls += 1
        self.started.set()
        if self.gate is not None:
            await self.gate.wait()
        if not self.killed:
            if self.output_path is not None:
                self.output_path.write_bytes(self.content)
            self.returncode = self.exit_code
        return self.stdout, self.stderr

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9
        if self.gate is not None:
            self.gate.set()


class LibreOfficeDocumentConverterTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.source = Path(self.temp_dir.name) / "분기 보고서.pptx"
        self.source.write_bytes(b"presentation")
        self.converter = LibreOfficeDocumentConverter()
        self.platform_patch = patch(f"{_MODULE}._IS_POSIX", False)
        self.platform_patch.start()
        self.addCleanup(self.platform_patch.stop)

    async def test_concurrent_previews_isolate_outputs_and_preserve_stored_pdf(self) -> None:
        stored_pdf = self.source.with_suffix(".pdf")
        stored_pdf.write_bytes(b"existing-document")
        gate = asyncio.Event()
        output_dirs: list[Path] = []
        profiles: list[str] = []

        async def launch(*args: str, **kwargs: object) -> ConversionProcess:
            output_dir = Path(args[args.index("--outdir") + 1])
            output_dirs.append(output_dir)
            profiles.append(next(arg for arg in args if arg.startswith("-env:")))
            process = ConversionProcess(
                output_path=output_dir / self.source.with_suffix(".pdf").name,
                content=f"%PDF-result-{len(output_dirs)}".encode(),
                gate=gate,
            )
            if len(output_dirs) == 2:
                gate.set()
            return process

        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", side_effect=launch):
            results = await asyncio.gather(
                self.converter.convert_to_pdf(str(self.source)),
                self.converter.convert_to_pdf(str(self.source)),
            )

        self.assertEqual([b"%PDF-result-1", b"%PDF-result-2"], results)
        self.assertEqual(2, len(set(output_dirs)))
        self.assertEqual(2, len(set(profiles)))
        self.assertTrue(all(profile.startswith("-env:UserInstallation=file:") for profile in profiles))
        self.assertTrue(all(not directory.parent.exists() for directory in output_dirs))
        self.assertEqual(b"existing-document", stored_pdf.read_bytes())
        self.assertEqual(b"presentation", self.source.read_bytes())

    async def test_missing_output_reports_both_streams_and_cleans_workspace(self) -> None:
        process = ConversionProcess(stdout=b"filter unavailable", stderr=b"source rejected")
        with (
            patch(f"{_MODULE}.asyncio.create_subprocess_exec", return_value=process) as launch,
            self.assertLogs(_MODULE, level="ERROR") as logs,
        ):
            with self.assertRaisesRegex(RuntimeError, "output file not found") as error:
                await self.converter.convert_to_pdf(str(self.source))

        args = launch.call_args.args
        output_dir = Path(args[args.index("--outdir") + 1])
        self.assertFalse(output_dir.parent.exists())
        self.assertIn("filter unavailable", str(error.exception))
        self.assertIn("source rejected", str(error.exception))
        self.assertIn("filter unavailable", "\n".join(logs.output))
        self.assertIn("source rejected", "\n".join(logs.output))

    async def test_nonzero_exit_reports_failure_and_cleans_workspace(self) -> None:
        process = ConversionProcess(exit_code=1, stderr=b"conversion failed")
        with (
            patch(f"{_MODULE}.asyncio.create_subprocess_exec", return_value=process) as launch,
            self.assertLogs(_MODULE, level="ERROR"),
        ):
            with self.assertRaisesRegex(RuntimeError, r"rc=1.*conversion failed"):
                await self.converter.convert_to_pdf(str(self.source))

        args = launch.call_args.args
        self.assertFalse(Path(args[args.index("--outdir") + 1]).parent.exists())

    async def test_timeout_kills_and_reaps_process_before_workspace_cleanup(self) -> None:
        process = ConversionProcess(gate=asyncio.Event())
        with (
            patch(f"{_MODULE}.asyncio.create_subprocess_exec", return_value=process) as launch,
            patch(f"{_MODULE}._CONVERSION_TIMEOUT_SECONDS", 0.01),
            self.assertLogs(_MODULE, level="ERROR"),
        ):
            with self.assertRaisesRegex(TimeoutError, "PDF conversion timed out"):
                await self.converter.convert_to_pdf(str(self.source))

        args = launch.call_args.args
        self.assertTrue(process.killed)
        self.assertEqual(2, process.communicate_calls)
        self.assertFalse(Path(args[args.index("--outdir") + 1]).parent.exists())

    async def test_cancellation_kills_and_reaps_process_before_workspace_cleanup(self) -> None:
        process = ConversionProcess(gate=asyncio.Event())
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", return_value=process) as launch:
            task = asyncio.create_task(self.converter.convert_to_pdf(str(self.source)))
            await process.started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        args = launch.call_args.args
        self.assertTrue(process.killed)
        self.assertEqual(2, process.communicate_calls)
        self.assertFalse(Path(args[args.index("--outdir") + 1]).parent.exists())

    async def test_missing_executable_has_actionable_error_and_cleans_workspace(self) -> None:
        with (
            patch(
                f"{_MODULE}.asyncio.create_subprocess_exec", side_effect=FileNotFoundError
            ) as launch,
            self.assertLogs(_MODULE, level="ERROR"),
        ):
            with self.assertRaisesRegex(RuntimeError, "LibreOffice executable not found"):
                await self.converter.convert_to_pdf(str(self.source))

        args = launch.call_args.args
        self.assertFalse(Path(args[args.index("--outdir") + 1]).parent.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX process groups are required")
    async def test_posix_cancellation_kills_process_group(self) -> None:
        process = ConversionProcess(gate=asyncio.Event())
        with (
            patch(f"{_MODULE}._IS_POSIX", True),
            patch(f"{_MODULE}.asyncio.create_subprocess_exec", return_value=process) as launch,
            patch(f"{_MODULE}.os.killpg", side_effect=lambda pid, sig: process.kill()) as killpg,
        ):
            task = asyncio.create_task(self.converter.convert_to_pdf(str(self.source)))
            await process.started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        self.assertTrue(launch.call_args.kwargs["start_new_session"])
        killpg.assert_called_once_with(process.pid, signal.SIGKILL)
        self.assertEqual(2, process.communicate_calls)

    @unittest.skipUnless(sys.platform == "linux", "Linux process inspection is required")
    async def test_timeout_releases_pipes_held_by_descendant_after_launcher_exits(self) -> None:
        original_launch = asyncio.create_subprocess_exec
        descendant_file = Path(self.temp_dir.name) / "descendant.pid"
        launched: list[asyncio.subprocess.Process] = []
        launch_code = (
            "import pathlib, subprocess, sys; "
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
            "pathlib.Path(sys.argv[1]).write_text(str(child.pid))"
        )

        async def launch(*args: str, **kwargs: object) -> asyncio.subprocess.Process:
            process = await original_launch(
                sys.executable, "-c", launch_code, str(descendant_file), **kwargs
            )
            launched.append(process)
            return process

        try:
            with (
                patch(f"{_MODULE}._IS_POSIX", True),
                patch(f"{_MODULE}.asyncio.create_subprocess_exec", side_effect=launch) as launcher,
                patch(f"{_MODULE}._CONVERSION_TIMEOUT_SECONDS", 0.5),
                self.assertLogs(_MODULE, level="ERROR"),
            ):
                with self.assertRaisesRegex(TimeoutError, "PDF conversion timed out"):
                    await asyncio.wait_for(self.converter.convert_to_pdf(str(self.source)), 5)

            self.assertEqual(0, launched[0].returncode)
            descendant_pid = int(descendant_file.read_text())
            descendant_state = Path(f"/proc/{descendant_pid}/stat")
            try:
                state = descendant_state.read_text()
            except FileNotFoundError:
                pass
            else:
                self.assertEqual("Z", state.split()[2])
            args = launcher.call_args.args
            self.assertFalse(Path(args[args.index("--outdir") + 1]).parent.exists())
        finally:
            for process in launched:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.communicate()
