# backend/tests/test_personal_data_reporting.py
import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx

from src.application.ports.personal_data_port import PersonalDataReportingFailure
from src.application.use_cases.report_personal_data import ReportPersonalDataUseCase
from src.domain.entities.personal_data import PersonalDataAccount, PersonalDataAction, PersonalDataProfile, PersonalDataReportResult
from src.infrastructure.external.personal_data_client import AtlassianPersonalDataClient
from src.infrastructure.security.personal_data_cipher import PersonalDataCipher

NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


class PersonalDataClientTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.grants = AsyncMock()
        self.grants.get_reporting_grant.return_value = ("owner", "sensitive-old-refresh")
        self.accounts = (PersonalDataAccount("account-one", NOW),)
        self.requests = []
        self.response = httpx.Response(204)

    async def handler(self, request):
        self.requests.append(request)
        if request.url.host == "auth.atlassian.com":
            return httpx.Response(200, json={"access_token": "sensitive-access", "refresh_token": "rotated-refresh"})
        self.grants.save_reporting_grant.assert_awaited_once_with("owner", "rotated-refresh")
        return self.response

    def client(self, handler=None):
        return AtlassianPersonalDataClient("client", "secret", self.grants, httpx.MockTransport(handler or self.handler))

    async def test_owner_rotation_is_saved_before_reporting_and_default_cycle_is_seven_days(self):
        result = await self.client().report(self.accounts)
        self.assertEqual(PersonalDataReportResult((), 604800), result)
        self.assertEqual("refresh_token", json.loads(self.requests[0].content)["grant_type"])
        self.assertEqual("https://api.atlassian.com/app/report-accounts/", str(self.requests[1].url))
        self.assertEqual({"accounts": [{"accountId": "account-one", "updatedAt": "2026-10-16T00:00:00Z"}]}, json.loads(self.requests[1].content))
        self.assertEqual("Bearer sensitive-access", self.requests[1].headers["authorization"])
        self.assertNotIn("sensitive", str(self.requests[1].url))

    async def test_cycle_header_is_days_and_valid_actions_are_preserved(self):
        self.response = httpx.Response(200, headers={"Cycle-Period": "15"}, json={"accounts": [{"accountId": "account-one", "status": "closed"}]})
        result = await self.client().report(self.accounts)
        self.assertEqual(15 * 86400, result.cycle_period_seconds)
        self.assertEqual((PersonalDataAction("account-one", "closed"),), result.actions)

    async def test_invalid_or_foreign_action_payloads_never_trigger_erasure(self):
        for payload in (
            [], {}, {"accounts": "invalid"}, {"accounts": [{"accountId": "someone-else", "status": "closed"}]},
            {"accounts": [{"accountId": "account-one", "status": "unknown"}]},
            {"accounts": [{"accountId": "account-one", "status": "updated"}] * 2},
        ):
            self.grants.save_reporting_grant.reset_mock()
            self.response = httpx.Response(200, json=payload)
            with self.assertRaises(PersonalDataReportingFailure):
                await self.client().report(self.accounts)

    async def test_rate_limit_retains_rotated_credential_and_exact_retry_delay(self):
        self.response = httpx.Response(429, headers={"Retry-After": "1800"}, json={"private": "provider-details"})
        with self.assertRaises(PersonalDataReportingFailure) as raised:
            await self.client().report(self.accounts)
        self.assertEqual(1800, raised.exception.retry_after_seconds)
        self.assertEqual("reporting_rate_limited", str(raised.exception))
        self.grants.save_reporting_grant.assert_awaited_once_with("owner", "rotated-refresh")

    async def test_invalid_cycle_stops_automatic_short_interval_retries(self):
        self.response = httpx.Response(204, headers={"Cycle-Period": "invalid"})
        with self.assertRaises(PersonalDataReportingFailure) as raised:
            await self.client().report(self.accounts)
        self.assertEqual("invalid_cycle_period", raised.exception.code)
        self.assertGreater(raised.exception.retry_after_seconds, 604800)

    async def test_refresh_denial_does_not_send_reporting_request(self):
        async def deny(request):
            self.requests.append(request)
            return httpx.Response(400, json={"refresh_token": "never-expose-this"})
        with self.assertRaises(PersonalDataReportingFailure) as raised:
            await self.client(deny).report(self.accounts)
        self.assertEqual("owner_authorization_required", str(raised.exception))
        self.assertEqual(1, len(self.requests))
        self.grants.save_reporting_grant.assert_not_awaited()

    async def test_incomplete_refresh_response_is_not_persisted(self):
        with self.assertRaises(PersonalDataReportingFailure):
            await self.client(lambda request: httpx.Response(200, json={"access_token": "token"})).report(self.accounts)
        self.grants.save_reporting_grant.assert_not_awaited()

    async def test_network_failure_is_generic_and_cancellation_propagates(self):
        def timeout(request):
            raise httpx.ReadTimeout("private details", request=request)
        with self.assertRaises(PersonalDataReportingFailure) as raised:
            await self.client(timeout).report(self.accounts)
        self.assertEqual("reporting_network_unavailable", str(raised.exception))
        async def cancel(request):
            raise asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await self.client(cancel).report(self.accounts)

    async def test_batches_require_one_to_ninety_unique_accounts(self):
        for accounts in ((), self.accounts * 2, tuple(PersonalDataAccount(str(i), NOW) for i in range(91))):
            with self.assertRaises(ValueError):
                await self.client().report(accounts)
        self.assertEqual([], self.requests)


