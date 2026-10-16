# backend/tests/test_snapshot_personal_data.py
import asyncio
import os
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from src.application.ports.jira_identity_history_port import JiraIdentityHistoryUnavailable
from src.application.services.snapshot_identity_backfill import backfill_snapshot_identities
from src.application.services.snapshot_personal_data import REDACTED_PERSON, aggregate_gaps, erase_snapshot_people, resolve_snapshot_account, snapshot_people
from src.domain.entities.jira_identity_history import JiraIdentityHistory, JiraUserChange, JiraUserValue
from src.domain.entities.redeployment_report import REDEPLOYMENT_START, RedeploymentReport, RedeploymentTicket
from src.domain.entities.report import NewReport
from src.domain.entities.widget import WidgetResult
from src.domain.entities.widget_data import RecentIssueDetail, RecentIssueWidgetData
from src.domain.value_objects.widget_id import WidgetId
from src.infrastructure.external.jira_identity_history_source import JiraIdentityHistorySource
from src.infrastructure.external.jira_user_identity import jira_account_id
from src.infrastructure.persistence.personal_data_snapshot_store import PersonalDataSnapshotStore
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.models import ReportORM
from src.infrastructure.persistence.redeployment_repository_impl import RedeploymentReportORM, RedeploymentRepositoryImpl
from src.infrastructure.persistence.report_repository_impl import ReportRepositoryImpl
from src.infrastructure.persistence.sla_violation_models import SlaViolationReportORM
from src.infrastructure.persistence.sla_violation_repository_impl import SlaViolationRepositoryImpl
from tests.test_sla_violation_workflow import sample_report

NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)
FIELDS = {"reporter": ("reporter",), "assignee": ("assignee",), "tac_assignee": ("customfield_12522",), "tac_team": ("customfield_10859", "customfield_12222", "assignee")}


def history(current=None, changes=(), complete=True):
    return JiraIdentityHistory("TACEA-1", NOW - timedelta(days=60), current or {"assignee": JiraUserValue("account-a", "동명이인")}, changes, complete)


