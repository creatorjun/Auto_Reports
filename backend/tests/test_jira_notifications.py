# backend/tests/test_jira_notifications.py
import asyncio
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI

from src.application.ports.jira_notification_port import JiraNotificationsReconnectRequired, JiraNotificationsUnavailable
from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.application.use_cases.jira_notifications import JiraNotificationsUseCase
from src.domain.entities.auth_identity import AuthIdentity
from src.domain.entities.jira_notification import JiraNotification, JiraNotificationPage
from src.infrastructure.security.memory_jira_user_grant_store import MemoryJiraUserGrantStore
from src.presentation.api.v1.jira_notifications import router


def notification_page() -> JiraNotificationPage:
    return JiraNotificationPage(items=(JiraNotification(
        id="notice-1", group_id="group-1", group_size=2, category="direct", is_read=False,
        created_at=datetime(2026, 10, 21, tzinfo=timezone.utc), title="TACEA-1 점검",
        message="새 댓글이 있습니다.", actor_name="담당자", url="https://example.atlassian.net/browse/TACEA-1",
    ),), next_cursor="next-page")


class JiraNotificationsUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.store = MemoryJiraUserGrantStore()
        self.identity = AuthIdentity("jira:cloud:user-one", "사용자", "jira")
        self.grant = JiraUserGrant("cloud", "user-one", "private-access-token", datetime.now(timezone.utc) + timedelta(hours=1))
        grant_id = await self.store.put(self.grant, self.identity)
        self.identity = replace(self.identity, jira_grant_id=grant_id)
        self.source = AsyncMock()
        self.source.fetch.return_value = notification_page()
        self.use_case = JiraNotificationsUseCase(self.source, self.store)

    async def asyncTearDown(self) -> None:
        await self.store.aclose()

    async def test_uses_only_the_authenticated_users_grant(self) -> None:
        result = await self.use_case.execute(self.identity, category="watching", cursor="cursor-one")
        self.assertEqual(notification_page(), result)
        self.source.fetch.assert_awaited_once_with(self.grant, category="watching", cursor="cursor-one")

    async def test_other_account_cannot_reuse_grant_or_fetch_data(self) -> None:
        intruder = replace(self.identity, username="jira:cloud:user-two")
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.execute(intruder)
        self.source.fetch.assert_not_awaited()
        self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_local_identity_and_missing_grant_never_contact_jira(self) -> None:
        with self.assertRaises(PermissionError):
            await self.use_case.execute(AuthIdentity("admin", "관리자"))
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.execute(replace(self.identity, jira_grant_id=None))
        self.source.fetch.assert_not_awaited()

    async def test_logout_during_request_drops_late_response(self) -> None:
        entered, proceed = asyncio.Event(), asyncio.Event()

        async def fetch(*args, **kwargs):
            entered.set()
            await proceed.wait()
            return notification_page()

        self.source.fetch.side_effect = fetch
        task = asyncio.create_task(self.use_case.execute(self.identity))
        await entered.wait()
        await self.store.revoke(self.identity.jira_grant_id, self.identity)
        proceed.set()
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await task

    async def test_privacy_cleanup_during_request_drops_late_response(self) -> None:
        async def fetch(*args, **kwargs):
            await self.store.clear()
            return notification_page()

        self.source.fetch.side_effect = fetch
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.execute(self.identity)

    async def test_upstream_auth_failure_invalidates_grant(self) -> None:
        self.source.fetch.side_effect = JiraNotificationsReconnectRequired()
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.execute(self.identity)
        self.assertIsNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_transient_failure_keeps_grant_and_cannot_serve_previous_data(self) -> None:
        await self.use_case.execute(self.identity)
        self.source.fetch.side_effect = JiraNotificationsUnavailable("private upstream detail")
        with self.assertRaises(JiraNotificationsUnavailable):
            await self.use_case.execute(self.identity)
        self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_read_uses_only_authenticated_grant_and_exact_notification_group(self) -> None:
        self.source.mark_read.return_value = None
        self.assertIsNone(await self.use_case.mark_read(self.identity, "notice-1", "group-1", "watching"))
        self.source.mark_read.assert_awaited_once_with(self.grant, "notice-1", "group-1", "watching")
        self.source.fetch.assert_not_awaited()

    async def test_read_cannot_use_another_account_or_sites_grant(self) -> None:
        for username in ("jira:cloud:user-two", "jira:other-cloud:user-one"):
            with self.subTest(username=username):
                with self.assertRaises(JiraNotificationsReconnectRequired):
                    await self.use_case.mark_read(replace(self.identity, username=username), "notice-1", "group-1", "direct")
        self.source.mark_read.assert_not_awaited()
        self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_read_local_missing_and_revoked_grants_never_contact_jira(self) -> None:
        with self.assertRaises(PermissionError):
            await self.use_case.mark_read(AuthIdentity("admin", "관리자"), "notice-1", "group-1", "direct")
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.mark_read(replace(self.identity, jira_grant_id=None), "notice-1", "group-1", "direct")
        await self.store.revoke(self.identity.jira_grant_id, self.identity)
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.mark_read(self.identity, "notice-1", "group-1", "direct")
        self.source.mark_read.assert_not_awaited()

    async def test_logout_during_read_never_returns_late_success(self) -> None:
        entered, proceed = asyncio.Event(), asyncio.Event()

        async def mark_read(*args):
            entered.set()
            await proceed.wait()

        self.source.mark_read.side_effect = mark_read
        task = asyncio.create_task(self.use_case.mark_read(self.identity, "notice-1", "group-1", "direct"))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            await self.store.revoke(self.identity.jira_grant_id, self.identity)
            proceed.set()
            with self.assertRaises(JiraNotificationsReconnectRequired):
                await task
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_privacy_cleanup_during_read_never_returns_success(self) -> None:
        async def mark_read(*args):
            await self.store.clear()

        self.source.mark_read.side_effect = mark_read
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.mark_read(self.identity, "notice-1", "group-1", "direct")

    async def test_queued_read_rechecks_grant_before_mutation(self) -> None:
        self.use_case._slots = asyncio.Semaphore(0)
        task = asyncio.create_task(self.use_case.mark_read(self.identity, "notice-1", "group-1", "direct"))
        try:
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            await self.store.revoke(self.identity.jira_grant_id, self.identity)
            self.use_case._slots.release()
            with self.assertRaises(JiraNotificationsReconnectRequired):
                await task
            self.source.mark_read.assert_not_awaited()
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_upstream_read_auth_failure_revokes_only_current_grant(self) -> None:
        self.source.mark_read.side_effect = JiraNotificationsReconnectRequired()
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.mark_read(self.identity, "notice-1", "group-1", "direct")
        self.assertIsNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_transient_read_failure_keeps_grant(self) -> None:
        self.source.mark_read.side_effect = JiraNotificationsUnavailable("private upstream detail")
        with self.assertRaises(JiraNotificationsUnavailable):
            await self.use_case.mark_read(self.identity, "notice-1", "group-1", "direct")
        self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_read_timeout_cancels_request_and_releases_capacity(self) -> None:
        cancelled = asyncio.Event()

        async def mark_read(*args):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.use_case._slots = asyncio.Semaphore(1)
        self.source.mark_read.side_effect = mark_read
        timeout = asyncio.timeout
        with patch("src.application.use_cases.jira_notifications.asyncio.timeout", side_effect=lambda _: timeout(0.01)):
            with self.assertRaises(JiraNotificationsUnavailable):
                await self.use_case.mark_read(self.identity, "notice-1", "group-1", "direct")
        self.assertTrue(cancelled.is_set())
        self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))
        self.source.mark_read.side_effect = None
        await asyncio.wait_for(self.use_case.mark_read(self.identity, "notice-2", "group-2", "direct"), 1)

    async def test_read_deadline_includes_wait_for_available_slot(self) -> None:
        self.use_case._slots = asyncio.Semaphore(0)
        timeout = asyncio.timeout
        with patch("src.application.use_cases.jira_notifications.asyncio.timeout", side_effect=lambda _: timeout(0.01)):
            with self.assertRaises(JiraNotificationsUnavailable):
                await self.use_case.mark_read(self.identity, "notice-1", "group-1", "direct")
        self.source.mark_read.assert_not_awaited()
        self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_fetch_and_read_share_eight_upstream_slots(self) -> None:
        entered, release = asyncio.Event(), asyncio.Event()
        active = peak = count = 0

        async def operation(*args, **kwargs):
            nonlocal active, peak, count
            active += 1
            count += 1
            peak = max(active, peak)
            if count == 8:
                entered.set()
            try:
                await release.wait()
                return notification_page()
            finally:
                active -= 1

        self.source.fetch.side_effect = operation
        self.source.mark_read.side_effect = operation
        tasks = [asyncio.create_task(self.use_case.execute(self.identity) if index % 2 else self.use_case.mark_read(self.identity, f"notice-{index}", "group-1", "direct")) for index in range(9)]
        try:
            await asyncio.wait_for(entered.wait(), 1)
            await asyncio.sleep(0)
            self.assertEqual(8, count)
            release.set()
            await asyncio.wait_for(asyncio.gather(*tasks), 1)
            self.assertEqual(9, count)
            self.assertEqual(8, peak)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def test_cancelled_read_propagates_and_releases_capacity(self) -> None:
        entered = asyncio.Event()

        async def mark_read(*args):
            entered.set()
            await asyncio.Event().wait()

        self.use_case._slots = asyncio.Semaphore(1)
        self.source.mark_read.side_effect = mark_read
        task = asyncio.create_task(self.use_case.mark_read(self.identity, "notice-1", "group-1", "direct"))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))
            self.source.mark_read.side_effect = None
            await asyncio.wait_for(self.use_case.mark_read(self.identity, "notice-2", "group-2", "direct"), 1)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


class JiraNotificationsApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.identity = AuthIdentity("jira:cloud:user-one", "사용자", "jira", jira_grant_id="opaque")
        self.auth = SimpleNamespace(enabled=True, resolve_access_identity=AsyncMock(return_value=self.identity))
        self.use_case = AsyncMock()
        self.use_case.execute.return_value = notification_page()
        app = FastAPI()
        app.state.services = SimpleNamespace(auth=self.auth, jira_notifications=self.use_case)
        app.include_router(router, prefix="/api/v1")
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://app.test")
        self.headers = {"Authorization": "Bearer app-session"}

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_authenticated_user_feed_is_not_cacheable_and_has_no_credentials(self) -> None:
        response = await self.client.get("/api/v1/jira/notifications?category=direct&cursor=cursor", headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.auth.resolve_access_identity.assert_awaited_once_with("app-session")
        self.use_case.execute.assert_awaited_once_with(self.identity, category="direct", cursor="cursor")
        payload = response.json()
        self.assertEqual("connected", payload["connection_status"])
        self.assertEqual("담당자", payload["items"][0]["actor"])
        self.assertFalse(payload["items"][0]["is_read"])
        self.assertEqual("group-1", payload["items"][0]["group_id"])
        for private in ("app-session", "opaque", "user-one", "access_token"):
            self.assertNotIn(private, response.text)

    async def test_local_guest_missing_and_expired_sessions_are_rejected(self) -> None:
        self.auth.resolve_access_identity.return_value = AuthIdentity("admin", "관리자")
        self.assertEqual(403, (await self.client.get("/api/v1/jira/notifications", headers=self.headers)).status_code)
        self.auth.enabled = False
        self.assertEqual(403, (await self.client.get("/api/v1/jira/notifications", headers=self.headers)).status_code)
        self.auth.enabled = True
        self.assertEqual(401, (await self.client.get("/api/v1/jira/notifications?token=app-session")).status_code)
        self.auth.resolve_access_identity.side_effect = ValueError("profile deleted")
        self.assertEqual(401, (await self.client.get("/api/v1/jira/notifications", headers=self.headers)).status_code)
        self.use_case.execute.assert_not_awaited()

    async def test_expired_jira_connection_does_not_end_valid_app_session(self) -> None:
        self.use_case.execute.side_effect = JiraNotificationsReconnectRequired()
        response = await self.client.get("/api/v1/jira/notifications", headers=self.headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual({"connection_status": "reconnect_required", "items": [], "next_cursor": None}, response.json())

    async def test_upstream_failure_is_not_a_fake_empty_feed_or_private_error(self) -> None:
        self.use_case.execute.side_effect = JiraNotificationsUnavailable("private GraphQL response")
        response = await self.client.get("/api/v1/jira/notifications", headers=self.headers)
        self.assertEqual(503, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertNotIn("private", response.text)
        self.assertNotIn("items", response.json())

    async def test_filter_and_cursor_are_bounded_before_upstream_requests(self) -> None:
        for suffix in ("?category=invalid", "?cursor=", "?cursor=%00", "?cursor=" + "a" * 4097):
            self.assertEqual(422, (await self.client.get("/api/v1/jira/notifications" + suffix, headers=self.headers)).status_code)
        self.use_case.execute.assert_not_awaited()

    async def test_read_success_uses_authenticated_identity_and_is_not_cacheable(self) -> None:
        body = {"notification_id": "notice-1", "group_id": "group-1", "category": "watching"}
        response = await self.client.post("/api/v1/jira/notifications/read", headers=self.headers, json=body)
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertEqual({"connection_status": "connected", "notification_id": "notice-1", "group_id": "group-1", "is_read": True}, response.json())
        self.auth.resolve_access_identity.assert_awaited_once_with("app-session")
        self.use_case.mark_read.assert_awaited_once_with(self.identity, "notice-1", "group-1", "watching")
        for private in ("app-session", "opaque", "user-one", "access_token"):
            self.assertNotIn(private, response.text)

    async def test_read_rejects_local_guest_missing_and_expired_sessions(self) -> None:
        body = {"notification_id": "notice-1", "group_id": "group-1", "category": "direct"}
        self.auth.resolve_access_identity.return_value = AuthIdentity("admin", "관리자")
        self.assertEqual(403, (await self.client.post("/api/v1/jira/notifications/read", headers=self.headers, json=body)).status_code)
        self.auth.enabled = False
        self.assertEqual(403, (await self.client.post("/api/v1/jira/notifications/read", headers=self.headers, json=body)).status_code)
        self.auth.enabled = True
        self.assertEqual(401, (await self.client.post("/api/v1/jira/notifications/read?token=app-session", json=body)).status_code)
        self.auth.resolve_access_identity.side_effect = ValueError("private profile deleted")
        response = await self.client.post("/api/v1/jira/notifications/read", headers=self.headers, json=body)
        self.assertEqual(401, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertNotIn("private", response.text)
        self.use_case.mark_read.assert_not_awaited()

    async def test_read_reconnect_is_not_reported_as_success(self) -> None:
        self.use_case.mark_read.side_effect = JiraNotificationsReconnectRequired()
        body = {"notification_id": "notice-1", "group_id": "group-1", "category": "direct"}
        response = await self.client.post("/api/v1/jira/notifications/read", headers=self.headers, json=body)
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertEqual({"connection_status": "reconnect_required", "notification_id": "notice-1", "group_id": "group-1", "is_read": False}, response.json())

    async def test_read_upstream_failure_does_not_leak_private_errors_or_report_success(self) -> None:
        self.use_case.mark_read.side_effect = JiraNotificationsUnavailable("private GraphQL response with access_token")
        body = {"notification_id": "notice-1", "group_id": "group-1", "category": "direct"}
        response = await self.client.post("/api/v1/jira/notifications/read", headers=self.headers, json=body)
        self.assertEqual(503, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertNotIn("private", response.text)
        self.assertNotIn("access_token", response.text)
        self.assertNotIn("is_read", response.json())

    async def test_read_identifiers_are_strict_bounded_and_cannot_inject_identity(self) -> None:
        valid = {"notification_id": "notice-1", "group_id": "group-1", "category": "direct"}
        invalid = [{key: value for key, value in valid.items() if key != missing} for missing in valid]
        invalid.extend({**valid, "category": value} for value in ("all", "unknown", None, 1))
        invalid.extend({**valid, field: value} for field in ("notification_id", "group_id") for value in ("", "a" * 2049, "a b", " a", "a ", "a\n", "a\t", "a\x00", "a\x7f", "a\x80", "a\u00a0", 1, True, None, []))
        invalid.extend({**valid, field: "injected"} for field in ("user_id", "grant_id", "account_id", "access_token"))
        for body in invalid:
            with self.subTest(body=body):
                self.assertEqual(422, (await self.client.post("/api/v1/jira/notifications/read", headers=self.headers, json=body)).status_code)
        self.use_case.mark_read.assert_not_awaited()
        for length in (1, 2048):
            body = {"notification_id": "n" * length, "group_id": "g" * length, "category": "direct"}
            self.assertEqual(200, (await self.client.post("/api/v1/jira/notifications/read", headers=self.headers, json=body)).status_code)
