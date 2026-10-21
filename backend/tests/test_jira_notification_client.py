# backend/tests/test_jira_notification_client.py
import asyncio
import copy
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx

from src.application.ports.jira_notification_port import (
    JiraNotificationsReconnectRequired,
    JiraNotificationsUnavailable,
)
from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.infrastructure.external.jira_notification_client import JiraNotificationClient


def _grant(token: str = "user-token", account_id: str = "user-1") -> JiraUserGrant:
    return JiraUserGrant("cloud-1", account_id, token, datetime.now(timezone.utc) + timedelta(minutes=10))


def _node() -> dict:
    return {
        "groupId": "group-1",
        "groupSize": 2,
        "readStates": ["read", "unread"],
        "headNotification": {
            "notificationId": "notification-1",
            "category": "direct",
            "readState": "read",
            "timestamp": "2026-10-21T05:00:00Z",
            "workspaceId": "cloud-1",
            "entityModel": {"cloudId": "cloud-1"},
            "content": {
                "message": "<b>Alice</b> mentioned you &amp; Bob.<script>secret()</script>",
                "url": "https://company.atlassian.net/browse/TAC-1?focusedCommentId=123",
                "actor": {"displayName": "Alice"},
                "entity": {"title": "TAC-1 <b>Problem</b>", "url": "https://company.atlassian.net/browse/TAC-1"},
            },
        },
    }


