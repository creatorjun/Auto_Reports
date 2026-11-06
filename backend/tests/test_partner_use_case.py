# backend/tests/test_partner_use_case.py
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.use_cases.partner_use_case import PartnerUseCase
from src.application.ports.jira_port import JiraIssue
from src.application.ports.issue_query import IssueOrder, IssueSelection
from src.domain.entities.partner import PartnerMember, PartnerOrganization


class PartnerJira:
    def __init__(self) -> None:
        self.jqls: list[IssueSelection] = []

    async def get_issue_counts_batch(self, jqls: list[IssueSelection]) -> list[int]:
        self.jqls = jqls
        counts = {
            'account-a': 17,
            'account-b': 204,
        }
        return [next(count for account_id, count in counts.items() if account_id in jql.reporters) for jql in jqls]

    async def get_issues_with_assignees(self, jql: IssueSelection, max_results: int | None) -> list[JiraIssue]:
        self.issue_limit = max_results
        return [JiraIssue(
            key="TACEA-1",
            summary="상태 필터 검증",
            issue_type="인시던트",
            status="할 일",
            created="2026-09-01T09:00:00.000+0900",
        )]


class PartnerServiceDesk:
    async def get_organizations(self) -> list[PartnerOrganization]:
        return [
            PartnerOrganization(id="1", name="가나다 파트너"),
            PartnerOrganization(id="2", name="라마바 파트너"),
            PartnerOrganization(id="3", name="이슈 없는 파트너"),
        ]

    async def get_members(self, org_id: str) -> list[PartnerMember]:
        return {
            "1": [PartnerMember("account-a", "", "")],
            "2": [PartnerMember("account-b", "", "")],
            "3": [],
        }[org_id]


class PartnerUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def test_organizations_include_full_issue_counts_in_descending_order(self) -> None:
        jira = PartnerJira()
        use_case = PartnerUseCase(
            jira=jira,
            service_desk=PartnerServiceDesk(),
            project_key="TACEA",
        )

        organizations = await use_case.get_organizations()

        self.assertEqual(
            [
                ("라마바 파트너", 204),
                ("가나다 파트너", 17),
                ("이슈 없는 파트너", 0),
            ],
            [(org.name, org.issue_count) for org in organizations],
        )
        self.assertEqual(2, len(jira.jqls))
        self.assertTrue(all(query.project == "TACEA" for query in jira.jqls))
        self.assertTrue(all(query.order == IssueOrder.NONE for query in jira.jqls))

    async def test_member_issues_keep_current_status_and_are_not_limited_to_500(self) -> None:
        jira = PartnerJira()
        use_case = PartnerUseCase(
            jira=jira,
            service_desk=PartnerServiceDesk(),
            project_key="TACEA",
        )

        issues = await use_case.get_issues_by_member("account-a")

        self.assertIsNone(jira.issue_limit)
        self.assertEqual("할 일", issues[0].status)
