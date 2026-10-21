# backend/src/infrastructure/external/jira_oauth_client.py
import asyncio
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

import httpx

from src.application.ports.jira_oauth_port import (
    JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort, JiraPersistentGrant, JiraReportingGrant,
)
from src.application.ports.jira_user_grant_port import JiraUserGrant, JiraUserGrantStorePort
from src.domain.entities.auth_identity import AuthIdentity
from src.infrastructure.external.jira_profile_fields import email_address

_SCOPES = ("read:jira-user", "read:jira-work")


class JiraOAuthClient(JiraOAuthPort):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        jira_base_url: str,
        project_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
        grants: JiraUserGrantStorePort | None = None,
    ) -> None:
        site = urlsplit(jira_base_url)
        callback = urlsplit(redirect_uri)
        if (
            not client_id or not client_secret or not project_key
            or site.scheme != "https" or not site.hostname or site.username or site.password
            or site.path.rstrip("/") or site.query or site.fragment
            or callback.scheme not in {"http", "https"} or not callback.hostname
            or callback.username or callback.password or callback.query or callback.fragment
        ):
            raise ValueError("Invalid Jira OAuth configuration")
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._site_url = jira_base_url.rstrip("/").lower()
        self._project_key = project_key
        self._transport = transport
        self._grants = grants

    def authorization_url(self, state: str, include_offline: bool = False) -> str:
        return "https://auth.atlassian.com/authorize?" + urlencode({
            "audience": "api.atlassian.com",
            "client_id": self._client_id,
            "scope": " ".join((*_SCOPES, "offline_access") if include_offline else _SCOPES),
            "redirect_uri": self._redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        })

    async def authenticate(self, code: str) -> AuthIdentity:
        identity, _, _ = await self._exchange(code, False)
        return identity

    async def authenticate_reporting_owner(self, code: str) -> JiraReportingGrant:
        identity, token, _ = await self._exchange(code, True)
        refresh_token = self._token_value(token.get("refresh_token"))
        return JiraReportingGrant(identity, refresh_token)

    async def authenticate_persistent(self, code: str) -> JiraPersistentGrant:
        identity, token, received_at = await self._exchange(code, True)
        _, cloud_id, account_id = identity.username.split(":", 2)
        grant = self._user_grant(cloud_id, account_id, token, received_at, include_refresh=True)
        return JiraPersistentGrant(identity, grant)

    async def refresh_user_grant(self, grant: JiraUserGrant) -> JiraUserGrant:
        async with self._client() as client:
            self._grant_owner(grant)
            refresh_token = self._token_value(grant.refresh_token)
            token = self._json(await client.post(
                "https://auth.atlassian.com/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": refresh_token,
                },
            ))
            return self._user_grant(
                grant.cloud_id, grant.account_id, token, datetime.now(timezone.utc), include_refresh=True,
            )

    async def validate_user_grant(self, grant: JiraUserGrant) -> AuthIdentity:
        async with self._client() as client:
            self._grant_owner(grant)
            if (
                not isinstance(grant.expires_at, datetime) or grant.expires_at.tzinfo is None
                or grant.expires_at.utcoffset() is None or grant.expires_at <= datetime.now(timezone.utc)
            ):
                raise JiraLoginDenied("Jira token expiration could not be verified")
            return await self._identity(client, self._token_value(grant.access_token), expected=grant)

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[httpx.AsyncClient]:
        try:
            async with asyncio.timeout(30):
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(10, connect=5),
                    follow_redirects=False,
                    transport=self._transport,
                ) as client:
                    yield client
        except (httpx.HTTPError, TimeoutError):
            raise JiraLoginUnavailable("Jira login is temporarily unavailable") from None
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, JiraLoginDenied):
                raise
            raise JiraLoginDenied("Jira login could not be verified") from None

    async def _exchange(self, code: str, include_offline: bool) -> tuple[AuthIdentity, dict, datetime]:
        async with self._client() as client:
            return await self._authenticate(client, code, include_offline)

    async def _authenticate(self, client: httpx.AsyncClient, code: str, include_offline: bool) -> tuple[AuthIdentity, dict, datetime]:
        token = self._json(await client.post(
            "https://auth.atlassian.com/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "redirect_uri": self._redirect_uri,
            },
        ))
        received_at = datetime.now(timezone.utc)
        access_token = self._token_value(token.get("access_token") if isinstance(token, dict) else None)
        identity = await self._identity(client, access_token)
        if self._grants is not None and not include_offline:
            _, cloud_id, account_id = identity.username.split(":", 2)
            grant = self._user_grant(cloud_id, account_id, token, received_at, include_refresh=False)
            grant_id = await self._grants.put(grant, identity)
            identity = replace(identity, jira_grant_id=grant_id)
        return identity, token, received_at

    async def _identity(
        self, client: httpx.AsyncClient, access_token: str, expected: JiraUserGrant | None = None,
    ) -> AuthIdentity:
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        resources = self._json(await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources", headers=headers,
        ))
        if not isinstance(resources, list):
            raise JiraLoginDenied("Jira site access is required")
        matching = [
            resource for resource in resources
            if isinstance(resource, dict)
            and str(resource.get("url", "")).rstrip("/").lower() == self._site_url
            and isinstance(resource.get("scopes"), list)
            and all(scope in resource["scopes"] for scope in _SCOPES)
        ]
        if len(matching) != 1:
            raise JiraLoginDenied("Jira site access is required")
        cloud_id = matching[0].get("id")
        if not isinstance(cloud_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,100}", cloud_id):
            raise JiraLoginDenied("Jira site could not be verified")
        if expected is not None and cloud_id != expected.cloud_id:
            raise JiraLoginDenied("Jira site could not be verified")
        base = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3"
        profile = self._json(await client.get(f"{base}/myself", headers=headers))
        if not isinstance(profile, dict) or profile.get("active") is not True or profile.get("accountType") != "atlassian":
            raise JiraLoginDenied("An active Jira account is required")
        account_id = profile.get("accountId")
        if not isinstance(account_id, str) or not re.fullmatch(r"[a-zA-Z0-9:_-]{1,128}", account_id):
            raise JiraLoginDenied("Jira identity could not be verified")
        if expected is not None and account_id != expected.account_id:
            raise JiraLoginDenied("Jira identity could not be verified")
        permissions = self._json(await client.get(
            f"{base}/mypermissions", headers=headers,
            params={"projectKey": self._project_key, "permissions": "BROWSE_PROJECTS"},
        ))
        permission_map = permissions.get("permissions") if isinstance(permissions, dict) else None
        browse = permission_map.get("BROWSE_PROJECTS") if isinstance(permission_map, dict) else None
        if not isinstance(browse, dict) or browse.get("havePermission") is not True:
            raise JiraLoginDenied("Jira project access is required")
        display_name = profile.get("displayName")
        if not isinstance(display_name, str) or not display_name.strip() or len(display_name) > 200:
            display_name = account_id
        return AuthIdentity(
            f"jira:{cloud_id}:{account_id}", display_name.strip(), "jira",
            email_address=email_address(profile.get("emailAddress")),
        )

    @staticmethod
    def _grant_owner(grant: JiraUserGrant) -> None:
        if (
            not isinstance(grant.cloud_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,100}", grant.cloud_id)
            or not isinstance(grant.account_id, str) or not re.fullmatch(r"[a-zA-Z0-9:_-]{1,128}", grant.account_id)
        ):
            raise JiraLoginDenied("Jira identity could not be verified")

    @staticmethod
    def _token_value(value: object) -> str:
        if (
            not isinstance(value, str) or not value or len(value) > 32768
            or not value.isascii() or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value)
        ):
            raise JiraLoginDenied("Jira token could not be verified")
        return value

    @classmethod
    def _user_grant(
        cls, cloud_id: str, account_id: str, token: object, received_at: datetime, include_refresh: bool,
    ) -> JiraUserGrant:
        if not isinstance(token, dict):
            raise JiraLoginDenied("Jira token could not be verified")
        access_token = cls._token_value(token.get("access_token"))
        refresh_token = cls._token_value(token.get("refresh_token")) if include_refresh else None
        expires_in = token.get("expires_in")
        if type(expires_in) is not int or expires_in <= 0:
            raise JiraLoginDenied("Jira token expiration could not be verified")
        try:
            expires_at = received_at + timedelta(seconds=expires_in)
        except OverflowError:
            raise JiraLoginDenied("Jira token expiration could not be verified") from None
        return JiraUserGrant(cloud_id, account_id, access_token, expires_at, refresh_token)

    @staticmethod
    def _json(response: httpx.Response):
        if response.status_code == 429 or response.status_code >= 500:
            raise JiraLoginUnavailable("Jira login is temporarily unavailable")
        if response.status_code != 200:
            raise JiraLoginDenied("Jira login could not be verified")
        return response.json()
