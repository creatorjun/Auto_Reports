# backend/src/domain/entities/job.py
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE    = "done"
    ERROR   = "error"


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    status: JobStatus
    report_id: Optional[int] = None
    error: Optional[str] = None