class SnapshotPersonalDataTest(unittest.TestCase):
    def person(self, name="동명이인", field="assignee"):
        return next(snapshot_people({"key": "TACEA-1", field: name}, NOW))

    def test_complete_unchanged_history_verifies_same_field_name_only(self):
        self.assertEqual(("account-a", "verified"), resolve_snapshot_account(self.person(), history(), FIELDS))
        self.assertEqual((None, "name_mismatch_at_snapshot"), resolve_snapshot_account(self.person("다른 이름"), history(), FIELDS))

    def test_reassignment_after_snapshot_uses_historical_id_even_with_same_name(self):
        change = JiraUserChange("assignee", NOW + timedelta(days=1), JiraUserValue("account-a", "동명이인"), JiraUserValue("account-b", "동명이인"))
        current = {"assignee": JiraUserValue("account-b", "동명이인")}
        self.assertEqual(("account-a", "verified"), resolve_snapshot_account(self.person(), history(current, (change,)), FIELDS))

    def test_incomplete_or_discontinuous_history_is_never_guessed(self):
        self.assertEqual((None, "incomplete_history"), resolve_snapshot_account(self.person(), history(complete=False), FIELDS))
        change = JiraUserChange("assignee", NOW + timedelta(days=1), JiraUserValue("account-a", "동명이인"), JiraUserValue("account-b", "동명이인"))
        self.assertEqual((None, "unverifiable_field_history"), resolve_snapshot_account(self.person(), history(changes=(change,)), FIELDS))

    def test_tac_team_obeys_historical_precedence_instead_of_matching_another_user(self):
        current = {"customfield_10859": JiraUserValue("account-x", "다른 이름"), "customfield_12222": JiraUserValue("account-y", "동명이인"), "assignee": JiraUserValue("account-a", "동명이인")}
        self.assertEqual((None, "name_mismatch_at_snapshot"), resolve_snapshot_account(self.person(field="tac_team"), history(current), FIELDS))

    def test_refreshed_dashboard_uses_unique_issue_local_history_and_rejects_namesakes(self):
        change = JiraUserChange("assignee", NOW + timedelta(days=1), JiraUserValue("account-a", "동명이인"), JiraUserValue("account-b", "새 담당자"))
        current = {"assignee": JiraUserValue("account-b", "새 담당자")}
        self.assertEqual(("account-a", "verified"), resolve_snapshot_account(self.person(), history(current, (change,)), FIELDS, refreshed_snapshot=True))
        current["assignee"] = JiraUserValue("account-b", "동명이인")
        change = replace(change, after=current["assignee"])
        self.assertEqual((None, "ambiguous_historical_name"), resolve_snapshot_account(self.person(), history(current, (change,)), FIELDS, refreshed_snapshot=True))

    def test_duplicate_old_transition_cannot_invalidate_verified_unchanged_snapshot_user(self):
        old = JiraUserValue("account-old", "이전 담당자")
        current = JiraUserValue("account-a", "동명이인")
        changes = (
            JiraUserChange("assignee", NOW - timedelta(days=2), old, current),
            JiraUserChange("assignee", NOW - timedelta(days=2) + timedelta(milliseconds=136), old, current),
        )
        self.assertEqual(("account-a", "verified"), resolve_snapshot_account(self.person(), history({"assignee": current}, changes), FIELDS))
        earlier_person = replace(self.person(), retrieved_at=NOW - timedelta(days=3))
        self.assertEqual((None, "unverifiable_field_history"), resolve_snapshot_account(earlier_person, history({"assignee": current}, changes), FIELDS))

    def test_refreshed_snapshot_rejects_unidentified_historical_namesake(self):
        change = JiraUserChange("assignee", NOW - timedelta(days=2), JiraUserValue(None, "동명이인"), JiraUserValue("account-a", "동명이인"))
        self.assertEqual((None, "unverifiable_field_history"), resolve_snapshot_account(self.person(), history(changes=(change,)), FIELDS, refreshed_snapshot=True))

    def test_erasure_uses_ids_preserves_same_name_other_account_and_all_counts(self):
        payload = {"total": 2, "by_assignee": {"동명이인": 2}, "latest_issues": [
            {"key": "TACEA-1", "summary": "이슈 내용", "assignee": "동명이인", "assignee_account_id": "account-a", "hours": 8},
            {"key": "TACEA-2", "assignee": "동명이인", "assignee_account_id": "account-b", "hours": 4},
        ]}
        self.assertTrue(erase_snapshot_people(payload, {"account-a"}))
        self.assertEqual(REDACTED_PERSON, payload["latest_issues"][0]["assignee"])
        self.assertEqual("동명이인", payload["latest_issues"][1]["assignee"])
        self.assertEqual({REDACTED_PERSON: 1, "동명이인": 1}, payload["by_assignee"])
        self.assertEqual((2, 8, "이슈 내용"), (payload["total"], payload["latest_issues"][0]["hours"], payload["latest_issues"][0]["summary"]))
        self.assertFalse(erase_snapshot_people(payload, {"account-a"}))
        self.assertEqual(["account-b"], [person.account_id for person in snapshot_people(payload, NOW)])

    def test_unmapped_aggregate_names_are_reported_and_not_name_erased(self):
        payload = {"by_assignee": {"동명이인": 3}, "latest_issues": [{"key": "TACEA-1", "assignee": "동명이인", "assignee_account_id": "account-a"}]}
        self.assertEqual(1, aggregate_gaps(payload))
        erase_snapshot_people(payload, {"account-a"})
        self.assertEqual({"동명이인": 3}, payload["by_assignee"])

    def test_account_id_parser_tracks_first_displayed_user_and_rejects_non_users(self):
        self.assertEqual("account-a", jira_account_id([{"displayName": "A", "accountId": "account-a"}, {"displayName": "B", "accountId": "account-b"}]))
        self.assertIsNone(jira_account_id([{"name": "asset"}, {"displayName": "B", "accountId": "account-b"}]))
        self.assertIsNone(jira_account_id({"displayName": "A", "accountId": "bad/value"}))
        self.assertIsNone(jira_account_id({"displayName": "A", "accountId": "unknown"}))


