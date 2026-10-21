# backend/src/infrastructure/external/rovo_automation_client.py
import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.application.ports.ai_port import AiPort
from src.domain.value_objects.ai_analysis import AiAnalysis

logger = logging.getLogger(__name__)
_MAX_PROMPT_BYTES = 60_000
_MAX_RESULT_BYTES = 65_536
_ISSUE_KEY = re.compile(r"\b[A-Z][A-Z0-9_]*-\d+\b")
_Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class _AnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    risks: list[_Text] = Field(max_length=5)
    bottlenecks: list[_Text] = Field(max_length=5)
    recommendations: list[_Text] = Field(max_length=5)
    sentiment: Literal["good", "warning", "critical"]


class RovoAutomationClient(AiPort):
    def __init__(
        self,
        *,
        webhook_url: str,
        webhook_token: str,
        result_issue_key: str,
        jira_base_url: str,
        jira_email: str,
        jira_api_token: str,
        timeout_seconds: float = 180,
        poll_seconds: float = 5,
        webhook_client: httpx.AsyncClient | None = None,
        jira_client: httpx.AsyncClient | None = None,
    ):
        webhook = urlsplit(webhook_url)
        allowed_paths = {
            "api-private.atlassian.com": "/automation/webhooks/",
            "api.atlassian.com": "/automation/webhooks/",
            "automation.atlassian.com": "/pro/hooks/",
        }
        if (
            webhook.scheme != "https" or webhook.hostname not in allowed_paths
            or not webhook.path.startswith(allowed_paths.get(webhook.hostname, "!"))
            or webhook.username or webhook.password or webhook.query or webhook.fragment
            or webhook.port not in (None, 443)
        ):
            raise ValueError("Rovo Automation requires an official HTTPS webhook URL")
        jira = urlsplit(jira_base_url)
        if jira.scheme != "https" or not jira.hostname or jira.username or jira.password or jira.query or jira.fragment:
            raise ValueError("Rovo Automation requires an HTTPS Jira base URL")
        if not webhook_token.strip() or not jira_email.strip() or not jira_api_token.strip():
            raise ValueError("Rovo Automation credentials are incomplete")
        if not _ISSUE_KEY.fullmatch(result_issue_key):
            raise ValueError("Rovo Automation requires a fixed result issue key")
        if timeout_seconds <= 0 or poll_seconds <= 0:
            raise ValueError("Rovo Automation time limits must be positive")
        self._webhook_url = webhook_url
        self._webhook_token = webhook_token
        self._issue_key = result_issue_key
        self._timeout = timeout_seconds
        self._poll_seconds = poll_seconds
        self._webhook = webhook_client or httpx.AsyncClient(timeout=15, follow_redirects=False)
        self._jira = jira_client or httpx.AsyncClient(
            base_url=jira_base_url.rstrip("/") + "/",
            auth=httpx.BasicAuth(jira_email, jira_api_token),
            timeout=15,
            follow_redirects=False,
            headers={"Accept": "application/json"},
        )
        self._slots = asyncio.Semaphore(2)

    async def analyze(self, prompt: str) -> AiAnalysis | None:
        if not prompt.strip() or len(prompt.encode("utf-8")) > _MAX_PROMPT_BYTES:
            logger.warning("Rovo analysis skipped: invalid input size")
            return None
        request_id = uuid.uuid4().hex
        input_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        properties_path = f"rest/api/3/issue/{self._issue_key}/properties"
        property_key = "auto_reports.rovo." + request_id
        result_path = properties_path + "/" + property_key
        expires_at_ms = int((time.time() + self._timeout) * 1000)
        posted = False
        try:
            async with asyncio.timeout(self._timeout):
                async with self._slots:
                    async with self._jira.stream("GET", properties_path) as response:
                        if response.status_code != 200:
                            raise ValueError("result_issue_unavailable")
                    payload = {
                        "schema_version": 1,
                        "issues": [self._issue_key],
                        "request_id": request_id,
                        "input_hash": input_hash,
                        "expires_at_ms": expires_at_ms,
                        "prompt": prompt,
                    }
                    posted = True
                    async with self._webhook.stream(
                        "POST", self._webhook_url, json=payload,
                        headers={"X-Automation-Webhook-Token": self._webhook_token},
                    ) as response:
                        if response.status_code not in (200, 201, 202, 204):
                            raise ValueError("webhook_rejected")
                    while True:
                        delay = self._poll_seconds
                        async with self._jira.stream("GET", result_path) as response:
                            if response.status_code == 200:
                                raw = bytearray()
                                async for chunk in response.aiter_bytes():
                                    raw.extend(chunk)
                                    if len(raw) > _MAX_RESULT_BYTES:
                                        raise ValueError("result_too_large")
                                value = json.loads(raw)
                                return self._parse(value, property_key, request_id, input_hash, prompt)
                            if response.status_code not in (404, 429, 502, 503, 504):
                                raise ValueError("result_lookup_failed")
                            if response.status_code == 429:
                                try:
                                    delay = max(delay, float(response.headers.get("Retry-After", delay)))
                                except ValueError:
                                    pass
                        await asyncio.sleep(min(delay, self._timeout))
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            logger.warning("Rovo analysis timed out before a verified result arrived")
        except Exception as error:
            logger.warning("Rovo analysis unavailable (%s)", type(error).__name__)
        finally:
            if posted:
                try:
                    async with asyncio.timeout(5):
                        response = await self._jira.delete(result_path)
                        if response.status_code not in (204, 404):
                            logger.warning("Rovo temporary result cleanup failed (HTTP %d)", response.status_code)
                except Exception as error:
                    logger.warning("Rovo temporary result cleanup unavailable (%s)", type(error).__name__)
        return None

    @staticmethod
    def _parse(payload: object, property_key: str, request_id: str, input_hash: str, prompt: str) -> AiAnalysis:
        if not isinstance(payload, dict) or payload.get("key") != property_key:
            raise ValueError("unexpected_result_property")
        value = payload.get("value")
        if not isinstance(value, dict) or (
            type(value.get("schema_version")) is not int or value.get("schema_version") != 1
            or value.get("request_id") != request_id or value.get("input_hash") != input_hash
            or value.get("status") != "completed" or not isinstance(value.get("output"), str)
        ):
            raise ValueError("unmatched_result")
        output = value["output"].strip()
        fence = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", output, re.DOTALL)
        if fence:
            output = fence.group(1)
        parsed = _AnalysisOutput.model_validate_json(output)
        decoded_output = "\n".join([
            parsed.summary, *parsed.risks, *parsed.bottlenecks, *parsed.recommendations,
        ])
        references = set(_ISSUE_KEY.findall(decoded_output))
        if not references.issubset(set(_ISSUE_KEY.findall(prompt))):
            raise ValueError("unknown_evidence_issue")
        return AiAnalysis(
            **parsed.model_dump(),
            provider="rovo_automation",
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )

    async def aclose(self) -> None:
        try:
            await self._webhook.aclose()
        finally:
            await self._jira.aclose()
