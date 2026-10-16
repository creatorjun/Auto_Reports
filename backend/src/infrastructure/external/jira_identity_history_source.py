# backend/src/infrastructure/external/jira_identity_history_source.py
from datetime import datetime
from urllib.parse import quote

import httpx

from src.application.ports.jira_identity_history_port import JiraIdentityHistoryPort, JiraIdentityHistoryUnavailable
from src.domain.entities.jira_identity_history import JiraIdentityHistory, JiraUserChange, JiraUserValue
from src.infrastructure.external.jira_user_identity import jira_account_id


def _current_user(value: object) -> JiraUserValue:
    if isinstance(value, list):
        value = next((item for item in value if isinstance(item, dict) and (item.get("displayName") or item.get("name"))), None)
    if not isinstance(value, dict):
        return JiraUserValue(None, None)
    name = value.get("displayName") or value.get("name")
    return JiraUserValue(jira_account_id(value), name if isinstance(name, str) else None)


class JiraIdentityHistorySource(JiraIdentityHistoryPort):
    def __init__(self, base_url: str, client: httpx.AsyncClient, field_ids: tuple[str, ...]) -> None:
        self._base = base_url.rstrip("/")
        self._client = client
        self._field_ids = frozenset(field_ids)
        self._non_user_fields: frozenset[str] = frozenset()

    async def prepare(self) -> None:
        response = await self._client.get(f"{self._base}/rest/api/3/field")
        response.raise_for_status()
        descriptors = response.json()
        if not isinstance(descriptors, list):
            raise ValueError("Invalid Jira field descriptors")
        self._non_user_fields = frozenset(
            item["id"] for item in descriptors if isinstance(item, dict) and item.get("id") in self._field_ids
            and isinstance(item.get("schema"), dict) and (
                item["schema"].get("type") == "option" or (
                    item["schema"].get("type") == "array" and item["schema"].get("items") == "cmdb-object-field"
                )
            )
        )

    async def fetch(self, issue_key: str) -> JiraIdentityHistory:
        try:
            return await self._fetch(issue_key)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise JiraIdentityHistoryUnavailable("Jira identity history unavailable") from error

    async def _fetch(self, issue_key: str) -> JiraIdentityHistory:
        path = f"{self._base}/rest/api/3/issue/{quote(issue_key, safe='')}"
        response = await self._client.get(path, params={"fields": ",".join(sorted(self._field_ids | {"created"}))})
        response.raise_for_status()
        raw = response.json()
        fields = raw.get("fields")
        if raw.get("key") != issue_key or not isinstance(fields, dict):
            raise ValueError("Invalid Jira identity snapshot")
        created = datetime.fromisoformat(fields["created"])
        if created.tzinfo is None:
            raise ValueError("Missing Jira identity timestamp timezone")
        current = {field_id: _current_user(fields[field_id]) for field_id in self._field_ids if field_id in fields}
        if any(current.get(field_id, JiraUserValue(None, None)).display_name for field_id in self._non_user_fields):
            raise ValueError("Non-user Jira field unexpectedly has a display name")
        start_at = 0
        expected_total = None
        seen: set[str] = set()
        changes = []
        complete = True
        while True:
            response = await self._client.get(f"{path}/changelog", params={"startAt": start_at, "maxResults": 100})
            response.raise_for_status()
            page = response.json()
            values, total = page.get("values"), page.get("total")
            if not isinstance(values, list) or not isinstance(total, int) or page.get("startAt") != start_at:
                raise ValueError("Invalid Jira identity history page")
            if expected_total is not None and total != expected_total:
                complete = False
            expected_total = total
            for history in values:
                history_id = str(history.get("id") or "")
                if not history_id or history_id in seen:
                    complete = False
                seen.add(history_id)
                changed_at = datetime.fromisoformat(history["created"])
                if changed_at.tzinfo is None:
                    raise ValueError("Missing Jira history timezone")
                for item in history.get("items", []):
                    field_id = item.get("fieldId") or item.get("field")
                    if field_id in self._field_ids and field_id not in self._non_user_fields:
                        changes.append(JiraUserChange(field_id, changed_at, JiraUserValue(item.get("from") or None, item.get("fromString") or None), JiraUserValue(item.get("to") or None, item.get("toString") or None)))
            next_at = start_at + len(values)
            if next_at > total or (next_at < total and (not values or page.get("isLast") is True)):
                raise ValueError("Truncated Jira identity history")
            if next_at == total:
                break
            start_at = next_at
        return JiraIdentityHistory(issue_key, created, current, tuple(changes), complete)
