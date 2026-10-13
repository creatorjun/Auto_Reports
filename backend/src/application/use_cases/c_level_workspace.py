# backend/src/application/use_cases/c_level_workspace.py
import re
from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Any

from src.application.errors import EntityNotFoundError
from src.application.ports.c_level_repository import CLevelPreviewPort, CLevelRepository
from src.application.use_cases.c_level_report import CLevelReportUseCase
from src.domain.entities.c_level_history import CLevelComment, CLevelSnapshotSummary


class CLevelPreviewExpiredError(ValueError):
    pass


class CLevelWorkspaceUseCase:
    def __init__(self, reports: CLevelReportUseCase, repository: CLevelRepository, previews: CLevelPreviewPort) -> None:
        self._reports = reports
        self._repository = repository
        self._previews = previews

    async def get_report(self, period: str, end_date: date | None, refresh: bool, actor: str) -> dict[str, Any]:
        report = await self._reports.execute(period=period, end_date=end_date, refresh=refresh)
        keys = [issue["key"] for issue in report.get("issues", [])]
        comments = await self._repository.get_comments(keys)
        report["comments"] = {comment.issue_key: asdict(comment) for comment in comments}
        token = self._previews.put(report, actor)
        return {**self._public_report(report), "report_token": token}

    @staticmethod
    def _public_report(report: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in report.items() if key != "source_issues"}

    def _preview(self, token: str, actor: str) -> dict[str, Any]:
        payload = self._previews.get(token, actor)
        if payload is None:
            raise CLevelPreviewExpiredError("조회한 보고서가 만료되었습니다. 새로 조회한 후 저장해 주세요.")
        return payload

    async def save_comment(self, token: str, issue_key: str, delay_reason: str, action_taken: str, prevention_plan: str, included: bool, actor: str) -> CLevelComment:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*-\d+", issue_key):
            raise ValueError("올바른 Jira 티켓 번호가 아닙니다.")
        payload = self._preview(token, actor)
        if not any(issue.get("key") == issue_key for issue in payload.get("issues", [])):
            raise EntityNotFoundError("조회한 보고서의 Jira 티켓", issue_key)
        if any(len(value) > 10000 for value in (delay_reason, action_taken, prevention_plan)):
            raise ValueError("보고용 코멘트는 항목당 10,000자 이내로 입력해 주세요.")
        comment = CLevelComment(
            issue_key=issue_key, delay_reason=delay_reason.strip(), action_taken=action_taken.strip(),
            prevention_plan=prevention_plan.strip(), included=included, updated_by=actor,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        result = await self._repository.save_comment(comment)
        latest = self._previews.get(token, actor)
        if latest is not None:
            latest.setdefault("comments", {})[issue_key] = asdict(result)
            self._previews.replace(token, latest, actor)
        return result

    async def save_snapshot(self, token: str, title: str | None, actor: str) -> CLevelSnapshotSummary:
        payload = self._preview(token, actor)
        title = (title or "").strip() or f"집중(특별) 관리 보고 · {payload['start_date']} ~ {payload['end_date']}"
        if len(title) > 200:
            raise ValueError("보고서 제목은 200자 이내로 입력해 주세요.")
        payload.pop("report_token", None)
        payload.pop("snapshot", None)
        return await self._repository.save_snapshot(payload, title, actor)

    async def list_snapshots(self, limit: int = 20, offset: int = 0) -> list[CLevelSnapshotSummary]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("조회 범위가 올바르지 않습니다.")
        return await self._repository.list_snapshots(limit, offset)

    async def get_snapshot(self, snapshot_id: int) -> dict[str, Any]:
        result = await self._repository.get_snapshot(snapshot_id)
        if result is None:
            raise EntityNotFoundError("저장된 C-Level 보고서", snapshot_id)
        summary, payload = result
        return {**self._public_report(payload), "report_token": None, "snapshot": asdict(summary)}
