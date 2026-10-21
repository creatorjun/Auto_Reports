# backend/tests/test_verify_rovo_automation.py
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from scripts import verify_rovo_automation
from src.domain.value_objects.ai_analysis import AiAnalysis


class VerifyRovoAutomationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            rovo_automation_webhook_url="https://automation.example.invalid/hooks/private-cli-hook",
            rovo_automation_webhook_token="private-cli-webhook-token",
            rovo_automation_result_issue_key="PRIVATECLI-123",
            jira_base_url="https://private-cli.atlassian.invalid",
            jira_email="private-cli@example.invalid",
            jira_api_token="private-cli-jira-token",
            rovo_automation_timeout_seconds=90.0,
            rovo_automation_poll_seconds=2.0,
        )
        self.client = SimpleNamespace(analyze=AsyncMock(), aclose=AsyncMock())
        settings_patch = patch.object(verify_rovo_automation, "Settings", return_value=self.settings)
        client_patch = patch.object(verify_rovo_automation, "RovoAutomationClient", return_value=self.client)
        self.settings_factory = settings_patch.start()
        self.addCleanup(settings_patch.stop)
        self.client_factory = client_patch.start()
        self.addCleanup(client_patch.stop)

    async def run_verify(self, execute: bool):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = await verify_rovo_automation.verify(execute)
        self.assertEqual(stderr.getvalue(), "")
        output = stdout.getvalue()
        self.assertEqual(len(output.splitlines()), 1)
        return exit_code, json.loads(output), output

    def assert_no_settings_disclosed(self, text: str):
        for value in vars(self.settings).values():
            if isinstance(value, str):
                self.assertNotIn(value, text)

    async def test_configuration_check_does_not_execute_and_closes_client(self):
        exit_code, payload, output = await self.run_verify(False)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload, {
            "configured": True,
            "executed": False,
            "note": "연결 시험은 --execute 옵션이 필요합니다.",
        })
        self.settings_factory.assert_called_once_with()
        self.client_factory.assert_called_once_with(
            webhook_url=self.settings.rovo_automation_webhook_url,
            webhook_token=self.settings.rovo_automation_webhook_token,
            result_issue_key=self.settings.rovo_automation_result_issue_key,
            jira_base_url=self.settings.jira_base_url,
            jira_email=self.settings.jira_email,
            jira_api_token=self.settings.jira_api_token,
            timeout_seconds=self.settings.rovo_automation_timeout_seconds,
            poll_seconds=self.settings.rovo_automation_poll_seconds,
        )
        self.client.analyze.assert_not_called()
        self.client.aclose.assert_awaited_once_with()
        self.assert_no_settings_disclosed(output)

    async def test_execute_sends_synthetic_prompt_and_prints_only_result_metadata(self):
        analysis = AiAnalysis(
            summary="private-analysis-summary",
            risks=["private-analysis-risk"],
            recommendations=["private-analysis-recommendation"],
            sentiment="warning",
            bottlenecks=["private-analysis-bottleneck"],
            provider="rovo_automation",
            analyzed_at="2026-10-21T03:04:05+00:00",
        )
        self.client.analyze.return_value = analysis

        exit_code, payload, output = await self.run_verify(True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload, {
            "configured": True,
            "executed": True,
            "verified_result": True,
            "provider": "rovo_automation",
            "analyzed_at": "2026-10-21T03:04:05+00:00",
            "company_report_transmitted": False,
        })
        self.client.analyze.assert_awaited_once()
        call = self.client.analyze.await_args
        self.assertEqual(call.kwargs, {})
        self.assertEqual(len(call.args), 1)
        prompt = call.args[0]
        self.assertIsInstance(prompt, str)
        for expected in (
            "합성 데이터 연결 시험",
            "실제 회사 자료를 조회하거나 변경하지 마세요",
            "2026-01-01~2026-01-31",
            "생성 20건, 완료 15건",
            "실제 병목 이력과 SLA 분모는 제공되지 않았습니다",
            "고객명이나 티켓 번호를 지어내지 마세요",
        ):
            self.assertIn(expected, prompt)
        for private_text in (
            analysis.summary,
            *analysis.risks,
            *analysis.recommendations,
            *analysis.bottlenecks,
        ):
            self.assertNotIn(private_text, output)
            self.assertNotIn(private_text, prompt)
        self.assert_no_settings_disclosed(prompt)
        self.assert_no_settings_disclosed(output)
        self.client.aclose.assert_awaited_once_with()

    async def test_unverified_result_returns_failure_and_closes_client(self):
        self.client.analyze.return_value = None

        exit_code, payload, output = await self.run_verify(True)

        self.assertEqual(exit_code, 1)
        self.assertEqual(payload, {
            "configured": True,
            "executed": True,
            "verified_result": False,
            "provider": None,
            "analyzed_at": None,
            "company_report_transmitted": False,
        })
        self.client.analyze.assert_awaited_once()
        self.client.aclose.assert_awaited_once_with()
        self.assert_no_settings_disclosed(output)

    async def test_settings_errors_hide_validation_inputs_and_do_not_create_client(self):
        secret = "private-invalid-setting-token"
        validation_error = ValidationError.from_exception_data("Settings", [{
            "type": "value_error",
            "loc": ("rovo_automation_webhook_token",),
            "input": secret,
            "ctx": {"error": ValueError(secret)},
        }])
        self.assertIn(secret, str(validation_error))

        for error in (ValueError(secret), validation_error):
            with self.subTest(error_type=type(error).__name__):
                self.settings_factory.side_effect = error

                exit_code, payload, output = await self.run_verify(True)

                self.assertEqual(exit_code, 1)
                self.assertEqual(payload, {
                    "configured": False,
                    "error": "Rovo 설정값을 확인하세요.",
                })
                self.assertNotIn(secret, output)
                self.assert_no_settings_disclosed(output)
                self.client_factory.assert_not_called()
                self.client.analyze.assert_not_called()
                self.client.aclose.assert_not_called()

    async def test_client_configuration_error_hides_secret_and_does_not_execute(self):
        secret = "private-invalid-webhook-secret"
        self.client_factory.side_effect = ValueError(secret)

        exit_code, payload, output = await self.run_verify(False)

        self.assertEqual(exit_code, 1)
        self.assertEqual(payload, {
            "configured": False,
            "error": "Rovo 설정값을 확인하세요.",
        })
        self.assertNotIn(secret, output)
        self.assert_no_settings_disclosed(output)
        self.client.analyze.assert_not_called()
        self.client.aclose.assert_not_called()


if __name__ == "__main__":
    unittest.main()
