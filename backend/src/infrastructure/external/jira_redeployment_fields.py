# backend/src/infrastructure/external/jira_redeployment_fields.py
import re


REDEPLOYMENT_FLAG_FIELD = "customfield_11819"
REDEPLOYMENT_MONTH_FIELD = "customfield_12421"


def jql_field(field_id: str) -> str:
    match = re.fullmatch(r"customfield_([0-9]+)", field_id)
    if match is None:
        raise ValueError("Invalid Jira custom field identifier")
    return f"cf[{match.group(1)}]"
