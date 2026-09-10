# backend/src/infrastructure/external/jira_client.py
import asyncio
import logging
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote

import httpx

from src.application.ports.jira_port import (
    JiraAssetReference,
    JiraAttachmentContent,
    JiraComment,
    JiraCommentImage,
    JiraChartIssuePage,
    JiraIssue,
    JiraIssueField,
    JiraPort,
)
from src.application.ports.service_desk_port import ServiceDeskPort
from src.application.ports.search_port import SearchPort
from src.domain.constants import JIRA_MAX_RESULT
from src.domain.entities.partner import PartnerMember, PartnerOrganization
from src.domain.entities.search import SearchResult, SearchSource
from src.infrastructure.cache.lru_cache import LruCache

logger = logging.getLogger(__name__)

_JIRA_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
_JIRA_LIMITS  = httpx.Limits(max_connections=30, max_keepalive_connections=15)

_SD_TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)
_SD_HEADERS = {
    "Accept": "application/json",
    "X-ExperimentalApi": "opt-in",
}

_REDEPLOYMENT_MONTH_FIELD = "customfield_12421"
_REDEPLOYMENT_CAUSE_FIELD = "customfield_11885"
_REDEPLOYMENT_PARTNER_FIELD = "customfield_10859"
_JIRA_FIELD_NAMES: dict[JiraIssueField, str] = {
    JiraIssueField.SUMMARY: "summary",
    JiraIssueField.ISSUE_TYPE: "issuetype",
    JiraIssueField.STATUS: "status",
    JiraIssueField.CREATED: "created",
    JiraIssueField.UPDATED: "updated",
    JiraIssueField.RESOLVED: "resolutiondate",
    JiraIssueField.PRIORITY: "priority",
    JiraIssueField.REPORTER: "reporter",
    JiraIssueField.ASSIGNEE: "assignee",
}

_FETCH_PAGE_SIZE      = 100

_COUNT_CACHE_MAXSIZE  = 256
_COUNT_CACHE_TTL      = 600.0
_COUNT_CACHE_STALE    = 120.0

_ISSUES_CACHE_MAXSIZE = 128
_ISSUES_CACHE_TTL     = 300.0
_ISSUES_CACHE_STALE   = 60.0

_COMMENT_IMAGE_MAX_BYTES = 20 * 1024 * 1024
_COMMENT_IMAGE_MEDIA_TYPES = frozenset({
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
})
_ATTACHMENT_ID_PATTERN = re.compile(
    r"/(?:rest/api/[23]/attachment/content|secure/attachment)/(\d+)(?:[/?#]|$)",
    re.IGNORECASE,
)


class _CommentImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[JiraCommentImage] = []
        self._seen: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "img":
            return
        values = {name.lower(): value or "" for name, value in attrs}
        match = _ATTACHMENT_ID_PATTERN.search(values.get("src", ""))
        if match is None or match.group(1) in self._seen:
            return
        attachment_id = match.group(1)
        self._seen.add(attachment_id)
        self.images.append(
            JiraCommentImage(
                attachment_id=attachment_id,
                alt=values.get("alt") or values.get("title") or "댓글 첨부 이미지",
            )
        )


def _adf_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_adf_text(item) for item in value)
    if not isinstance(value, dict):
        return ""
    node_type = value.get("type", "")
    attrs = value.get("attrs") or {}
    if node_type == "text":
        return str(value.get("text", ""))
    if node_type == "hardBreak":
        return "\n"
    if node_type == "mention":
        return str(attrs.get("text") or attrs.get("displayName") or "")
    if node_type == "emoji":
        return str(attrs.get("text") or attrs.get("shortName") or "")
    content = _adf_text(value.get("content") or [])
    if node_type == "listItem":
        return f"- {content.strip()}\n"
    if node_type in {"paragraph", "heading", "blockquote", "codeBlock"}:
        return f"{content.rstrip()}\n"
    return content


