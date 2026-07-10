# backend/src/application/mappers/job_mapper.py
from src.domain.entities.job import JobRecord
from src.presentation.schemas.report_schema import JobStatusSchema


class JobMapper:
    @staticmethod
    def to_schema(record: JobRecord) -> JobStatusSchema:
        return JobStatusSchema(
            job_id=record.job_id,
            status=record.status.value,
            report_id=record.report_id,
            error=record.error,
        )
