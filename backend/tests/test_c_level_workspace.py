# backend/tests/test_c_level_workspace.py
import unittest
from copy import deepcopy
from unittest.mock import AsyncMock

from src.application.errors import EntityNotFoundError
from src.application.use_cases.c_level_workspace import CLevelPreviewExpiredError, CLevelWorkspaceUseCase
from src.domain.entities.c_level_history import CLevelSnapshotSummary
from src.infrastructure.cache.c_level_preview_cache import CLevelPreviewCache


class CLevelWorkspaceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.payload = {
            "period": "week", "start_date": "2026-10-06", "end_date": "2026-10-12",
            "as_of": "2026-10-13T00:00:00+09:00", "issues": [{"key": "TACEA-3340"}],
            "summary": [{"unresolved": 3, "resolution_rate": None}],
        }
        self.reports = AsyncMock()
        self.reports.execute.side_effect = lambda **kwargs: deepcopy(self.payload)
        self.repository = AsyncMock()
        self.repository.get_comments.return_value = []
        self.repository.save_comment.side_effect = lambda value: value
        self.previews = CLevelPreviewCache()
        self.use_case = CLevelWorkspaceUseCase(self.reports, self.repository, self.previews)

    async def test_snapshot_uses_server_preview_and_frozen_comments(self) -> None:
        report = await self.use_case.get_report("week", None, False, "engineer")
        report["summary"][0]["unresolved"] = 999
        await self.use_case.save_comment(report["report_token"], "TACEA-3340", "원인 확인 중", "고객 안내", "검토 예정", True, "engineer")
        frozen = []
        self.repository.save_snapshot.side_effect = lambda payload, title, actor: frozen.append(deepcopy(payload))
        await self.use_case.save_snapshot(report["report_token"], None, "engineer")
        await self.use_case.save_comment(report["report_token"], "TACEA-3340", "이후 변경", "", "", False, "engineer")
        self.assertEqual(3, frozen[0]["summary"][0]["unresolved"])
        self.assertIsNone(frozen[0]["summary"][0]["resolution_rate"])
        self.assertEqual("원인 확인 중", frozen[0]["comments"]["TACEA-3340"]["delay_reason"])
        self.assertEqual("engineer", frozen[0]["comments"]["TACEA-3340"]["updated_by"])
        self.assertNotIn("report_token", frozen[0])

    async def test_token_cannot_be_used_by_another_actor(self) -> None:
        report = await self.use_case.get_report("week", None, False, "engineer")
        with self.assertRaises(CLevelPreviewExpiredError):
            await self.use_case.save_snapshot(report["report_token"], None, "other")
        self.repository.save_snapshot.assert_not_awaited()

    async def test_missing_issue_and_failed_write_do_not_change_preview(self) -> None:
        report = await self.use_case.get_report("week", None, False, "engineer")
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.save_comment(report["report_token"], "TACEA-999", "", "", "", True, "engineer")
        self.repository.save_comment.side_effect = RuntimeError("database unavailable")
        with self.assertRaises(RuntimeError):
            await self.use_case.save_comment(report["report_token"], "TACEA-3340", "unsaved", "", "", True, "engineer")
        self.assertEqual({}, self.previews.get(report["report_token"], "engineer")["comments"])

    async def test_saved_report_is_read_without_jira_or_current_comments(self) -> None:
        summary = CLevelSnapshotSummary(1, "주간 보고", "week", "2026-10-06", "2026-10-12", self.payload["as_of"], "engineer", "2026-10-13T01:00:00Z")
        payload = {**self.payload, "comments": {"TACEA-3340": {"delay_reason": "저장 당시 원인"}}}
        self.repository.get_snapshot.return_value = (summary, deepcopy(payload))
        result = await self.use_case.get_snapshot(1)
        self.assertIsNone(result["report_token"])
        self.assertEqual(payload["as_of"], result["as_of"])
        self.assertEqual("저장 당시 원인", result["comments"]["TACEA-3340"]["delay_reason"])
        self.reports.execute.assert_not_awaited()
        self.repository.get_comments.assert_not_awaited()

    async def test_committed_comment_remains_successful_when_preview_expires_during_write(self) -> None:
        report = await self.use_case.get_report("week", None, False, "engineer")

        async def save(value):
            await self.previews.aclose()
            return value

        self.repository.save_comment.side_effect = save
        result = await self.use_case.save_comment(report["report_token"], "TACEA-3340", "저장 완료", "", "", True, "engineer")
        self.assertEqual("저장 완료", result.delay_reason)
        with self.assertRaises(CLevelPreviewExpiredError):
            await self.use_case.save_snapshot(report["report_token"], None, "engineer")

    async def test_expired_and_evicted_previews_require_reload(self) -> None:
        cache = CLevelPreviewCache(maxsize=1)
        first = cache.put(self.payload, "a")
        second = cache.put(self.payload, "a")
        self.assertIsNone(cache.get(first, "a"))
        self.assertIsNotNone(cache.get(second, "a"))
        await cache.aclose()
        self.assertIsNone(cache.get(second, "a"))
        expired = CLevelPreviewCache(ttl_seconds=-1)
        self.assertIsNone(expired.get(expired.put(self.payload, "a"), "a"))
