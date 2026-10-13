# backend/src/infrastructure/external/c_level_jira_source.py
import asyncio
import json
import math
import re
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import quote

import httpx

from src.application.ports.c_level_port import CLevelSourcePort
from src.domain.entities.c_level_report import (
    CLevelFieldChange,
    CLevelIssue,
    CLevelSlaCycle,
    CLevelStatus,
    CLevelStatusChange,
)


_TYPE_IDS = ("10104", "10105", "10110")
_DIMENSIONS = {
    "customfield_11022": "customer_name",
    "customfield_10854": "customer_asset",
    "customfield_10859": "partner_names",
    "customfield_12522": "tac_assignee",
    "assignee": "assignee",
    "reporter": "reporter",
    "customfield_12051": "delay_reason",
    "customfield_12018": "delay_responsibility",
}


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("displayName", "label", "value", "name"):
            if isinstance(value.get(key), str):
                return value[key].strip()
    return ""


def _date(value: object) -> datetime | None:
    if isinstance(value, dict):
        millis = value.get("epochMillis")
        if isinstance(millis, (int, float)) and not isinstance(millis, bool):
            try:
                return datetime.fromtimestamp(millis / 1000, timezone.utc)
            except (ValueError, OverflowError, OSError):
                return None
        value = value.get("iso8601") or value.get("jira")
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result if result.tzinfo is not None else None


def _millis(value: object) -> int | None:
    raw = value.get("millis") if isinstance(value, dict) else None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(raw):
        return int(raw)
    return None


