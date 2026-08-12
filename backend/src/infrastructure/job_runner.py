# backend/src/infrastructure/job_runner.py
import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime

from src.application.errors import JobAlreadyRunningError
from src.application.ports.job_repository import JobRepository
from src.application.ports.job_runner_port import JobRunnerPort
from src.domain.entities.job import JobRecord, JobStatus
from src.domain.entities.report import Report

logger = logging.getLogger(__name__)


class JobRunner(JobRunnerPort):
    def __init__(
        self,
        generate_report: Callable[
            [datetime | None, datetime | None],
            Awaitable[Report],
        ],
        job_repository: JobRepository,
    ) -> None:
        self._generate_report = generate_report
        self._repo = job_repository
        self._lock = asyncio.Lock()
        self._running_job_id: str | None = None
        self._notify_events: dict[str, set[asyncio.Event]] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def _notify(self, job_id: str) -> None:
        for event in self._notify_events.get(job_id, set()):
            event.set()

    async def wait_for_update(
        self,
        job_id: str,
        known_status: JobStatus,
        timeout: float = 30.0,
    ) -> None:
        current = await self._repo.find(job_id)
        if current is None or current.status != known_status:
            return
        event = asyncio.Event()
        waiters = self._notify_events.setdefault(job_id, set())
        waiters.add(event)
        try:
            current = await self._repo.find(job_id)
            if current is not None and current.status == known_status:
                await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            waiters.discard(event)
            if not waiters:
                self._notify_events.pop(job_id, None)

    async def get_job_status(self, job_id: str) -> JobRecord | None:
        return await self._repo.find(job_id)

    async def submit(
        self,
        job_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> None:
        async with self._lock:
            if self._running_job_id is not None:
                raise JobAlreadyRunningError(self._running_job_id)
            self._running_job_id = job_id

        try:
            await self._repo.save(
                JobRecord(job_id=job_id, status=JobStatus.PENDING)
            )
        except Exception:
            await self._release(job_id)
            raise

        task = asyncio.create_task(
            self._execute(job_id, start_date, end_date),
            name=f"report-job-{job_id}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _execute(
        self,
        job_id: str,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> None:
        try:
            await self._repo.save(
                JobRecord(job_id=job_id, status=JobStatus.RUNNING)
            )
            self._notify(job_id)
            report = await self._generate_report(start_date, end_date)
            await self._repo.save(
                JobRecord(job_id=job_id, status=JobStatus.DONE, report_id=report.id)
            )
            self._notify(job_id)
            logger.info("[job:%s] 완료 report_id=%s", job_id, report.id)
        except asyncio.CancelledError:
            await self._repo.save(
                JobRecord(
                    job_id=job_id,
                    status=JobStatus.ERROR,
                    error="작업이 취소되었습니다.",
                )
            )
            self._notify(job_id)
            raise
        except Exception as error:
            await self._repo.save(
                JobRecord(job_id=job_id, status=JobStatus.ERROR, error=str(error))
            )
            self._notify(job_id)
            logger.exception("[job:%s] 실패", job_id)
        finally:
            await self._release(job_id)

    async def _release(self, job_id: str) -> None:
        async with self._lock:
            if self._running_job_id == job_id:
                self._running_job_id = None

    async def run_scheduled_job(self) -> None:
        job_id = str(uuid.uuid4())
        logger.info("스케줄 실행 [job:%s]", job_id)
        try:
            await self.submit(job_id)
        except JobAlreadyRunningError as error:
            logger.warning("스케줄 작업 생략: %s", error)

    async def aclose(self) -> None:
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        for waiters in self._notify_events.values():
            for event in waiters:
                event.set()
        self._notify_events.clear()
