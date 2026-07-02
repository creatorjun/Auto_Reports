# backend/src/infrastructure/external/jira_client.py
import logging
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(email, api_token)
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def get_issue_count(self, jql: str) -> int:
        url = f"{self._base_url}/rest/api/3/search/approximate-count"
        try:
            resp = self._session.post(url, json={"jql": jql}, timeout=30)
            resp.raise_for_status()
            return resp.json().get("count", 0)
        except requests.exceptions.RequestException as e:
            logger.error(f"JQL 카운트 실패: {jql[:80]}... → {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"응답 상세: {e.response.text[:200]}")
            return 0

    def get_issues(self, jql: str, max_results: int = 200, fields: str = "") -> list[dict[str, Any]]:
        url = f"{self._base_url}/rest/api/3/search/jql"
        payload: dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "fieldsByKeys": False,
        }
        if fields:
            payload["fields"] = fields.split(",")
        try:
            resp = self._session.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json().get("issues", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"JQL 검색 실패: {jql[:80]}... → {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"응답 상세: {e.response.text[:200]}")
            return []
