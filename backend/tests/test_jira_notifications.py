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
        self.source.fetch.assert_awaited_once_with(self.grant, category="watching", cursor="cursor-one", unread_only=False)

    async def test_unread_filter_is_forwarded_upstream_with_pagination(self) -> None:
        result = await self.use_case.execute(self.identity, category="direct", cursor="next", unread_only=True)
        self.assertEqual(notification_page(), result)
        self.source.fetch.assert_awaited_once_with(self.grant, category="direct", cursor="next", unread_only=True)

    async def test_read_all_uses_authenticated_grant_and_category_without_fetching_a_page(self) -> None:
        self.source.mark_all_read.return_value = None
        for category in (None, "direct", "watching"):
            with self.subTest(category=category):
                self.assertIsNone(await self.use_case.mark_all_read(self.identity, category=category))
                self.source.mark_all_read.assert_awaited_with(self.grant, category=category)
        self.assertEqual(3, self.source.mark_all_read.await_count)
        self.source.fetch.assert_not_awaited()
        self.source.mark_read.assert_not_awaited()

    async def test_read_all_rejects_other_accounts_sites_and_missing_grants(self) -> None:
        for identity in (replace(self.identity, username="jira:cloud:other"), replace(self.identity, username="jira:other:user-one"), replace(self.identity, jira_grant_id=None)):
            with self.assertRaises(JiraNotificationsReconnectRequired):
                await self.use_case.mark_all_read(identity)
        with self.assertRaises(PermissionError):
            await self.use_case.mark_all_read(AuthIdentity("admin", "관리자"))
        self.source.mark_all_read.assert_not_awaited()
        self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_read_all_rechecks_grant_before_and_after_mutation(self) -> None:
        self.use_case._slots = asyncio.Semaphore(0)
        task = asyncio.create_task(self.use_case.mark_all_read(self.identity))
        try:
            await asyncio.sleep(0)
            await self.store.revoke(self.identity.jira_grant_id, self.identity)
            self.use_case._slots.release()
            with self.assertRaises(JiraNotificationsReconnectRequired):
                await task
            self.source.mark_all_read.assert_not_awaited()
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        grant_id = await self.store.put(self.grant, self.identity)
        self.identity = replace(self.identity, jira_grant_id=grant_id)

        async def mark_all_read(*args, **kwargs):
            await self.store.clear()

        self.source.mark_all_read.side_effect = mark_all_read
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.mark_all_read(self.identity)

    async def test_read_all_transient_error_preserves_grant_but_auth_error_revokes_it(self) -> None:
        self.source.mark_all_read.side_effect = JiraNotificationsUnavailable("private upstream data")
        with self.assertRaises(JiraNotificationsUnavailable):
            await self.use_case.mark_all_read(self.identity)
        self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))
        self.source.mark_all_read.side_effect = JiraNotificationsReconnectRequired()
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self.use_case.mark_all_read(self.identity)
        self.assertIsNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_read_all_timeout_covers_queue_and_cancels_inflight_request(self) -> None:
        timeout = asyncio.timeout
        self.use_case._slots = asyncio.Semaphore(0)
        with patch("src.application.use_cases.jira_notifications.asyncio.timeout", side_effect=lambda _: timeout(0.01)):
            with self.assertRaises(JiraNotificationsUnavailable):
                await self.use_case.mark_all_read(self.identity)
        self.source.mark_all_read.assert_not_awaited()
        self.use_case._slots.release()
        cancelled = asyncio.Event()

        async def mark_all_read(*args, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.source.mark_all_read.side_effect = mark_all_read
        with patch("src.application.use_cases.jira_notifications.asyncio.timeout", side_effect=lambda _: timeout(0.01)):
            with self.assertRaises(JiraNotificationsUnavailable):
                await self.use_case.mark_all_read(self.identity)
        self.assertTrue(cancelled.is_set())
        self.source.mark_all_read.side_effect = None
        await asyncio.wait_for(self.use_case.mark_all_read(self.identity), 1)
        self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))

    async def test_cancelled_read_all_propagates_and_releases_capacity(self) -> None:
        entered = asyncio.Event()

        async def mark_all_read(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        self.use_case._slots = asyncio.Semaphore(1)
        self.source.mark_all_read.side_effect = mark_all_read
        task = asyncio.create_task(self.use_case.mark_all_read(self.identity))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.source.mark_all_read.side_effect = None
            await asyncio.wait_for(self.use_case.mark_all_read(self.identity), 1)
            self.assertIsNotNone(await self.store.get(self.identity.jira_grant_id, self.identity))
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

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

    async def test_fetch_read_and_read_all_share_eight_upstream_slots(self) -> None:
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
        self.source.mark_all_read.side_effect = operation
        tasks = []
        for index in range(9):
            if index % 3 == 0:
                pending = self.use_case.execute(self.identity)
            elif index % 3 == 1:
                pending = self.use_case.mark_read(self.identity, f"notice-{index}", "group-1", "direct")
            else:
                pending = self.use_case.mark_all_read(self.identity)
            tasks.append(asyncio.create_task(pending))
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
        self.use_case.execute.assert_awaited_once_with(self.identity, category="direct", cursor="cursor", unread_only=False)
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
        for suffix in ("?category=invalid", "?cursor=", "?cursor=%00", "?cursor=" + "a" * 4097, "?unread_only=invalid"):
            self.assertEqual(422, (await self.client.get("/api/v1/jira/notifications" + suffix, headers=self.headers)).status_code)
        self.use_case.execute.assert_not_awaited()

    async def test_unread_query_forwards_category_cursor_and_flag(self) -> None:
        for flag, expected in (("true", True), ("false", False)):
            with self.subTest(flag=flag):
                response = await self.client.get(f"/api/v1/jira/notifications?category=watching&cursor=next&unread_only={flag}", headers=self.headers)
                self.assertEqual(200, response.status_code)
                self.assertEqual("no-store", response.headers["cache-control"])
                self.assertEqual("next-page", response.json()["next_cursor"])
                self.use_case.execute.assert_awaited_with(self.identity, category="watching", cursor="next", unread_only=expected)

    async def test_read_all_success_uses_current_identity_and_selected_category(self) -> None:
        for category in ("all", "direct", "watching"):
            with self.subTest(category=category):
                response = await self.client.post("/api/v1/jira/notifications/read-all", headers=self.headers, json={"category": category})
                self.assertEqual(200, response.status_code)
                self.assertEqual("no-store", response.headers["cache-control"])
                self.assertEqual({"connection_status": "connected", "category": category, "is_read": True}, response.json())
                self.use_case.mark_all_read.assert_awaited_with(self.identity, category=None if category == "all" else category)
                for private in ("app-session", "opaque", "user-one", "access_token"):
                    self.assertNotIn(private, response.text)
        self.assertEqual(3, self.use_case.mark_all_read.await_count)
        self.use_case.execute.assert_not_awaited()
        self.use_case.mark_read.assert_not_awaited()

    async def test_read_all_rejects_local_guest_missing_and_expired_sessions(self) -> None:
        body = {"category": "all"}
        self.auth.resolve_access_identity.return_value = AuthIdentity("admin", "관리자")
        self.assertEqual(403, (await self.client.post("/api/v1/jira/notifications/read-all", headers=self.headers, json=body)).status_code)
        self.auth.enabled = False
        self.assertEqual(403, (await self.client.post("/api/v1/jira/notifications/read-all", headers=self.headers, json=body)).status_code)
        self.auth.enabled = True
        self.assertEqual(401, (await self.client.post("/api/v1/jira/notifications/read-all?token=app-session", json=body)).status_code)
        self.auth.resolve_access_identity.side_effect = ValueError("private profile deleted")
        response = await self.client.post("/api/v1/jira/notifications/read-all", headers=self.headers, json=body)
        self.assertEqual(401, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertNotIn("private", response.text)
        self.use_case.mark_all_read.assert_not_awaited()

    async def test_read_all_body_requires_category_and_forbids_scope_or_identity_injection(self) -> None:
        invalid = [{}, None, [], "all"]
        invalid.extend({"category": value} for value in (None, 1, True, [], "", "invalid", " all", "all\n"))
        invalid.extend({"category": "all", key: "injected"} for key in ("user_id", "account_id", "grant_id", "cloud_id", "access_token", "cursor", "unread_only"))
        for body in invalid:
            with self.subTest(body=body):
                self.assertEqual(422, (await self.client.post("/api/v1/jira/notifications/read-all", headers=self.headers, json=body)).status_code)
        self.use_case.mark_all_read.assert_not_awaited()

    async def test_read_all_reconnect_is_not_success_and_keeps_app_session(self) -> None:
        self.use_case.mark_all_read.side_effect = JiraNotificationsReconnectRequired()
        response = await self.client.post("/api/v1/jira/notifications/read-all", headers=self.headers, json={"category": "direct"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertEqual({"connection_status": "reconnect_required", "category": "direct", "is_read": False}, response.json())

    async def test_read_all_failure_is_safe_and_never_reports_success(self) -> None:
        self.use_case.mark_all_read.side_effect = JiraNotificationsUnavailable("private GraphQL access_token")
        response = await self.client.post("/api/v1/jira/notifications/read-all", headers=self.headers, json={"category": "all"})
        self.assertEqual(503, response.status_code)
        self.assertEqual("no-store", response.headers["cache-control"])
        self.assertNotIn("private", response.text)
        self.assertNotIn("access_token", response.text)
        self.assertNotIn("is_read", response.json())

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
