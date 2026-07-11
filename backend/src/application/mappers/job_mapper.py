# backend/src/application/mappers/job_mapper.py
from src.domain.entities.job import JobRecord, JobStatus
from src.presentation.schemas.report_schema import JobStatusSchema

_RETRY_AFTER: dict[JobStatus, int | None] = {
    JobStatus.PENDING: 3,
    JobStatus.RUNNING: 5,
    JobStatus.DONE:    None,
    JobStatus.ERROR:   None,
}


class JobMapper:
    @staticmethod
    def to_schema(record: JobRecord) -> JobStatusSchema:
        status = JobStatus(record.status) if isinstance(record.status, str) else record.status
        return JobStatusSchema(
            job_id=record.job_id,
            status=record.status if isinstance(record.status, str) else record.status.value,
            report_id=record.report_id,
            error=record.error,
            retry_after=_RETRY_AFTER.get(status),
        )
