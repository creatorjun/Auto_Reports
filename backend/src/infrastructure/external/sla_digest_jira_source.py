# backend/src/infrastructure/external/sla_digest_jira_source.py
import asyncio
import logging
import re
from dataclasses import replace
from typing import Any

import httpx

from src.application.ports.sla_digest_port import SlaDigestSourcePort
from src.domain.entities.sla_digest import SlaDigestEntry
from src.domain.services.issue_type_policy import is_license_issue_type


_SLA_SCHEMA = "com.atlassian.servicedesk:sd-sla-field"
_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
_LOGGER = logging.getLogger(__name__)


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Jira SLA digest {label} is missing or invalid")
    return value.strip()


def _millis(cycle: dict, field: str, signed: bool = False) -> int:
    duration = cycle.get(field)
    value = duration.get("millis") if isinstance(duration, dict) else None
    if not isinstance(value, int) or isinstance(value, bool) or (not signed and value < 0):
        raise RuntimeError(f"Jira SLA digest {field} is missing or invalid")
    return value


class SlaDigestJiraSource(SlaDigestSourcePort):
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str = "TACEA",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", project_key):
            raise ValueError("Invalid Jira project key")
        self._base_url = base_url.rstrip("/")
        self._project_key = project_key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=_TIMEOUT,
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
        )
        self._fetch_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()
        self._closed = False

    async def __aenter__(self) -> "SlaDigestJiraSource":
        self._ensure_open()
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        if self._owns_client:
            await self._client.aclose()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("SLA digest Jira source is closed")

    async def _request(self, method: str, path: str, **kwargs: Any) -> object:
        self._ensure_open()
        try:
            response = await self._client.request(
                method, f"{self._base_url}{path}", timeout=_TIMEOUT, **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise RuntimeError("Jira SLA digest request failed") from error

    async def fetch_entries(self) -> tuple[SlaDigestEntry, ...]:
        self._ensure_open()
        async with self._fetch_lock:
            self._ensure_open()
            task = asyncio.create_task(self._load())
            self._tasks.add(task)
            try:
                return await task
            finally:
                self._tasks.discard(task)

    async def _fields(self) -> tuple[tuple[str, str], ...]:
        data = await self._request("GET", "/rest/api/3/field")
        if not isinstance(data, list):
            raise RuntimeError("Jira SLA digest field catalog is invalid")
        fields: dict[str, str] = {}
        for field in data:
            if not isinstance(field, dict):
                raise RuntimeError("Jira SLA digest field definition is invalid")
            schema = field.get("schema")
            if not isinstance(schema, dict) or schema.get("custom") != _SLA_SCHEMA:
                continue
            identifier = _required_text(field.get("id"), "field identifier")
            name = _required_text(field.get("name"), "field name")
            if not re.fullmatch(r"customfield_\d+", identifier):
                raise RuntimeError("Jira SLA digest field identifier is invalid")
            if identifier in fields and fields[identifier] != name:
                raise RuntimeError("Jira SLA digest field definitions conflict")
            fields[identifier] = name
        if not fields:
            raise RuntimeError("Jira SLA digest field catalog contains no SLA fields")
        return tuple(fields.items())

    async def _load(self) -> tuple[SlaDigestEntry, ...]:
        sla_fields = await self._fields()
        fields = ["summary", "status", "assignee", "issuetype", *(field for field, _ in sla_fields)]
        jql = f'project = "{self._project_key}" AND statusCategory != Done ORDER BY key ASC'
        result: dict[str, tuple[SlaDigestEntry, ...]] = {}
        tokens: set[str] = set()
        token = None
        while True:
            payload: dict[str, Any] = {"jql": jql, "fields": fields, "maxResults": 100}
            if token is not None:
                payload["nextPageToken"] = token
            data = await self._request("POST", "/rest/api/3/search/jql", json=payload)
            if not isinstance(data, dict) or not isinstance(data.get("issues"), list):
                raise RuntimeError("Jira SLA digest search page is invalid")
            for issue in data["issues"]:
                if not isinstance(issue, dict):
                    raise RuntimeError("Jira SLA digest issue is invalid")
                key = _required_text(issue.get("key"), "issue identifier")
                result[key] = self._entries(key, issue.get("fields"), sla_fields)
            next_token = data.get("nextPageToken")
            if data.get("isLast") is True:
                if next_token is not None and next_token != "":
                    raise RuntimeError("Jira SLA digest pagination is inconsistent")
                return tuple(entry for entries in result.values() for entry in entries)
            if "isLast" in data and not isinstance(data["isLast"], bool):
                raise RuntimeError("Jira SLA digest pagination marker is invalid")
            if not isinstance(next_token, str) or not next_token.strip() or next_token in tokens or not data["issues"]:
                raise RuntimeError("Jira SLA digest search is truncated or pagination repeated")
            tokens.add(next_token)
            token = next_token

    def _entries(
        self, key: str, fields: object, sla_fields: tuple[tuple[str, str], ...],
    ) -> tuple[SlaDigestEntry, ...]:
        if not isinstance(fields, dict):
            raise RuntimeError("Jira SLA digest issue fields are invalid")
        summary = _required_text(fields.get("summary"), "issue summary")
        status_value = fields.get("status")
        status = _required_text(status_value.get("name") if isinstance(status_value, dict) else None, "issue status")
        issue_type = fields.get("issuetype")
        issue_type_name = _required_text(issue_type.get("name") if isinstance(issue_type, dict) else None, "issue type")
        if is_license_issue_type(issue_type_name):
            return ()
        category = status_value.get("statusCategory")
        if category is not None:
            if not isinstance(category, dict):
                raise RuntimeError("Jira SLA digest issue status category is invalid")
            if category.get("key") == "done":
                return ()
        if "assignee" not in fields:
            raise RuntimeError("Jira SLA digest assignee field is missing")
        assignee_value = fields["assignee"]
        assignee = "미지정" if assignee_value is None else _required_text(
            assignee_value.get("displayName") if isinstance(assignee_value, dict) else None, "issue assignee",
        )
        result = []
        issue_has_breached_sla = False
        for identifier, name in sla_fields:
            if identifier not in fields:
                raise RuntimeError(f"Jira SLA digest field {identifier} is missing from the search response")
            value = fields[identifier]
            if value is None:
                continue
            if not isinstance(value, dict):
                raise RuntimeError(f"Jira SLA digest field {identifier} is invalid")
            completed = value.get("completedCycles")
            if completed is not None and not isinstance(completed, list):
                raise RuntimeError(f"Jira SLA digest completed cycles {identifier} are invalid")
            for completed_cycle in completed or []:
                if not isinstance(completed_cycle, dict) or not isinstance(completed_cycle.get("breached"), bool):
                    raise RuntimeError(f"Jira SLA digest completed cycle {identifier} is invalid")
                issue_has_breached_sla = issue_has_breached_sla or completed_cycle["breached"]
            cycle = value.get("ongoingCycle")
            if cycle is None:
                continue
            if not isinstance(cycle, dict) or not isinstance(cycle.get("paused"), bool) or not isinstance(cycle.get("breached"), bool):
                raise RuntimeError(f"Jira SLA digest ongoing cycle {identifier} is invalid")
            goal = _millis(cycle, "goalDuration")
            remaining = _millis(cycle, "remainingTime", signed=True)
            issue_has_breached_sla = issue_has_breached_sla or cycle["breached"] or remaining < 0
            if goal == 0:
                _LOGGER.warning("Skipping zero-duration SLA goal for %s / %s", key, identifier)
                continue
            if remaining > goal:
                raise RuntimeError(f"Jira SLA digest remaining time exceeds goal for {identifier}")
            if "elapsedTime" in cycle and goal - _millis(cycle, "elapsedTime") != remaining:
                raise RuntimeError(f"Jira SLA digest cycle timing is inconsistent for {identifier}")
            if (cycle["breached"] and remaining > 0) or (not cycle["breached"] and remaining < 0):
                raise RuntimeError(f"Jira SLA digest breach flag and timing are inconsistent for {identifier}")
            result.append(SlaDigestEntry(
                key=key, summary=summary, status=status, assignee=assignee,
                sla_id=identifier, sla_name=name, goal_millis=goal, remaining_millis=remaining,
                paused=cycle["paused"], breached=cycle["breached"],
            ))
        return tuple(replace(entry, issue_has_breached_sla=issue_has_breached_sla) for entry in result)
