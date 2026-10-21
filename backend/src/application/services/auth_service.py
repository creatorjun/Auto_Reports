# backend/src/application/services/auth_service.py
import hmac
import secrets
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic

from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort
from src.application.ports.jira_login_port import JiraLoginPort
from src.application.ports.jira_user_grant_port import JiraUserGrantAccessPort
from src.application.ports.personal_data_port import PersonalDataProfilePort, PersonalDataReportingPort
from src.application.ports.token_service_port import TokenServicePort
from src.domain.entities.auth_identity import AuthIdentity


@dataclass
class _JiraLoginAttempt:
    expires_at: float
    cancelled: bool = False
    device_token: str | None = field(default=None, repr=False)
    identity: AuthIdentity | None = field(default=None, repr=False)


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
        jira_grants: JiraUserGrantAccessPort | None = None,
        jira_login: JiraLoginPort | None = None,
        jira_device_expire_days: int = 90,
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
        self._jira_grants = jira_grants
        self._jira_login = jira_login
        self.jira_device_expire_days = jira_device_expire_days
        self._jira_states: dict[str, float] = {}
        self._jira_privacy_states: dict[str, int] = {}
        self._jira_attempts: dict[str, _JiraLoginAttempt] = {}
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
            self._jira_attempts = {
                key: attempt for key, attempt in self._jira_attempts.items() if attempt.expires_at > now
            }
            if len(self._jira_states) + len(self._jira_attempts) >= 1024:
                raise JiraLoginUnavailable("Jira login is temporarily unavailable")
            self._jira_states[state] = now + self.jira_state_expire_seconds
            if privacy_generation is not None:
                self._jira_privacy_states[state] = privacy_generation
        if privacy_generation is not None:
            return state, self._jira_oauth.authorization_url(state, include_offline=True)
        if self._jira_login is not None:
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
            now = monotonic()
            if expiry is None or expiry <= now:
                raise JiraLoginDenied("Expired Jira login state")
            if privacy_generation is None:
                self._jira_attempts[state] = _JiraLoginAttempt(now + self.jira_state_expire_seconds)
        return privacy_generation

    async def cancel_jira_login(self, state: str | None) -> None:
        if not isinstance(state, str) or not state or len(state) > 128:
            return
        with self._jira_state_lock:
            if state in self._jira_privacy_states:
                return
            self._jira_states.pop(state, None)
            attempt = self._jira_attempts.get(state)
            if attempt is None:
                return
            attempt.cancelled = True
            device_token, identity = attempt.device_token, attempt.identity
        if device_token is not None:
            await self.forget_jira_login(device_token)
        elif identity is not None:
            await self.logout(identity)

    def _check_jira_attempt(self, attempt: _JiraLoginAttempt) -> None:
        with self._jira_state_lock:
            if attempt.cancelled or attempt.expires_at <= monotonic():
                raise JiraLoginDenied("Jira login was cancelled")

    def jira_login_cancelled(self, state: str | None) -> bool:
        with self._jira_state_lock:
            attempt = self._jira_attempts.get(state)
            return attempt is None or attempt.cancelled

    async def _complete_jira_attempt(
        self, attempt: _JiraLoginAttempt, identity: AuthIdentity, device_token: str | None,
    ) -> tuple[AuthIdentity, str | None]:
        with self._jira_state_lock:
            attempt.identity, attempt.device_token = identity, device_token
            cancelled = attempt.cancelled or attempt.expires_at <= monotonic()
            if not cancelled:
                attempt.expires_at = monotonic() + self.jira_state_expire_seconds
        if cancelled:
            if device_token is not None:
                await self.forget_jira_login(device_token)
            else:
                await self.logout(identity)
            raise JiraLoginDenied("Jira login was cancelled")
        return identity, device_token

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
        try:
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
        except BaseException:
            await self.logout(identity)
            raise

    async def complete_jira_login(self, code: str, remember_token: str | None, *, state: str) -> tuple[AuthIdentity, str | None]:
        with self._jira_state_lock:
            attempt = self._jira_attempts.get(state)
        if attempt is None:
            raise JiraLoginDenied("Invalid Jira login state")
        self._check_jira_attempt(attempt)
        if self._jira_login is None:
            identity = await self.authenticate_jira(code)
            return await self._complete_jira_attempt(attempt, identity, None)
        if not self.jira_enabled or self._personal_data is None:
            raise JiraLoginUnavailable("Jira login is not configured")
        if not code or len(code) > 4096:
            raise JiraLoginDenied("Invalid Jira authorization code")
        result = await self._jira_oauth.authenticate_persistent(code)
        self._check_jira_attempt(attempt)
        identity = result.identity
        if identity.auth_provider != "jira" or identity.username in {self.admin_username, self.superadmin_username}:
            raise JiraLoginDenied("Invalid Jira account identity")
        try:
            identity = await self._personal_data.register_identity(identity)
        except ValueError:
            raise JiraLoginDenied("Jira account is no longer available") from None
        self._check_jira_attempt(attempt)
        identity, device_token = await self._jira_login.finish_login(result.grant, identity, remember_token)
        return await self._complete_jira_attempt(attempt, identity, device_token)

    async def resume_jira_login(self, remember_token: str | None) -> AuthIdentity | None:
        if not self.jira_enabled or self._jira_login is None or not remember_token:
            return None
        try:
            return await self._jira_login.resume(remember_token)
        except JiraLoginDenied:
            return None

    async def has_remembered_jira_login(self, remember_token: str | None) -> bool:
        return bool(
            self.jira_enabled and self._jira_login is not None and remember_token
            and await self._jira_login.has_device(remember_token)
        )

    async def forget_jira_login(self, remember_token: str | None) -> None:
        if self._jira_login is not None and remember_token:
            await self._jira_login.forget(remember_token)

    async def logout(self, identity: AuthIdentity) -> None:
        if self._jira_grants is not None and identity.auth_provider == "jira" and identity.jira_grant_id:
            await self._jira_grants.revoke(identity.jira_grant_id, identity)

    async def clear_jira_grants(self) -> None:
        if self._jira_login is not None:
            await self._jira_login.reconcile_privacy()
        elif self._jira_grants is not None:
            await self._jira_grants.clear()

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
            identity = await self._personal_data.resolve_identity(identity)
            if self._jira_login is not None:
                identity = await self._jira_login.resolve(identity)
            return identity
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
