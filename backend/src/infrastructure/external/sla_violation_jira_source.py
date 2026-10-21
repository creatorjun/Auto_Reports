# backend/src/infrastructure/external/sla_violation_jira_source.py
import asyncio
import math
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from time import monotonic_ns
from typing import Any
from urllib.parse import quote

import httpx

from src.application.ports.sla_violation_port import SlaViolationSourcePort
from src.application.ports.sla_status_port import SlaStatusDetailsPort
from src.domain.entities.sla_clock import SlaClockCalendar
from src.infrastructure.external.jira_sla_calendar import calendar_ids_for_project, parse_clock_calendar
from src.infrastructure.external.jira_user_identity import jira_account_id
from src.domain.entities.sla_violation_report import (
    SlaViolationChange,
    SlaViolationCycle,
    SlaViolationIssue,
    SlaViolationMetric,
)


_CUSTOMER_NAME_FIELD = "customfield_11022"
_CUSTOMER_ASSET_FIELD = "customfield_10854"
_PARTNER_FIELD = "customfield_10859"


def _snapshot_window(
    server_date: str | None,
    local_before: datetime,
    local_after: datetime,
    request_duration: timedelta,
) -> tuple[datetime, datetime]:
    if not isinstance(server_date, str):
        return local_before, local_after
    server_date = server_date.strip()
    if not re.fullmatch(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} \d{2}:\d{2}:\d{2} GMT", server_date):
        return local_before, local_after
    try:
        parsed = parsedate_to_datetime(server_date)
    except (TypeError, ValueError, OverflowError):
        return local_before, local_after
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0) or ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[parsed.weekday()] != server_date[:3]:
        return local_before, local_after
    try:
        return parsed - request_duration, parsed + timedelta(seconds=1) + request_duration
    except OverflowError:
        return local_before, local_after


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


def _duration_millis(cycle: dict, field: str, label: str, warnings: list[str], signed: bool = False) -> int | None:
    raw = cycle.get(field)
    if raw is None:
        return None
    value = raw.get("millis") if isinstance(raw, dict) else None
    if isinstance(value, int) and not isinstance(value, bool) and (signed or value >= 0):
        return value
    name = {"goalDuration": "목표 시간", "elapsedTime": "경과 시간", "remainingTime": "잔여 시간"}[field]
    warnings.append(f"{label} SLA {name} 값이 유효하지 않아 해당 시간을 확인할 수 없습니다.")
    return None


def _cycle_timing(cycle: dict, label: str, warnings: list[str]) -> tuple[int | None, int | None, int | None]:
    goal = _duration_millis(cycle, "goalDuration", label, warnings)
    elapsed = _duration_millis(cycle, "elapsedTime", label, warnings)
    remaining = _duration_millis(cycle, "remainingTime", label, warnings, signed=True)
    difference = elapsed - goal if goal is not None and elapsed is not None else None
    if difference is not None and remaining is not None and difference != -remaining:
        warnings.append(f"{label} SLA 목표·경과·잔여 시간이 일치하지 않아 초과 시간을 확인할 수 없습니다.")
        return goal, elapsed, None
    difference = difference if difference is not None else -remaining if remaining is not None else None
    if difference is None:
        return goal, elapsed, None
    if (cycle["breached"] and difference < 0) or (not cycle["breached"] and difference > 0):
        warnings.append(f"{label} SLA 위반 여부와 시간이 일치하지 않아 초과 시간을 확인할 수 없습니다.")
        return goal, elapsed, None
    return goal, elapsed, max(0, difference)


