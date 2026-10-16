# backend/src/infrastructure/external/jira_user_identity.py
import re


def jira_account_id(value: object) -> str | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and (item.get("displayName") or item.get("name")):
                return jira_account_id(item)
        return None
    if not isinstance(value, dict):
        return None
    account_id = value.get("accountId")
    if isinstance(account_id, str) and account_id != "unknown" and re.fullmatch(r"[A-Za-z0-9:_-]{1,128}", account_id):
        return account_id
    return None
