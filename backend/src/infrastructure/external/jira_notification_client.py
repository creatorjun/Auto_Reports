# backend/src/infrastructure/external/jira_notification_client.py
import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urljoin, urlsplit

import httpx

from src.application.ports.jira_notification_port import (
    JiraNotificationSourcePort,
    JiraNotificationsReconnectRequired,
    JiraNotificationsUnavailable,
)
from src.application.ports.jira_user_grant_port import JiraUserGrant
from src.domain.entities.jira_notification import JiraNotification, JiraNotificationPage

_QUERY = """
query JiraUserNotifications($filter: InfluentsNotificationFilter, $first: Int, $after: String, $routing: String) {
  notifications {
    notificationFeed(filter: $filter, first: $first, after: $after, collabContextRoutingAri: $routing) {
      nodes {
        groupId
        groupSize
        readStates
        headNotification {
          notificationId
          category
          readState
          timestamp
          workspaceId
          entityModel { cloudId }
          content {
            message
            url
            actor { displayName }
            entity { title url }
          }
        }
      }
      pageInfo { endCursor hasNextPage }
    }
  }
}
"""
_UNAVAILABLE = "Jira notifications are temporarily unavailable"
_RECONNECT = "Jira login must be renewed to view notifications"
_GROUP_QUERY = """
query JiraNotificationReadState($groupId: String!, $filter: InfluentsNotificationFilter, $routing: String) {
  notifications {
    notificationGroup(groupId: $groupId, filter: $filter, first: 30, collabContextRoutingAri: $routing) {
      nodes { notificationId category readState timestamp entityModel { cloudId } }
    }
  }
}
"""
_MARK_READ = """
mutation MarkJiraNotificationRead($groupId: String!, $notificationId: String!, $category: InfluentsNotificationCategory!, $routing: String) {
  notifications {
    markNotificationsByGroupIdAsRead(groupId: $groupId, beforeInclusive: $notificationId, category: $category, collabContextRoutingAri: $routing)
  }
}
"""
_MARK_ALL_READ = """
mutation MarkAllJiraNotificationsRead($category: InfluentsNotificationCategory, $product: String, $workspaceId: String, $routing: String) {
  notifications {
    markNotificationsAsRead(category: $category, product: $product, workspaceId: $workspaceId, collabContextRoutingAri: $routing)
  }
}
"""


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._suppressed: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "template"}:
            self._suppressed.append(tag)
        elif tag in {"br", "p", "div", "li"} and not self._suppressed:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self._suppressed:
            if tag == self._suppressed[-1]:
                self._suppressed.pop()
        elif tag in {"p", "div", "li"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._suppressed:
            self.parts.append(data)


class JiraNotificationClient(JiraNotificationSourcePort):
    def __init__(
        self,
        jira_base_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        site = urlsplit(jira_base_url)
        if (
            site.scheme != "https" or not site.hostname or site.username or site.password
            or site.path.rstrip("/") or site.query or site.fragment
        ):
            raise ValueError("Invalid Jira notification site")
        self._site_url = jira_base_url.rstrip("/")
        self._origin = (site.scheme, site.hostname, site.port or 443)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(15, connect=5),
            follow_redirects=False,
            transport=transport,
        )
        self._closed = False

    async def fetch(
        self,
        grant: JiraUserGrant,
        category: Literal["direct", "watching"] | None = None,
        cursor: str | None = None,
        unread_only: bool = False,
    ) -> JiraNotificationPage:
        if category not in {None, "direct", "watching"}:
            raise ValueError("Invalid notification category")
        if cursor is not None and (not isinstance(cursor, str) or not cursor or len(cursor) > 4096):
            raise ValueError("Invalid notification cursor")
        if not isinstance(unread_only, bool):
            raise ValueError("Invalid notification read filter")
        filters = {"productFilter": "jira", "workspaceId": grant.cloud_id}
        if category is not None:
            filters["categoryFilter"] = category
        if unread_only:
            filters["readStateFilter"] = "unread"
        try:
            async with asyncio.timeout(20):
                data = await self._request(grant, _QUERY, "JiraUserNotifications", {
                    "filter": filters, "first": 30, "after": cursor,
                    "routing": f"ari:cloud:platform::site/{grant.cloud_id}",
                })
            return self._page(data, grant.cloud_id, category, cursor)
        except (httpx.HTTPError, TimeoutError):
            raise JiraNotificationsUnavailable(_UNAVAILABLE) from None
        except (KeyError, TypeError, ValueError, OverflowError):
            raise JiraNotificationsUnavailable(_UNAVAILABLE) from None

    async def mark_all_read(
        self, grant: JiraUserGrant, category: Literal["direct", "watching"] | None = None,
    ) -> None:
        if category not in {None, "direct", "watching"}:
            raise ValueError("Invalid notification category")
        routing = f"ari:cloud:platform::site/{grant.cloud_id}"
        cutoff = (datetime.now(timezone.utc) + timedelta(milliseconds=1)).isoformat(timespec="milliseconds")
        filters = {
            "productFilter": "jira", "workspaceId": grant.cloud_id,
            "readStateFilter": "unread", "beforeTimestamp": cutoff,
        }
        if category is not None:
            filters["categoryFilter"] = category
        try:
            async with asyncio.timeout(20):
                result = await self._request(grant, _MARK_ALL_READ, "MarkAllJiraNotificationsRead", {
                    "category": category, "product": "jira", "workspaceId": grant.cloud_id, "routing": routing,
                })
                acknowledged = result["data"]["notifications"]["markNotificationsAsRead"]
                if acknowledged is not None and not isinstance(acknowledged, str):
                    raise ValueError("Invalid notification mutation response")
                unread = await self._request(grant, _QUERY, "JiraUserNotifications", {
                    "filter": filters, "first": 30, "after": None, "routing": routing,
                })
                page = self._page(unread, grant.cloud_id, category, None)
                if page.items or page.next_cursor is not None:
                    raise JiraNotificationsUnavailable(_UNAVAILABLE)
        except (httpx.HTTPError, TimeoutError, KeyError, TypeError, ValueError, OverflowError):
            raise JiraNotificationsUnavailable(_UNAVAILABLE) from None

    async def mark_read(
        self, grant: JiraUserGrant, notification_id: str, group_id: str,
        category: Literal["direct", "watching"],
    ) -> None:
        if category not in {"direct", "watching"} or any(
            not isinstance(value, str) or not value or len(value) > 2048
            or re.search(r"[\s\x00-\x1f\x7f]", value)
            for value in (notification_id, group_id)
        ):
            raise ValueError("Invalid notification read target")
        routing = f"ari:cloud:platform::site/{grant.cloud_id}"
        variables = {
            "groupId": group_id, "routing": routing,
            "filter": {"productFilter": "jira", "workspaceId": grant.cloud_id, "categoryFilter": category},
        }
        try:
            async with asyncio.timeout(20):
                before = await self._request(grant, _GROUP_QUERY, "JiraNotificationReadState", variables)
                _, selected_timestamp = self._group_read_state(before, grant.cloud_id, notification_id, category)
                unread_cutoff = (selected_timestamp + timedelta(milliseconds=1)).astimezone(timezone.utc).isoformat(timespec="milliseconds")
                result = await self._request(grant, _MARK_READ, "MarkJiraNotificationRead", {
                    "groupId": group_id, "notificationId": notification_id,
                    "category": category, "routing": routing,
                })
                acknowledged = result["data"]["notifications"]["markNotificationsByGroupIdAsRead"]
                if acknowledged is not None and not isinstance(acknowledged, str):
                    raise ValueError("Invalid notification mutation response")
                after = await self._request(grant, _GROUP_QUERY, "JiraNotificationReadState", variables)
                is_read, _ = self._group_read_state(after, grant.cloud_id, notification_id, category)
                if not is_read:
                    raise JiraNotificationsUnavailable(_UNAVAILABLE)
                unread = await self._request(grant, _GROUP_QUERY, "JiraNotificationReadState", {
                    **variables,
                    "filter": {
                        **variables["filter"], "readStateFilter": "unread",
                        "beforeTimestamp": unread_cutoff,
                    },
                })
                if self._group_nodes(unread):
                    raise JiraNotificationsUnavailable(_UNAVAILABLE)
        except (httpx.HTTPError, TimeoutError, KeyError, TypeError, ValueError, OverflowError):
            raise JiraNotificationsUnavailable(_UNAVAILABLE) from None

    def _group_read_state(
        self, data: dict, cloud_id: str, notification_id: str, category: str,
    ) -> tuple[bool, datetime]:
        nodes = self._group_nodes(data)
        found = None
        seen = set()
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("Invalid notification group item")
            item_id = self._string(node["notificationId"], 2048)
            model = node.get("entityModel")
            if (
                item_id in seen or node["category"] != category or node["readState"] not in {"read", "unread"}
                or model is not None and (not isinstance(model, dict) or model.get("cloudId") not in {None, cloud_id})
            ):
                raise ValueError("Invalid notification group state")
            seen.add(item_id)
            if item_id == notification_id:
                timestamp = datetime.fromisoformat(self._string(node["timestamp"], 64).replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    raise ValueError("Invalid notification timestamp")
                found = (node["readState"] == "read", timestamp)
        if found is None:
            raise JiraNotificationsUnavailable(_UNAVAILABLE)
        return found

    @staticmethod
    def _group_nodes(data: dict) -> list:
        nodes = data["data"]["notifications"]["notificationGroup"]["nodes"]
        if not isinstance(nodes, list) or len(nodes) > 30:
            raise ValueError("Invalid notification group response")
        return nodes

    async def _request(self, grant: JiraUserGrant, query: str, operation: str, variables: dict) -> dict:
        if (
            grant.expires_at.tzinfo is None
            or grant.expires_at <= datetime.now(timezone.utc)
            or not grant.access_token or len(grant.access_token) > 32768
            or re.search(r"[\x00-\x20\x7f]", grant.access_token)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", grant.cloud_id)
        ):
            raise JiraNotificationsReconnectRequired(_RECONNECT)
        if self._closed:
            raise JiraNotificationsUnavailable(_UNAVAILABLE)
        async with self._client.stream(
            "POST", "https://api.atlassian.com/graphql",
            headers={"Authorization": f"Bearer {grant.access_token}", "Accept": "application/json"},
            json={"query": query, "operationName": operation, "variables": variables},
        ) as response:
            if response.status_code in {401, 403}:
                raise JiraNotificationsReconnectRequired(_RECONNECT)
            if response.status_code != 200:
                raise JiraNotificationsUnavailable(_UNAVAILABLE)
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > 2_000_000:
                    raise JiraNotificationsUnavailable(_UNAVAILABLE)
            data = json.loads(content)
        self._check_errors(data)
        return data

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            await self._client.aclose()

    def _page(
        self,
        data: object,
        cloud_id: str,
        category: Literal["direct", "watching"] | None,
        previous_cursor: str | None,
    ) -> JiraNotificationPage:
        feed = data["data"]["notifications"]["notificationFeed"]
        nodes = feed["nodes"]
        info = feed["pageInfo"]
        if not isinstance(nodes, list) or len(nodes) > 30 or not isinstance(info, dict):
            raise ValueError("Invalid notification page")
        if not isinstance(info.get("hasNextPage"), bool):
            raise ValueError("Invalid notification pagination")
        next_cursor = None
        if info["hasNextPage"]:
            next_cursor = self._string(info["endCursor"], 4096)
            if next_cursor == previous_cursor:
                raise ValueError("Invalid notification pagination")
        items = tuple(self._item(node, cloud_id, category) for node in nodes)
        if len({item.id for item in items}) != len(items) or len({item.group_id for item in items}) != len(items):
            raise ValueError("Duplicate notification groups")
        return JiraNotificationPage(items=items, next_cursor=next_cursor)

    @staticmethod
    def _check_errors(data: object) -> None:
        if not isinstance(data, dict):
            raise ValueError("Invalid notification response")
        errors = data.get("errors")
        if errors:
            if isinstance(errors, list) and any(
                isinstance(error, dict)
                and isinstance(error.get("extensions"), dict)
                and str(error["extensions"].get("statusCode")) in {"401", "403"}
                for error in errors
            ):
                raise JiraNotificationsReconnectRequired(_RECONNECT)
            raise JiraNotificationsUnavailable(_UNAVAILABLE)

    def _item(
        self,
        node: object,
        cloud_id: str,
        requested_category: Literal["direct", "watching"] | None,
    ) -> JiraNotification:
        if not isinstance(node, dict):
            raise ValueError("Invalid notification item")
        head = node["headNotification"]
        if not isinstance(head, dict):
            raise ValueError("Invalid notification head")
        content = head["content"]
        if not isinstance(content, dict):
            raise ValueError("Invalid notification content")
        entity = content.get("entity")
        actor = content["actor"]
        model = head.get("entityModel")
        if not isinstance(actor, dict):
            raise ValueError("Invalid notification content")
        if entity is not None and not isinstance(entity, dict):
            raise ValueError("Invalid notification entity")
        if model is not None and (not isinstance(model, dict) or model.get("cloudId") not in {None, cloud_id}):
            raise ValueError("Notification belongs to a different Jira site")
        category = head["category"]
        read_state = head["readState"]
        read_states = node["readStates"]
        if isinstance(read_states, list):
            read_states = [state.lower() if isinstance(state, str) else state for state in read_states]
        if (
            category not in {"direct", "watching"}
            or requested_category is not None and category != requested_category
            or read_state not in {"read", "unread"}
            or not isinstance(read_states, list)
            or any(state not in {None, "read", "unread"} for state in read_states)
        ):
            raise ValueError("Invalid notification state")
        group_size = node["groupSize"]
        if isinstance(group_size, bool) or not isinstance(group_size, int) or group_size < 1:
            raise ValueError("Invalid notification group")
        timestamp = datetime.fromisoformat(self._string(head["timestamp"], 64).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("Invalid notification timestamp")
        message = self._plain(self._string(content["message"], 20000, empty=True), 2000)
        title = self._optional_plain(entity.get("title") if entity else None, 500) or message or "Jira 알림"
        return JiraNotification(
            id=self._string(head["notificationId"], 2048),
            group_id=self._string(node["groupId"], 2048),
            group_size=group_size,
            category=category,
            is_read=read_state == "read" and all(state == "read" for state in read_states),
            created_at=timestamp,
            title=title,
            message=message,
            actor_name=self._optional_plain(actor.get("displayName"), 200),
            url=self._safe_url(content.get("url")) or self._safe_url(entity.get("url") if entity else None),
        )

    def _safe_url(self, value: object) -> str | None:
        if not isinstance(value, str) or not value or len(value) > 4096 or re.search(r"[\x00-\x20\x7f\\]", value):
            return None
        try:
            parsed = urlsplit(urljoin(self._site_url + "/", value))
            if (
                parsed.username or parsed.password
                or (parsed.scheme, parsed.hostname, parsed.port or 443) != self._origin
            ):
                return None
            return parsed.geturl()
        except ValueError:
            return None

    @staticmethod
    def _string(value: object, maximum: int, empty: bool = False) -> str:
        if not isinstance(value, str) or len(value) > maximum or (not empty and not value):
            raise ValueError("Invalid notification text")
        return value

    @staticmethod
    def _plain(value: str, maximum: int) -> str:
        parser = _TextParser()
        parser.feed(value)
        parser.close()
        return " ".join("".join(parser.parts).split())[:maximum]

    def _optional_plain(self, value: object, maximum: int) -> str | None:
        if value is None:
            return None
        return self._plain(self._string(value, 20000, empty=True), maximum) or None
