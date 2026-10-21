# backend/src/infrastructure/external/personal_data_client.py
import asyncio
import math
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from src.application.ports.personal_data_port import PersonalDataReporterPort, PersonalDataReportingFailure, PersonalDataReportingGrantPort
from src.domain.entities.personal_data import PersonalDataAccount, PersonalDataAction, PersonalDataReportResult


class AtlassianPersonalDataClient(PersonalDataReporterPort):
    def __init__(self, client_id: str, client_secret: str, grants: PersonalDataReportingGrantPort, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._grants = grants
        self._transport = transport

    async def report(self, accounts: tuple[PersonalDataAccount, ...]) -> PersonalDataReportResult:
        if not accounts or len(accounts) > 90 or len({account.account_id for account in accounts}) != len(accounts):
            raise ValueError("Personal data reports require one to ninety unique accounts")
        try:
            async with asyncio.timeout(45):
                async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5), follow_redirects=False, transport=self._transport) as client:
                    access = await self._refresh_access(client)
                    response = await client.post(
                        "https://api.atlassian.com/app/report-accounts/",
                        headers={"Authorization": f"Bearer {access}", "Accept": "application/json"},
                        json={"accounts": [{
                            "accountId": account.account_id,
                            "updatedAt": account.updated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                        } for account in accounts]},
                    )
                    self._check_response(response, (200, 204))
                    period = self._cycle_period(response.headers.get("Cycle-Period"))
                    if response.status_code == 204:
                        return PersonalDataReportResult(cycle_period_seconds=period)
                    payload = response.json()
                    if not isinstance(payload, dict) or not isinstance(payload.get("accounts"), list):
                        raise PersonalDataReportingFailure("invalid_reporting_response")
                    requested = {account.account_id for account in accounts}
                    seen: set[str] = set()
                    actions = []
                    for item in payload["accounts"]:
                        if not isinstance(item, dict):
                            raise PersonalDataReportingFailure("invalid_reporting_response")
                        account_id, status = item.get("accountId"), item.get("status")
                        if not isinstance(account_id, str) or account_id not in requested or account_id in seen or status not in {"updated", "closed"}:
                            raise PersonalDataReportingFailure("invalid_reporting_response")
                        seen.add(account_id)
                        actions.append(PersonalDataAction(account_id, status))
                    return PersonalDataReportResult(tuple(actions), period)
        except (httpx.HTTPError, TimeoutError):
            raise PersonalDataReportingFailure("reporting_network_unavailable") from None
        except (ValueError, TypeError, KeyError):
            raise PersonalDataReportingFailure("invalid_reporting_response") from None

    async def _refresh_access(self, client: httpx.AsyncClient) -> str:
        owner, refresh_token = await self._grants.get_reporting_grant()
        response = await client.post("https://auth.atlassian.com/oauth/token", json={
            "grant_type": "refresh_token", "client_id": self._client_id,
            "client_secret": self._client_secret, "refresh_token": refresh_token,
        })
        self._check_response(response, (200,))
        payload = response.json()
        if not isinstance(payload, dict):
            raise PersonalDataReportingFailure("invalid_owner_token_response")
        access, rotated = payload.get("access_token"), payload.get("refresh_token")
        if not isinstance(access, str) or not access or not isinstance(rotated, str) or not rotated:
            raise PersonalDataReportingFailure("invalid_owner_token_response")
        await self._grants.save_reporting_grant(owner, rotated)
        return access

    @staticmethod
    def _cycle_period(value: str | None) -> int:
        if value is None:
            return 604800
        try:
            days = float(value)
            if not math.isfinite(days) or days <= 0 or days > 36500:
                raise ValueError
            return max(1, math.ceil(days * 86400))
        except ValueError:
            raise PersonalDataReportingFailure("invalid_cycle_period", 3153600000) from None

    @staticmethod
    def _check_response(response: httpx.Response, expected: tuple[int, ...]) -> None:
        if response.status_code in expected:
            return
        if response.status_code == 429:
            retry = response.headers.get("Retry-After", "300")
            try:
                seconds = max(1, math.ceil(float(retry)))
            except (ValueError, OverflowError):
                try:
                    seconds = max(1, math.ceil((parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()))
                except (ValueError, TypeError, OverflowError):
                    seconds = 300
            raise PersonalDataReportingFailure("reporting_rate_limited", seconds)
        if response.status_code in {400, 401, 403}:
            raise PersonalDataReportingFailure("owner_authorization_required", 3600)
        raise PersonalDataReportingFailure("reporting_provider_unavailable", 300)
