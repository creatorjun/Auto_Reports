# backend/src/infrastructure/external/redeployment_jira_source.py
import asyncio
import math
import re
from datetime import datetime
from urllib.parse import quote

import httpx

from src.domain.constants import KST
from src.domain.entities.redeployment_report import REDEPLOYMENT_START, RedeploymentTicket

REDEPLOYMENT_FIELDS = {
    "flag": "customfield_11819", "cause": "customfield_11885", "reason": "customfield_11852",
    "month": "customfield_12421", "count": "customfield_11753", "customer": "customfield_11022",
    "partner": "customfield_10859",
}


def _text(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("value", "displayName", "name", "text"):
            if isinstance(value.get(key), str):
                return _text(value[key])
        if isinstance(value.get("content"), list):
            return "\n".join(filter(None, (_text(item) for item in value["content"]))) or None
    return None


class RedeploymentJiraSource:
    def __init__(self, base_url: str, email: str, api_token: str, project_key: str,
                 client: httpx.AsyncClient | None = None) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", project_key):
            raise ValueError("Invalid Jira project key")
        self._base = base_url.rstrip("/")
        self._project = project_key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            auth=(email, api_token), timeout=30,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=5),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch(self, as_of: datetime) -> tuple[str, tuple[RedeploymentTicket, ...], tuple[str, ...]]:
        cutoff = as_of.astimezone(KST).strftime("%Y-%m-%d %H:%M")
        jql = (
            f'project = {self._project} AND cf[11819] = Y AND issuetype != "라이선스" '
            f'AND ((status = Closed AND resolved >= "{REDEPLOYMENT_START}" '
            f'AND resolved <= "{cutoff}") OR status != Closed) ORDER BY key ASC'
        )
        field_list = ["summary", "issuetype", "status", "created", "resolutiondate", "assignee", "reporter", *REDEPLOYMENT_FIELDS.values()]
        issues: dict[str, dict] = {}
        token = None
        seen: set[str] = set()
        try:
            while True:
                payload = {"jql": jql, "fields": field_list, "maxResults": 100}
                if token:
                    payload["nextPageToken"] = token
                response = await self._client.post(f"{self._base}/rest/api/3/search/jql", json=payload)
                response.raise_for_status()
                data = response.json()
                page = data.get("issues")
                if not isinstance(page, list):
                    raise ValueError("Invalid Jira issue page")
                for issue in page:
                    if not isinstance(issue, dict) or not issue.get("key") or not isinstance(issue.get("fields"), dict):
                        raise ValueError("Invalid Jira issue")
                    issues[issue["key"]] = issue
                token = data.get("nextPageToken")
                if data.get("isLast") is True:
                    break
                if not token:
                    raise ValueError("Jira pagination was truncated")
                if not isinstance(token, str) or token in seen or not page:
                    raise ValueError("Jira pagination did not advance")
                seen.add(token)
        except (httpx.HTTPError, ValueError, AttributeError) as error:
            raise RuntimeError("Jira 재배포 목록을 불러오지 못했습니다.") from error
        references = set()
        for issue in issues.values():
            for item in issue["fields"].get(REDEPLOYMENT_FIELDS["partner"]) or []:
                if isinstance(item, dict) and item.get("workspaceId") and item.get("objectId"):
                    references.add((item["workspaceId"], item["objectId"]))
        labels: dict[tuple[str, str], str] = {}
        warnings: list[str] = []
        semaphore = asyncio.Semaphore(4)

        async def resolve(reference: tuple[str, str]) -> None:
            workspace, object_id = (quote(value, safe="") for value in reference)
            async with semaphore:
                try:
                    response = await self._client.get(f"{self._base}/gateway/api/jsm/assets/workspace/{workspace}/v1/object/{object_id}")
                    response.raise_for_status()
                    label = _text(response.json().get("label"))
                    if not label:
                        raise ValueError("Missing asset label")
                    labels[reference] = label
                except (httpx.HTTPError, ValueError, AttributeError):
                    labels[reference] = f"이름 확인 불가 (객체 {reference[1]})"
                    warnings.append(f"파트너사 객체 {reference[1]}의 이름을 확인하지 못했습니다.")

        await asyncio.gather(*(resolve(reference) for reference in sorted(references)))
        tickets = []
        for key, issue in issues.items():
            fields = issue["fields"]
            status = fields.get("status") or {}
            if not status.get("id") or not _text(status) or not fields.get("created"):
                raise RuntimeError(f"{key}의 필수 정보가 누락되어 보고서를 저장하지 않았습니다.")
            closed = str(status["id"]) == "6"
            try:
                created = datetime.fromisoformat(fields["created"])
                resolved = datetime.fromisoformat(fields["resolutiondate"]) if fields.get("resolutiondate") else None
                if created.tzinfo is None or (resolved and resolved.tzinfo is None) or (closed and resolved is None):
                    raise ValueError("Missing timezone or resolution date")
            except (ValueError, TypeError) as error:
                raise RuntimeError(f"{key}의 날짜가 유효하지 않아 보고서를 저장하지 않았습니다.") from error
            count = fields.get(REDEPLOYMENT_FIELDS["count"])
            valid_count = isinstance(count, (int, float)) and not isinstance(count, bool) and math.isfinite(count) and count >= 0 and int(count) == count
            partners = []
            for item in fields.get(REDEPLOYMENT_FIELDS["partner"]) or []:
                ref = (item.get("workspaceId"), item.get("objectId")) if isinstance(item, dict) else (None, None)
                partners.append(labels.get(ref, "이름 확인 불가"))
            tickets.append(RedeploymentTicket(
                key=key, summary=_text(fields.get("summary")) or key,
                issue_type=_text(fields.get("issuetype")) or "미지정", status=_text(status) or "미지정",
                closed=closed, created_at=fields["created"], resolved_at=fields.get("resolutiondate"),
                completion_month=_text(fields.get(REDEPLOYMENT_FIELDS["month"])),
                cause=_text(fields.get(REDEPLOYMENT_FIELDS["cause"])), reason=_text(fields.get(REDEPLOYMENT_FIELDS["reason"])),
                repatch_count=int(count) if valid_count else None, customer=_text(fields.get(REDEPLOYMENT_FIELDS["customer"])),
                partners=tuple(dict.fromkeys(partners)), assignee=_text(fields.get("assignee")), reporter=_text(fields.get("reporter")),
            ))
        return jql, tuple(tickets), tuple(sorted(warnings))
