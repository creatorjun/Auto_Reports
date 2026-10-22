# backend/tests/test_issue_management_details.py
import pathlib
import sys
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.errors import EntityNotFoundError
from src.application.ports.issue_management_snapshot_port import IssueManagementSnapshot, IssueManagementSnapshotPort
from src.application.ports.jira_port import JiraAttachmentContent, JiraComment, JiraCommentImage, JiraIssueDescription
from src.application.use_cases.issue_management import IssueManagementUseCase
from src.domain.constants import KST
from src.domain.entities.widget_data import RecentIssueDetail
from src.presentation.api.v1.router import router


def saved_snapshot(*keys):
    now = datetime.now(KST)
    return IssueManagementSnapshot(tuple(RecentIssueDetail(
        key=key, summary="저장된 이슈", type="인시던트", status="닫힘", stage_index=0,
        created="2026-01-01", elapsed_days=0,
    ) for key in keys), now, now)


class IssueManagementDetailsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira = AsyncMock()
        self.snapshots = AsyncMock(spec=IssueManagementSnapshotPort)
        self.snapshots.load.return_value = saved_snapshot("TACEA-1", "OTHER-1")
        self.use_case = IssueManagementUseCase(self.jira, snapshots=self.snapshots)
        self.jira.get_issue_description.return_value = JiraIssueDescription("본문", (JiraCommentImage("17", "그림"),))
        self.jira.get_attachment_content.return_value = JiraAttachmentContent(b"image", "image/png")
        self.comments = [JiraComment(str(number), "작성자", f"댓글 {number}", "2026-10-22T10:30:00+09:00", "2026-10-22T10:31:00+09:00", (JiraCommentImage("18", "댓글 그림"),)) for number in range(12, 0, -1)]
        self.jira.get_issue_comments.side_effect = lambda key, max_results, offset=0: self.comments[offset:offset + max_results]
        self.jira.get_issue_comment.return_value = self.comments[0]

    async def asyncTearDown(self):
        await self.use_case.aclose()

    async def test_restores_snapshot_and_reads_closed_issue_without_sync_or_report(self):
        body = await self.use_case.get_issue_description("tacea-1")
        self.assertEqual("본문", body.body)
        self.assertEqual("17", body.images[0].attachment_id)
        self.jira.get_issue_description.assert_awaited_once_with("TACEA-1")
        self.snapshots.load.assert_awaited_once_with("TACEA")
        self.jira.get_report_chart_issues.assert_not_awaited()
        self.assertIsNone(self.use_case._task)

    async def test_all_detail_reads_reject_unlisted_foreign_and_malformed_keys_before_jira(self):
        for key in ("TACEA-2", "OTHER-1", "TACEA-1/other", "TACEA-1 OR 1=1"):
            for read in (
                lambda: self.use_case.get_issue_description(key),
                lambda: self.use_case.get_description_image(key, "17"),
                lambda: self.use_case.list_recent_comments(key),
                lambda: self.use_case.get_comment_image(key, "12", "18"),
            ):
                with self.subTest(key=key), self.assertRaises(EntityNotFoundError):
                    await read()
        self.jira.get_issue_description.assert_not_awaited()
        self.jira.get_issue_comments.assert_not_awaited()
        self.jira.get_issue_comment.assert_not_awaited()
        self.jira.get_attachment_content.assert_not_awaited()

    async def test_missing_or_failed_snapshot_fails_closed_and_does_not_start_sync(self):
        self.snapshots.load.return_value = None
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.get_issue_description("TACEA-1")
        self.jira.get_issue_description.assert_not_awaited()
        self.jira.get_report_chart_issues.assert_not_awaited()
        self.use_case = IssueManagementUseCase(self.jira, snapshots=self.snapshots)
        self.snapshots.load.side_effect = RuntimeError("database unavailable")
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.list_recent_comments("TACEA-1")
        self.jira.get_issue_comments.assert_not_awaited()
        self.jira.get_report_chart_issues.assert_not_awaited()

    async def test_removed_snapshot_members_cannot_continue_loading_comments(self):
        await self.use_case.get_issue_description("TACEA-1")
        self.use_case._accept_snapshot(saved_snapshot())
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.list_recent_comments("TACEA-1")
        self.jira.get_issue_comments.assert_not_awaited()

    async def test_recent_five_and_cumulative_more_preserve_order_and_next_offset(self):
        for limit, expected_count, next_offset in ((5, 5, 5), (10, 10, 10), (15, 12, None)):
            with self.subTest(limit=limit):
                page = await self.use_case.list_recent_comments("tacea-1", limit=limit)
                self.assertEqual([comment.id for comment in self.comments[:limit]], [comment.id for comment in page.comments])
                self.assertEqual(expected_count, len(page.comments))
                self.assertEqual(next_offset, page.next_offset)
                self.assertEqual("2026-10-22 10:30", page.comments[0].created)
                self.assertEqual("18", page.comments[0].images[0].attachment_id)
                self.jira.get_issue_comments.assert_awaited_with("TACEA-1", max_results=limit + 1, offset=0)
        page = await self.use_case.list_recent_comments("TACEA-1", offset=10)
        self.assertEqual(["2", "1"], [comment.id for comment in page.comments])
        self.assertIsNone(page.next_offset)

    async def test_invalid_comment_pagination_does_not_restore_or_call_jira(self):
        for offset, limit in ((-1, 5), (0, 0), (0, -1)):
            with self.subTest(offset=offset, limit=limit), self.assertRaises(ValueError):
                await self.use_case.list_recent_comments("TACEA-1", offset, limit)
        self.snapshots.load.assert_not_awaited()
        self.jira.get_issue_comments.assert_not_awaited()

    async def test_description_image_requires_current_body_reference(self):
        image = await self.use_case.get_description_image("TACEA-1", "17")
        self.assertEqual(b"image", image.data)
        for attachment_id in ("18", "../17", "invalid"):
            with self.subTest(attachment_id=attachment_id), self.assertRaises(EntityNotFoundError):
                await self.use_case.get_description_image("TACEA-1", attachment_id)
        self.jira.get_issue_description.return_value = JiraIssueDescription("본문")
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.get_description_image("TACEA-1", "17")
        self.jira.get_attachment_content.assert_awaited_once_with("17")
        self.jira.get_issue_description.return_value = None
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.get_issue_description("TACEA-1")

    async def test_comment_image_requires_matching_comment_and_attachment(self):
        image = await self.use_case.get_comment_image("tacea-1", "12", "18")
        self.assertEqual("image/png", image.media_type)
        self.jira.get_issue_comment.assert_awaited_once_with("TACEA-1", "12")
        for comment_id, attachment_id in (("12", "17"), ("11", "18"), ("../12", "18")):
            with self.subTest(comment_id=comment_id, attachment_id=attachment_id), self.assertRaises(EntityNotFoundError):
                await self.use_case.get_comment_image("TACEA-1", comment_id, attachment_id)
        self.jira.get_issue_comment.return_value = None
        with self.assertRaises(EntityNotFoundError):
            await self.use_case.get_comment_image("TACEA-1", "12", "18")
        self.jira.get_attachment_content.assert_awaited_once_with("18")


class IssueManagementDetailsApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await IssueManagementDetailsTest.asyncSetUp(self)
        self.app = FastAPI()
        self.services = SimpleNamespace(auth=SimpleNamespace(enabled=False), issue_management=self.use_case)
        self.app.state.services = self.services
        self.app.include_router(router)

        @self.app.exception_handler(EntityNotFoundError)
        async def not_found(request, error):
            return JSONResponse(status_code=404, content={"detail": str(error)})

        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await IssueManagementDetailsTest.asyncTearDown(self)

    async def test_api_serializes_body_comments_and_private_images(self):
        body = await self.client.get("/api/v1/issue-management/issues/tacea-1/description")
        self.assertEqual(200, body.status_code)
        self.assertEqual({"body": "본문", "images": [{"attachment_id": "17", "alt": "그림"}]}, body.json())
        for limit in (5, 10, 15):
            response = await self.client.get("/api/v1/issue-management/issues/TACEA-1/comments", params={"offset": 0, "limit": limit})
            self.assertEqual(200, response.status_code)
            self.assertEqual(min(limit, 12), len(response.json()["comments"]))
        for suffix in ("description/images/17", "comments/12/images/18"):
            image = await self.client.get("/api/v1/issue-management/issues/TACEA-1/" + suffix)
            self.assertEqual(200, image.status_code)
            self.assertEqual(b"image", image.content)
            self.assertEqual("image/png", image.headers["content-type"])
            self.assertEqual("private, max-age=120", image.headers["cache-control"])

    async def test_api_requires_login_for_all_detail_endpoints(self):
        self.services.auth.enabled = True
        for suffix in ("description", "description/images/17", "comments", "comments/12/images/18"):
            response = await self.client.get("/api/v1/issue-management/issues/TACEA-1/" + suffix)
            self.assertEqual(401, response.status_code)
        self.snapshots.load.assert_not_awaited()
        self.jira.get_issue_description.assert_not_awaited()
        self.jira.get_issue_comments.assert_not_awaited()
        self.jira.get_issue_comment.assert_not_awaited()

    async def test_api_rejects_unlisted_keys_and_unrelated_images(self):
        for key, suffix in (("TACEA-2", "description"), ("OTHER-1", "comments"), ("TACEA-1", "description/images/18"), ("TACEA-1", "comments/12/images/17")):
            with self.subTest(key=key, suffix=suffix):
                response = await self.client.get(f"/api/v1/issue-management/issues/{key}/{suffix}")
                self.assertEqual(404, response.status_code)
        self.jira.get_attachment_content.assert_not_awaited()

    async def test_api_validates_pagination(self):
        for params in ({"offset": -1}, {"offset": "1.5"}, {"offset": "bad"}, {"limit": 0}, {"limit": -1}, {"limit": "1.5"}, {"limit": "bad"}):
            with self.subTest(params=params):
                response = await self.client.get("/api/v1/issue-management/issues/TACEA-1/comments", params=params)
                self.assertEqual(422, response.status_code)
        self.jira.get_issue_comments.assert_not_awaited()

    async def test_api_unavailable_returns_503(self):
        self.services.issue_management = None
        for suffix in ("description", "description/images/17", "comments", "comments/12/images/18"):
            response = await self.client.get("/api/v1/issue-management/issues/TACEA-1/" + suffix)
            self.assertEqual(503, response.status_code)

    async def test_api_hides_upstream_errors_and_never_reports_empty_success(self):
        self.jira.get_issue_description.side_effect = RuntimeError("private upstream body")
        self.jira.get_issue_comments.side_effect = RuntimeError("private upstream comments")
        self.jira.get_issue_comment.side_effect = RuntimeError("private upstream image")
        for suffix in ("description", "description/images/17", "comments", "comments/12/images/18"):
            response = await self.client.get("/api/v1/issue-management/issues/TACEA-1/" + suffix)
            self.assertEqual(502, response.status_code)
            self.assertNotIn("private", response.text)