def _boolean(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


class CLevelJiraSource(CLevelSourcePort):
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str = "TACEA",
        sla_initial_response_field_id: str = "customfield_12152",
        sla_resolution_field_id: str = "customfield_12151",
        client: httpx.AsyncClient | None = None,
        cache_ttl_seconds: float = 120.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", project_key):
            raise ValueError("Invalid Jira project key")
        self._base_url = base_url.rstrip("/")
        self._project_key = project_key
        self._sla_fields = {
            sla_initial_response_field_id: "initial_response",
            sla_resolution_field_id: "resolution",
        }
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            auth=(email, api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
            limits=httpx.Limits(max_connections=6, max_keepalive_connections=6),
        )
        self._limit = asyncio.Semaphore(6)
        self._fetch_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()
        self._closed = False
        self._clock = clock
        self._ttl = max(0.0, cache_ttl_seconds)
        self._cache: OrderedDict[tuple[datetime, datetime], tuple[float, tuple[CLevelIssue, ...]]] = OrderedDict()
        self._assets: OrderedDict[tuple[str, str], tuple[float, str]] = OrderedDict()
        self._history_cache: OrderedDict[tuple[str, str], tuple[float, tuple[dict, ...]]] = OrderedDict()
        self._history_count = 0
        self._status_cache: tuple[float, dict[str, CLevelStatus]] | None = None
        self._legacy_status_cache: OrderedDict[str, tuple[float, CLevelStatus | None]] = OrderedDict()
        self._legacy_status_lock = asyncio.Lock()

    async def __aenter__(self) -> "CLevelJiraSource":
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
        self._cache.clear()
        self._assets.clear()
        self._history_cache.clear()
        self._history_count = 0
        self._status_cache = None
        self._legacy_status_cache.clear()
        if self._owns_client:
            await self._client.aclose()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("C-Level Jira source is closed")

    async def _request(self, method: str, path: str, **kwargs: Any) -> object:
        self._ensure_open()
        async with self._limit:
            response = await self._client.request(method, f"{self._base_url}{path}", **kwargs)
            response.raise_for_status()
            return response.json()

    async def fetch_issues(
        self, earliest: datetime, as_of: datetime, refresh: bool = False,
    ) -> tuple[CLevelIssue, ...]:
        if earliest.tzinfo is None or as_of.tzinfo is None or earliest >= as_of:
            raise ValueError("C-Level period requires ordered timezone-aware timestamps")
        self._ensure_open()
        key = (earliest, as_of)
        async with self._fetch_lock:
            self._ensure_open()
            cached = self._cache.get(key)
            if not refresh and cached is not None and cached[0] > self._clock():
                self._cache.move_to_end(key)
                return cached[1]
            if refresh:
                self._assets.clear()
                self._history_cache.clear()
                self._history_count = 0
                self._status_cache = None
                self._legacy_status_cache.clear()
            task = asyncio.create_task(self._load(earliest, as_of))
            self._tasks.add(task)
            try:
                issues = await task
            except (httpx.HTTPError, json.JSONDecodeError) as error:
                raise RuntimeError("Jira C-Level collection failed") from error
            finally:
                self._tasks.discard(task)
            self._cache[key] = (self._clock() + self._ttl, issues)
            self._cache.move_to_end(key)
            while len(self._cache) > 8 or sum(len(entry[1]) for entry in self._cache.values()) > 20000:
                self._cache.popitem(last=False)
            return issues

    def _jql(self, earliest: datetime, as_of: datetime) -> str:
        lower = (earliest.astimezone(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
        upper = (as_of.astimezone(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
        return (
            f'project = "{self._project_key}" AND issuetype in ({", ".join(_TYPE_IDS)}) '
            f'AND created < "{upper}" AND (created >= "{lower}" OR statusCategory != Done '
            f'OR status CHANGED AFTER "{lower}" OR resolved >= "{lower}") ORDER BY key ASC'
        )

    async def _load(self, earliest: datetime, as_of: datetime) -> tuple[CLevelIssue, ...]:
        statuses = await self._statuses()
        raw_issues = await self._search(self._jql(earliest, as_of))
        selected = []
        for issue in raw_issues:
            fields = issue.get("fields")
            if not isinstance(fields, dict):
                raise RuntimeError("Jira issue fields are invalid")
            created = _date(fields.get("created"))
            if created is None:
                raise RuntimeError("Jira issue creation timestamp is invalid")
            if created < as_of:
                selected.append(issue)
        result = []
        for start in range(0, len(selected), 6):
            tasks = [asyncio.create_task(self._issue(issue, statuses, as_of)) for issue in selected[start:start + 6]]
            try:
                result.extend(await asyncio.gather(*tasks))
            except BaseException:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
        return tuple(result)

    async def _statuses(self) -> dict[str, CLevelStatus]:
        if self._status_cache is not None and self._status_cache[0] > self._clock():
            return self._status_cache[1]
        data = await self._request("GET", f"/rest/api/3/project/{quote(self._project_key, safe='')}/statuses")
        if not isinstance(data, list):
            raise RuntimeError("Jira project status registry is invalid")
        statuses = {}
        for issue_type in data:
            if not isinstance(issue_type, dict) or not isinstance(issue_type.get("statuses"), list):
                raise RuntimeError("Jira project status registry is invalid")
            for status in issue_type["statuses"]:
                parsed = self._status(status, {})
                if not parsed.id:
                    raise RuntimeError("Jira project status identifier is missing")
                statuses[parsed.id] = parsed
        self._status_cache = (self._clock() + 300, statuses)
        return statuses

    @staticmethod
    def _status(value: object, registry: dict[str, CLevelStatus]) -> CLevelStatus:
        if not isinstance(value, dict):
            return CLevelStatus(id="", name="", category="")
        identifier = str(value.get("id") or "")
        known = registry.get(identifier)
        category = value.get("statusCategory")
        category_key = _text(category.get("key")) if isinstance(category, dict) else ""
        return CLevelStatus(
            id=identifier,
            name=_text(value.get("name")) or (known.name if known else ""),
            category=category_key or (known.category if known else ""),
        )

    async def _legacy_status(self, identifier: str) -> CLevelStatus | None:
        async with self._legacy_status_lock:
            cached = self._legacy_status_cache.get(identifier)
            if cached is not None and cached[0] > self._clock():
                self._legacy_status_cache.move_to_end(identifier)
                return cached[1]
            try:
                data = await self._request("GET", f"/rest/api/3/status/{quote(identifier, safe='')}")
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 404:
                    raise
                status = None
            else:
                status = self._status(data, {})
                if status.id != identifier or not status.category:
                    raise RuntimeError(f"Jira historical status metadata is invalid for {identifier}")
            self._legacy_status_cache[identifier] = (self._clock() + (3600 if status else 300), status)
            self._legacy_status_cache.move_to_end(identifier)
            while len(self._legacy_status_cache) > 512:
                self._legacy_status_cache.popitem(last=False)
            return status

    async def _search(self, jql: str) -> list[dict]:
        issues = []
        keys: set[str] = set()
        tokens: set[str] = set()
        token = None
        fields = ["summary", "issuetype", "created", "updated", "status", "customfield_12454", *_DIMENSIONS, *self._sla_fields]
        while True:
            payload: dict[str, Any] = {"jql": jql, "fields": fields, "maxResults": 100}
            if token is not None:
                payload["nextPageToken"] = token
            data = await self._request("POST", "/rest/api/3/search/jql", json=payload)
            if not isinstance(data, dict) or not isinstance(data.get("issues"), list):
                raise RuntimeError("Jira C-Level search page is invalid")
            for issue in data["issues"]:
                if not isinstance(issue, dict) or not isinstance(issue.get("key"), str) or not issue["key"]:
                    raise RuntimeError("Jira C-Level issue identifier is missing")
                if issue["key"] in keys:
                    raise RuntimeError("Jira C-Level search returned duplicate issues")
                keys.add(issue["key"])
                issues.append(issue)
                if len(issues) > 50000:
                    raise RuntimeError("Jira C-Level candidate limit exceeded; narrow the report period")
            next_token = data.get("nextPageToken")
            if data.get("isLast") is True:
                if next_token:
                    raise RuntimeError("Jira C-Level search pagination is inconsistent")
                return issues
            if not isinstance(next_token, str) or not next_token or next_token in tokens or not data["issues"]:
                raise RuntimeError("Jira C-Level search is truncated or pagination repeated")
            tokens.add(next_token)
            token = next_token

    async def _histories(self, key: str, updated: str) -> tuple[dict, ...]:
        cache_key = (key, updated)
        cached = self._history_cache.get(cache_key) if updated else None
        if cached is not None and cached[0] > self._clock():
            self._history_cache.move_to_end(cache_key)
            return cached[1]
        histories = []
        identifiers: set[str] = set()
        start = 0
        expected_total = None
        while True:
            data = await self._request(
                "GET", f"/rest/api/3/issue/{quote(key, safe='')}/changelog",
                params={"startAt": start, "maxResults": 100},
            )
            if not isinstance(data, dict) or not isinstance(data.get("values"), list) or data.get("startAt") != start:
                raise RuntimeError(f"Jira history page is invalid for {key}")
            values = data["values"]
            total = data.get("total")
            if not isinstance(total, int) or isinstance(total, bool) or total < start + len(values):
                raise RuntimeError(f"Jira history total is invalid for {key}")
            if expected_total is not None and expected_total != total:
                raise RuntimeError(f"Jira history changed during collection for {key}; retry required")
            expected_total = total
            for history in values:
                if not isinstance(history, dict) or not isinstance(history.get("items"), list):
                    raise RuntimeError(f"Jira history entries are invalid for {key}")
                identifier = str(history.get("id") or "")
                if identifier and identifier in identifiers:
                    raise RuntimeError(f"Jira history pagination repeated for {key}")
                identifiers.add(identifier)
                histories.append(history)
                if len(histories) > 10000:
                    raise RuntimeError(f"Jira history limit exceeded for {key}; collection requires review")
            start += len(values)
            if start == total:
                result = tuple(histories)
                if updated:
                    previous = self._history_cache.pop(cache_key, None)
                    if previous is not None:
                        self._history_count -= len(previous[1])
                    self._history_cache[cache_key] = (self._clock() + 300, result)
                    self._history_count += len(result)
                    while len(self._history_cache) > 2048 or self._history_count > 50000:
                        _, removed = self._history_cache.popitem(last=False)
                        self._history_count -= len(removed[1])
                return result
            if not values or data.get("isLast") is True:
                raise RuntimeError(f"Jira history is truncated for {key}")

    async def _asset_names(self, value: object) -> tuple[str, ...]:
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
                continue
            reference = (str(asset["workspaceId"]), str(asset["objectId"]))
            cached = self._assets.get(reference)
            if cached is not None and cached[0] > self._clock():
                self._assets.move_to_end(reference)
                labels.append(cached[1])
                continue
            workspace, identifier = (quote(part, safe="") for part in reference)
            data = await self._request("GET", f"/gateway/api/jsm/assets/workspace/{workspace}/v1/object/{identifier}")
            label = _text(data)
            if not label:
                raise RuntimeError("Jira Assets object label is missing")
            self._assets[reference] = (self._clock() + 3600, label)
            self._assets.move_to_end(reference)
            while len(self._assets) > 1024:
                self._assets.popitem(last=False)
            labels.append(label)
        return tuple(dict.fromkeys(labels))

    def _cycles(self, fields: dict, warnings: list[str]) -> tuple[CLevelSlaCycle, ...]:
        result = []
        for field, metric in self._sla_fields.items():
            raw = fields.get(field)
            if not isinstance(raw, dict):
                warnings.append(f"{metric}: SLA 데이터 없음")
                continue
            completed = raw.get("completedCycles", [])
            if not isinstance(completed, list):
                warnings.append(f"{metric}: SLA 완료 이력 형식 확인 필요")
                continue
            cycles = [(cycle, False) for cycle in completed]
            if raw.get("ongoingCycle") is not None:
                cycles.append((raw["ongoingCycle"], True))
            for index, (cycle, ongoing) in enumerate(cycles):
                if not isinstance(cycle, dict):
                    warnings.append(f"{metric}: SLA 이력 형식 확인 필요")
                    continue
                start = _date(cycle.get("startTime"))
                result.append(CLevelSlaCycle(
                    metric=metric,
                    cycle_id=f"{metric}:{start.isoformat() if start else index}",
                    start_at=start,
                    stop_at=_date(cycle.get("stopTime")),
                    breach_at=_date(cycle.get("breachTime")),
                    goal_ms=_millis(cycle.get("goalDuration")),
                    elapsed_ms=_millis(cycle.get("elapsedTime")),
                    remaining_ms=_millis(cycle.get("remainingTime")),
                    breached=_boolean(cycle.get("breached")),
                    paused=_boolean(cycle.get("paused")),
                    ongoing=ongoing,
                ))
        return tuple(result)

    async def _issue(self, raw: dict, registry: dict[str, CLevelStatus], as_of: datetime) -> CLevelIssue:
        key = raw["key"]
        fields = raw["fields"]
        warnings: list[str] = []
        current_status = self._status(fields.get("status"), registry)
        if current_status.id and current_status.category:
            registry = {**registry, current_status.id: current_status}
        histories = await self._histories(key, _text(fields.get("updated")))
        missing_ids: set[str] = set()
        for history in histories:
            for item in history["items"]:
                if not isinstance(item, dict) or (item.get("fieldId") or item.get("field")) != "status":
                    continue
                for side in ("from", "to"):
                    identifier = str(item.get(side) or "")
                    if identifier and (identifier not in registry or not registry[identifier].category):
                        missing_ids.add(identifier)
        for identifier in sorted(missing_ids):
            legacy = await self._legacy_status(identifier)
            if legacy is not None:
                registry = {**registry, identifier: legacy}
        changes = []
        field_changes = []
        asset_changes = []
        uncertain_dimensions: set[str] = set()
        raw_dimensions: dict[str, object] = {logical: fields.get(field) for field, logical in _DIMENSIONS.items()}
        complete = True
        for history in histories:
            changed_at = _date(history.get("created"))
            if changed_at is None:
                complete = False
                warnings.append("변경 이력 시각 확인 필요")
                continue
            for item in history["items"]:
                if not isinstance(item, dict):
                    raise RuntimeError(f"Jira history item is invalid for {key}")
                field = item.get("fieldId") or item.get("field")
                if field == "status":
                    old = self._status({"id": item.get("from"), "name": item.get("fromString")}, registry)
                    new = self._status({"id": item.get("to"), "name": item.get("toString")}, registry)
                    changes.append(CLevelStatusChange(changed_at=changed_at, from_status=old, to_status=new))
                    if not old.category or not new.category:
                        warnings.append("삭제되었거나 등록되지 않은 상태의 완료 범주 확인 필요")
                if field in _DIMENSIONS:
                    logical = _DIMENSIONS[field]
                    field_changes.append(CLevelFieldChange(
                        changed_at=changed_at, field_id=logical,
                        from_value=item.get("fromString"), to_value=item.get("toString"),
                    ))
                    if logical in {"customer_asset", "partner_names"}:
                        asset_changes.append((changed_at, logical, item.get("from"), item.get("fromString")))
        for change in sorted(field_changes, key=lambda item: item.changed_at, reverse=True):
            if change.changed_at < as_of:
                continue
            old_value = change.from_value
            if change.field_id in {"customer_asset", "partner_names"}:
                continue
            elif old_value is None:
                raw_dimensions[change.field_id] = None
                uncertain_dimensions.add(change.field_id)
                warnings.append(f"{change.field_id}: 기준일 이전 값 확인 필요")
            else:
                raw_dimensions[change.field_id] = old_value
                uncertain_dimensions.discard(change.field_id)
        for changed_at, logical, old_id, old_label in sorted(asset_changes, key=lambda item: item[0], reverse=True):
            if changed_at < as_of:
                continue
            if old_id is None and not old_label:
                raw_dimensions[logical] = None
            elif isinstance(old_id, str) and re.fullmatch(r"[A-Za-z0-9_:-]+", old_id) and isinstance(old_label, str) and old_label.strip():
                raw_dimensions[logical] = old_label
            else:
                raw_dimensions[logical] = None
                warnings.append(f"{logical}: 기준일 이후 Assets 변경으로 과거 명칭 확인 필요")
        if not complete:
            for field in raw_dimensions:
                raw_dimensions[field] = None
            warnings.append("변경 시각 누락으로 과거 고객사 및 담당자 확인 필요")
        customer = _text(raw_dimensions["customer_name"])
        if not customer and "customer_name" not in uncertain_dimensions:
            customer = ", ".join(await self._asset_names(raw_dimensions["customer_asset"]))
        partners = await self._asset_names(raw_dimensions["partner_names"])
        if not customer:
            warnings.append("고객사 값 확인 필요")
        if not current_status.category:
            warnings.append("현재 상태의 완료 범주 확인 필요")
        return CLevelIssue(
            key=key, summary=_text(fields.get("summary")),
            issue_type=_text(fields.get("issuetype")),
            created_at=_date(fields["created"]), updated_at=_date(fields.get("updated")),
            status=current_status, customer_name=customer, partner_names=partners,
            reporter=_text(raw_dimensions["reporter"]), assignee=_text(raw_dimensions["assignee"]),
            tac_assignee=_text(raw_dimensions["tac_assignee"]),
            status_changes=tuple(sorted(changes, key=lambda item: item.changed_at)),
            field_changes=tuple(sorted(field_changes, key=lambda item: item.changed_at)),
            sla_cycles=self._cycles(fields, warnings), history_complete=complete,
            warnings=tuple(dict.fromkeys(warnings)),
            first_response_at=_date(fields.get("customfield_12454")),
            jira_delay_reason=_text(raw_dimensions["delay_reason"]),
            jira_delay_responsibility=_text(raw_dimensions["delay_responsibility"]),
        )
