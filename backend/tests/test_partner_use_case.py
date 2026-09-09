# backend/tests/test_partner_use_case.py
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.use_cases.partner_use_case import PartnerUseCase


class PartnerJira:
    def __init__(self) -> None:
        self.jqls: list[str] = []

    async def get_issue_counts_batch(self, jqls: list[str]) -> list[int]:
        self.jqls = jqls
        counts = {
            '"account-a"': 17,
            '"account-b"': 204,
        }
        return [next(count for account_id, count in counts.items() if account_id in jql) for jql in jqls]


class PartnerServiceDesk:
    async def get_organizations(self) -> list[dict]:
        return [
            {"id": "1", "name": "가나다 파트너"},
            {"id": "2", "name": "라마바 파트너"},
            {"id": "3", "name": "이슈 없는 파트너"},
        ]

    async def get_members(self, org_id: str) -> list[dict]:
        return {
            "1": [{"account_id": "account-a"}],
            "2": [{"account_id": "account-b"}],
            "3": [],
        }[org_id]


class PartnerUseCaseTest(unittest.IsolatedAsyncioTestCase):
    async def test_organizations_include_full_issue_counts_in_descending_order(self) -> None:
        jira = PartnerJira()
        use_case = PartnerUseCase(
            jira=jira,
            service_desk=PartnerServiceDesk(),
            project_key="TACEA",
            tac_assignee_fid="",
            qa_assignee_fid="",
        )

        organizations = await use_case.get_organizations()

        self.assertEqual(
            [
                ("라마바 파트너", 204),
                ("가나다 파트너", 17),
                ("이슈 없는 파트너", 0),
            ],
            [(org["name"], org["issue_count"]) for org in organizations],
        )
        self.assertEqual(2, len(jira.jqls))
        self.assertTrue(all('project = "TACEA"' in jql for jql in jira.jqls))
        self.assertTrue(all("ORDER BY" not in jql for jql in jira.jqls))
