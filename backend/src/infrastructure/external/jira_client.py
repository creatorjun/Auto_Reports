# backend/src/infrastructure/external/jira_client.py
import asyncio
import logging
from typing import Any

import httpx

from src.domain.ports.jira_port import JiraPort
from src.shared.constants import JIRA_MAX_RESULTS_DEFAULT

logger = logging.getLogger(__name__)

SLA_SCHEMA_TYPE = "sd-servicelevelagreement"
_JIRA_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
_JIRA_LIMITS  = httpx.Limits(max_connections=30, max_keepalive_connections=15)

_SLA_INITIAL_KEY    = "_sla_initial"
_SLA_RESOLUTION_KEY = "_sla_resolution"
_TAC_ASSIGNEE_KEY   = "_tac_assignee"
_QA_ASSIGNEE_KEY    = "_qa_assignee"


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

    async def get_issue_count(self, jql: str) -> int:
        url = f"{self._base_url}/rest/api/3/search/approximate-count"
        try:
            resp = await self._client.post(url, json={"jql": jql})
            resp.raise_for_status()
            return resp.json().get("count", 0)
        except httpx.HTTPError as e:
            logger.error(f"JQL 카운트 실패: {jql[:80]}... -> {e}")
            if isinstance(e, httpx.HTTPStatusError):
                logger.error(f"응답 상세: {e.response.text[:200]}")
            return 0

    async def get_issues(
        self,
        jql: str,
        max_results: int = JIRA_MAX_RESULTS_DEFAULT,
        fields: str = "",
    ) -> list[dict[str, Any]]:
        url = f"{self._base_url}/rest/api/3/search/jql"
        payload: dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "fieldsByKeys": False,
        }
        if fields:
            payload["fields"] = [f.strip() for f in fields.split(",") if f.strip()]
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("issues", [])
        except httpx.HTTPError as e:
            logger.error(f"JQL 검색 실패: {jql[:80]}... -> {e}")
            if isinstance(e, httpx.HTTPStatusError):
                logger.error(f"응답 상세: {e.response.text[:200]}")
            return []

    async def get_issues_with_sla(
        self,
        jql: str,
        max_results: int = 500,
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
        max_results: int = 200,
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
