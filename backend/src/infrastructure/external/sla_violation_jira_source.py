# backend/src/infrastructure/external/sla_violation_jira_source.py
import asyncio
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

from src.application.ports.sla_violation_port import SlaViolationSourcePort
from src.domain.entities.sla_violation_report import (
    SlaViolationChange,
    SlaViolationCycle,
    SlaViolationIssue,
    SlaViolationMetric,
)


_CUSTOMER_NAME_FIELD = "customfield_11022"
_CUSTOMER_ASSET_FIELD = "customfield_10854"
_PARTNER_FIELD = "customfield_10859"


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("displayName", "label", "value", "name"):
            if isinstance(value.get(key), str) and value[key].strip():
                return value[key].strip()
    if isinstance(value, list):
        return ", ".join(dict.fromkeys(text for item in value if (text := _text(item))))
    return ""


def _date(value: object) -> datetime | None:
    if isinstance(value, dict):
        millis = value.get("epochMillis")
        if isinstance(millis, (int, float)) and not isinstance(millis, bool) and math.isfinite(millis):
            try:
                return datetime.fromtimestamp(millis / 1000, timezone.utc)
            except (ValueError, OverflowError, OSError):
                pass
        value = value.get("iso8601") or value.get("jira")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


class SlaViolationJiraSource(SlaViolationSourcePort):
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str = "TACEA",
        sla_initial_response_field_id: str = "customfield_12152",
        sla_resolution_field_id: str = "customfield_12151",
        tac_assignee_field_id: str = "customfield_12522",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", project_key):
            raise ValueError("Invalid Jira project key")
        fields = (sla_initial_response_field_id, sla_resolution_field_id)
        if any(not re.fullmatch(r"customfield_\d+", field) for field in fields) or len(set(fields)) != 2:
            raise ValueError("Distinct initial-response and resolution SLA fields are required")
        if not re.fullmatch(r"customfield_\d+", tac_assignee_field_id):
            raise ValueError("A valid Jira TAC assignee field is required")
        self._base_url = base_url.rstrip("/")
        self._project_key = project_key
        self._sla_fields: tuple[tuple[str, SlaViolationMetric], ...] = (
            (sla_initial_response_field_id, "initial_response"),
            (sla_resolution_field_id, "resolution"),
        )
        self._tac_field = tac_assignee_field_id
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=5),
        )
        self._limit = asyncio.Semaphore(5)
        self._fetch_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()
        self._closed = False

    async def __aenter__(self) -> "SlaViolationJiraSource":
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
            raise RuntimeError("SLA violation Jira source is closed")

    async def _request(self, method: str, path: str, **kwargs: Any) -> object:
        self._ensure_open()
        async with self._limit:
            self._ensure_open()
            try:
                response = await self._client.request(method, f"{self._base_url}{path}", **kwargs)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as error:
                raise RuntimeError("Jira SLA violation request failed") from error

    async def fetch_issues(self, start: datetime, end: datetime) -> tuple[SlaViolationIssue, ...]:
        if start.tzinfo is None or end.tzinfo is None or start >= end:
            raise ValueError("SLA violation period requires ordered timezone-aware timestamps")
        self._ensure_open()
        async with self._fetch_lock:
            self._ensure_open()
            task = asyncio.create_task(self._load(start, end))
            self._tasks.add(task)
            try:
                return await task
            finally:
                self._tasks.discard(task)

    async def _load(self, start: datetime, end: datetime) -> tuple[SlaViolationIssue, ...]:
        lower = (start.astimezone(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
        upper = (end.astimezone(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
        jql = (
            f'project = "{self._project_key}" AND created >= "{lower}" '
            f'AND created < "{upper}" ORDER BY key ASC'
        )
        selected = []
        for raw in await self._search(jql):
            fields = raw.get("fields")
            if not isinstance(fields, dict):
                raise RuntimeError("Jira issue fields are invalid")
            created = _date(fields.get("created"))
            if created is None:
                raise RuntimeError(f"Jira issue creation timestamp is invalid for {raw['key']}")
            if not start <= created < end:
                continue
            warnings: list[str] = []
            cycles = self._cycles(fields, warnings)
            if cycles:
                selected.append((raw, created, cycles, warnings))
        assets: dict[tuple[str, str], str | None] = {}
        result = []
        for index in range(0, len(selected), 5):
            tasks = [asyncio.create_task(self._issue(*item, assets)) for item in selected[index:index + 5]]
            try:
                result.extend(await asyncio.gather(*tasks))
            except BaseException:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
        return tuple(result)

    async def _search(self, jql: str) -> list[dict]:
        fields = list(dict.fromkeys((
            "summary", "created", "status", "reporter", "assignee",
            _CUSTOMER_NAME_FIELD, _CUSTOMER_ASSET_FIELD, _PARTNER_FIELD,
            self._tac_field, *(field for field, _ in self._sla_fields),
        )))
        issues: list[dict] = []
        keys: set[str] = set()
        tokens: set[str] = set()
        token = None
        while True:
            payload: dict[str, Any] = {"jql": jql, "fields": fields, "maxResults": 100}
            if token is not None:
                payload["nextPageToken"] = token
            data = await self._request("POST", "/rest/api/3/search/jql", json=payload)
            if not isinstance(data, dict) or not isinstance(data.get("issues"), list):
                raise RuntimeError("Jira SLA violation search page is invalid")
            for issue in data["issues"]:
                if not isinstance(issue, dict) or not isinstance(issue.get("key"), str) or not issue["key"]:
                    raise RuntimeError("Jira issue identifier is missing")
                if issue["key"] in keys:
                    raise RuntimeError("Jira SLA violation search returned duplicate issues")
                keys.add(issue["key"])
                issues.append(issue)
            next_token = data.get("nextPageToken")
            if data.get("isLast") is True:
                if next_token:
                    raise RuntimeError("Jira search pagination is inconsistent")
                return issues
            if not isinstance(next_token, str) or not next_token or next_token in tokens or not data["issues"]:
                raise RuntimeError("Jira search is truncated or pagination repeated")
            tokens.add(next_token)
            token = next_token

    def _cycles(self, fields: dict, warnings: list[str]) -> tuple[SlaViolationCycle, ...]:
        result = []
        for field, metric in self._sla_fields:
            if field not in fields:
                raise RuntimeError(f"Jira SLA field {field} is missing from the search response")
            raw = fields[field]
            if raw is None:
                continue
            if not isinstance(raw, dict) or not isinstance(raw.get("completedCycles", []), list):
                raise RuntimeError(f"Jira {metric} SLA data is invalid")
            cycles = list(raw.get("completedCycles", []))
            if raw.get("ongoingCycle") is not None:
                cycles.append(raw["ongoingCycle"])
            for cycle in cycles:
                if not isinstance(cycle, dict) or not isinstance(cycle.get("breached"), bool):
                    raise RuntimeError(f"Jira {metric} SLA cycle is invalid")
                if cycle["breached"]:
                    breached_at = _date(cycle.get("breachTime"))
                    result.append(SlaViolationCycle(metric=metric, breached_at=breached_at))
                    if breached_at is None:
                        label = "최초응답" if metric == "initial_response" else "해결"
                        warnings.append(f"{label} SLA 위반 시각 확인 불가")
        return tuple(result)

    async def _histories(self, key: str, current_status: object) -> tuple[tuple[SlaViolationChange, ...], bool]:
        changes: list[tuple[datetime, str, str, str, str]] = []
        identifiers: set[str] = set()
        start = 0
        expected_total = None
        complete = True

        def result(valid: bool) -> tuple[tuple[SlaViolationChange, ...], bool]:
            ordered = sorted(changes, key=lambda change: change[0])
            labels: dict[str, str] = {}
            for _, from_id, to_id, from_name, to_name in reversed(ordered):
                if to_id:
                    labels.setdefault(to_id, to_name)
                if from_id:
                    labels.setdefault(from_id, from_name)
            current_id = _text(current_status.get("id")) if isinstance(current_status, dict) else ""
            current_name = _text(current_status)
            if current_id and current_name:
                labels[current_id] = current_name
            previous_id = ""
            for _, from_id, to_id, _, _ in ordered:
                if previous_id and from_id and previous_id != from_id:
                    valid = False
                previous_id = to_id
            if previous_id and current_id and previous_id != current_id:
                valid = False
            return tuple(
                SlaViolationChange(changed_at, labels.get(from_id, from_name), labels.get(to_id, to_name))
                for changed_at, from_id, to_id, from_name, to_name in ordered
            ), valid

        while True:
            data = await self._request(
                "GET", f"/rest/api/3/issue/{quote(key, safe='')}/changelog",
                params={"startAt": start, "maxResults": 100},
            )
            if not isinstance(data, dict) or not isinstance(data.get("values"), list) or data.get("startAt") != start:
                return result(False)
            values = data["values"]
            total = data.get("total")
            if not isinstance(total, int) or isinstance(total, bool) or total < start + len(values):
                return result(False)
            if expected_total is not None and expected_total != total:
                return result(False)
            expected_total = total
            for history in values:
                if not isinstance(history, dict) or not isinstance(history.get("items"), list):
                    complete = False
                    continue
                identifier = str(history.get("id") or "")
                if identifier and identifier in identifiers:
                    return result(False)
                if identifier:
                    identifiers.add(identifier)
                for item in history["items"]:
                    if not isinstance(item, dict):
                        complete = False
                        continue
                    if item.get("fieldId") != "status" and item.get("field") != "status":
                        continue
                    changed_at = _date(history.get("created"))
                    from_status = _text(item.get("fromString"))
                    to_status = _text(item.get("toString"))
                    if changed_at is None or not from_status or not to_status:
                        complete = False
                        continue
                    changes.append((changed_at, _text(item.get("from")), _text(item.get("to")), from_status, to_status))
            start += len(values)
            if start == total:
                return result(complete)
            if not values or data.get("isLast") is True:
                return result(False)

    async def _asset_names(
        self, value: object, assets: dict[tuple[str, str], str | None],
    ) -> tuple[str, ...] | None:
        if value is None:
            return ()
        values = value if isinstance(value, list) else [value]
        labels = []
        for asset in values:
            label = _text(asset)
            if label:
                labels.append(label)
                continue
            if not isinstance(asset, dict) or not asset.get("workspaceId") or not asset.get("objectId"):
                return None
            reference = (str(asset["workspaceId"]), str(asset["objectId"]))
            if reference not in assets:
                workspace, identifier = (quote(part, safe="") for part in reference)
                data = await self._request("GET", f"/gateway/api/jsm/assets/workspace/{workspace}/v1/object/{identifier}")
                assets[reference] = _text(data) or None
            if assets[reference] is None:
                return None
            labels.append(assets[reference])
        return tuple(dict.fromkeys(labels))

    async def _issue(
        self, raw: dict, created: datetime, cycles: tuple[SlaViolationCycle, ...],
        warnings: list[str], assets: dict[tuple[str, str], str | None],
    ) -> SlaViolationIssue:
        key = raw["key"]
        fields = raw["fields"]
        changes, complete = await self._histories(key, fields.get("status"))
        if not complete:
            warnings.append("상태 변경 이력이 불완전하여 상태별 체류 기간 및 위반 당시 상태 확인 불가")
        customer = _text(fields.get(_CUSTOMER_NAME_FIELD))
        if not customer:
            customers = await self._asset_names(fields.get(_CUSTOMER_ASSET_FIELD), assets)
            customer = ", ".join(customers) if customers else ""
        partners = await self._asset_names(fields[_PARTNER_FIELD], assets) if _PARTNER_FIELD in fields else None
        if partners is None:
            warnings.append("담당 파트너사 확인 불가")
        return SlaViolationIssue(
            key=key, summary=_text(fields.get("summary")), created_at=created,
            current_status=_text(fields.get("status")), customer=customer or None,
            partners=partners, reporter=_text(fields.get("reporter")) or None,
            assignee=_text(fields.get("assignee")) or None,
            tac_assignee=_text(fields.get(self._tac_field)) or None,
            cycles=cycles, changes=changes, history_complete=complete,
            warnings=tuple(dict.fromkeys(warnings)),
        )
