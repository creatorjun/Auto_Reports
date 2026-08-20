# scripts/get_issue_status.py
import os
import sys

import requests
from requests.auth import HTTPBasicAuth

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_TOKEN    = os.environ["JIRA_API_TOKEN"]


def get_issue_status(issue_key: str) -> str:
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
    params = {"fields": "status"}
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}

    response = requests.get(url, params=params, auth=auth, headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()
    return data["fields"]["status"]["name"]


def main() -> None:
    issue_key = sys.argv[1] if len(sys.argv) > 1 else "TACEA-4715"
    status = get_issue_status(issue_key)
    print(f"{issue_key}: {status}")


if __name__ == "__main__":
    main()