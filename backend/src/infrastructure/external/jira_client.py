import logging
from typing import Any

import httpx

from src.domain.ports.jira_port import JiraPort

logger = logging.getLogger(__name__)

SLA_SCHEMA_TYPE = "sd-servicelevelagreement"


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
        self._sla_field_ids_cache: dict[str, str] | None = None

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

    async def get_sla_field_ids(self) -> dict[str, str]:
        """
        schema.type == 'sd-servicelevelagreement' 인 필드만 반환.
        {'\ud544\ub4dc \uc774\ub984': 'customfield_NNNNN'}
        """
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

    async def aclose(self) -> None:
        await self._client.aclose()
