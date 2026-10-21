# backend/src/infrastructure/external/jira_personal_data_client.py
import asyncio
import math
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from src.application.ports.personal_data_port import PersonalDataReportingFailure, PersonalDataUserSourcePort
from src.application.services.snapshot_personal_data import is_person_name, valid_account_id
from src.domain.entities.personal_data import PersonalDataProfile


class JiraPersonalDataClient(PersonalDataUserSourcePort):
    def __init__(self, base_url: str, email: str, api_token: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = (email, api_token)
        self._transport = transport

    async def get_profile(self, account_id: str) -> PersonalDataProfile:
        if not valid_account_id(account_id):
            raise PersonalDataReportingFailure("invalid_profile_account")
        try:
            async with asyncio.timeout(25):
                async with httpx.AsyncClient(
                    auth=self._auth, timeout=httpx.Timeout(20, connect=5),
                    follow_redirects=False, transport=self._transport,
                ) as client:
                    response = await client.get(
                        self._base_url + "/rest/api/3/user",
                        params={"accountId": account_id}, headers={"Accept": "application/json"},
                    )
                    if response.status_code == 429:
                        raise PersonalDataReportingFailure("profile_rate_limited", self._retry_seconds(response.headers.get("Retry-After")))
                    if response.status_code in {401, 403}:
                        raise PersonalDataReportingFailure("profile_access_unavailable", 3600)
                    if response.status_code != 200:
                        raise PersonalDataReportingFailure("profile_lookup_unavailable")
                    payload = response.json()
                    if not isinstance(payload, dict) or payload.get("accountId") != account_id:
                        raise PersonalDataReportingFailure("invalid_profile_response")
                    name = payload.get("displayName")
                    if not is_person_name(name) or len(name.strip()) > 200:
                        raise PersonalDataReportingFailure("invalid_profile_response")
                    return PersonalDataProfile(account_id, name.strip(), datetime.now(timezone.utc))
        except (httpx.HTTPError, TimeoutError):
            raise PersonalDataReportingFailure("profile_network_unavailable") from None
        except (ValueError, TypeError):
            raise PersonalDataReportingFailure("invalid_profile_response") from None

    @staticmethod
    def _retry_seconds(value: str | None) -> int:
        try:
            seconds = float(value or "300")
            if not math.isfinite(seconds):
                raise ValueError
            return max(1, math.ceil(seconds))
        except (ValueError, OverflowError):
            try:
                return max(1, math.ceil((parsedate_to_datetime(value or "") - datetime.now(timezone.utc)).total_seconds()))
            except (ValueError, TypeError, OverflowError):
                return 300