class SlaViolationJiraSource(SlaViolationSourcePort, SlaStatusDetailsPort):
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
        resolution_pause_statuses: tuple[str, ...] = ("결과 대기 중", "자료 요청 중", "보류 중"),
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
        self._pause_statuses = resolution_pause_statuses
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

    async def _request(
        self, method: str, path: str,
        snapshot: list[tuple[datetime, datetime]] | None = None,
        **kwargs: Any,
    ) -> object:
        self._ensure_open()
        async with self._limit:
            self._ensure_open()
            try:
                if snapshot is not None:
                    local_before = datetime.now(timezone.utc)
                    request_started_ns = monotonic_ns()
                response = await self._client.request(method, f"{self._base_url}{path}", **kwargs)
                if snapshot is not None:
                    request_duration = timedelta(microseconds=(monotonic_ns() - request_started_ns + 999) // 1000)
                    local_after = datetime.now(timezone.utc)
                response.raise_for_status()
                if snapshot is not None:
                    snapshot.append(_snapshot_window(response.headers.get("Date"), local_before, local_after, request_duration))
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
            if any(cycle.breached for cycle in cycles):
                selected.append((raw, created, cycles, warnings))
        return await self._enrich(selected)

    async def fetch_details(self, keys: tuple[str, ...]) -> tuple[SlaViolationIssue, ...]:
        self._ensure_open()
        if any(not re.fullmatch(r"[A-Z][A-Z0-9_]*-\d+", key) for key in keys):
            raise ValueError("Invalid SLA status issue key")
        if not keys:
            return ()
        async with self._fetch_lock:
            self._ensure_open()
            task = asyncio.create_task(self._load_details(tuple(dict.fromkeys(keys))))
            self._tasks.add(task)
            try:
                return await task
            finally:
                self._tasks.discard(task)

    async def _load_details(self, keys: tuple[str, ...]) -> tuple[SlaViolationIssue, ...]:
        selected = []
        for index in range(0, len(keys), 100):
            batch = keys[index:index + 100]
            quoted_keys = ", ".join(f'"{key}"' for key in batch)
            jql = f'project = "{self._project_key}" AND key IN ({quoted_keys}) AND statusCategory != Done ORDER BY key ASC'
            for raw in await self._search(jql):
                if raw["key"] not in batch:
                    raise RuntimeError("Jira SLA status returned an unrequested issue")
                fields = raw.get("fields")
                if not isinstance(fields, dict):
                    raise RuntimeError("Jira SLA status issue fields are invalid")
                status = fields.get("status")
                if not isinstance(status, dict):
                    raise RuntimeError("Jira SLA status issue status is invalid")
                category = status.get("statusCategory", {})
                if isinstance(category, dict) and category.get("key") == "done":
                    continue
                created = _date(fields.get("created"))
                if created is None:
                    raise RuntimeError("Jira SLA status creation timestamp is invalid")
                warnings: list[str] = []
                selected.append((raw, created, self._cycles(fields, warnings), warnings))
        return await self._enrich(selected)

    async def _enrich(self, selected: list) -> tuple[SlaViolationIssue, ...]:
        assets: dict[tuple[str, str], str | None] = {}
        asset_locks: dict[tuple[str, str], asyncio.Lock] = {}
        project_ids = {
            str(project["id"])
            for raw, _, _, _ in selected
            if isinstance(project := raw["fields"].get("project"), dict) and project.get("id")
        }
        calendars = await self._calendars(next(iter(project_ids))) if len(project_ids) == 1 else ()
        result: dict[int, SlaViolationIssue] = {}
        pending = iter(enumerate(selected))

        async def collect() -> None:
            for index, item in pending:
                result[index] = await self._issue(*item, assets, asset_locks, calendars)

        tasks = [asyncio.create_task(collect()) for _ in range(min(5, len(selected)))]
        try:
            await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        return tuple(result[index] for index in range(len(selected)))

    async def _calendars(self, project_id: str) -> tuple[SlaClockCalendar, ...]:
        try:
            listing = await self._request("GET", "/rest/workinghours/1/api/calendar")
            identifiers = calendar_ids_for_project(listing, project_id)
            calendars = []
            for identifier in identifiers:
                payload = await self._request("GET", f"/rest/workinghours/1/api/calendar/{identifier}")
                calendars.append(parse_clock_calendar(payload, identifier))
            return tuple(calendars)
        except ValueError:
            return ()
        except RuntimeError as error:
            cause = error.__cause__
            if isinstance(cause, httpx.HTTPStatusError) and cause.response.status_code in (403, 404):
                return ()
            raise

    async def _search(self, jql: str) -> list[dict]:
        fields = list(dict.fromkeys((
            "summary", "created", "status", "reporter", "assignee", "issuetype", "project",
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
            snapshot: list[tuple[datetime, datetime]] = []
            data = await self._request("POST", "/rest/api/3/search/jql", snapshot=snapshot, json=payload)
            snapshot_before, snapshot_after = snapshot[0]
            if not isinstance(data, dict) or not isinstance(data.get("issues"), list):
                raise RuntimeError("Jira SLA violation search page is invalid")
            for issue in data["issues"]:
                if not isinstance(issue, dict) or not isinstance(issue.get("key"), str) or not issue["key"]:
                    raise RuntimeError("Jira issue identifier is missing")
                if issue["key"] in keys:
                    raise RuntimeError("Jira SLA violation search returned duplicate issues")
                keys.add(issue["key"])
                issue["_sla_snapshot_before"] = snapshot_before
                issue["_sla_snapshot_after"] = snapshot_after
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
            if not isinstance(raw, dict):
                raise RuntimeError(f"Jira {metric} SLA data is invalid")
            completed = raw.get("completedCycles")
            if completed is not None and not isinstance(completed, list):
                raise RuntimeError(f"Jira {metric} SLA data is invalid")
            cycles = [(cycle, False) for cycle in completed or []]
            if raw.get("ongoingCycle") is not None:
                cycles.append((raw["ongoingCycle"], True))
            for cycle, ongoing in cycles:
                if not isinstance(cycle, dict) or not isinstance(cycle.get("breached"), bool):
                    raise RuntimeError(f"Jira {metric} SLA cycle is invalid")
                label = "최초응답" if metric == "initial_response" else "해결"
                breached_at = _date(cycle.get("breachTime")) if cycle["breached"] else None
                goal, elapsed, exceeded = _cycle_timing(cycle, label, warnings)
                paused = cycle.get("paused") if ongoing else None
                if paused is not None and not isinstance(paused, bool):
                    warnings.append(f"{label} SLA 일시정지 여부 확인 불가")
                    paused = None
                result.append(SlaViolationCycle(
                    metric=metric, breached_at=breached_at, breached=cycle["breached"],
                    ongoing=ongoing, paused=paused, goal_ms=goal, elapsed_ms=elapsed,
                    exceeded_ms=exceeded, started_at=_date(cycle.get("startTime")),
                    stopped_at=_date(cycle.get("stopTime")) if not ongoing else None,
                ))
                if cycle["breached"] and breached_at is None:
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
        asset_locks: dict[tuple[str, str], asyncio.Lock],
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
                async with asset_locks.setdefault(reference, asyncio.Lock()):
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
        asset_locks: dict[tuple[str, str], asyncio.Lock],
        calendars: tuple[SlaClockCalendar, ...],
    ) -> SlaViolationIssue:
        key = raw["key"]
        fields = raw["fields"]
        changes, complete = await self._histories(key, fields.get("status"))
        if not complete:
            warnings.append("상태 변경 이력이 불완전하여 상태별 체류 기간 및 위반 당시 상태 확인 불가")
        customer = _text(fields.get(_CUSTOMER_NAME_FIELD))
        if not customer:
            customers = await self._asset_names(fields.get(_CUSTOMER_ASSET_FIELD), assets, asset_locks)
            customer = ", ".join(customers) if customers else ""
        partners = await self._asset_names(fields[_PARTNER_FIELD], assets, asset_locks) if _PARTNER_FIELD in fields else None
        if partners is None:
            warnings.append("담당 파트너사 확인 불가")
        return SlaViolationIssue(
            key=key, summary=_text(fields.get("summary")), created_at=created,
            current_status=_text(fields.get("status")), customer=customer or None,
            partners=partners, reporter=_text(fields.get("reporter")) or None,
            assignee=_text(fields.get("assignee")) or None,
            tac_assignee=_text(fields.get(self._tac_field)) or None,
            reporter_account_id=jira_account_id(fields.get("reporter")),
            assignee_account_id=jira_account_id(fields.get("assignee")),
            tac_assignee_account_id=jira_account_id(fields.get(self._tac_field)),
            personal_data_retrieved_at=raw["_sla_snapshot_after"].isoformat() if raw.get("_sla_snapshot_after") else None,
            cycles=cycles, changes=changes, history_complete=complete,
            warnings=tuple(dict.fromkeys(warnings)),
            issue_type=_text(fields.get("issuetype")) or None,
            clock_calendars=calendars,
            clock_snapshot_before=raw.get("_sla_snapshot_before"),
            clock_snapshot_after=raw.get("_sla_snapshot_after"),
            clock_pause_statuses=self._pause_statuses,
        )
