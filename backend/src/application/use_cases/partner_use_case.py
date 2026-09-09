# backend/src/application/use_cases/partner_use_case.py
import asyncio
import logging
from dataclasses import replace
from datetime import datetime

from src.application.ports.jira_port import JiraIssue, JiraPort
from src.application.ports.service_desk_port import ServiceDeskPort
from src.domain.constants import STAGE_MAP, SUMMARY_TRUNCATE_LEN
from src.domain.entities.partner import PartnerIssue, PartnerMember, PartnerOrganization

logger = logging.getLogger(__name__)

def _build_issue(issue: JiraIssue, now_ts: datetime) -> PartnerIssue:
    created = issue.created
    status_name = issue.status or "기타"
    elapsed     = (now_ts - datetime.fromisoformat(created[:19])).days if created else 0
    return PartnerIssue(
        key=issue.key,
        summary=issue.summary[:SUMMARY_TRUNCATE_LEN],
        type=issue.issue_type or "기타",
        status=status_name,
        stage_index=STAGE_MAP.get(status_name, 0),
        created=created[:16].replace("T", " "),
        elapsed_days=elapsed,
        reporter=issue.reporter or "미지정",
        tac_team=(
            issue.tac_assignee
            or issue.qa_assignee
            or issue.assignee
            or "미지정"
        ),
    )


class PartnerUseCase:
    def __init__(
        self,
        jira: JiraPort,
        service_desk: ServiceDeskPort,
        project_key: str,
    ):
        self._jira             = jira
        self._service_desk     = service_desk
        self._project_key      = project_key

    async def get_organizations(self) -> list[PartnerOrganization]:
        organizations = await self._service_desk.get_organizations()
        if not organizations:
            return []

        members_by_org = await asyncio.gather(*(
            self._service_desk.get_members(org.id)
            for org in organizations
        ))
        organizations_with_counts = [
            replace(org, issue_count=0)
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
                organizations_with_counts[index] = replace(
                    organizations_with_counts[index],
                    issue_count=count,
                )

        organizations_with_counts.sort(key=lambda org: (
            -org.issue_count,
            org.name.casefold(),
            org.id,
        ))
        return organizations_with_counts

    async def get_members(self, org_id: str) -> list[PartnerMember]:
        return await self._service_desk.get_members(org_id)

    async def get_issues_by_org(self, org_id: str) -> list[PartnerIssue]:
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
        members: list[PartnerMember],
        *,
        order_by_created: bool = False,
    ) -> str | None:
        account_ids = [
            member.account_id
            for member in members
            if member.account_id
        ]
        if not account_ids:
            return None
        ids_str = ", ".join(f'"{account_id}"' for account_id in account_ids)
        jql = f'project = "{self._project_key}" AND reporter IN ({ids_str})'
        return f"{jql} ORDER BY created DESC" if order_by_created else jql

    async def get_issues_by_member(self, account_id: str) -> list[PartnerIssue]:
        jql = (
            f'project = "{self._project_key}" '
            f'AND reporter = "{account_id}" '
            f'ORDER BY created DESC'
        )
        return await self._fetch_issues(jql)

    async def _fetch_issues(self, jql: str) -> list[PartnerIssue]:
        issues = await self._jira.get_issues_with_assignees(
            jql,
            max_results=None,
        )
        now_ts = datetime.now()
        result = [_build_issue(i, now_ts) for i in issues]
        logger.info(f"[파트너 이슈] JQL={jql[:80]} → {len(result)}건")
        return result
