# backend/src/application/use_cases/partner_use_case.py
import logging
from datetime import datetime

import httpx

from src.domain.ports.jira_port import JiraPort
from src.shared.constants import JIRA_MAX_RESULT, STAGE_MAP, SUMMARY_TRUNCATE_LEN

logger = logging.getLogger(__name__)

_TAC_ASSIGNEE_KEY  = "_tac_assignee"
_QA_ASSIGNEE_KEY   = "_qa_assignee"
_COMPANY_FIELD_ID  = "customfield_11023"

_SD_TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)
_SD_HEADERS = {
    "Accept": "application/json",
    "X-ExperimentalApi": "opt-in",
}


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
        jira_base_url: str,
        jira_email: str,
        jira_api_token: str,
    ):
        self._jira             = jira
        self._project_key      = project_key
        self._tac_assignee_fid = tac_assignee_fid
        self._qa_assignee_fid  = qa_assignee_fid
        self._sd_client = httpx.AsyncClient(
            base_url=jira_base_url.rstrip("/"),
            auth=(jira_email, jira_api_token),
            headers=_SD_HEADERS,
            timeout=_SD_TIMEOUT,
        )
        self._org_name_cache: dict[str, str] = {}

    async def get_organizations(self) -> list[dict]:
        results, start = [], 0
        while True:
            resp = await self._sd_client.get(
                "/rest/servicedeskapi/organization",
                params={"start": start, "limit": 50},
            )
            resp.raise_for_status()
            data   = resp.json()
            values = data.get("values", [])
            for v in values:
                if v.get("id") and v.get("name"):
                    oid  = str(v["id"])
                    name = v["name"]
                    results.append({"id": oid, "name": name})
                    self._org_name_cache[oid] = name
            if data.get("isLastPage", True):
                break
            start += len(values)

        results.sort(key=lambda x: x["name"])
        logger.info(f"[파트너] 조직 {len(results)}개")
        return results

    async def _resolve_org_name(self, org_id: str) -> str:
        if org_id in self._org_name_cache:
            return self._org_name_cache[org_id]
        resp = await self._sd_client.get(f"/rest/servicedeskapi/organization/{org_id}")
        resp.raise_for_status()
        name = resp.json().get("name", "")
        self._org_name_cache[org_id] = name
        return name

    async def get_members(self, org_id: str) -> list[dict]:
        results, start = [], 0
        while True:
            resp = await self._sd_client.get(
                f"/rest/servicedeskapi/organization/{org_id}/user",
                params={"start": start, "limit": 50},
            )
            resp.raise_for_status()
            data   = resp.json()
            values = data.get("values", [])
            results.extend(
                {
                    "account_id":   v.get("accountId", ""),
                    "display_name": v.get("displayName", ""),
                    "email":        v.get("emailAddress", ""),
                }
                for v in values
            )
            if data.get("isLastPage", True):
                break
            start += len(values)

        results.sort(key=lambda x: x["display_name"])
        logger.info(f"[파트너] org_id={org_id} 멤버 {len(results)}명")
        return results

    async def get_issues_by_org(self, org_id: str) -> list[dict]:
        org_name = await self._resolve_org_name(org_id)
        if not org_name:
            logger.warning(f"[파트너] org_id={org_id} 이름 불명 → 빈 결과 반환")
            return []
        jql = (
            f'project = "{self._project_key}" '
            f'AND "{_COMPANY_FIELD_ID}" = "{org_name}" '
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
        logger.info(f"[파트너 이슈] JQL={jql[:80]} → {len(result)}건")
        return result

    async def aclose(self) -> None:
        await self._sd_client.aclose()
