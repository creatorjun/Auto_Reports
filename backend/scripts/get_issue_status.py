# backend/scripts/get_issue_status.py
import sys

from lib.jira_status_client import JiraStatusClient


def main() -> None:
    issue_key = sys.argv[1] if len(sys.argv) > 1 else "TACEA-4715"
    client = JiraStatusClient()
    status = client.get_status(issue_key)
    print(f"{issue_key}: {status}")


if __name__ == "__main__":
    main()
