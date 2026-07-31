# backend/src/infrastructure/external/jira_client.py
import asyncio
import logging
from typing import Any

import httpx

from src.domain.ports.jira_port import JiraPort
from src.shared.cache import LruCache
from src.shared.constants import (
    JIRA_MAX_RESULT
)

logger = logging.getLogger(__name__)

SLA_SCHEMA_TYPE = "sd-servicelevelagreement"
_JIRA_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
_JIRA_LIMITS  = httpx.Limits(max_connections=30, max_keepalive_connections=15)

_SLA_INITIAL_KEY    = "_sla_initial"
_SLA_RESOLUTION_KEY = "_sla_resolution"
_TAC_ASSIGNEE_KEY   = "_tac_assignee"
_QA_ASSIGNEE_KEY    = "_qa_assignee"

_FETCH_PAGE_SIZE          = 100
_PARALLEL_TOTAL_THRESHOLD = 400

_COUNT_CACHE_MAXSIZE  = 256
_COUNT_CACHE_TTL      = 600.0
_COUNT_CACHE_STALE    = 120.0


class JiraClient(JiraPort):
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        sla_initial_response_field_id: str = "",
        sla_resolution_field_id: str = "",
        jira_tac_assignee_field_id: str = "",
        jira_qa_assignee_field_id: str = "",
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
        self._sla_field_ids_cache: dict[str, str] | None = None
        self._sla_initial_fid    = sla_initial_response_field_id
        self._sla_resolution_fid = sla_resolution_field_id
        self._tac_assignee_fid   = jira_tac_assignee_field_id
        self._qa_assignee_fid    = jira_qa_assignee_field_id

        self._count_cache: LruCache[str, int] = LruCache(
            maxsize=_COUNT_CACHE_MAXSIZE,
            ttl_seconds=_COUNT_CACHE_TTL,
            stale_ttl_seconds=_COUNT_CACHE_STALE,
        )

    async def get_issue_count(self, jql: str) -> int:
        cached = await self._count_cache.async_get(jql)
        if cached is not None:
            logger.debug(f"[cache-hit] count: {jql[:60]}")
            return cached

        url = f"{self._base_url}/rest/api/3/search/approximate-count"
        try:
            resp = await self._client.post(url, json={"jql": jql})
            resp.raise_for_status()
            count = resp.json().get("count", 0)
        except httpx.HTTPError as e:
            logger.error(f"JQL 카운트 실패: {jql[:80]}... -> {e}")
            if isinstance(e, httpx.HTTPStatusError):
                logger.error(f"응답 상세: {e.response.text[:200]}")
            count = 0

        await self._count_cache.async_set(jql, count)
        return count

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

    async def _fetch_page_by_start(
        self,
        jql: str,
        fields: list[str] | None,
        start_at: int,
        page_size: int,
    ) -> list[dict[str, Any]]:
        url = f"{self._base_url}/rest/api/3/search/jql"
        payload: dict[str, Any] = {
            "jql": jql,
            "maxResults": page_size,
            "startAt": start_at,
        }
        if fields:
            payload["fields"] = fields
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("issues", [])
        except httpx.HTTPError as e:
            logger.error(f"JQL 병렬 페이지 실패 (startAt={start_at}): {jql[:80]}... -> {e}")
            return []

    async def get_issues(
        self,
        jql: str,
        max_results: int = JIRA_MAX_RESULT,
        fields: str = "",
    ) -> list[dict[str, Any]]:
        field_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else None
        page_size = min(_FETCH_PAGE_SIZE, max_results)

        first_page, first_token = await self._fetch_page(jql, field_list, None, page_size)
        logger.info(f"JQL 첫 페이지 수신: {len(first_page)}건, nextPageToken={first_token}")

        if not first_page:
            return []

        if len(first_page) >= max_results:
            return first_page[:max_results]

        total = await self.get_issue_count(jql)
        fetch_count = min(total, max_results)
        logger.info(f"JQL 전체 건수: {total}, 수집 목표: {fetch_count}")

        if first_token is None:
            if total <= len(first_page):
                return first_page
            offsets = list(range(len(first_page), fetch_count, page_size))
            logger.info(f"JQL startAt 방식 수집: pages={len(offsets)}")
            tasks = [
                self._fetch_page_by_start(jql, field_list, offset, page_size)
                for offset in offsets
            ]
            pages = await asyncio.gather(*tasks)
            all_issues = list(first_page)
            for page in pages:
                all_issues.extend(page)
            logger.info(f"JQL startAt 수집 완료: 누적={len(all_issues)}건")
            return all_issues[:max_results]

        if total < _PARALLEL_TOTAL_THRESHOLD:
            all_issues = list(first_page)
            next_token: str | None = first_token
            while next_token and len(all_issues) < max_results:
                page, next_token = await self._fetch_page(jql, field_list, next_token, page_size)
                all_issues.extend(page)
                logger.info(f"JQL 순차 페이지: 수신={len(page)}, 누적={len(all_issues)}")
                if not page:
                    break
            return all_issues[:max_results]

        remaining_start = page_size
        offsets = list(range(remaining_start, fetch_count, page_size))
        logger.info(f"JQL 병렬 페이지 fetch: total={total}, pages={len(offsets)+1}")
        tasks = [
            self._fetch_page_by_start(jql, field_list, offset, page_size)
            for offset in offsets
        ]
        parallel_pages = await asyncio.gather(*tasks)
        all_issues = list(first_page)
        for page in parallel_pages:
            all_issues.extend(page)
        logger.info(f"JQL 병렬 수집 완료: 누적={len(all_issues)}건")
        return all_issues[:max_results]

    async def get_issues_with_sla(
        self,
        jql: str,
        max_results: int = JIRA_MAX_RESULT,
        extra_fields: str = "",
    ) -> list[dict[str, Any]]:
        base = "summary,issuetype,status,created,resolutiondate"
        sla_part = ",".join(filter(None, [self._sla_initial_fid, self._sla_resolution_fid]))
        fields_str = ",".join(filter(None, [base, sla_part, extra_fields]))
        issues = await self.get_issues(jql, max_results=max_results, fields=fields_str)
        for issue in issues:
            f = issue.get("fields") or {}
            f[_SLA_INITIAL_KEY]    = f.get(self._sla_initial_fid)
            f[_SLA_RESOLUTION_KEY] = f.get(self._sla_resolution_fid)
        return issues

    async def get_issues_with_assignees(
        self,
        jql: str,
        max_results: int = JIRA_MAX_RESULT,
        extra_fields: str = "",
    ) -> list[dict[str, Any]]:
        base = "summary,issuetype,status,created,reporter,assignee"
        assignee_part = ",".join(filter(None, [self._tac_assignee_fid, self._qa_assignee_fid]))
        fields_str = ",".join(filter(None, [base, assignee_part, extra_fields]))
        issues = await self.get_issues(jql, max_results=max_results, fields=fields_str)
        for issue in issues:
            f = issue.get("fields") or {}
            f[_TAC_ASSIGNEE_KEY] = f.get(self._tac_assignee_fid)
            f[_QA_ASSIGNEE_KEY]  = f.get(self._qa_assignee_fid)
        return issues

    async def get_sla_field_ids(self) -> dict[str, str]:
        if self._sla_field_ids_cache is not None:
            return self._sla_field_ids_cache

        url = f"{self._base_url}/rest/api/3/field"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            all_fields = resp.json()
        except httpx.HTTPError as e:
            logger.error(f"field 목록 조회 실패: {e}")
            return {}

        result: dict[str, str] = {}
        for f in all_fields:
            schema     = f.get("schema") or {}
            field_type = schema.get("type", "")
            field_id   = f.get("id", "")
            field_name = f.get("name", "")
            if (
                field_type == SLA_SCHEMA_TYPE
                and field_id.startswith("customfield_")
                and field_name
            ):
                result[field_name] = field_id
                logger.info(f"SLA 필드 발견: '{field_name}' = {field_id}")

        if not result:
            for f in all_fields:
                schema      = f.get("schema") or {}
                custom_type = schema.get("custom", "")
                field_id    = f.get("id", "")
                field_name  = f.get("name", "")
                if (
                    "sd-sla" in custom_type.lower()
                    and field_id.startswith("customfield_")
                    and field_name
                ):
                    result[field_name] = field_id
                    logger.info(f"SLA 필드 (fallback): '{field_name}' = {field_id}")

        if not result:
            logger.error("SLA 필드를 하나도 발견하지 못했습니다!")

        self._sla_field_ids_cache = result
        return result

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
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

        results: list[dict[str, Any]] = []

        if isinstance(jira_resp, httpx.Response):
            try:
                jira_resp.raise_for_status()
                for issue in jira_resp.json().get("issues", []):
                    fields = issue.get("fields", {})
                    results.append({
                        "type": "jira",
                        "key": issue.get("key", ""),
                        "title": fields.get("summary", ""),
                        "status": (fields.get("status") or {}).get("name", ""),
                        "issue_type": (fields.get("issuetype") or {}).get("name", ""),
                        "url": f"{self._base_url}/browse/{issue.get('key', '')}",
                    })
            except httpx.HTTPError as e:
                logger.error(f"Jira 검색 실패: {e}")
        else:
            logger.error(f"Jira 검색 실패: {jira_resp}")

        if isinstance(confluence_resp, httpx.Response):
            try:
                confluence_resp.raise_for_status()
                for page in confluence_resp.json().get("results", []):
                    space_key = (page.get("space") or {}).get("key", "")
                    results.append({
                        "type": "confluence",
                        "key": page.get("id", ""),
                        "title": page.get("title", ""),
                        "status": (page.get("space") or {}).get("name", ""),
                        "issue_type": page.get("type", "page"),
                        "url": f"{self._base_url}/wiki/spaces/{space_key}/pages/{page.get('id', '')}",
                    })
            except httpx.HTTPError as e:
                logger.warning(f"Confluence 검색 실패 (옵션): {e}")
        else:
            logger.warning(f"Confluence 검색 실패 (옵션): {confluence_resp}")

        results.sort(key=lambda x: x["type"])
        return results[:limit]

    async def aclose(self) -> None:
        await self._client.aclose()