class SnapshotBackfillTest(unittest.IsolatedAsyncioTestCase):
    async def test_backfill_changes_only_id_metadata_and_fetches_each_issue_once(self):
        payload = {"tickets": [{"key": "TACEA-1", "assignee": "동명이인", "reporter": "확인 불가", "summary": "원문", "elapsed_days": 123}]}
        before = deepcopy(payload)
        source = SimpleNamespace(fetch=AsyncMock(return_value=history({"assignee": JiraUserValue("account-a", "동명이인"), "reporter": JiraUserValue("account-r", "다른 보고자")})))
        result = await backfill_snapshot_identities([("sla", 3, NOW, payload)], source, FIELDS)
        self.assertEqual((1, 1, 1), (result.issues, result.verified_fields, len(result.failures)))
        self.assertEqual("account-a", payload["tickets"][0].pop("assignee_account_id"))
        self.assertEqual(before, payload)
        source.fetch.assert_awaited_once_with("TACEA-1")

    async def test_provider_failure_is_unresolved_and_programming_errors_propagate(self):
        source = SimpleNamespace(fetch=AsyncMock(side_effect=JiraIdentityHistoryUnavailable()))
        documents = [("sla", 3, NOW, {"tickets": [{"key": "TACEA-1", "assignee": "동명이인"}]})]
        result = await backfill_snapshot_identities(documents, source, FIELDS)
        self.assertEqual("jira_history_unavailable", result.failures[0]["reason"])
        source.fetch.side_effect = AssertionError("unexpected")
        with self.assertRaises(AssertionError):
            await backfill_snapshot_identities(documents, source, FIELDS)

    async def test_snapshot_store_coverage_oldest_retrieval_and_exact_row_erasure(self):
        rows = [SimpleNamespace(id=1, created_at=NOW, widgets={"w7": {"data": {"issue_details": [{"key": "TACEA-1", "reporter": "A", "reporter_account_id": "account-a", "personal_data_retrieved_at": (NOW - timedelta(days=1)).isoformat()}]}}})]
        sla_rows = [SimpleNamespace(id=2, generated_at=NOW, payload={"tickets": [{"key": "TACEA-2", "reporter": "A", "reporter_account_id": "account-a", "assignee": "unmapped"}], "count": 1})]
        session = SimpleNamespace(execute=AsyncMock(), flush=AsyncMock(), get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))
        def result(statement):
            table = str(statement)
            values = sla_rows if "sla_violation_reports" in table else [] if "redeployment_reports" in table else rows
            return Mock(scalars=lambda: Mock(all=lambda: values))
        session.execute.side_effect = result
        store = PersonalDataSnapshotStore(session)
        self.assertEqual({"known_accounts": 1, "unmapped_personal_fields": 1}, await store.coverage())
        accounts = await store.collect_accounts()
        self.assertEqual(NOW - timedelta(days=1), accounts[0].updated_at)
        self.assertEqual(2, await store.erase_personal_data(("account-a",)))
        self.assertEqual((1,), store.erased_report_ids)
        self.assertEqual((1, "unmapped"), (sla_rows[0].payload["count"], sla_rows[0].payload["tickets"][0]["assignee"]))
        self.assertEqual((), await store.collect_accounts())


