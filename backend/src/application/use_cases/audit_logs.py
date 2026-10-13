# backend/src/application/use_cases/audit_logs.py
from src.application.ports.audit_log_reader_port import AuditLogReaderPort
from src.domain.entities.audit_log import AuditLogPage, AuditLogQuery


class AuditLogsUseCase:
    def __init__(self, reader: AuditLogReaderPort) -> None:
        self._reader = reader

    async def execute(self, query: AuditLogQuery) -> AuditLogPage:
        if query.start_date and query.end_date and query.start_date > query.end_date:
            raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")
        if not 1 <= query.limit <= 100 or not 0 <= query.offset < query.limit * 100:
            raise ValueError("한 페이지에 최대 100건, 최대 100페이지까지 조회할 수 있습니다. 기간이나 검색 조건을 좁혀 주세요.")
        if any(len(value) > 200 for value in (query.event, query.username, query.ip, query.search)):
            raise ValueError("검색 조건은 200자 이내로 입력해 주세요.")
        return await self._reader.read(query)
