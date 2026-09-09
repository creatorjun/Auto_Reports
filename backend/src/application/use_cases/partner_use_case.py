# backend/src/application/use_cases/partner_use_case.py
import asyncio
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
        organizations = await self._service_desk.get_organizations()
        if not organizations:
            return []

        members_by_org = await asyncio.gather(*(
            self._service_desk.get_members(str(org["id"]))
            for org in organizations
        ))
        organizations_with_counts = [
            {**org, "issue_count": 0}
            for org in organizations
        ]
        count_targets: list[tuple[int, str]] = []
        for index, members in enumerate(members_by_org):
            jql = self._reporter_jql(members)
            if jql:
                count_targets.append((index, jql))

        if count_targets:
            counts = await self._jira.get_issue_counts_batch([
                jql for _, jql in count_targets
            ])
            for (index, _), count in zip(count_targets, counts, strict=True):
                organizations_with_counts[index]["issue_count"] = count

        organizations_with_counts.sort(key=lambda org: (
            -org["issue_count"],
            str(org["name"]).casefold(),
            str(org["id"]),
        ))
        return organizations_with_counts

    async def get_members(self, org_id: str) -> list[dict]:
        return await self._service_desk.get_members(org_id)

    async def get_issues_by_org(self, org_id: str) -> list[dict]:
        members = await self._service_desk.get_members(org_id)
        jql = self._reporter_jql(members, order_by_created=True)
        if not jql:
            org_name = await self._service_desk.resolve_org_name(org_id)
            logger.info(f"[파트너 이슈] org_id={org_id} ({org_name}) 멤버 없음 → 0건")
            return []
        org_name = await self._service_desk.resolve_org_name(org_id)
        logger.info(f"[파트너 이슈] org={org_name}({org_id}) 멤버={len(members)}명 → reporter IN 방식")
        return await self._fetch_issues(jql)

    def _reporter_jql(
        self,
        members: list[dict],
        *,
        order_by_created: bool = False,
    ) -> str | None:
        account_ids = [
            member.get("account_id")
            for member in members
            if member.get("account_id")
        ]
        if not account_ids:
            return None
        ids_str = ", ".join(f'"{account_id}"' for account_id in account_ids)
        jql = f'project = "{self._project_key}" AND reporter IN ({ids_str})'
        return f"{jql} ORDER BY created DESC" if order_by_created else jql

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