def _comment_images(value: object) -> tuple[JiraCommentImage, ...]:
    if not isinstance(value, str) or not value:
        return ()
    parser = _CommentImageParser()
    parser.feed(value)
    parser.close()
    return tuple(parser.images)


class JiraClient(JiraPort, SearchPort, ServiceDeskPort):
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        sla_initial_response_field_id: str = "",
        sla_resolution_field_id: str = "",
        jira_tac_assignee_field_id: str = "",
        jira_qa_assignee_field_id: str = "",
        jira_recent_tac_assignee_field_id: str = "",
    ):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            auth=(email, api_token),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=_JIRA_TIMEOUT,
            limits=_JIRA_LIMITS,
        )
        self._sd_client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=(email, api_token),
            headers=_SD_HEADERS,
            timeout=_SD_TIMEOUT,
        )
        self._sla_initial_fid    = sla_initial_response_field_id
        self._sla_resolution_fid = sla_resolution_field_id
        self._tac_assignee_fid   = jira_tac_assignee_field_id
        self._qa_assignee_fid    = jira_qa_assignee_field_id
        self._recent_tac_assignee_fid = jira_recent_tac_assignee_field_id

        self._count_cache: LruCache[str, int] = LruCache(
            maxsize=_COUNT_CACHE_MAXSIZE,
            ttl_seconds=_COUNT_CACHE_TTL,
            stale_ttl_seconds=_COUNT_CACHE_STALE,
        )
        self._issues_cache: LruCache[str, list[JiraIssue]] = LruCache(
            maxsize=_ISSUES_CACHE_MAXSIZE,
            ttl_seconds=_ISSUES_CACHE_TTL,
            stale_ttl_seconds=_ISSUES_CACHE_STALE,
        )
        self._org_name_cache: dict[str, str] = {}
        self._asset_object_label_cache: dict[JiraAssetReference, str] = {}

    @staticmethod
    def _display_name(value: object) -> str:
        if isinstance(value, list):
            return next(
                (
                    name
                    for item in value
                    if (name := JiraClient._display_name(item))
                ),
                "",
            )
        if isinstance(value, dict):
            return str(value.get("displayName") or value.get("name") or "")
        return ""

    @staticmethod
    def _sla_breached(value: object) -> bool:
        if not isinstance(value, dict):
            return False
        if any(
            isinstance(cycle, dict) and cycle.get("breached")
            for cycle in value.get("completedCycles") or []
        ):
            return True
        ongoing = value.get("ongoingCycle")
        return bool(isinstance(ongoing, dict) and ongoing.get("breached"))

    @staticmethod
    def _option_value(value: object) -> str:
        if isinstance(value, dict):
            return str(value.get("value") or "")
        return str(value or "")

    def _map_issue(self, issue: dict[str, Any]) -> JiraIssue:
        fields = issue.get("fields") or {}
        partner_references = tuple(
            JiraAssetReference(
                workspace_id=str(partner.get("workspaceId") or ""),
                object_id=str(partner.get("objectId") or ""),
            )
            for partner in fields.get(_REDEPLOYMENT_PARTNER_FIELD) or []
            if isinstance(partner, dict)
            and partner.get("workspaceId")
            and partner.get("objectId")
        )
        return JiraIssue(
            key=str(issue.get("key") or ""),
            summary=str(fields.get("summary") or ""),
            issue_type=str((fields.get("issuetype") or {}).get("name") or ""),
            status=str((fields.get("status") or {}).get("name") or ""),
            created=str(fields.get("created") or ""),
            updated=str(fields.get("updated") or ""),
            resolved=str(fields.get("resolutiondate") or ""),
            priority=str((fields.get("priority") or {}).get("name") or ""),
            reporter=self._display_name(fields.get("reporter")),
            assignee=self._display_name(fields.get("assignee")),
            tac_assignee=self._display_name(fields.get(self._tac_assignee_fid)),
            qa_assignee=self._display_name(fields.get(self._qa_assignee_fid)),
            recent_tac_assignee=self._display_name(
                fields.get(self._recent_tac_assignee_fid)
            ),
            initial_response_breached=self._sla_breached(
                fields.get(self._sla_initial_fid)
            ),
            resolution_breached=self._sla_breached(
                fields.get(self._sla_resolution_fid)
            ),
            redeployment_month=self._option_value(
                fields.get(_REDEPLOYMENT_MONTH_FIELD)
            ),
            redeployment_cause=self._option_value(
                fields.get(_REDEPLOYMENT_CAUSE_FIELD)
            ),
            partner_references=partner_references,
        )

    @staticmethod
    def _map_comment(comment: dict[str, Any]) -> JiraComment:
        author = comment.get("author") or {}
        return JiraComment(
            id=str(comment.get("id") or ""),
            author=str(
                author.get("displayName") or author.get("name") or "알 수 없음"
            ),
            body=_adf_text(comment.get("body")).strip(),
            created=str(comment.get("created") or ""),
            updated=str(comment.get("updated") or ""),
            images=_comment_images(comment.get("renderedBody")),
        )

    async def get_project_issue_types(self, project_key: str) -> list[str]:
        encoded_key = quote(project_key, safe="")
        url = f"{self._base_url}/rest/api/3/project/{encoded_key}"
        resp = await self._client.get(url, params={"expand": "issueTypes"})
        resp.raise_for_status()
        names = [
            str(issue_type.get("name", "")).strip()
            for issue_type in resp.json().get("issueTypes", [])
            if not issue_type.get("subtask")
        ]
        return list(dict.fromkeys(name for name in names if name))

    async def get_issue_count(self, jql: str) -> int:
        async def fetch(_: str) -> int:
            url = f"{self._base_url}/rest/api/3/search/approximate-count"
            try:
                resp = await self._client.post(url, json={"jql": jql})
                resp.raise_for_status()
                return int(resp.json().get("count", 0))
            except httpx.HTTPError as e:
                logger.error(f"JQL 카운트 실패: {jql[:80]}... -> {e}")
                if isinstance(e, httpx.HTTPStatusError):
                    logger.error(f"응답 상세: {e.response.text[:200]}")
                return 0

        count = await self._count_cache.async_get(jql, refresh_fn=fetch)
        return count if count is not None else 0

    async def get_issue_counts_batch(self, jqls: list[str]) -> list[int]:
        return list(await asyncio.gather(*[self.get_issue_count(jql) for jql in jqls]))

    async def _fetch_page(
        self,
        jql: str,
        fields: list[str] | None,
        next_page_token: str | None = None,
        page_size: int = _FETCH_PAGE_SIZE,
    ) -> tuple[list[dict[str, Any]], str | None]:
        url = f"{self._base_url}/rest/api/3/search/jql"
        payload: dict[str, Any] = {
            "jql": jql,
            "maxResults": page_size,
        }
        if fields:
            payload["fields"] = fields
        if next_page_token:
            payload["nextPageToken"] = next_page_token
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            token: str | None = data.get("nextPageToken") or None
            return data.get("issues", []), token
        except httpx.HTTPError as e:
            logger.error(f"JQL 페이지 요청 실패 (nextPageToken={next_page_token}): {jql[:80]}... -> {e}")
            if isinstance(e, httpx.HTTPStatusError):
                logger.error(f"응답 상세: {e.response.text[:200]}")
            return [], None

    def _issues_cache_key(
        self,
        jql: str,
        max_results: int | None,
        fields: tuple[str, ...],
    ) -> str:
        return f"{jql}|{max_results}|{','.join(fields)}"

    async def _get_mapped_issues(
        self,
        jql: str,
        max_results: int | None,
        fields: tuple[str, ...],
    ) -> list[JiraIssue]:
        cache_key = self._issues_cache_key(jql, max_results, fields)
        issues = await self._issues_cache.async_get(
            cache_key,
            refresh_fn=lambda _: self._load_issues(jql, max_results, fields),
        )
        return list(issues) if issues is not None else []

    async def get_issues(
        self,
        jql: str,
        max_results: int | None = JIRA_MAX_RESULT,
        fields: frozenset[JiraIssueField] = frozenset(),
    ) -> list[JiraIssue]:
        jira_fields = tuple(sorted(
            (_JIRA_FIELD_NAMES[field] for field in fields),
        ))
        return await self._get_mapped_issues(jql, max_results, jira_fields)

    async def _load_issues(
        self,
        jql: str,
        max_results: int | None,
        fields: tuple[str, ...],
    ) -> list[JiraIssue]:
        field_list = list(fields) if fields else None
        page_size = _FETCH_PAGE_SIZE if max_results is None else min(_FETCH_PAGE_SIZE, max_results)

        first_page, first_token = await self._fetch_page(jql, field_list, None, page_size)
        logger.info(f"JQL 첫 페이지 수신: {len(first_page)}건, nextPageToken={first_token is not None}")

        if not first_page:
            return []

        if max_results is not None and len(first_page) >= max_results:
            return [self._map_issue(issue) for issue in first_page[:max_results]]

        if first_token is None:
            logger.info(f"JQL 단일 페이지 완료: {len(first_page)}건 (nextPageToken 없음)")
            return [self._map_issue(issue) for issue in first_page]

        all_issues = list(first_page)
        next_token: str | None = first_token
        while next_token and (max_results is None or len(all_issues) < max_results):
            page, next_token = await self._fetch_page(jql, field_list, next_token, page_size)
            all_issues.extend(page)
            logger.info(f"JQL 순차 페이지: 수신={len(page)}, 누적={len(all_issues)}")
            if not page:
                break

        logger.info(f"JQL 수집 완료: 총={len(all_issues)}건")
        selected = all_issues if max_results is None else all_issues[:max_results]
        return [self._map_issue(issue) for issue in selected]

    async def get_issues_with_sla(
        self,
        jql: str,
        max_results: int | None = JIRA_MAX_RESULT,
    ) -> list[JiraIssue]:
        base = "summary,issuetype,status,created,resolutiondate"
        sla_part = ",".join(filter(None, [self._sla_initial_fid, self._sla_resolution_fid]))
        fields = tuple(filter(None, f"{base},{sla_part}".split(",")))
        return await self._get_mapped_issues(jql, max_results, fields)

    async def get_report_chart_issues(
        self,
        jql: str,
        max_results: int | None,
        fields: frozenset[JiraIssueField],
        with_sla: bool = False,
        with_redeployment: bool = False,
    ) -> JiraChartIssuePage:
        if max_results is not None and max_results <= 0:
            raise ValueError("Chart issue limit must be positive")
        field_list = sorted(_JIRA_FIELD_NAMES[field] for field in fields)
        if with_sla:
            field_list.extend(filter(None, [self._sla_initial_fid, self._sla_resolution_fid]))
        if with_redeployment:
            field_list.extend([
                _REDEPLOYMENT_MONTH_FIELD,
                _REDEPLOYMENT_CAUSE_FIELD,
                _REDEPLOYMENT_PARTNER_FIELD,
            ])
        issues: list[dict[str, Any]] = []
        next_token: str | None = None
        seen_tokens: set[str] = set()
        while True:
            remaining = _FETCH_PAGE_SIZE if max_results is None else min(_FETCH_PAGE_SIZE, max_results - len(issues))
            payload: dict[str, Any] = {"jql": jql, "maxResults": remaining, "fields": list(dict.fromkeys(field_list))}
            if next_token is not None:
                payload["nextPageToken"] = next_token
            try:
                response = await self._client.post(f"{self._base_url}/rest/api/3/search/jql", json=payload)
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError) as error:
                raise RuntimeError("Jira chart issue query failed") from error
            if not isinstance(data, dict):
                raise RuntimeError("Jira chart issue response is invalid")
            page = data.get("issues")
            if not isinstance(page, list) or any(
                not isinstance(issue, dict)
                or (issue.get("fields") is not None and not isinstance(issue["fields"], dict))
                for issue in page
            ):
                raise RuntimeError("Jira chart issue response is invalid")
            issues.extend(page)
            next_token = data.get("nextPageToken") or None
            if next_token is not None and not isinstance(next_token, str):
                raise RuntimeError("Jira chart issue pagination token is invalid")
            if next_token is not None and (not page or next_token in seen_tokens):
                raise RuntimeError("Jira chart issue pagination did not advance")
            if next_token is None or (max_results is not None and len(issues) >= max_results):
                break
            seen_tokens.add(next_token)
        selected = issues if max_results is None else issues[:max_results]
        try:
            mapped = [self._map_issue(issue) for issue in selected]
        except (AttributeError, TypeError, ValueError) as error:
            raise RuntimeError("Jira chart issue response is invalid") from error
        return JiraChartIssuePage(issues=mapped, has_more=next_token is not None or len(selected) < len(issues))

    async def get_issues_with_assignees(
        self,
        jql: str,
        max_results: int | None = JIRA_MAX_RESULT,
    ) -> list[JiraIssue]:
        base = "summary,issuetype,status,created,reporter,assignee"
        assignee_part = ",".join(filter(None, [
            self._tac_assignee_fid,
            self._qa_assignee_fid,
            self._recent_tac_assignee_fid,
        ]))
        fields = tuple(filter(None, f"{base},{assignee_part}".split(",")))
        return await self._get_mapped_issues(jql, max_results, fields)

    async def get_redeployment_issues(
        self,
        jql: str,
        max_results: int | None = JIRA_MAX_RESULT,
    ) -> list[JiraIssue]:
        fields = tuple((
            "summary,issuetype,priority,resolutiondate,assignee,"
            f"{_REDEPLOYMENT_MONTH_FIELD},{_REDEPLOYMENT_CAUSE_FIELD},"
            f"{_REDEPLOYMENT_PARTNER_FIELD}"
        ).split(","))
        return await self._get_mapped_issues(jql, max_results, fields)

    async def get_issue_comments(
        self,
        issue_key: str,
        max_results: int = 5,
        offset: int = 0,
    ) -> list[JiraComment]:
        if offset < 0:
            raise ValueError("Comment offset must be nonnegative")
        limit = max(1, max_results)
        encoded_key = quote(issue_key, safe="")
        url = f"{self._base_url}/rest/api/3/issue/{encoded_key}/comment"
        result: list[dict[str, Any]] = []
        try:
            while len(result) < limit:
                page_limit = min(limit - len(result), 100)
                response = await self._client.get(
                    url,
                    params={
                        "orderBy": "-created",
                        "maxResults": page_limit,
                        "startAt": offset + len(result),
                        "expand": "renderedBody",
                    },
                )
                response.raise_for_status()
                data = response.json()
                comments = list(data.get("comments") or data.get("values") or [])[:page_limit]
                result.extend(comments)
                total = data.get("total")
                if not comments:
                    break
                if isinstance(total, int):
                    if offset + len(result) >= total:
                        break
                elif len(comments) < page_limit:
                    break
        except httpx.HTTPError as error:
            logger.error(f"Jira 댓글 조회 실패: {issue_key} -> {error}")
            raise RuntimeError("Jira comments request failed") from error

        return [self._map_comment(comment) for comment in result]

    async def get_issue_comment(
        self,
        issue_key: str,
        comment_id: str,
    ) -> JiraComment | None:
        encoded_key = quote(issue_key, safe="")
        encoded_id = quote(comment_id, safe="")
        url = f"{self._base_url}/rest/api/3/issue/{encoded_key}/comment/{encoded_id}"
        try:
            response = await self._client.get(url, params={"expand": "renderedBody"})
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._map_comment(response.json())
        except httpx.HTTPError as error:
            logger.error(f"Jira 댓글 조회 실패: {issue_key}/{comment_id} -> {error}")
            raise RuntimeError("Jira comment request failed") from error

    async def get_attachment_content(
        self,
        attachment_id: str,
    ) -> JiraAttachmentContent:
        if not attachment_id.isdigit():
            raise RuntimeError("Invalid Jira attachment id")
        encoded_id = quote(attachment_id, safe="")
        url = f"{self._base_url}/rest/api/3/attachment/content/{encoded_id}"
        try:
            response = await self._client.get(
                url,
                params={"redirect": "false"},
                headers={"Accept": "*/*"},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.error(f"Jira 댓글 이미지 조회 실패: {attachment_id} -> {error}")
            raise RuntimeError("Jira attachment request failed") from error

        media_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        content_length = response.headers.get("Content-Length")
        if media_type not in _COMMENT_IMAGE_MEDIA_TYPES:
            raise RuntimeError("Unsupported Jira attachment image type")
        if content_length and int(content_length) > _COMMENT_IMAGE_MAX_BYTES:
            raise RuntimeError("Jira attachment image is too large")
        if len(response.content) > _COMMENT_IMAGE_MAX_BYTES:
            raise RuntimeError("Jira attachment image is too large")
        return JiraAttachmentContent(data=response.content, media_type=media_type)

    async def get_asset_object_labels(
        self,
        references: list[JiraAssetReference],
    ) -> dict[JiraAssetReference, str]:
        unique_references = list(dict.fromkeys(references))

        async def resolve(reference: JiraAssetReference) -> tuple[JiraAssetReference, str]:
            cached = self._asset_object_label_cache.get(reference)
            if cached is not None:
                return reference, cached
            workspace = quote(reference.workspace_id, safe="")
            object_key = quote(reference.object_id, safe="")
            url = (
                f"{self._base_url}/gateway/api/jsm/assets/workspace/"
                f"{workspace}/v1/object/{object_key}"
            )
            label = f"\ud30c\ud2b8\ub108 \uac1d\uccb4 {reference.object_id}"
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                label = str(response.json().get("label") or label)
            except httpx.HTTPError as error:
                logger.warning(f"Assets \uac1d\uccb4 \uc870\ud68c \uc2e4\ud328: {reference.object_id} -> {error}")
            self._asset_object_label_cache[reference] = label
            return reference, label

        resolved = await asyncio.gather(*(resolve(reference) for reference in unique_references))
        return dict(resolved)

    async def get_report_chart_asset_labels(
        self,
        references: list[JiraAssetReference],
    ) -> dict[JiraAssetReference, str]:
        async def resolve(reference: JiraAssetReference) -> tuple[JiraAssetReference, str]:
            workspace = quote(reference.workspace_id, safe="")
            object_id = quote(reference.object_id, safe="")
            url = f"{self._base_url}/gateway/api/jsm/assets/workspace/{workspace}/v1/object/{object_id}"
            try:
                response = await self._client.get(url)
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError) as error:
                raise RuntimeError("Jira chart partner label query failed") from error
            label = data.get("label") if isinstance(data, dict) else None
            if not isinstance(label, str) or not label.strip():
                raise RuntimeError("Jira chart partner label response is invalid")
            return reference, label
        resolved = await asyncio.gather(*(resolve(reference) for reference in dict.fromkeys(references)))
        return dict(resolved)

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        jira_url = f"{self._base_url}/rest/api/3/search/jql"
        jira_payload: dict[str, Any] = {
            "jql": f'text ~ "{query}" ORDER BY updated DESC',
            "maxResults": limit,
            "fields": ["summary", "status", "issuetype", "priority", "assignee"],
        }

        confluence_url = f"{self._base_url}/wiki/rest/api/content/search"
        confluence_params = {
            "cql": f'type in (page, blogpost) AND text ~ "{query}" ORDER BY lastmodified DESC',
            "limit": limit,
            "expand": "space",
        }

        jira_task = self._client.post(jira_url, json=jira_payload)
        confluence_task = self._client.get(confluence_url, params=confluence_params)
        jira_resp, confluence_resp = await asyncio.gather(
            jira_task, confluence_task, return_exceptions=True
        )

        results: list[SearchResult] = []

        if isinstance(jira_resp, httpx.Response):
            try:
                jira_resp.raise_for_status()
                for issue in jira_resp.json().get("issues", []):
                    fields = issue.get("fields", {})
                    key = str(issue.get("key") or "")
                    results.append(SearchResult(
                        source=SearchSource.JIRA,
                        key=key,
                        title=str(fields.get("summary") or ""),
                        status=str((fields.get("status") or {}).get("name") or ""),
                        item_type=str((fields.get("issuetype") or {}).get("name") or ""),
                        url=f"{self._base_url}/browse/{key}",
                    ))
            except httpx.HTTPError as e:
                logger.error(f"Jira 검색 실패: {e}")
        else:
            logger.error(f"Jira 검색 실패: {jira_resp}")

        if isinstance(confluence_resp, httpx.Response):
            try:
                confluence_resp.raise_for_status()
                for page in confluence_resp.json().get("results", []):
                    space_key = (page.get("space") or {}).get("key", "")
                    page_id = str(page.get("id") or "")
                    results.append(SearchResult(
                        source=SearchSource.CONFLUENCE,
                        key=page_id,
                        title=str(page.get("title") or ""),
                        status=str((page.get("space") or {}).get("name") or ""),
                        item_type=str(page.get("type") or "page"),
                        url=f"{self._base_url}/wiki/spaces/{space_key}/pages/{page_id}",
                    ))
            except httpx.HTTPError as e:
                logger.warning(f"Confluence 검색 실패 (옵션): {e}")
        else:
            logger.warning(f"Confluence 검색 실패 (옵션): {confluence_resp}")

        results.sort(key=lambda result: result.source)
        return results[:limit]

    async def get_organizations(self) -> list[PartnerOrganization]:
        results, start = [], 0
        while True:
            resp = await self._sd_client.get(
                "/rest/servicedeskapi/organization",
                params={"start": start, "limit": 50},
            )
            resp.raise_for_status()
            data   = resp.json()
            values = data.get("values", [])
            for v in values:
                if v.get("id") and v.get("name"):
                    oid  = str(v["id"])
                    name = str(v["name"])
                    results.append(PartnerOrganization(id=oid, name=name))
                    self._org_name_cache[oid] = name
            if data.get("isLastPage", True):
                break
            start += len(values)
        results.sort(key=lambda organization: organization.name)
        logger.info(f"[파트너] 조직 {len(results)}개")
        return results

    async def resolve_org_name(self, org_id: str) -> str:
        if org_id in self._org_name_cache:
            return self._org_name_cache[org_id]
        resp = await self._sd_client.get(f"/rest/servicedeskapi/organization/{org_id}")
        resp.raise_for_status()
        name = resp.json().get("name", "")
        self._org_name_cache[org_id] = name
        return name

    async def get_members(self, org_id: str) -> list[PartnerMember]:
        results, start = [], 0
        while True:
            resp = await self._sd_client.get(
                f"/rest/servicedeskapi/organization/{org_id}/user",
                params={"start": start, "limit": 50},
            )
            resp.raise_for_status()
            data   = resp.json()
            values = data.get("values", [])
            results.extend(
                PartnerMember(
                    account_id=str(v.get("accountId") or ""),
                    display_name=str(v.get("displayName") or ""),
                    email=str(v.get("emailAddress") or ""),
                )
                for v in values
            )
            if data.get("isLastPage", True):
                break
            start += len(values)
        results.sort(key=lambda member: member.display_name)
        logger.info(f"[파트너] org_id={org_id} 멤버 {len(results)}명")
        return results

    async def aclose(self) -> None:
        await asyncio.gather(
            self._count_cache.aclose(),
            self._issues_cache.aclose(),
        )
        await self._client.aclose()
        await self._sd_client.aclose()
