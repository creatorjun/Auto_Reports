# backend/tests/test_jira_notification_client.py
import asyncio
import copy
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

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
