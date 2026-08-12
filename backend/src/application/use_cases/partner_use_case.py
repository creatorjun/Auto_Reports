# backend/src/application/use_cases/partner_use_case.py
import logging
from datetime import datetime

from src.application.ports.jira_port import JiraPort
from src.application.ports.service_desk_port import ServiceDeskPort
from src.domain.constants import JIRA_MAX_RESULT, STAGE_MAP, SUMMARY_TRUNCATE_LEN

logger = logging.getLogger(__name__)

_TAC_ASSIGNEE_KEY  = "_tac_assignee"
_QA_ASSIGNEE_KEY   = "_qa_assignee"


def _display_name(value: object) -> str:
    if isinstance(value, list):
        for item in value:
            name = _display_name(item)
            if name:
                return name
        return ""
    if isinstance(value, dict):
        return value.get("displayName") or value.get("name") or ""
    return ""


def _pick_user(fields: dict, *keys: str) -> str:
    for k in keys:
        name = _display_name(fields.get(k))
        if name:
            return name
    return "미지정"


def _build_issue(issue: dict, now_ts: datetime) -> dict:
    fields      = issue.get("fields") or {}
    created     = fields.get("created", "")
    status_name = (fields.get("status") or {}).get("name", "기타")
    elapsed     = (now_ts - datetime.fromisoformat(created[:19])).days if created else 0
    reporter    = _pick_user(fields, "reporter")
    tac_team    = _pick_user(fields, _TAC_ASSIGNEE_KEY, _QA_ASSIGNEE_KEY, "assignee")
    return {
        "key":          issue.get("key", ""),
        "summary":      (fields.get("summary") or "")[:SUMMARY_TRUNCATE_LEN],
        "type":         (fields.get("issuetype") or {}).get("name", "기타"),
        "status":       status_name,
        "stage_index":  STAGE_MAP.get(status_name, 0),
        "created":      created[:16].replace("T", " "),
        "elapsed_days": elapsed,
        "reporter":     reporter,
        "tac_team":     tac_team,
    }


class PartnerUseCase:
    def __init__(
        self,
        jira: JiraPort,
        service_desk: ServiceDeskPort,
        project_key: str,
        tac_assignee_fid: str,
        qa_assignee_fid: str,
    ):
        self._jira             = jira
        self._service_desk     = service_desk
        self._project_key      = project_key
        self._tac_assignee_fid = tac_assignee_fid
        self._qa_assignee_fid  = qa_assignee_fid

    async def get_organizations(self) -> list[dict]:
        return await self._service_desk.get_organizations()

    async def get_members(self, org_id: str) -> list[dict]:
        return await self._service_desk.get_members(org_id)

    async def get_issues_by_org(self, org_id: str) -> list[dict]:
        members = await self._service_desk.get_members(org_id)
        if not members:
            org_name = await self._service_desk.resolve_org_name(org_id)
            logger.info(f"[파트너 이슈] org_id={org_id} ({org_name}) 멤버 없음 → 0건")
            return []

        account_ids = [m["account_id"] for m in members if m["account_id"]]
        if not account_ids:
            return []

        ids_str  = ", ".join(f'"{aid}"' for aid in account_ids)
        org_name = await self._service_desk.resolve_org_name(org_id)
        jql = (
            f'project = "{self._project_key}" '
            f'AND reporter IN ({ids_str}) '
            f'ORDER BY created DESC'
        )
        logger.info(f"[파트너 이슈] org={org_name}({org_id}) 멤버={len(account_ids)}명 → reporter IN 방식")
        return await self._fetch_issues(jql)

    async def get_issues_by_member(self, account_id: str) -> list[dict]:
        jql = (
            f'project = "{self._project_key}" '
            f'AND reporter = "{account_id}" '
            f'ORDER BY created DESC'
        )
        return await self._fetch_issues(jql)

    async def _fetch_issues(self, jql: str) -> list[dict]:
        base_fields  = "summary,issuetype,status,created,reporter,assignee"
        extra_fields = ",".join(filter(None, [self._tac_assignee_fid, self._qa_assignee_fid]))
        fields_str   = ",".join(filter(None, [base_fields, extra_fields]))

        issues = await self._jira.get_issues(
            jql, max_results=JIRA_MAX_RESULT, fields=fields_str
        )
        for issue in issues:
            f = issue.get("fields") or {}
            f[_TAC_ASSIGNEE_KEY] = f.get(self._tac_assignee_fid)
            f[_QA_ASSIGNEE_KEY]  = f.get(self._qa_assignee_fid)

        now_ts = datetime.now()
        result = [_build_issue(i, now_ts) for i in issues]
        logger.info(f"[파트너 이슈] JQL={jql[:80]} → {len(result)}건")
        return result
