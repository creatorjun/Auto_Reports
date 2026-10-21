# backend/tests/test_rovo_automation_client.py
import asyncio
import base64
import hashlib
import json
import time
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
from pydantic import ValidationError

from src.infrastructure.config.settings import Settings
from src.infrastructure.external.rovo_automation_client import RovoAutomationClient
from src.infrastructure.factories.ai_factory import AiFactory

_MODULE = "src.infrastructure.external.rovo_automation_client"
_FACTORY = "src.infrastructure.factories.ai_factory"
_WEBHOOK_URL = "https://api-private.atlassian.com/automation/webhooks/test-hook"
_JIRA_URL = "https://reports-test.atlassian.net"
_PROMPT = "공급된 보고서 근거: TACEA-12, TACEA-13. 추가 조회 없이 요약하세요."
_CONFIG = {
    "webhook_url": _WEBHOOK_URL,
    "webhook_token": "test-webhook-secret",
    "result_issue_key": "REPORT-1",
    "jira_base_url": _JIRA_URL,
    "jira_email": "report@example.test",
    "jira_api_token": "test-jira-secret",
    "timeout_seconds": 0.2,
    "poll_seconds": 0.001,
}


def analysis_output() -> dict:
    return {
        "summary": "TACEA-12가 포함된 보고서 요약입니다.",
        "risks": ["추가 상태 이력 확인이 필요합니다."],
        "bottlenecks": [],
        "recommendations": ["근거가 있는 항목부터 확인하세요."],
        "sentiment": "warning",
    }


class AutomationTransport:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.payloads: list[dict] = []
        self.preflight_status = 200
        self.webhook_status = 200
        self.poll_statuses: list[int] = []
        self.poll_default_status = 200
        self.retry_after = "0.02"
        self.cleanup_status = 204
        self.cleanup_error = False
        self.failure_phase: str | None = None
        self.output = json.dumps(analysis_output(), ensure_ascii=False)
        self.envelope_transform = None
        self.raw_result: bytes | None = None
        self.poll_started: asyncio.Event | None = None
        self.poll_release: asyncio.Event | None = None

    def requests_for(self, method: str) -> list[httpx.Request]:
        return [request for request in self.requests if request.method == method]

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        phase = (
            "webhook" if request.method == "POST" else
            "cleanup" if request.method == "DELETE" else
            "preflight" if request.url.path.endswith("/properties") else "poll"
        )
        if phase == self.failure_phase:
            raise httpx.ConnectError("test-jira-secret test-webhook-secret sensitive report", request=request)
        if request.method == "POST":
            self.payloads.append(json.loads(request.content))
            return httpx.Response(
                self.webhook_status,
                headers={"Location": "https://redirect.example.test/capture"},
                json={"message": "accepted"},
            )
        if request.method == "DELETE":
            if self.cleanup_error:
                raise httpx.ConnectError("sensitive upstream details", request=request)
            return httpx.Response(self.cleanup_status)
        if request.url.path.endswith("/properties"):
            return httpx.Response(self.preflight_status, json={"keys": []})
        if self.poll_started is not None:
            self.poll_started.set()
        if self.poll_release is not None:
            await self.poll_release.wait()
        status = self.poll_statuses.pop(0) if self.poll_statuses else self.poll_default_status
        if status != 200:
            return httpx.Response(status, headers={"Retry-After": self.retry_after})
        if self.raw_result is not None:
            return httpx.Response(200, content=self.raw_result)
        payload = self.payloads[-1]
        result = {
            "key": "auto_reports.rovo." + payload["request_id"],
            "value": {
                "schema_version": 1,
                "request_id": payload["request_id"],
                "input_hash": payload["input_hash"],
                "status": "completed",
                "output": self.output,
            },
        }
        if self.envelope_transform is not None:
            result = self.envelope_transform(result)
        return httpx.Response(200, json=result)


