# backend/tests/test_jira_personal_data_client.py
import asyncio
import unittest
from datetime import datetime, timezone

import httpx

from src.application.ports.personal_data_port import PersonalDataReportingFailure
from src.infrastructure.external.jira_personal_data_client import JiraPersonalDataClient


class JiraPersonalDataClientTest(unittest.IsolatedAsyncioTestCase):
    def client(self, handler):
        return JiraPersonalDataClient("https://company.atlassian.net/", "service@example.com", "secret", httpx.MockTransport(handler))

    async def test_fetches_exact_account_and_returns_fresh_name_without_requiring_active_account(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"accountId": "account:one", "displayName": " 최신 이름 ", "active": False})
        before = datetime.now(timezone.utc)
        profile = await self.client(handler).get_profile("account:one")
        self.assertEqual("account:one", profile.account_id)
        self.assertEqual("최신 이름", profile.display_name)
        self.assertGreaterEqual(profile.retrieved_at, before)
        self.assertEqual("/rest/api/3/user", requests[0].url.path)
        self.assertEqual("account:one", requests[0].url.params["accountId"])
        self.assertEqual("GET", requests[0].method)

    async def test_visible_email_is_trimmed_and_returned_with_the_current_profile(self):
        payload = {
            "accountId": "account:one", "displayName": "현재 이름", "active": False,
            "emailAddress": "  engineer@company.example  ",
        }
        profile = await self.client(lambda request: httpx.Response(200, json=payload)).get_profile("account:one")
        self.assertEqual("engineer@company.example", profile.email_address)
        self.assertEqual("현재 이름", profile.display_name)
        self.assertEqual("account:one", profile.account_id)

    async def test_private_or_invalid_email_does_not_fail_an_otherwise_valid_profile(self):
        base = {"accountId": "account:one", "displayName": "현재 이름"}
        for payload in (
            base,
            *(dict(base, emailAddress=value) for value in (
                None, "", 123, True, {}, [], "account:one", "@company.example", "engineer@",
                "engineer@@company.example", "engineer name@company.example", "engineer\tname@company.example",
                "engineer\x00name@company.example", "engineer\x7fname@company.example", "x" * 319 + "@x",
            )),
        ):
            with self.subTest(email=payload.get("emailAddress")):
                profile = await self.client(lambda request: httpx.Response(200, json=payload)).get_profile("account:one")
                self.assertIsNone(profile.email_address)
                self.assertEqual("현재 이름", profile.display_name)
                self.assertEqual("account:one", profile.account_id)

    async def test_invalid_identity_or_name_cannot_replace_saved_information(self):
        for payload in ([], {}, {"accountId": "other", "displayName": "Name"}, {"accountId": "one", "displayName": ""}, {"accountId": "one", "displayName": "개인정보 삭제"}, {"accountId": "one", "displayName": "사용자 정보 갱신 필요"}, {"accountId": "one", "displayName": "x" * 201}):
            with self.subTest(payload=payload):
                with self.assertRaises(PersonalDataReportingFailure) as raised:
                    await self.client(lambda request: httpx.Response(200, json=payload)).get_profile("one")
                self.assertEqual("invalid_profile_response", raised.exception.code)

    async def test_missing_permissions_not_found_and_redirects_remain_retryable_not_closed(self):
        for status in (401, 403, 404, 302, 500):
            requests = []
            def handler(request):
                requests.append(request)
                return httpx.Response(status, headers={"Location": "https://elsewhere.example/private"}, json={"private": "sensitive-response"})
            with self.subTest(status=status):
                with self.assertRaises(PersonalDataReportingFailure) as raised:
                    await self.client(handler).get_profile("one")
                self.assertNotIn("sensitive", str(raised.exception))
                self.assertNotIn("closed", str(raised.exception))
                self.assertEqual(1, len(requests))

    async def test_rate_limit_obeys_provider_retry_delay(self):
        with self.assertRaises(PersonalDataReportingFailure) as raised:
            await self.client(lambda request: httpx.Response(429, headers={"Retry-After": "1800"})).get_profile("one")
        self.assertEqual("profile_rate_limited", raised.exception.code)
        self.assertEqual(1800, raised.exception.retry_after_seconds)

    async def test_invalid_accounts_do_not_make_requests(self):
        def handler(request):
            self.fail("Invalid account must not be sent to Jira")
        for account in ("", "unknown", "../one", "one?other=two"):
            with self.assertRaises(PersonalDataReportingFailure):
                await self.client(handler).get_profile(account)

    async def test_network_failure_is_sanitized_and_cancellation_propagates(self):
        def timeout(request):
            raise httpx.ReadTimeout("sensitive-url", request=request)
        with self.assertRaises(PersonalDataReportingFailure) as raised:
            await self.client(timeout).get_profile("one")
        self.assertEqual("profile_network_unavailable", raised.exception.code)
        def cancel(request):
            raise asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await self.client(cancel).get_profile("one")
