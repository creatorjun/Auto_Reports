# backend/src/infrastructure/external/jira_client.py
import logging
from typing import Any

import httpx

from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)


class JiraClient(JiraPort):
    def __init__(self, base_url: str, email: str, api_token: str):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            auth=(email, api_token),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    async def get_issue_count(self, jql: str) -> int:
        url = f"{self._base_url}/rest/api/3/search/approximate-count"
        try:
            resp = await self._client.post(url, json={"jql": jql})
            resp.raise_for_status()
            return resp.json().get("count", 0)
        except httpx.HTTPError as e:
            logger.error(f"JQL 카운트 실패: {jql[:80]}... → {e}")
            if isinstance(e, httpx.HTTPStatusError):
                logger.error(f"응답 상세: {e.response.text[:200]}")
            return 0

    async def get_issues(
        self,
        jql: str,
        max_results: int = 200,
        fields: str = "",
    ) -> list[dict[str, Any]]:
        url = f"{self._base_url}/rest/api/3/search/jql"
        payload: dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "fieldsByKeys": False,
        }
        if fields:
            payload["fields"] = fields.split(",")
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("issues", [])
        except httpx.HTTPError as e:
            logger.error(f"JQL 검색 실패: {jql[:80]}... → {e}")
            if isinstance(e, httpx.HTTPStatusError):
                logger.error(f"응답 상세: {e.response.text[:200]}")
            return []

    async def get_issue_changelog(
        self,
        issue_key: str,
    ) -> list[dict[str, Any]]:
        """이슈 changelog 전체 반환 (상태 전환 이력)"""
        url = f"{self._base_url}/rest/api/3/issue/{issue_key}/changelog"
        histories: list[dict[str, Any]] = []
        start = 0
        while True:
            try:
                resp = await self._client.get(url, params={"startAt": start, "maxResults": 100})
                resp.raise_for_status()
                body = resp.json()
                values = body.get("values", [])
                histories.extend(values)
                if len(values) < 100:
                    break
                start += len(values)
            except httpx.HTTPError as e:
                logger.error(f"changelog 조회 실패: {issue_key} → {e}")
                break
        return histories

    async def aclose(self) -> None:
        await self._client.aclose()