class RovoAutomationClientTest(unittest.IsolatedAsyncioTestCase):
    def make_adapter(self, transport: AutomationTransport, **overrides) -> RovoAutomationClient:
        original_client = httpx.AsyncClient
        mock_transport = httpx.MockTransport(transport)
        clients: list[httpx.AsyncClient] = []

        def create_client(**kwargs):
            client = original_client(transport=mock_transport, **kwargs)
            clients.append(client)
            return client

        with patch(f"{_MODULE}.httpx.AsyncClient", side_effect=create_client):
            adapter = RovoAutomationClient(**(_CONFIG | overrides))
        self.addAsyncCleanup(adapter.aclose)
        self.clients = clients
        return adapter

    async def test_accepted_webhook_waits_for_matching_result_and_cleans_it(self) -> None:
        transport = AutomationTransport()
        transport.poll_statuses = [404]
        adapter = self.make_adapter(transport)
        before = time.time()

        result = await adapter.analyze(_PROMPT)

        self.assertIsNotNone(result)
        self.assertEqual("rovo_automation", result.provider)
        self.assertEqual(analysis_output()["summary"], result.summary)
        self.assertEqual([], result.bottlenecks)
        self.assertIsNotNone(datetime.fromisoformat(result.analyzed_at).tzinfo)
        self.assertEqual(["GET", "POST", "GET", "GET", "DELETE"], [r.method for r in transport.requests])
        payload = transport.payloads[0]
        self.assertEqual(1, payload["schema_version"])
        self.assertEqual(["REPORT-1"], payload["issues"])
        self.assertEqual(_PROMPT, payload["prompt"])
        self.assertEqual(hashlib.sha256(_PROMPT.encode("utf-8")).hexdigest(), payload["input_hash"])
        self.assertRegex(payload["request_id"], r"^[a-f0-9]{32}$")
        self.assertGreaterEqual(payload["expires_at_ms"], int(before * 1000))
        self.assertLessEqual(payload["expires_at_ms"], int((time.time() + 0.2) * 1000))
        self.assertEqual(transport.requests[-2].url, transport.requests[-1].url)
        self.assertNotIn(_PROMPT, str(transport.requests[-1].url))

    async def test_actual_constructor_keeps_jira_and_webhook_credentials_separate(self) -> None:
        transport = AutomationTransport()
        adapter = self.make_adapter(transport)

        await adapter.analyze(_PROMPT)

        basic = base64.b64encode(b"report@example.test:test-jira-secret").decode("ascii")
        for request in transport.requests:
            if request.method == "POST":
                self.assertEqual("api-private.atlassian.com", request.url.host)
                self.assertEqual("test-webhook-secret", request.headers["X-Automation-Webhook-Token"])
                self.assertNotIn("Authorization", request.headers)
                self.assertNotIn("test-jira-secret", request.content.decode("utf-8"))
            else:
                self.assertEqual("reports-test.atlassian.net", request.url.host)
                self.assertEqual("Basic " + basic, request.headers["Authorization"])
                self.assertNotIn("X-Automation-Webhook-Token", request.headers)
            self.assertNotIn("test-webhook-secret", str(request.url))
            self.assertNotIn("test-jira-secret", str(request.url))

    async def test_bad_secret_accepted_as_200_times_out_without_reposting(self) -> None:
        transport = AutomationTransport()
        transport.poll_default_status = 404
        adapter = self.make_adapter(transport, timeout_seconds=0.025)
        started = time.monotonic()

        with self.assertLogs(_MODULE, level="WARNING") as logs:
            result = await adapter.analyze(_PROMPT)

        self.assertIsNone(result)
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual(1, len(transport.requests_for("POST")))
        self.assertEqual(1, len(transport.requests_for("DELETE")))
        self.assertIn("timed out", " ".join(logs.output))

    async def test_every_correlation_field_and_schema_version_must_match(self) -> None:
        cases = [
            ("key", "auto_reports.rovo.other"),
            ("request_id", "other-request"),
            ("input_hash", "other-hash"),
            ("schema_version", 2),
            ("schema_version", True),
            ("schema_version", "1"),
            ("status", "pending"),
            ("output", analysis_output()),
        ]
        for field, replacement in cases:
            with self.subTest(field=field, replacement=replacement):
                transport = AutomationTransport()

                def transform(result, field=field, replacement=replacement):
                    target = result if field == "key" else result["value"]
                    target[field] = replacement
                    return result

                transport.envelope_transform = transform
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING"):
                    self.assertIsNone(await adapter.analyze(_PROMPT))
                self.assertEqual(1, len(transport.requests_for("DELETE")))

    async def test_missing_correlation_fields_and_wrong_envelope_types_are_rejected(self) -> None:
        for field in ("schema_version", "request_id", "input_hash", "status", "output"):
            with self.subTest(field=field):
                transport = AutomationTransport()

                def transform(result, field=field):
                    del result["value"][field]
                    return result

                transport.envelope_transform = transform
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING"):
                    self.assertIsNone(await adapter.analyze(_PROMPT))
        for body in (b"null", b"[]", b"{}", b'{"key":"wrong","value":null}'):
            with self.subTest(body=body):
                transport = AutomationTransport()
                transport.raw_result = body
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING"):
                    self.assertIsNone(await adapter.analyze(_PROMPT))

    async def test_malformed_result_json_is_rejected_and_cleaned(self) -> None:
        transport = AutomationTransport()
        transport.raw_result = b"not-json"
        adapter = self.make_adapter(transport)
        with self.assertLogs(_MODULE, level="WARNING"):
            self.assertIsNone(await adapter.analyze(_PROMPT))
        self.assertEqual(1, len(transport.requests_for("DELETE")))

    async def test_output_requires_every_field_with_strict_types_and_limits(self) -> None:
        invalid_outputs = []
        for field in analysis_output():
            missing = analysis_output()
            del missing[field]
            invalid_outputs.append(missing)
        invalid_outputs.extend([
            analysis_output() | {"extra": "unrequested"},
            analysis_output() | {"summary": " "},
            analysis_output() | {"summary": "x" * 1001},
            analysis_output() | {"risks": "not a list"},
            analysis_output() | {"risks": [123]},
            analysis_output() | {"bottlenecks": [" "]},
            analysis_output() | {"recommendations": ["x"] * 6},
            analysis_output() | {"risks": ["x" * 301]},
            analysis_output() | {"sentiment": "excellent"},
        ])
        for index, output in enumerate(invalid_outputs):
            with self.subTest(case=index):
                transport = AutomationTransport()
                transport.output = json.dumps(output)
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING"):
                    self.assertIsNone(await adapter.analyze(_PROMPT))
                self.assertEqual(1, len(transport.requests_for("DELETE")))

    async def test_unknown_issue_references_in_any_analysis_field_are_rejected(self) -> None:
        for field in ("summary", "risks", "bottlenecks", "recommendations"):
            with self.subTest(field=field):
                output = analysis_output()
                output[field] = "UNKNOWN-99" if field == "summary" else ["UNKNOWN-99 관련 확인"]
                transport = AutomationTransport()
                transport.output = json.dumps(output)
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING"):
                    self.assertIsNone(await adapter.analyze(_PROMPT))

    async def test_json_escaped_unknown_issue_reference_is_rejected_after_decoding(self) -> None:
        transport = AutomationTransport()
        output = analysis_output() | {"summary": "UNKNOWN-99 확인"}
        transport.output = json.dumps(output).replace("UNKNOWN-99", "\\u0055NKNOWN\\u002d99")
        self.assertNotIn("UNKNOWN-99", transport.output)
        adapter = self.make_adapter(transport)
        with self.assertLogs(_MODULE, level="WARNING"):
            self.assertIsNone(await adapter.analyze(_PROMPT))
        self.assertEqual(1, len(transport.requests_for("DELETE")))

    async def test_json_escaped_known_issue_reference_is_accepted_after_decoding(self) -> None:
        transport = AutomationTransport()
        transport.output = transport.output.replace("TACEA-12", "\\u0054ACEA\\u002d12")
        adapter = self.make_adapter(transport)
        result = await adapter.analyze(_PROMPT)
        self.assertIsNotNone(result)
        self.assertIn("TACEA-12", result.summary)

    async def test_complete_json_fence_is_accepted_but_surrounding_prose_is_rejected(self) -> None:
        for prefix in ("```json\n", "```\n"):
            with self.subTest(prefix=prefix):
                transport = AutomationTransport()
                transport.output = prefix + transport.output + "\n```"
                adapter = self.make_adapter(transport)
                self.assertIsNotNone(await adapter.analyze(_PROMPT))
        for output in ("not-json", "설명\n" + json.dumps(analysis_output()), "```json\n{}\n```\n후기"):
            with self.subTest(output=output):
                transport = AutomationTransport()
                transport.output = output
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING"):
                    self.assertIsNone(await adapter.analyze(_PROMPT))

    async def test_oversized_response_is_rejected(self) -> None:
        transport = AutomationTransport()
        transport.raw_result = b" " * 65_537
        adapter = self.make_adapter(transport)
        with self.assertLogs(_MODULE, level="WARNING"):
            self.assertIsNone(await adapter.analyze(_PROMPT))
        self.assertEqual(1, len(transport.requests_for("DELETE")))

    async def test_maximum_korean_analysis_fits_jira_property_byte_limit(self) -> None:
        output = {
            "summary": "가" * 1000,
            "risks": ["나" * 300] * 5,
            "bottlenecks": ["다" * 300] * 5,
            "recommendations": ["라" * 300] * 5,
            "sentiment": "warning",
        }
        transport = AutomationTransport()
        transport.output = json.dumps(output, ensure_ascii=False)
        serialized_envelopes: list[bytes] = []

        def record_size(envelope):
            serialized_envelopes.append(json.dumps(envelope, ensure_ascii=False).encode("utf-8"))
            return envelope

        transport.envelope_transform = record_size
        adapter = self.make_adapter(transport)
        result = await adapter.analyze(_PROMPT)
        self.assertIsNotNone(result)
        self.assertEqual(output["summary"], result.summary)
        self.assertEqual(output["recommendations"], result.recommendations)
        self.assertEqual(1, len(serialized_envelopes))
        self.assertLess(len(serialized_envelopes[0]), 32_768)

    async def test_empty_and_utf8_oversized_input_make_no_http_calls(self) -> None:
        transport = AutomationTransport()
        adapter = self.make_adapter(transport)
        for prompt in ("", " \n", "x" * 60_001, "가" * 20_001):
            with self.subTest(size=len(prompt)), self.assertLogs(_MODULE, level="WARNING"):
                self.assertIsNone(await adapter.analyze(prompt))
        self.assertEqual([], transport.requests)

    async def test_utf8_input_at_limit_is_accepted(self) -> None:
        transport = AutomationTransport()
        transport.output = json.dumps(analysis_output() | {"summary": "집계 요약"})
        adapter = self.make_adapter(transport)
        self.assertIsNotNone(await adapter.analyze("가" * 20_000))
        self.assertEqual(1, len(transport.requests_for("POST")))

    async def test_denied_result_issue_preflight_never_posts(self) -> None:
        for status in (401, 403, 404, 302):
            with self.subTest(status=status):
                transport = AutomationTransport()
                transport.preflight_status = status
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING"):
                    self.assertIsNone(await adapter.analyze(_PROMPT))
                self.assertEqual(["GET"], [r.method for r in transport.requests])

    async def test_rejected_or_redirected_webhook_is_never_followed_or_retried(self) -> None:
        for status in (301, 302, 307, 308, 400, 401, 403, 429, 500):
            with self.subTest(status=status):
                transport = AutomationTransport()
                transport.webhook_status = status
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING"):
                    self.assertIsNone(await adapter.analyze(_PROMPT))
                self.assertEqual(["GET", "POST", "DELETE"], [r.method for r in transport.requests])
                self.assertNotIn("redirect.example.test", [r.url.host for r in transport.requests])

    async def test_transport_failures_are_sanitized_and_only_posted_requests_are_cleaned(self) -> None:
        for phase, expected in (
            ("preflight", ["GET"]),
            ("webhook", ["GET", "POST", "DELETE"]),
            ("poll", ["GET", "POST", "GET", "DELETE"]),
        ):
            with self.subTest(phase=phase):
                transport = AutomationTransport()
                transport.failure_phase = phase
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING") as logs:
                    self.assertIsNone(await adapter.analyze(_PROMPT))
                self.assertEqual(expected, [r.method for r in transport.requests])
                messages = " ".join(logs.output)
                self.assertIn("ConnectError", messages)
                for private in ("test-jira-secret", "test-webhook-secret", "sensitive report", _WEBHOOK_URL, _PROMPT):
                    self.assertNotIn(private, messages)

    async def test_denied_or_redirected_result_is_not_retried(self) -> None:
        for status in (302, 400, 401, 403):
            with self.subTest(status=status):
                transport = AutomationTransport()
                transport.poll_default_status = status
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING"):
                    self.assertIsNone(await adapter.analyze(_PROMPT))
                self.assertEqual(["GET", "POST", "GET", "DELETE"], [r.method for r in transport.requests])

    async def test_transient_result_statuses_retry_without_reposting(self) -> None:
        transport = AutomationTransport()
        transport.poll_statuses = [404, 502, 503, 504]
        adapter = self.make_adapter(transport)
        self.assertIsNotNone(await adapter.analyze(_PROMPT))
        self.assertEqual(1, len(transport.requests_for("POST")))
        self.assertEqual(6, len(transport.requests_for("GET")))

    async def test_rate_limit_honors_retry_after_with_bounded_wait(self) -> None:
        for retry_after, expected_delay in (("0.02", 0.02), ("600", 0.2), ("invalid", 0.001)):
            with self.subTest(retry_after=retry_after):
                transport = AutomationTransport()
                transport.poll_statuses = [429]
                transport.retry_after = retry_after
                adapter = self.make_adapter(transport)
                with patch(f"{_MODULE}.asyncio.sleep", new_callable=AsyncMock) as sleep:
                    self.assertIsNotNone(await adapter.analyze(_PROMPT))
                sleep.assert_awaited_once_with(expected_delay)
                self.assertEqual(1, len(transport.requests_for("POST")))

    async def test_cancellation_propagates_and_cleans_posted_result(self) -> None:
        transport = AutomationTransport()
        transport.poll_started = asyncio.Event()
        transport.poll_release = asyncio.Event()
        adapter = self.make_adapter(transport, timeout_seconds=1)
        task = asyncio.create_task(adapter.analyze(_PROMPT))
        await asyncio.wait_for(transport.poll_started.wait(), 1)

        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertEqual(1, len(transport.requests_for("DELETE")))
        self.assertEqual(1, len(transport.requests_for("POST")))

    async def test_request_expiry_includes_waiting_for_concurrency_slot(self) -> None:
        transport = AutomationTransport()
        adapter = self.make_adapter(transport)
        await adapter._slots.acquire()
        await adapter._slots.acquire()
        try:
            with patch(f"{_MODULE}.time.time", return_value=1000) as wall_time:
                task = asyncio.create_task(adapter.analyze(_PROMPT))
                await asyncio.sleep(0)
                self.assertFalse(task.done())
                self.assertEqual([], transport.requests)
                wall_time.return_value = 1010
                adapter._slots.release()
                self.assertIsNotNone(await task)
        finally:
            adapter._slots.release()
        self.assertEqual(1_000_200, transport.payloads[0]["expires_at_ms"])

    async def test_cleanup_failure_keeps_verified_result_and_logs_no_payload(self) -> None:
        for status, error in ((500, False), (204, True)):
            with self.subTest(status=status, error=error):
                transport = AutomationTransport()
                transport.cleanup_status = status
                transport.cleanup_error = error
                adapter = self.make_adapter(transport)
                with self.assertLogs(_MODULE, level="WARNING") as logs:
                    result = await adapter.analyze(_PROMPT)
                self.assertIsNotNone(result)
                messages = " ".join(logs.output)
                for private in (_PROMPT, "test-webhook-secret", "test-jira-secret", "sensitive upstream details", _WEBHOOK_URL):
                    self.assertNotIn(private, messages)

    async def test_missing_cleanup_property_is_normal(self) -> None:
        transport = AutomationTransport()
        transport.cleanup_status = 404
        adapter = self.make_adapter(transport)
        with self.assertNoLogs(_MODULE, level="WARNING"):
            self.assertIsNotNone(await adapter.analyze(_PROMPT))

    async def test_calls_use_distinct_result_properties_and_clean_each(self) -> None:
        transport = AutomationTransport()
        adapter = self.make_adapter(transport)
        self.assertIsNotNone(await adapter.analyze(_PROMPT))
        self.assertIsNotNone(await adapter.analyze(_PROMPT))
        self.assertNotEqual(transport.payloads[0]["request_id"], transport.payloads[1]["request_id"])
        self.assertNotEqual(transport.requests_for("DELETE")[0].url, transport.requests_for("DELETE")[1].url)

    async def test_aclose_releases_both_real_http_clients(self) -> None:
        adapter = self.make_adapter(AutomationTransport())
        self.assertTrue(all(not client.is_closed for client in self.clients))
        await adapter.aclose()
        await adapter.aclose()
        self.assertTrue(all(client.is_closed for client in self.clients))

    async def test_aclose_attempts_jira_close_if_webhook_close_fails(self) -> None:
        webhook = AsyncMock(spec=httpx.AsyncClient)
        jira = AsyncMock(spec=httpx.AsyncClient)
        webhook.aclose.side_effect = RuntimeError("close failed")
        adapter = RovoAutomationClient(**_CONFIG, webhook_client=webhook, jira_client=jira)
        with self.assertRaisesRegex(RuntimeError, "close failed"):
            await adapter.aclose()
        jira.aclose.assert_awaited_once_with()

    def test_invalid_urls_credentials_issue_keys_and_time_limits_fail_before_clients(self) -> None:
        invalid_configs = [
            {"webhook_url": "http://api.atlassian.com/automation/webhooks/test"},
            {"webhook_url": "https://api.atlassian.com.evil.test/automation/webhooks/test"},
            {"webhook_url": "https://api.atlassian.com/other/test"},
            {"webhook_url": _WEBHOOK_URL + "?token=secret"},
            {"webhook_url": _WEBHOOK_URL + "#fragment"},
            {"webhook_url": "https://user:secret@api.atlassian.com/automation/webhooks/test"},
            {"webhook_url": "https://api.atlassian.com:8443/automation/webhooks/test"},
            {"jira_base_url": "http://reports-test.atlassian.net"},
            {"jira_base_url": "https://user:secret@reports-test.atlassian.net"},
            {"jira_base_url": _JIRA_URL + "?token=secret"},
            {"jira_base_url": _JIRA_URL + "#fragment"},
            {"webhook_token": " "}, {"jira_email": ""}, {"jira_api_token": " "},
            {"result_issue_key": "bad key"}, {"result_issue_key": "REPORT-1/properties/other"},
            {"timeout_seconds": 0}, {"poll_seconds": -1},
        ]
        for overrides in invalid_configs:
            with self.subTest(overrides=overrides), patch(f"{_MODULE}.httpx.AsyncClient") as client:
                with self.assertRaises(ValueError):
                    RovoAutomationClient(**(_CONFIG | overrides))
                client.assert_not_called()