class IdentityHistorySourceTest(unittest.IsolatedAsyncioTestCase):
    async def test_schema_verified_assets_and_options_do_not_become_user_history(self):
        def respond(request):
            if request.url.path.endswith("/field"):
                return httpx.Response(200, json=[{"id": "customfield_10859", "schema": {"type": "array", "items": "cmdb-object-field"}}, {"id": "customfield_12222", "schema": {"type": "option"}}])
            if request.url.path.endswith("/changelog"):
                return httpx.Response(200, json={"startAt": 0, "total": 1, "values": [{"id": "1", "created": NOW.isoformat(), "items": [{"fieldId": "customfield_10859", "from": "1", "fromString": "회사1", "to": "2", "toString": "회사2"}]}]})
            return httpx.Response(200, json={"key": "TACEA-1", "fields": {"created": (NOW - timedelta(days=5)).isoformat(), "customfield_10859": [{"objectId": "2"}], "customfield_12222": {"value": "테스트완료"}, "assignee": {"accountId": "account-a", "displayName": "동명이인"}}})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            source = JiraIdentityHistorySource("https://example.atlassian.net", client, FIELDS["tac_team"])
            await source.prepare()
            record = await source.fetch("TACEA-1")
        person = next(snapshot_people({"key": "TACEA-1", "tac_team": "동명이인"}, NOW))
        self.assertEqual(("account-a", "verified"), resolve_snapshot_account(person, record, FIELDS))

    async def test_full_history_pagination_and_truncated_pages(self):
        calls = []
        def respond(request):
            calls.append(request.url.path)
            if not request.url.path.endswith("changelog"):
                return httpx.Response(200, json={"key": "TACEA-1", "fields": {"created": (NOW - timedelta(days=5)).isoformat(), "assignee": {"accountId": "account-b", "displayName": "B"}}})
            return httpx.Response(200, json={"startAt": 0, "total": 2, "isLast": True, "values": [{"id": "1", "created": NOW.isoformat(), "items": [{"fieldId": "assignee", "from": "account-a", "fromString": "A", "to": "account-b", "toString": "B"}]}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            source = JiraIdentityHistorySource("https://example.atlassian.net", client, ("assignee",))
            with self.assertRaises(JiraIdentityHistoryUnavailable):
                await source.fetch("TACEA-1")
        self.assertEqual(2, len(calls))


class SnapshotSuppressionTest(unittest.IsolatedAsyncioTestCase):
    async def test_saved_sla_snapshot_and_return_value_suppress_deleted_account_names(self):
        engine = create_engine("sqlite:///:memory:")
        PersonalDataAccountORM.__table__.create(engine)
        SlaViolationReportORM.__table__.create(engine)
        session = Session(engine)
        try:
            session.add(PersonalDataAccountORM(account_id="account-a", oldest_retrieved_at=NOW, profile_version=2, status="closed"))
            session.commit()
            bridge = SimpleNamespace(
                get_bind=session.get_bind,
                execute=AsyncMock(side_effect=session.execute),
                add=session.add,
                flush=AsyncMock(side_effect=session.flush),
                commit=AsyncMock(side_effect=session.commit),
                rollback=AsyncMock(side_effect=session.rollback),
            )
            original = sample_report()
            ticket = replace(original.tickets[0], reporter_account_id="account-a", assignee_account_id="account-b")
            saved = await SlaViolationRepositoryImpl(bridge).save(replace(original, tickets=(ticket,)))
            self.assertEqual(REDACTED_PERSON, saved.tickets[0].reporter)
            self.assertEqual(ticket.assignee, saved.tickets[0].assignee)
            self.assertEqual((1, 1, 1), (saved.ticket_count, saved.initial_response_count, saved.resolution_count))
            stored = session.execute(select(SlaViolationReportORM)).scalar_one()
            self.assertEqual(REDACTED_PERSON, stored.payload["tickets"][0]["reporter"])
            self.assertEqual("account-a", stored.payload["tickets"][0]["reporter_account_id"])
        finally:
            session.close()
            engine.dispose()


@unittest.skipUnless(os.environ.get("PERSONAL_DATA_TEST_DATABASE_URL"), "Requires an isolated PostgreSQL PERSONAL_DATA_TEST_DATABASE_URL")
class SnapshotPostgresTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = Database(os.environ["PERSONAL_DATA_TEST_DATABASE_URL"])
        self.saved_ids = {ReportORM: [], SlaViolationReportORM: [], RedeploymentReportORM: []}
        async with self.database.session() as session:
            await session.execute(delete(PersonalDataAccountORM).where(PersonalDataAccountORM.account_id == "snapshot-account"))
            session.add(PersonalDataAccountORM(account_id="snapshot-account", oldest_retrieved_at=NOW, profile_version=2, status="closed"))

    async def asyncTearDown(self):
        async with self.database.session() as session:
            for model, ids in self.saved_ids.items():
                if ids:
                    await session.execute(delete(model).where(model.id.in_(ids)))
            await session.execute(delete(PersonalDataAccountORM).where(PersonalDataAccountORM.account_id == "snapshot-account"))
        await self.database.aclose()

    async def test_all_report_save_paths_preserve_metrics_and_return_erased_names(self):
        detail = RecentIssueDetail("TACEA-1", "summary", "개선", "할 일", 0, "2026-10-01", 15, reporter="name", reporter_account_id="snapshot-account")
        new = NewReport(NOW.date(), NOW.date(), str(NOW.date()), {WidgetId.RECENT_ISSUES: WidgetResult("최근", 1, "query", RecentIssueWidgetData([detail]))})
        async with self.database.session() as session:
            report = await ReportRepositoryImpl(session).save(new)
            self.saved_ids[ReportORM].append(report.id)
            self.assertEqual(REDACTED_PERSON, report.widgets[WidgetId.RECENT_ISSUES].data.issue_details[0].reporter)
            updated = await ReportRepositoryImpl(session).update_widgets(report.id, new)
            self.assertEqual(REDACTED_PERSON, updated.widgets[WidgetId.RECENT_ISSUES].data.issue_details[0].reporter)
        base = sample_report()
        async with self.database.session() as session:
            sla = await SlaViolationRepositoryImpl(session).save(replace(base, tickets=(replace(base.tickets[0], reporter_account_id="snapshot-account"),)))
            self.saved_ids[SlaViolationReportORM].append(sla.id)
            self.assertEqual(REDACTED_PERSON, sla.tickets[0].reporter)
            self.assertEqual(1, sla.ticket_count)
        ticket = RedeploymentTicket("TACEA-1", "summary", "개선", "할 일", False, str(NOW), None, None, None, None, None, None, (), "name", None, assignee_account_id="snapshot-account")
        async with self.database.session() as session:
            redeployment = await RedeploymentRepositoryImpl(session).save(RedeploymentReport(0, REDEPLOYMENT_START, NOW, "schedule", "query", (ticket,)))
            self.saved_ids[RedeploymentReportORM].append(redeployment.id)
            self.assertEqual(REDACTED_PERSON, redeployment.tickets[0].assignee)
        async with self.database.session() as session:
            self.assertFalse(any(item.account_id == "snapshot-account" for item in await PersonalDataSnapshotStore(session).collect_accounts()))

    async def test_erasure_write_lock_serializes_concurrent_generation(self):
        started = asyncio.Event()
        async with self.database.session() as erasure_session:
            await PersonalDataSnapshotStore(erasure_session).erase_personal_data(("snapshot-account",))
            async def generate():
                async with self.database.session() as session:
                    started.set()
                    base = sample_report()
                    saved = await SlaViolationRepositoryImpl(session).save(replace(base, tickets=(replace(base.tickets[0], reporter_account_id="snapshot-account"),)))
                    self.saved_ids[SlaViolationReportORM].append(saved.id)
                    return saved
            task = asyncio.create_task(generate())
            await started.wait()
            await asyncio.sleep(0.05)
            self.assertFalse(task.done())
        saved = await asyncio.wait_for(task, 5)
        self.assertEqual(REDACTED_PERSON, saved.tickets[0].reporter)
