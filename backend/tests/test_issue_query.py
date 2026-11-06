# backend/tests/test_issue_query.py
import json
import unittest

import httpx

from src.application.ports.issue_query import IssueOrder, IssueSelection
from src.infrastructure.external.issue_query import compile_issue_query
from src.infrastructure.external.jira_client import JiraClient


class IssueQueryTest(unittest.TestCase):
    def test_existing_query_text_is_preserved(self):
        query = 'project = TAC AND status = "Closed"'
        self.assertEqual(query, compile_issue_query(query))

    def test_selection_preserves_queries_for_each_use_case(self):
        cases = (
            (IssueSelection(project="TACEA", reporters=("a", "b")),
             'project = "TACEA" AND reporter IN ("a", "b")'),
            (IssueSelection(project="TACEA", reporter="a", order=IssueOrder.NEWEST),
             'project = "TACEA" AND reporter = "a" ORDER BY created DESC'),
            (IssueSelection(project="TACEA", order=IssueOrder.NEWEST_WITH_KEY),
             'project = "TACEA" ORDER BY created DESC, key DESC'),
            (IssueSelection(project="TACEA", updated_within_minutes=9, order=IssueOrder.NEWEST_WITH_KEY),
             'project = "TACEA" AND updated >= "-9m" ORDER BY created DESC, key DESC'),
            (IssueSelection(keys=("TACEA-1", "TACEA-2"), order=IssueOrder.OLDEST_WITH_KEY),
             'issuekey IN (TACEA-1, TACEA-2) ORDER BY created ASC, issuekey ASC'),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(expected, compile_issue_query(query))

    def test_reporter_values_are_escaped_at_the_provider_boundary(self):
        self.assertEqual(
            'project = "TAC" AND reporter = "a\\\\b\\\"c"',
            compile_issue_query(IssueSelection(project="TAC", reporter='a\\b"c')),
        )

    def test_empty_and_invalid_selections_do_not_expand_to_unrestricted_queries(self):
        for selection in (
            IssueSelection(), IssueSelection(reporters=()), IssueSelection(keys=()),
            IssueSelection(keys=("T-1) OR project = OTHER",)),
            IssueSelection(project="T", updated_within_minutes=-1),
            IssueSelection(project="T", updated_within_minutes=True),
        ):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                compile_issue_query(selection)


class IssueQueryAdapterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.jira = JiraClient("https://jira.example.test", "test", "test")
        await self.jira._client.aclose()
        self.payloads = []

        def handler(request):
            self.payloads.append(json.loads(request.content))
            return httpx.Response(200, json={"issues": [], "count": 7})

        self.jira._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def asyncTearDown(self):
        await self.jira.aclose()

    async def test_all_query_entry_points_translate_before_transport(self):
        selection = IssueSelection(project="TAC", reporter="account", order=IssueOrder.NEWEST)
        with self.jira.bypass_cache(True):
            self.assertEqual([7], await self.jira.get_issue_counts_batch([selection]))
            await self.jira.get_issues(selection)
            await self.jira.get_issues_with_sla(selection)
            await self.jira.get_issues_with_assignees(selection)
            await self.jira.get_redeployment_issues(selection)
            await self.jira.get_report_chart_issues(selection, None, frozenset())
        self.assertEqual(6, len(self.payloads))
        self.assertEqual(
            {'project = "TAC" AND reporter = "account" ORDER BY created DESC'},
            {payload["jql"] for payload in self.payloads},
        )

    async def test_structured_and_text_queries_share_the_same_cache_entry(self):
        selection = IssueSelection(project="TAC")
        await self.jira.get_issue_count(selection)
        await self.jira.get_issue_count('project = "TAC"')
        await self.jira.get_issues(selection)
        await self.jira.get_issues('project = "TAC"')
        self.assertEqual(2, len(self.payloads))
