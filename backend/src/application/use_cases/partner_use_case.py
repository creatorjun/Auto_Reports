# backend/src/application/use_cases/partner_use_case.py
import logging
from datetime import datetime

from src.domain.ports.jira_port import JiraPort
from src.shared.constants import JIRA_MAX_RESULT, STAGE_MAP, SUMMARY_TRUNCATE_LEN

logger = logging.getLogger(__name__)

_TAC_ASSIGNEE_KEY = "_tac_assignee"
_QA_ASSIGNEE_KEY  = "_qa_assignee"

_ORG_FIELD_ID      = "customfield_10010"
_PARTNER_FIELD_ID  = "customfield_10303"
_ORG_NAME_FIELD_ID = "customfield_10388"


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
        project_key: str,
        tac_assignee_fid: str,
        qa_assignee_fid: str,
    ):
        self._jira            = jira
        self._project_key     = project_key
        self._tac_assignee_fid = tac_assignee_fid
        self._qa_assignee_fid  = qa_assignee_fid

    async def get_organizations(self) -> list[dict]:
        jql = (
            f'project = "{self._project_key}" '
            f'AND "파트너사" is not EMPTY '
            f'ORDER BY created DESC'
        )
        fields_str = f"reporter,{_PARTNER_FIELD_ID},{_ORG_NAME_FIELD_ID}"
        issues = await self._jira.get_issues(
            jql, max_results=JIRA_MAX_RESULT, fields=fields_str
        )

        org_map: dict[str, dict] = {}
        for issue in issues:
            f = issue.get("fields") or {}

            partners = f.get(_PARTNER_FIELD_ID) or []
            if isinstance(partners, dict):
                partners = [partners]

            org_name_raw = f.get(_ORG_NAME_FIELD_ID, "")
            org_name = ""
            if isinstance(org_name_raw, str):
                org_name = org_name_raw
            elif isinstance(org_name_raw, dict):
                org_name = org_name_raw.get("value") or org_name_raw.get("name") or ""

            for p in partners:
                if not isinstance(p, dict):
                    continue
                pid   = str(p.get("objectId") or p.get("id") or "")
                pname = p.get("name") or org_name or pid
                if not pid:
                    continue

                if pid not in org_map:
                    org_map[pid] = {"id": pid, "name": pname, "_members": {}}

                reporter = f.get("reporter") or {}
                account_id = reporter.get("accountId", "")
                display    = reporter.get("displayName", "")
                if account_id and account_id not in org_map[pid]["_members"]:
                    org_map[pid]["_members"][account_id] = display

        result = []
        for org in sorted(org_map.values(), key=lambda x: x["name"]):
            members = [
                {"account_id": aid, "display_name": dname}
                for aid, dname in sorted(org["_members"].items(), key=lambda x: x[1])
            ]
            result.append({"id": org["id"], "name": org["name"], "members": members})

        logger.info(f"[파트너 관리] 조직 {len(result)}개 수집")
        return result

    async def get_issues_by_org(self, org_name: str) -> list[dict]:
        jql = (
            f'project = "{self._project_key}" '
            f'AND "회사명" = "{org_name}" '
            f'ORDER BY created DESC'
        )
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
        logger.info(f"[파트너 이슈] JQL={jql[:60]} → {len(result)}건")
        return result