class RovoAiFactoryTest(unittest.TestCase):
    def settings(self, **overrides) -> Settings:
        values = {
            "jira_base_url": _JIRA_URL,
            "jira_email": "report@example.test",
            "jira_api_token": "test-jira-secret",
            "ai_enabled": True,
            "ai_provider": "rovo_automation",
            "gemini_api_key": "test-gemini-secret",
            "rovo_automation_webhook_url": _WEBHOOK_URL,
            "rovo_automation_webhook_token": "test-webhook-secret",
            "rovo_automation_result_issue_key": "REPORT-1",
            "rovo_automation_timeout_seconds": 120,
            "rovo_automation_poll_seconds": 3,
        }
        return Settings(_env_file=None, **(values | overrides))

    def test_disabled_ai_creates_no_provider_even_with_missing_rovo_config(self) -> None:
        settings = self.settings(ai_enabled=False, rovo_automation_webhook_url="")
        with patch(f"{_FACTORY}.RovoAutomationClient") as rovo, patch(f"{_FACTORY}.GeminiClient") as gemini:
            self.assertIsNone(AiFactory.create(settings))
        rovo.assert_not_called()
        gemini.assert_not_called()

    def test_rovo_selection_passes_config_without_creating_gemini(self) -> None:
        with patch(f"{_FACTORY}.RovoAutomationClient") as rovo, patch(f"{_FACTORY}.GeminiClient") as gemini:
            result = AiFactory.create(self.settings())
        self.assertIs(rovo.return_value, result)
        rovo.assert_called_once_with(**(_CONFIG | {"timeout_seconds": 120, "poll_seconds": 3.0}))
        gemini.assert_not_called()

    def test_gemini_selection_is_explicit_and_does_not_create_rovo(self) -> None:
        with patch(f"{_FACTORY}.RovoAutomationClient") as rovo, patch(f"{_FACTORY}.GeminiClient") as gemini:
            result = AiFactory.create(self.settings(ai_provider="gemini"))
        self.assertIs(gemini.return_value, result)
        gemini.assert_called_once_with("test-gemini-secret")
        rovo.assert_not_called()

    def test_invalid_rovo_configuration_raises_without_gemini_fallback(self) -> None:
        for overrides in (
            {"rovo_automation_webhook_url": ""},
            {"rovo_automation_webhook_token": ""},
            {"rovo_automation_result_issue_key": ""},
        ):
            with self.subTest(overrides=overrides), patch(f"{_FACTORY}.GeminiClient") as gemini:
                with self.assertRaises(ValueError):
                    AiFactory.create(self.settings(**overrides))
                gemini.assert_not_called()

    def test_settings_reject_unknown_provider_and_unbounded_poll_configuration(self) -> None:
        for overrides in (
            {"ai_provider": "unknown"},
            {"rovo_automation_timeout_seconds": 14},
            {"rovo_automation_timeout_seconds": 301},
            {"rovo_automation_poll_seconds": 0},
            {"rovo_automation_poll_seconds": 31},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                self.settings(**overrides)
