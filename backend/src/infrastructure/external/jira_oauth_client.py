# backend/src/infrastructure/external/jira_oauth_client.py
import asyncio
import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

import httpx

from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort, JiraReportingGrant
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
        identity, _ = await self._exchange(code, False)
        return identity

    async def authenticate_reporting_owner(self, code: str) -> JiraReportingGrant:
        identity, refresh_token = await self._exchange(code, True)
        if not isinstance(refresh_token, str) or not refresh_token or len(refresh_token) > 32768:
            raise JiraLoginDenied("Reporting authorization requires offline access")
        return JiraReportingGrant(identity, refresh_token)

    async def _exchange(self, code: str, include_offline: bool) -> tuple[AuthIdentity, str | None]:
        try:
            async with asyncio.timeout(30):
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(10, connect=5),
                    follow_redirects=False,
                    transport=self._transport,
                ) as client:
                    return await self._authenticate(client, code, include_offline)
        except (httpx.HTTPError, TimeoutError):
            raise JiraLoginUnavailable("Jira login is temporarily unavailable") from None
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, JiraLoginDenied):
                raise
            raise JiraLoginDenied("Jira login could not be verified") from None

    async def _authenticate(self, client: httpx.AsyncClient, code: str, include_offline: bool) -> tuple[AuthIdentity, str | None]:
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
        access_token = token.get("access_token") if isinstance(token, dict) else None
        if not isinstance(access_token, str) or not access_token:
            raise JiraLoginDenied("Jira login could not be verified")
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
        base = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3"
        profile = self._json(await client.get(f"{base}/myself", headers=headers))
        if not isinstance(profile, dict) or profile.get("active") is not True or profile.get("accountType") != "atlassian":
            raise JiraLoginDenied("An active Jira account is required")
        account_id = profile.get("accountId")
        if not isinstance(account_id, str) or not re.fullmatch(r"[a-zA-Z0-9:_-]{1,128}", account_id):
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
        identity = AuthIdentity(
            f"jira:{cloud_id}:{account_id}", display_name.strip(), "jira",
            email_address=email_address(profile.get("emailAddress")),
        )
        if self._grants is not None and not include_offline:
            expires_in = token.get("expires_in")
            if type(expires_in) is not int or expires_in <= 0:
                raise JiraLoginDenied("Jira token expiration could not be verified")
            try:
                expires_at = received_at + timedelta(seconds=expires_in)
            except OverflowError:
                raise JiraLoginDenied("Jira token expiration could not be verified") from None
            grant_id = await self._grants.put(JiraUserGrant(cloud_id, account_id, access_token, expires_at), identity)
            identity = replace(identity, jira_grant_id=grant_id)
        return identity, token.get("refresh_token") if include_offline else None

    @staticmethod
    def _json(response: httpx.Response):
        if response.status_code == 429 or response.status_code >= 500:
            raise JiraLoginUnavailable("Jira login is temporarily unavailable")
        if response.status_code != 200:
            raise JiraLoginDenied("Jira login could not be verified")
        return response.json()
