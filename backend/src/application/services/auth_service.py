# backend/src/application/services/auth_service.py
import hmac
import secrets
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic

from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort
from src.application.ports.personal_data_port import PersonalDataProfilePort, PersonalDataReportingPort
from src.application.ports.token_service_port import TokenServicePort
from src.domain.entities.auth_identity import AuthIdentity


class AuthService:
    def __init__(
        self,
        tokens: TokenServicePort,
        enabled: bool,
        admin_username: str,
        admin_password: str,
        superadmin_username: str,
        superadmin_password: str,
        refresh_expire_days: int,
        cookie_secure: bool,
        jira_oauth: JiraOAuthPort | None = None,
        personal_data: PersonalDataProfilePort | None = None,
        reporting: PersonalDataReportingPort | None = None,
        privacy_owner_account_id: str = "",
    ) -> None:
        self._tokens = tokens
        self.enabled = enabled
        self.admin_username = admin_username
        self._admin_password = admin_password
        self.superadmin_username = superadmin_username
        self._superadmin_password = superadmin_password
        self.refresh_expire_days = refresh_expire_days
        self.cookie_secure = cookie_secure
        self._jira_oauth = jira_oauth
        self._personal_data = personal_data
        self._reporting = reporting
        self._privacy_owner_account_id = privacy_owner_account_id
        self._jira_states: dict[str, float] = {}
        self._jira_privacy_states: dict[str, int] = {}
        self._jira_state_lock = Lock()
        self.jira_state_expire_seconds = 600

    @property
    def jira_enabled(self) -> bool:
        return self.enabled and self._jira_oauth is not None

    def begin_jira_login(self, privacy_generation: int | None = None) -> tuple[str, str]:
        if not self.jira_enabled:
            raise JiraLoginUnavailable("Jira login is not configured")
        now = monotonic()
        state = secrets.token_urlsafe(32)
        with self._jira_state_lock:
            self._jira_states = {key: expiry for key, expiry in self._jira_states.items() if expiry > now}
            self._jira_privacy_states = {
                key: generation for key, generation in self._jira_privacy_states.items() if key in self._jira_states
            }
            if len(self._jira_states) >= 1024:
                raise JiraLoginUnavailable("Jira login is temporarily unavailable")
            self._jira_states[state] = now + self.jira_state_expire_seconds
            if privacy_generation is not None:
                self._jira_privacy_states[state] = privacy_generation
        if privacy_generation is not None:
            return state, self._jira_oauth.authorization_url(state, include_offline=True)
        return state, self._jira_oauth.authorization_url(state)

    def begin_jira_privacy(self) -> tuple[str, str]:
        if self._reporting is None or not self._privacy_owner_account_id:
            raise JiraLoginUnavailable("Personal data reporting is not configured")
        return self.begin_jira_login(self.current_superadmin_generation())

    def consume_jira_state(self, state: str | None, cookie_state: str | None) -> int | None:
        if not state or not cookie_state or len(state) > 128 or len(cookie_state) > 128:
            raise JiraLoginDenied("Invalid Jira login state")
        if not hmac.compare_digest(state.encode("utf-8"), cookie_state.encode("utf-8")):
            raise JiraLoginDenied("Invalid Jira login state")
        with self._jira_state_lock:
            expiry = self._jira_states.pop(state, None)
            privacy_generation = self._jira_privacy_states.pop(state, None)
        if expiry is None or expiry <= monotonic():
            raise JiraLoginDenied("Expired Jira login state")
        return privacy_generation

    async def connect_jira_privacy(self, code: str, root_refresh: str | None, generation: int) -> None:
        if not self.jira_enabled or self._reporting is None or not self._privacy_owner_account_id:
            raise JiraLoginUnavailable("Personal data reporting is not configured")
        try:
            identity = self.decode_refresh_identity(root_refresh or "")
        except ValueError:
            raise JiraLoginDenied("Administrator session expired") from None
        if (
            identity.auth_provider != "local" or not self.is_superadmin_user(identity.username)
            or generation != self.current_superadmin_generation() or not code or len(code) > 4096
        ):
            raise JiraLoginDenied("Administrator session required")
        grant = await self._jira_oauth.authenticate_reporting_owner(code)
        account_parts = grant.identity.username.split(":", 2)
        if (
            grant.identity.auth_provider != "jira" or len(account_parts) != 3
            or not hmac.compare_digest(account_parts[2], self._privacy_owner_account_id)
        ):
            raise JiraLoginDenied("The configured application owner must authorize reporting")
        try:
            self.decode_refresh_identity(root_refresh or "")
        except ValueError:
            raise JiraLoginDenied("Administrator session expired") from None
        if generation != self.current_superadmin_generation():
            raise JiraLoginDenied("Administrator session expired")
        await self._reporting.save_reporting_grant(account_parts[2], grant.refresh_token)

    async def jira_privacy_status(self) -> dict:
        if self._reporting is None:
            raise JiraLoginUnavailable("Personal data reporting is not configured")
        return await self._reporting.reporting_status()

    async def run_jira_privacy(self) -> dict:
        if self._reporting is None:
            raise JiraLoginUnavailable("Personal data reporting is not configured")
        return await self._reporting.run_reporting()

    async def authenticate_jira(self, code: str) -> AuthIdentity:
        if not self.jira_enabled:
            raise JiraLoginUnavailable("Jira login is not configured")
        if not code or len(code) > 4096:
            raise JiraLoginDenied("Invalid Jira authorization code")
        identity = await self._jira_oauth.authenticate(code)
        if identity.auth_provider != "jira" or identity.username in {self.admin_username, self.superadmin_username}:
            raise JiraLoginDenied("Invalid Jira account identity")
        if self._personal_data is None:
            raise JiraLoginUnavailable("Jira profile storage is not configured")
        try:
            identity = await self._personal_data.register_identity(identity)
        except ValueError:
            raise JiraLoginDenied("Jira account is no longer available") from None
        return replace(
            identity,
            session_expires_at=int((datetime.now(timezone.utc) + timedelta(days=self.refresh_expire_days)).timestamp()),
        )

    def is_valid_credentials(self, username: str, password: str) -> bool:
        if not password:
            return False
        return self._matches(
            username,
            password,
            self.admin_username,
            self._admin_password,
        ) or self.is_superadmin(username, password)

    def is_superadmin(self, username: str, password: str) -> bool:
        return bool(
            self.is_superadmin_user(username)
            and self._matches(
                username,
                password,
                self.superadmin_username,
                self._superadmin_password,
            )
        )

    def is_superadmin_user(self, username: str) -> bool:
        return bool(
            self.enabled
            and self.superadmin_username
            and self._superadmin_password
            and self.superadmin_username != self.admin_username
            and hmac.compare_digest(username.encode("utf-8"), self.superadmin_username.encode("utf-8"))
        )

    def create_access_token(self, username: str, generation: int | None = None) -> str:
        return self._tokens.create_access_token(username, generation)

    def create_refresh_token(self, username: str, generation: int | None = None) -> str:
        return self._tokens.create_refresh_token(username, generation)

    def decode_access_token(self, token: str) -> str:
        return self.decode_access_identity(token).username

    def decode_refresh_token(self, token: str) -> str:
        return self.decode_refresh_identity(token).username

    def create_identity_access_token(self, identity: AuthIdentity, generation: int | None = None) -> str:
        return self._tokens.create_identity_access_token(identity, generation)

    def create_identity_refresh_token(self, identity: AuthIdentity, generation: int | None = None) -> str:
        return self._tokens.create_identity_refresh_token(identity, generation)

    def decode_access_identity(self, token: str) -> AuthIdentity:
        return self._validate_identity(self._tokens.decode_access_identity(token))

    def decode_refresh_identity(self, token: str) -> AuthIdentity:
        return self._validate_identity(self._tokens.decode_refresh_identity(token))

    async def resolve_access_identity(self, token: str) -> AuthIdentity:
        return await self._resolve_identity(self.decode_access_identity(token))

    async def resolve_refresh_identity(self, token: str) -> AuthIdentity:
        return await self._resolve_identity(self.decode_refresh_identity(token))

    async def _resolve_identity(self, identity: AuthIdentity) -> AuthIdentity:
        if identity.auth_provider == "jira":
            if self._personal_data is None:
                raise ValueError("Jira profile storage is not configured")
            return await self._personal_data.resolve_identity(identity)
        return identity

    def _validate_identity(self, identity: AuthIdentity) -> AuthIdentity:
        if identity.auth_provider == "jira" and (
            not self.jira_enabled or identity.username in {self.admin_username, self.superadmin_username}
            or identity.session_expires_at is None
        ):
            raise ValueError("Invalid Jira account identity")
        return identity

    def begin_superadmin_session(self) -> int:
        return self._tokens.bump_superadmin_generation()

    def current_superadmin_generation(self) -> int:
        return self._tokens.current_superadmin_generation()

    @staticmethod
    def _matches(
        username: str,
        password: str,
        expected_username: str,
        expected_password: str,
    ) -> bool:
        return hmac.compare_digest(username.encode("utf-8"), expected_username.encode("utf-8")) and hmac.compare_digest(
            password.encode("utf-8"),
            expected_password.encode("utf-8"),
        )
