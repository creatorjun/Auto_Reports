# backend/scripts/lib/jira_status_client.py
import httpx

from lib.env_loader import get_env


class JiraStatusClient:
    def __init__(self) -> None:
        self._base_url = get_env("JIRA_BASE_URL").rstrip("/")
        self._auth = (get_env("JIRA_EMAIL"), get_env("JIRA_API_TOKEN"))
        self._headers = {"Accept": "application/json"}

    def get_status(self, issue_key: str) -> str:
        url = f"{self._base_url}/rest/api/3/issue/{issue_key}"
        with httpx.Client(auth=self._auth, headers=self._headers, timeout=10.0) as client:
            response = client.get(url, params={"fields": "status"})
            response.raise_for_status()
        return response.json()["fields"]["status"]["name"]