def _response(nodes: list | None = None, has_next: bool = False, cursor: str | None = None) -> dict:
    return {
        "data": {
            "notifications": {
                "notificationFeed": {
                    "nodes": [_node()] if nodes is None else nodes,
                    "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                },
            },
        },
    }


def _group_response(read_state: str = "unread") -> dict:
    return {"data": {"notifications": {"notificationGroup": {"nodes": [{
        "notificationId": "notification-1", "category": "direct", "readState": read_state,
        "timestamp": "2026-10-21T05:00:00Z",
        "entityModel": {"cloudId": "cloud-1"},
    }]}}}}


def _read_response(value=None) -> dict:
    return {"data": {"notifications": {"markNotificationsByGroupIdAsRead": value}}}


def _all_read_response(value=None) -> dict:
    return {"data": {"notifications": {"markNotificationsAsRead": value}}}


def _empty_group_response() -> dict:
    return {"data": {"notifications": {"notificationGroup": {"nodes": []}}}}


class JiraNotificationClientTests(unittest.IsolatedAsyncioTestCase):
    def _client(self, handler) -> JiraNotificationClient:
        client = JiraNotificationClient("https://company.atlassian.net", transport=httpx.MockTransport(handler))
        self.addAsyncCleanup(client.aclose)
        return client

    async def test_reads_user_notifications_using_oauth_and_site_routing(self) -> None:
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=_response(has_next=True, cursor="next-page"))

        page = await self._client(handler).fetch(_grant(), "direct", "previous-page")
        request = requests[0]
        body = json.loads(request.content)
        self.assertEqual(str(request.url), "https://api.atlassian.com/graphql")
        self.assertEqual(request.headers["Authorization"], "Bearer user-token")
        self.assertEqual(body["operationName"], "JiraUserNotifications")
        self.assertNotIn("mutation", body["query"])
        self.assertEqual(body["variables"], {
            "first": 30,
            "after": "previous-page",
            "routing": "ari:cloud:platform::site/cloud-1",
            "filter": {"productFilter": "jira", "workspaceId": "cloud-1", "categoryFilter": "direct"},
        })
        self.assertEqual(page.next_cursor, "next-page")
        item = page.items[0]
        self.assertEqual(item.title, "TAC-1 Problem")
        self.assertEqual(item.message, "Alice mentioned you & Bob.")
        self.assertEqual(item.actor_name, "Alice")
        self.assertEqual(item.group_size, 2)
        self.assertFalse(item.is_read)
        self.assertEqual(item.created_at, datetime(2026, 10, 21, 5, tzinfo=timezone.utc))

    async def test_all_categories_omits_category_filter_and_does_not_cache_users(self) -> None:
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=_response(nodes=[]))

        client = self._client(handler)
        first = await client.fetch(_grant("token-one", "one"))
        second = await client.fetch(_grant("token-two", "two"))
        self.assertEqual(first.items, ())
        self.assertEqual(second.items, ())
        self.assertEqual([request.headers["Authorization"] for request in requests], ["Bearer token-one", "Bearer token-two"])
        self.assertNotIn("categoryFilter", json.loads(requests[0].content)["variables"]["filter"])
        self.assertNotIn("readStateFilter", json.loads(requests[0].content)["variables"]["filter"])

    async def test_unread_filter_is_preserved_when_loading_the_next_page(self) -> None:
        requests = []
        responses = iter([_response(has_next=True, cursor="next-unread"), _response(nodes=[])])

        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json=next(responses))

        client = self._client(handler)
        first = await client.fetch(_grant(), "direct", unread_only=True)
        second = await client.fetch(_grant(), "direct", first.next_cursor, unread_only=True)
        self.assertFalse(first.items[0].is_read)
        self.assertEqual((), second.items)
        self.assertEqual([None, "next-unread"], [body["variables"]["after"] for body in requests])
        self.assertTrue(all(body["variables"]["filter"] == {
            "productFilter": "jira", "workspaceId": "cloud-1", "categoryFilter": "direct", "readStateFilter": "unread",
        } for body in requests))

    async def test_invalid_unread_filters_do_not_contact_jira(self) -> None:
        calls = []
        client = self._client(lambda request: calls.append(request))
        for value in (None, "true", 0, 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                await client.fetch(_grant(), unread_only=value)
        self.assertEqual([], calls)

    async def test_watching_category_is_passed_and_preserved(self) -> None:
        node = _node()
        node["headNotification"]["category"] = "watching"
        client = self._client(lambda request: httpx.Response(200, json=_response([node])))
        page = await client.fetch(_grant(), "watching")
        self.assertEqual(page.items[0].category, "watching")

    async def test_group_unread_state_does_not_use_only_the_head(self) -> None:
        for group_states, head_state, expected in [
            (["read"], "read", True),
            (["READ"], "read", True),
            (["read", "unread"], "read", False),
            (["read"], "unread", False),
            ([None], "read", False),
            ([], "read", True),
        ]:
            with self.subTest(group_states=group_states, head_state=head_state):
                node = _node()
                node["readStates"] = group_states
                node["headNotification"]["readState"] = head_state
                client = self._client(lambda request: httpx.Response(200, json=_response([node])))
                self.assertEqual((await client.fetch(_grant())).items[0].is_read, expected)

    async def test_unsafe_notification_links_are_not_exposed(self) -> None:
        values = [
            "https://other.atlassian.net/browse/OTHER-1",
            "https://company.atlassian.net.evil.example/",
            "https://company.atlassian.net@evil.example/",
            "http://company.atlassian.net/browse/TAC-1",
            "javascript:alert(1)",
            "//evil.example/browse/TAC-1",
            "https://company.atlassian.net:8443/browse/TAC-1",
            "https://company.atlassian.net\\@evil.example/",
            "https://company.atlassian.net/\ninvalid",
            "https://company.atlassian.net:invalid/",
        ]
        for value in values:
            with self.subTest(value=value):
                node = _node()
                node["headNotification"]["content"]["url"] = value
                node["headNotification"]["content"]["entity"]["url"] = None
                client = self._client(lambda request: httpx.Response(200, json=_response([node])))
                self.assertIsNone((await client.fetch(_grant())).items[0].url)

    async def test_safe_relative_and_fallback_links(self) -> None:
        for value in ["/browse/TAC-1", "https://company.atlassian.net/browse/TAC-1"]:
            with self.subTest(value=value):
                node = _node()
                node["headNotification"]["content"]["url"] = value
                client = self._client(lambda request: httpx.Response(200, json=_response([node])))
                self.assertEqual((await client.fetch(_grant())).items[0].url, "https://company.atlassian.net/browse/TAC-1")

    async def test_http_auth_denial_requires_reconnection(self) -> None:
        for status in [401, 403]:
            with self.subTest(status=status):
                client = self._client(lambda request: httpx.Response(status, text="private provider error user-token"))
                with self.assertRaises(JiraNotificationsReconnectRequired) as raised:
                    await client.fetch(_grant())
                self.assertNotIn("user-token", str(raised.exception))

    async def test_graphql_auth_denial_requires_reconnection_even_with_partial_data(self) -> None:
        for status in [401, 403, "403"]:
            with self.subTest(status=status):
                payload = _response()
                payload["errors"] = [{"message": "sensitive", "extensions": {"statusCode": status}}]
                client = self._client(lambda request: httpx.Response(200, json=payload))
                with self.assertRaises(JiraNotificationsReconnectRequired):
                    await client.fetch(_grant())

    async def test_partial_graphql_data_never_becomes_a_successful_page(self) -> None:
        payload = _response()
        payload["errors"] = [{"message": "private provider error", "extensions": {"statusCode": 500}}]
        client = self._client(lambda request: httpx.Response(200, json=payload))
        with self.assertRaises(JiraNotificationsUnavailable) as raised:
            await client.fetch(_grant())
        self.assertNotIn("private", str(raised.exception))

    async def test_remote_failures_and_redirects_do_not_return_fake_empty_results(self) -> None:
        for status in [302, 400, 429, 500, 503]:
            with self.subTest(status=status):
                requests = []

                def handler(request):
                    requests.append(request)
                    return httpx.Response(status, headers={"Location": "https://evil.example"})

                with self.assertRaises(JiraNotificationsUnavailable):
                    await self._client(handler).fetch(_grant())
                self.assertEqual(len(requests), 1)

    async def test_network_timeout_is_unavailable(self) -> None:
        def handler(request):
            raise httpx.ReadTimeout("user-token", request=request)

        with self.assertRaises(JiraNotificationsUnavailable) as raised:
            await self._client(handler).fetch(_grant())
        self.assertNotIn("user-token", str(raised.exception))

    async def test_expired_and_invalid_grants_are_rejected_without_network_calls(self) -> None:
        calls = []
        client = self._client(lambda request: calls.append(request))
        grants = [
            replace(_grant(), expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)),
            replace(_grant(), expires_at=datetime(2026, 1, 1)),
            replace(_grant(), access_token=""),
            replace(_grant(), access_token="token\nother"),
            replace(_grant(), cloud_id="cloud/../../other"),
        ]
        for grant in grants:
            with self.subTest(grant=grant):
                with self.assertRaises(JiraNotificationsReconnectRequired):
                    await client.fetch(grant)
        self.assertEqual(calls, [])

    async def test_invalid_input_is_rejected_without_network_calls(self) -> None:
        calls = []
        client = self._client(lambda request: calls.append(request))
        for category, cursor in [("invalid", None), (None, ""), (None, "x" * 4097)]:
            with self.subTest(category=category, cursor_length=len(cursor or "")):
                with self.assertRaises(ValueError):
                    await client.fetch(_grant(), category, cursor)
        self.assertEqual(calls, [])

    async def test_malformed_response_is_unavailable(self) -> None:
        payloads = [None, [], {}, {"data": None}, {"data": {"notifications": None}}]
        for path, value in [
            (("nodes",), None),
            (("nodes",), [None]),
            (("nodes", 0, "headNotification"), None),
            (("nodes", 0, "headNotification", "content"), None),
            (("nodes", 0, "headNotification", "content", "actor"), None),
            (("nodes", 0, "headNotification", "timestamp"), "invalid"),
            (("nodes", 0, "headNotification", "timestamp"), "2026-10-21T05:00:00"),
            (("nodes", 0, "headNotification", "entityModel", "cloudId"), "other-cloud"),
            (("nodes", 0, "readStates"), None),
            (("nodes", 0, "groupSize"), 0),
            (("nodes", 0, "groupSize"), True),
            (("pageInfo", "hasNextPage"), 1),
        ]:
            payload = _response()
            target = payload["data"]["notifications"]["notificationFeed"]
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            payloads.append(payload)
        for payload in payloads:
            with self.subTest(payload=payload):
                client = self._client(lambda request: httpx.Response(200, json=payload))
                with self.assertRaises(JiraNotificationsUnavailable):
                    await client.fetch(_grant())

    async def test_pagination_repetition_and_missing_cursor_are_unavailable(self) -> None:
        for cursor in [None, "", "same-cursor", "x" * 4097]:
            with self.subTest(cursor=cursor):
                client = self._client(lambda request: httpx.Response(200, json=_response(has_next=True, cursor=cursor)))
                with self.assertRaises(JiraNotificationsUnavailable):
                    await client.fetch(_grant(), cursor="same-cursor")

    async def test_duplicate_groups_or_notifications_are_unavailable(self) -> None:
        for same_id in [True, False]:
            first, second = _node(), copy.deepcopy(_node())
            if same_id:
                second["groupId"] = "different-group"
            else:
                second["headNotification"]["notificationId"] = "different-id"
            client = self._client(lambda request: httpx.Response(200, json=_response([first, second])))
            with self.assertRaises(JiraNotificationsUnavailable):
                await client.fetch(_grant())

    async def test_mismatched_category_is_unavailable(self) -> None:
        client = self._client(lambda request: httpx.Response(200, json=_response()))
        with self.assertRaises(JiraNotificationsUnavailable):
            await client.fetch(_grant(), "watching")

    async def test_oversized_or_invalid_json_is_unavailable(self) -> None:
        for content in [b"x" * 2_000_001, b"not json"]:
            client = self._client(lambda request: httpx.Response(200, content=content))
            with self.assertRaises(JiraNotificationsUnavailable):
                await client.fetch(_grant())

    async def test_cancelled_request_remains_cancelled(self) -> None:
        async def handler(request):
            raise asyncio.CancelledError()

        with self.assertRaises(asyncio.CancelledError):
            await self._client(handler).fetch(_grant())

    async def test_shutdown_closes_client_and_rejects_new_requests(self) -> None:
        client = self._client(lambda request: httpx.Response(200, json=_response()))
        await client.aclose()
        await client.aclose()
        self.assertTrue(client._client.is_closed)
        with self.assertRaises(JiraNotificationsUnavailable):
            await client.fetch(_grant())

    def test_invalid_jira_origin_is_rejected(self) -> None:
        for url in ["http://company.atlassian.net", "https://user:password@company.atlassian.net", "https://company.atlassian.net/path"]:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    JiraNotificationClient(url)

    async def test_mark_read_verifies_membership_and_provider_readback_with_exact_cutoff(self) -> None:
        requests = []
        responses = [_group_response(), _read_response(), _group_response("read"), _empty_group_response()]

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=responses[len(requests) - 1])

        await self._client(handler).mark_read(_grant(), "notification-1", "group-1", "direct")
        bodies = [json.loads(request.content) for request in requests]
        self.assertEqual([body["operationName"] for body in bodies], [
            "JiraNotificationReadState", "MarkJiraNotificationRead", "JiraNotificationReadState", "JiraNotificationReadState",
        ])
        self.assertTrue(all(request.headers["Authorization"] == "Bearer user-token" for request in requests))
        self.assertEqual(bodies[0]["variables"], {
            "groupId": "group-1", "routing": "ari:cloud:platform::site/cloud-1",
            "filter": {"productFilter": "jira", "workspaceId": "cloud-1", "categoryFilter": "direct"},
        })
        self.assertEqual(bodies[1]["variables"], {
            "groupId": "group-1", "notificationId": "notification-1", "category": "direct",
            "routing": "ari:cloud:platform::site/cloud-1",
        })
        self.assertIn("beforeInclusive: $notificationId", bodies[1]["query"])
        self.assertNotIn("markNotificationsAsRead(", bodies[1]["query"])
        self.assertEqual(bodies[0], bodies[2])
        self.assertEqual(bodies[3]["variables"], {
            "groupId": "group-1", "routing": "ari:cloud:platform::site/cloud-1",
            "filter": {
                "productFilter": "jira", "workspaceId": "cloud-1", "categoryFilter": "direct",
                "readStateFilter": "unread", "beforeTimestamp": "2026-10-21T05:00:00.001+00:00",
            },
        })

    async def test_unverified_or_cross_site_group_does_not_mutate(self) -> None:
        variants = []
        for field, value in [
            ("notificationId", "other"), ("category", "watching"), ("readState", "bad"),
            ("entityModel", {"cloudId": "other-cloud"}),
            ("timestamp", None), ("timestamp", "invalid"), ("timestamp", "2026-10-21T05:00:00"),
        ]:
            payload = _group_response()
            payload["data"]["notifications"]["notificationGroup"]["nodes"][0][field] = value
            variants.append(payload)
        variants.extend([{}, {"data": {"notifications": {"notificationGroup": {"nodes": []}}}}])
        for payload in variants:
            calls = []

            def handler(request):
                calls.append(request)
                return httpx.Response(200, json=payload)

            with self.subTest(payload=payload):
                with self.assertRaises(JiraNotificationsUnavailable):
                    await self._client(handler).mark_read(_grant(), "notification-1", "group-1", "direct")
                self.assertEqual(len(calls), 1)

    async def test_mutation_acknowledgement_without_readback_is_not_success(self) -> None:
        for readback in [_group_response(), {}, {"errors": [{"message": "private"}]}]:
            responses = iter([_group_response(), _read_response("OK"), readback])
            client = self._client(lambda request: httpx.Response(200, json=next(responses)))
            with self.assertRaises(JiraNotificationsUnavailable):
                await client.mark_read(_grant(), "notification-1", "group-1", "direct")

    async def test_already_read_head_does_not_hide_older_unread_notifications_in_the_group(self) -> None:
        group = _group_response("read")
        older = copy.deepcopy(group["data"]["notifications"]["notificationGroup"]["nodes"][0])
        older.update(notificationId="older-notification", readState="unread", timestamp="2026-10-20T05:00:00Z")
        group["data"]["notifications"]["notificationGroup"]["nodes"].append(older)
        unread = _empty_group_response()
        unread["data"]["notifications"]["notificationGroup"]["nodes"] = [older]
        responses = iter([group, _read_response(), group, unread])
        client = self._client(lambda request: httpx.Response(200, json=next(responses)))
        with self.assertRaises(JiraNotificationsUnavailable):
            await client.mark_read(_grant(), "notification-1", "group-1", "direct")

    async def test_newer_unread_notification_does_not_change_the_selected_group_cutoff(self) -> None:
        calls = []
        selected = _group_response("read")
        newer = copy.deepcopy(selected["data"]["notifications"]["notificationGroup"]["nodes"][0])
        newer.update(notificationId="newer-notification", readState="unread", timestamp="2026-10-21T05:01:00Z")
        selected["data"]["notifications"]["notificationGroup"]["nodes"].insert(0, newer)

        def handler(request):
            body = json.loads(request.content)
            calls.append(body)
            if body["operationName"] == "MarkJiraNotificationRead":
                self.assertEqual("notification-1", body["variables"]["notificationId"])
                return httpx.Response(200, json=_read_response())
            filters = body["variables"]["filter"]
            if filters.get("readStateFilter") == "unread":
                cutoff = datetime.fromisoformat(filters["beforeTimestamp"])
                self.assertGreater(datetime.fromisoformat(newer["timestamp"]), cutoff)
                return httpx.Response(200, json=_empty_group_response())
            return httpx.Response(200, json=selected)

        await self._client(handler).mark_read(_grant(), "notification-1", "group-1", "direct")
        self.assertEqual(4, len(calls))

    async def test_unread_cutoff_uses_the_next_millisecond_and_normalizes_timezone(self) -> None:
        timestamp = "2026-10-21T14:00:00.123456+09:00"
        before, after = _group_response(), _group_response("read")
        for payload in (before, after):
            payload["data"]["notifications"]["notificationGroup"]["nodes"][0]["timestamp"] = timestamp
        responses = iter([before, _read_response(), after, _empty_group_response()])
        requests = []

        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json=next(responses))

        await self._client(handler).mark_read(_grant(), "notification-1", "group-1", "direct")
        cutoff = requests[-1]["variables"]["filter"]["beforeTimestamp"]
        self.assertEqual("2026-10-21T05:00:00.124+00:00", cutoff)
        self.assertGreater(datetime.fromisoformat(cutoff), datetime.fromisoformat(timestamp))

    async def test_missing_malformed_or_failed_unread_check_never_reports_success(self) -> None:
        payloads = [{}, {"errors": [{"message": "private provider response"}]}]
        for nodes in (None, {}, [None], [_group_response()] * 31):
            payload = _empty_group_response()
            payload["data"]["notifications"]["notificationGroup"]["nodes"] = nodes
            payloads.append(payload)
        for unread in payloads:
            with self.subTest(unread=unread):
                responses = iter([_group_response(), _read_response(), _group_response("read"), unread])
                client = self._client(lambda request: httpx.Response(200, json=next(responses)))
                with self.assertRaises(JiraNotificationsUnavailable) as raised:
                    await client.mark_read(_grant(), "notification-1", "group-1", "direct")
                self.assertNotIn("private", str(raised.exception))

    async def test_auth_denial_on_final_unread_check_still_requires_reconnection(self) -> None:
        responses = iter([
            httpx.Response(200, json=_group_response()), httpx.Response(200, json=_read_response()),
            httpx.Response(200, json=_group_response("read")), httpx.Response(403),
        ])
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self._client(lambda request: next(responses)).mark_read(_grant(), "notification-1", "group-1", "direct")

    async def test_total_deadline_includes_final_unread_verification(self) -> None:
        responses = iter([_group_response(), _read_response(), _group_response("read")])
        calls = []
        cancelled = asyncio.Event()

        async def handler(request):
            calls.append(request)
            if len(calls) < 4:
                return httpx.Response(200, json=next(responses))
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        original_timeout = asyncio.timeout
        client = self._client(handler)
        with patch("src.infrastructure.external.jira_notification_client.asyncio.timeout", side_effect=lambda seconds: original_timeout(0.03)) as timeout:
            with self.assertRaises(JiraNotificationsUnavailable):
                await client.mark_read(_grant(), "notification-1", "group-1", "direct")
            timeout.assert_called_once_with(20)
        self.assertEqual(4, len(calls))
        self.assertTrue(cancelled.is_set())

    async def test_mutation_errors_and_malformed_acknowledgement_do_not_report_success(self) -> None:
        for payload in [{}, _read_response(True), {"errors": [{"message": "private"}], **_read_response("OK")}]:
            responses = iter([_group_response(), payload])
            client = self._client(lambda request: httpx.Response(200, json=next(responses)))
            with self.assertRaises(JiraNotificationsUnavailable) as raised:
                await client.mark_read(_grant(), "notification-1", "group-1", "direct")
            self.assertNotIn("private", str(raised.exception))

    async def test_auth_failure_on_mutation_requires_reconnection(self) -> None:
        responses = iter([
            httpx.Response(200, json=_group_response()),
            httpx.Response(200, json={"errors": [{"extensions": {"statusCode": 403}}]}),
        ])
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await self._client(lambda request: next(responses)).mark_read(_grant(), "notification-1", "group-1", "direct")

    async def test_read_validation_and_expired_grants_prevent_network_calls(self) -> None:
        calls = []
        client = self._client(lambda request: calls.append(request))
        for target in [("", "group-1", "direct"), ("id", "g\n", "direct"), ("id", "g", "all"), ("x" * 2049, "g", "direct")]:
            with self.assertRaises(ValueError):
                await client.mark_read(_grant(), *target)
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await client.mark_read(replace(_grant(), expires_at=datetime.now(timezone.utc)), "id", "g", "direct")
        self.assertEqual(calls, [])

    async def test_cancellation_before_mutation_prevents_write(self) -> None:
        async def handler(request):
            raise asyncio.CancelledError()

        with self.assertRaises(asyncio.CancelledError):
            await self._client(handler).mark_read(_grant(), "notification-1", "group-1", "direct")

    async def test_bulk_read_scopes_mutation_and_readback_to_current_site_and_category(self) -> None:
        for category in (None, "direct", "watching"):
            with self.subTest(category=category):
                requests = []
                responses = iter([_all_read_response(), _response(nodes=[])])

                def handler(request):
                    requests.append(request)
                    return httpx.Response(200, json=next(responses))

                started = datetime.now(timezone.utc)
                await self._client(handler).mark_all_read(_grant(), category)
                finished = datetime.now(timezone.utc)
                bodies = [json.loads(request.content) for request in requests]
                self.assertEqual(["MarkAllJiraNotificationsRead", "JiraUserNotifications"], [body["operationName"] for body in bodies])
                self.assertEqual({
                    "category": category, "product": "jira", "workspaceId": "cloud-1",
                    "routing": "ari:cloud:platform::site/cloud-1",
                }, bodies[0]["variables"])
                self.assertIn("markNotificationsAsRead(", bodies[0]["query"])
                self.assertNotIn("markNotificationsByIdsAsRead", bodies[0]["query"])
                self.assertTrue(all(request.headers["Authorization"] == "Bearer user-token" for request in requests))
                self.assertEqual(30, bodies[1]["variables"]["first"])
                self.assertIsNone(bodies[1]["variables"]["after"])
                filters = bodies[1]["variables"]["filter"]
                self.assertEqual("jira", filters["productFilter"])
                self.assertEqual("cloud-1", filters["workspaceId"])
                self.assertEqual("unread", filters["readStateFilter"])
                self.assertEqual(category, filters.get("categoryFilter"))
                self.assertRegex(filters["beforeTimestamp"], r"\.\d{3}\+00:00$")
                cutoff = datetime.fromisoformat(filters["beforeTimestamp"])
                self.assertGreater(cutoff, started)
                self.assertLessEqual(cutoff, finished + timedelta(milliseconds=1))

    async def test_bulk_read_accepts_nullable_string_only_after_empty_readback(self) -> None:
        for value in (None, "", "OK", "provider-request-id"):
            with self.subTest(acknowledgement=value):
                responses = iter([_all_read_response(value), _response(nodes=[])])
                client = self._client(lambda request: httpx.Response(200, json=next(responses)))
                await client.mark_all_read(_grant())

    async def test_bulk_read_rejects_remaining_unread_and_incomplete_empty_page(self) -> None:
        other_site, other_category = _node(), _node()
        other_site["headNotification"]["entityModel"]["cloudId"] = "other-cloud"
        other_category["headNotification"]["category"] = "watching"
        for readback in (
            _response(), _response(nodes=[], has_next=True, cursor="remaining-page"),
            _response([other_site]), _response([other_category]), {},
            {"errors": [{"message": "private failure"}], **_response(nodes=[])},
        ):
            with self.subTest(readback=readback):
                responses = iter([_all_read_response("OK"), readback])
                client = self._client(lambda request: httpx.Response(200, json=next(responses)))
                with self.assertRaises(JiraNotificationsUnavailable) as raised:
                    await client.mark_all_read(_grant(), "direct")
                self.assertNotIn("private", str(raised.exception))

    async def test_bulk_read_does_not_trust_acknowledgement_or_provider_errors(self) -> None:
        for payload in ({}, _all_read_response(True), {"errors": [{"message": "private failure"}], **_all_read_response("OK")}):
            requests = []

            def handler(request):
                requests.append(request)
                return httpx.Response(200, json=payload)

            with self.subTest(payload=payload), self.assertRaises(JiraNotificationsUnavailable):
                await self._client(handler).mark_all_read(_grant())
            self.assertEqual(1, len(requests))

    async def test_bulk_read_preserves_new_notifications_for_the_next_feed_fetch(self) -> None:
        started = datetime.now(timezone.utc)
        new_node = _node()
        new_node["headNotification"]["timestamp"] = (started + timedelta(seconds=1)).isoformat()
        new_node["headNotification"]["readState"] = "unread"
        requests = []

        def handler(request):
            body = json.loads(request.content)
            requests.append(body)
            if body["operationName"] == "MarkAllJiraNotificationsRead":
                return httpx.Response(200, json=_all_read_response())
            cutoff = body["variables"]["filter"].get("beforeTimestamp")
            if cutoff is not None:
                self.assertLess(datetime.fromisoformat(cutoff), datetime.fromisoformat(new_node["headNotification"]["timestamp"]))
                return httpx.Response(200, json=_response(nodes=[]))
            return httpx.Response(200, json=_response([new_node]))

        client = self._client(handler)
        with patch("src.infrastructure.external.jira_notification_client.datetime", wraps=datetime) as clock:
            clock.now.return_value = started
            await client.mark_all_read(_grant())
        fresh = await client.fetch(_grant(), unread_only=True)
        self.assertEqual(1, len(fresh.items))
        self.assertFalse(fresh.items[0].is_read)
        self.assertNotIn("beforeTimestamp", requests[-1]["variables"]["filter"])

    async def test_bulk_read_auth_denial_on_either_request_requires_reconnection(self) -> None:
        for denied_stage in (0, 1):
            responses = [httpx.Response(200, json=_all_read_response())] * denied_stage
            responses.append(httpx.Response(200, json={"errors": [{"extensions": {"statusCode": 403}}]}))
            pending = iter(responses)
            with self.subTest(stage=denied_stage), self.assertRaises(JiraNotificationsReconnectRequired):
                await self._client(lambda request: next(pending)).mark_all_read(_grant())

    async def test_bulk_read_invalid_category_or_expired_grant_never_contacts_jira(self) -> None:
        requests = []
        client = self._client(lambda request: requests.append(request))
        with self.assertRaises(ValueError):
            await client.mark_all_read(_grant(), "all")
        with self.assertRaises(JiraNotificationsReconnectRequired):
            await client.mark_all_read(replace(_grant(), expires_at=datetime.now(timezone.utc)))
        self.assertEqual([], requests)

    async def test_bulk_read_deadline_includes_verification_and_cancellation_propagates(self) -> None:
        requests = []
        cancelled = asyncio.Event()

        async def handler(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(200, json=_all_read_response())
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        original_timeout = asyncio.timeout
        client = self._client(handler)
        with patch("src.infrastructure.external.jira_notification_client.asyncio.timeout", side_effect=lambda seconds: original_timeout(0.03)) as timeout:
            with self.assertRaises(JiraNotificationsUnavailable):
                await client.mark_all_read(_grant())
            timeout.assert_called_once_with(20)
        self.assertEqual(2, len(requests))
        self.assertTrue(cancelled.is_set())

        async def abort(request):
            raise asyncio.CancelledError()

        with self.assertRaises(asyncio.CancelledError):
            await self._client(abort).mark_all_read(_grant())