class PersonalDataCipherTest(unittest.TestCase):
    def test_refresh_token_is_encrypted_and_key_changes_fail_closed(self):
        cipher = PersonalDataCipher("configured-server-secret-with-at-least-32-bytes")
        encrypted = cipher.encrypt("private-owner-refresh-token")
        self.assertNotIn("private-owner-refresh-token", encrypted)
        self.assertEqual("private-owner-refresh-token", cipher.decrypt(encrypted))
        with self.assertRaises(ValueError):
            PersonalDataCipher("changed-server-secret-with-at-least-32-bytes").decrypt(encrypted)

    def test_unconfigured_key_and_empty_token_are_rejected(self):
        for key in ("", "please-set-JWT_SECRET-in-env", "short-key"):
            with self.assertRaises(ValueError):
                PersonalDataCipher(key)
        with self.assertRaises(ValueError):
            PersonalDataCipher("configured-server-secret-with-at-least-32-bytes").encrypt("")


class MemoryRepository:
    def __init__(self):
        self.accounts = {}
        self.next_report = {}
        self.actions = {}
        self.status = {}
        self.profiles = {}
        self.refreshed_batches = []
        self.events = []

    async def record_result(self, account_ids, actions, checked_at, next_report_at):
        await self.stage_actions(actions)
        await self.mark_reported(account_ids, checked_at, next_report_at)

    async def register_accounts(self, accounts):
        for account in accounts:
            if account.account_id not in self.accounts:
                self.accounts[account.account_id] = account
                self.next_report[account.account_id] = NOW
                self.status[account.account_id] = "active"

    async def due_accounts(self, now, limit):
        return tuple(value for key, value in self.accounts.items() if self.status[key] == "active" and self.next_report[key] <= now)[:limit]

    async def pending_actions(self):
        return tuple(PersonalDataAction(account_id, status.removeprefix("pending_")) for account_id, status in self.status.items() if status in {"pending_updated", "pending_closed", "updated", "closed"})

    async def stage_actions(self, actions):
        for action in actions:
            self.actions[action.account_id] = action
            self.status[action.account_id] = f"pending_{action.status}"

    async def finish_actions(self, actions):
        self.events.append(("finish", actions))
        for action in actions:
            self.actions.pop(action.account_id, None)
            if self.status[action.account_id] == f"pending_{action.status}":
                self.status[action.account_id] = action.status

    async def apply_refreshed_profiles(self, profiles):
        self.events.append(("apply", profiles))
        self.refreshed_batches.append(profiles)
        for profile in profiles:
            if self.status[profile.account_id] not in {"updated", "pending_updated"}:
                continue
            self.profiles[profile.account_id] = profile
            self.accounts[profile.account_id] = PersonalDataAccount(profile.account_id, profile.retrieved_at)
            self.status[profile.account_id] = "active"
            self.actions.pop(profile.account_id, None)
        return len(profiles)

    async def mark_reported(self, account_ids, checked_at, next_report_at):
        for account_id in account_ids:
            self.next_report[account_id] = next_report_at


class PersonalDataUseCaseTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repository = MemoryRepository()
        self.snapshots = AsyncMock()
        self.snapshots.collect_accounts.return_value = tuple(PersonalDataAccount(f"account-{i}", NOW - timedelta(days=30)) for i in range(181))
        self.snapshots.erase_personal_data.return_value = 3
        self.snapshots.mark_personal_data_updated.return_value = 2
        self.reporter = AsyncMock()
        self.reporter.report.return_value = PersonalDataReportResult(cycle_period_seconds=14 * 86400)
        self.profiles = AsyncMock()
        self.profiles.get_profile.side_effect = self.latest_profile
        self.use_case = ReportPersonalDataUseCase(self.repository, self.reporter, self.snapshots, self.profiles)

    async def latest_profile(self, account_id):
        self.repository.events.append(("get_profile", account_id))
        return PersonalDataProfile(account_id, f"최신 이름 {account_id}", NOW)

    async def test_accounts_are_split_into_ninety_and_oldest_timestamp_is_preserved(self):
        result = await self.use_case.execute(NOW)
        self.assertEqual(181, result["reported_accounts"])
        self.assertEqual([90, 90, 1], [len(call.args[0]) for call in self.reporter.report.await_args_list])
        self.assertEqual(NOW - timedelta(days=30), self.reporter.report.await_args_list[0].args[0][0].updated_at)
        result = await self.use_case.execute(NOW + timedelta(days=13))
        self.assertEqual(0, result["reported_accounts"])
        self.assertEqual(3, self.reporter.report.await_count)

    async def test_pending_erasure_survives_failure_and_resumes_without_reporting_again(self):
        self.snapshots.collect_accounts.return_value = (PersonalDataAccount("account-0", NOW),)
        self.reporter.report.return_value = PersonalDataReportResult((PersonalDataAction("account-0", "closed"),))
        self.snapshots.erase_personal_data.side_effect = RuntimeError("temporary write failure")
        with self.assertRaises(RuntimeError):
            await self.use_case.execute(NOW)
        self.assertEqual("pending_closed", self.repository.status["account-0"])
        self.snapshots.erase_personal_data.side_effect = None
        result = await self.use_case.execute(NOW)
        self.assertEqual("closed", self.repository.status["account-0"])
        self.assertEqual(0, result["reported_accounts"])
        self.reporter.report.assert_awaited_once()

    async def test_updated_response_refreshes_profile_and_snapshot_names_without_erasure(self):
        self.snapshots.collect_accounts.return_value = (PersonalDataAccount("account-0", NOW),)
        self.reporter.report.return_value = PersonalDataReportResult((PersonalDataAction("account-0", "updated"),))
        result = await self.use_case.execute(NOW)
        profile = PersonalDataProfile("account-0", "최신 이름 account-0", NOW)
        self.assertEqual({"reported_accounts": 1, "erased_report_rows": 0}, result)
        self.snapshots.erase_personal_data.assert_not_awaited()
        self.snapshots.mark_personal_data_updated.assert_awaited_once_with(("account-0",))
        self.profiles.get_profile.assert_awaited_once_with("account-0")
        self.assertEqual([(profile,)], self.repository.refreshed_batches)
        self.assertEqual(profile, self.repository.profiles["account-0"])
        self.assertEqual("active", self.repository.status["account-0"])
        self.assertEqual((), await self.repository.pending_actions())

    async def test_closed_deletion_finishes_before_failed_profile_lookup_and_update_retries_without_reporting_again(self):
        self.snapshots.collect_accounts.return_value = (PersonalDataAccount("changed", NOW), PersonalDataAccount("closed", NOW))
        self.reporter.report.return_value = PersonalDataReportResult((PersonalDataAction("changed", "updated"), PersonalDataAction("closed", "closed")))
        self.profiles.get_profile.side_effect = PersonalDataReportingFailure("profile_unavailable", 60)
        with self.assertRaises(PersonalDataReportingFailure):
            await self.use_case.execute(NOW)
        self.snapshots.erase_personal_data.assert_awaited_once_with(("closed",))
        self.snapshots.mark_personal_data_updated.assert_awaited_once_with(("changed",))
        self.profiles.get_profile.assert_awaited_once_with("changed")
        self.assertEqual("closed", self.repository.status["closed"])
        self.assertEqual("updated", self.repository.status["changed"])
        self.assertEqual([], self.repository.refreshed_batches)
        self.assertEqual(("finish", (PersonalDataAction("closed", "closed"),)), self.repository.events[0])
        self.profiles.get_profile.side_effect = self.latest_profile
        result = await self.use_case.execute(NOW)
        self.assertEqual(0, result["reported_accounts"])
        self.assertEqual(3, result["erased_report_rows"])
        self.assertEqual("active", self.repository.status["changed"])
        self.assertEqual("closed", self.repository.status["closed"])
        self.assertEqual(["changed", "changed"], [call.args[0] for call in self.profiles.get_profile.await_args_list])
        self.reporter.report.assert_awaited_once()

    async def test_failed_updated_account_does_not_block_other_successful_profiles(self):
        self.snapshots.collect_accounts.return_value = (PersonalDataAccount("failed", NOW), PersonalDataAccount("success", NOW))
        self.reporter.report.return_value = PersonalDataReportResult((PersonalDataAction("failed", "updated"), PersonalDataAction("success", "updated")))
        failure = PersonalDataReportingFailure("profile_unavailable", 120)

        async def fetch(account_id):
            if account_id == "failed":
                raise failure
            return await self.latest_profile(account_id)

        self.profiles.get_profile.side_effect = fetch
        with self.assertRaises(PersonalDataReportingFailure) as raised:
            await self.use_case.execute(NOW)
        self.assertIs(failure, raised.exception)
        self.assertEqual(["failed", "success"], [call.args[0] for call in self.profiles.get_profile.await_args_list])
        self.assertEqual("updated", self.repository.status["failed"])
        self.assertEqual("active", self.repository.status["success"])
        self.assertEqual([(PersonalDataProfile("success", "최신 이름 success", NOW),)], self.repository.refreshed_batches)
        self.snapshots.erase_personal_data.assert_not_awaited()
        self.profiles.get_profile.reset_mock()
        self.profiles.get_profile.side_effect = self.latest_profile
        await self.use_case.execute(NOW)
        self.profiles.get_profile.assert_awaited_once_with("failed")
        self.assertEqual("active", self.repository.status["failed"])
        self.reporter.report.assert_awaited_once()

    async def test_apply_failure_keeps_updated_state_until_atomic_retry_succeeds(self):
        self.snapshots.collect_accounts.return_value = (PersonalDataAccount("account-0", NOW - timedelta(days=30)),)
        self.reporter.report.return_value = PersonalDataReportResult((PersonalDataAction("account-0", "updated"),))
        profile = PersonalDataProfile("account-0", "검증한 최신 이름", NOW + timedelta(minutes=1))
        self.profiles.get_profile.side_effect = None
        self.profiles.get_profile.return_value = profile
        with patch.object(self.repository, "apply_refreshed_profiles", side_effect=RuntimeError("temporary write failure")) as apply:
            with self.assertRaises(RuntimeError):
                await self.use_case.execute(NOW)
            apply.assert_awaited_once_with((profile,))
        self.assertEqual("updated", self.repository.status["account-0"])
        self.assertEqual({}, self.repository.profiles)
        self.assertEqual(NOW - timedelta(days=30), self.repository.accounts["account-0"].updated_at)
        result = await self.use_case.execute(NOW)
        self.assertEqual(0, result["erased_report_rows"])
        self.assertEqual("active", self.repository.status["account-0"])
        self.assertEqual(profile.retrieved_at, self.repository.accounts["account-0"].updated_at)
        self.assertEqual(NOW + timedelta(days=7), self.repository.next_report["account-0"])
        self.snapshots.erase_personal_data.assert_not_awaited()
        self.reporter.report.assert_awaited_once()

    async def test_legacy_updated_accounts_are_refreshed_but_closed_accounts_never_request_profiles(self):
        await self.repository.register_accounts((PersonalDataAccount("legacy-updated", NOW), PersonalDataAccount("legacy-closed", NOW)))
        self.repository.status.update({"legacy-updated": "updated", "legacy-closed": "closed"})
        count = await self.use_case.erase_pending()
        self.assertEqual(3, count)
        self.snapshots.erase_personal_data.assert_awaited_once_with(("legacy-closed",))
        self.snapshots.mark_personal_data_updated.assert_awaited_once_with(("legacy-updated",))
        self.profiles.get_profile.assert_awaited_once_with("legacy-updated")
        self.assertEqual("active", self.repository.status["legacy-updated"])
        self.assertEqual("closed", self.repository.status["legacy-closed"])
        self.reporter.report.assert_not_awaited()

    async def test_profile_cancellation_propagates_with_closed_processed_and_update_retryable(self):
        await self.repository.register_accounts((PersonalDataAccount("changed", NOW), PersonalDataAccount("closed", NOW)))
        await self.repository.stage_actions((PersonalDataAction("changed", "updated"), PersonalDataAction("closed", "closed")))
        self.profiles.get_profile.side_effect = asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await self.use_case.erase_pending()
        self.assertEqual("closed", self.repository.status["closed"])
        self.assertEqual("updated", self.repository.status["changed"])
        self.assertEqual([], self.repository.refreshed_batches)
        self.profiles.get_profile.assert_awaited_once_with("changed")

    async def test_profile_refresh_limits_one_pending_pass_to_ninety_accounts(self):
        accounts = tuple(PersonalDataAccount(f"changed-{index}", NOW) for index in range(95))
        await self.repository.register_accounts(accounts)
        await self.repository.stage_actions(tuple(PersonalDataAction(account.account_id, "updated") for account in accounts))
        self.assertEqual(0, await self.use_case.erase_pending())
        self.assertEqual(90, self.profiles.get_profile.await_count)
        self.assertEqual(90, sum(status == "active" for status in self.repository.status.values()))
        self.assertEqual(5, len(await self.repository.pending_actions()))
        self.snapshots.erase_personal_data.assert_not_awaited()

    async def test_rate_limit_after_other_failure_preserves_provider_retry_delay_and_prior_successes(self):
        account_ids = ("success", "failed", "limited", "later")
        await self.repository.register_accounts(tuple(PersonalDataAccount(account_id, NOW) for account_id in account_ids))
        await self.repository.stage_actions(tuple(PersonalDataAction(account_id, "updated") for account_id in account_ids))
        limited = PersonalDataReportingFailure("profile_rate_limited", 1800)

        async def fetch(account_id):
            if account_id == "failed":
                raise PersonalDataReportingFailure("profile_unavailable", 300)
            if account_id == "limited":
                raise limited
            return await self.latest_profile(account_id)

        self.profiles.get_profile.side_effect = fetch
        with self.assertRaises(PersonalDataReportingFailure) as raised:
            await self.use_case.erase_pending()
        self.assertEqual(1800, raised.exception.retry_after_seconds)
        self.assertEqual(["success", "failed", "limited"], [call.args[0] for call in self.profiles.get_profile.await_args_list])
        self.assertEqual("active", self.repository.status["success"])
        self.assertEqual(["updated", "updated", "updated"], [self.repository.status[account_id] for account_id in account_ids[1:]])
        self.assertEqual([(PersonalDataProfile("success", "최신 이름 success", NOW),)], self.repository.refreshed_batches)
        self.snapshots.erase_personal_data.assert_not_awaited()

    async def test_no_pending_accounts_never_calls_profile_or_snapshot_mutations(self):
        self.assertEqual(0, await self.use_case.erase_pending())
        self.profiles.get_profile.assert_not_awaited()
        self.snapshots.erase_personal_data.assert_not_awaited()
        self.snapshots.mark_personal_data_updated.assert_not_awaited()
        self.assertEqual([], self.repository.refreshed_batches)

    async def test_provider_failure_does_not_mark_accounts_reported(self):
        self.reporter.report.side_effect = PersonalDataReportingFailure("reporting_rate_limited", 30)
        with self.assertRaises(PersonalDataReportingFailure):
            await self.use_case.execute(NOW)
        self.assertEqual(90, len(await self.repository.due_accounts(NOW, 90)))
        self.snapshots.erase_personal_data.assert_not_awaited()

    async def test_cycle_deadline_starts_when_reporting_response_is_received(self):
        self.snapshots.collect_accounts.return_value = (PersonalDataAccount("account-0", NOW),)
        received_at = NOW + timedelta(minutes=2)
        with patch("src.application.use_cases.report_personal_data.datetime") as clock:
            clock.now.side_effect = [NOW, received_at]
            await self.use_case.execute()
        self.assertEqual(received_at + timedelta(days=14), self.repository.next_report["account-0"])
