# backend/src/application/services/auth_service.py
import hmac
import secrets
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic

from src.application.ports.jira_oauth_port import JiraLoginDenied, JiraLoginUnavailable, JiraOAuthPort
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
        self._jira_states: dict[str, float] = {}
        self._jira_state_lock = Lock()
        self.jira_state_expire_seconds = 600

    @property
    def jira_enabled(self) -> bool:
        return self.enabled and self._jira_oauth is not None

    def begin_jira_login(self) -> tuple[str, str]:
        if not self.jira_enabled:
            raise JiraLoginUnavailable("Jira login is not configured")
        now = monotonic()
        state = secrets.token_urlsafe(32)
        with self._jira_state_lock:
            self._jira_states = {key: expiry for key, expiry in self._jira_states.items() if expiry > now}
            if len(self._jira_states) >= 1024:
                raise JiraLoginUnavailable("Jira login is temporarily unavailable")
            self._jira_states[state] = now + self.jira_state_expire_seconds
        return state, self._jira_oauth.authorization_url(state)

    def consume_jira_state(self, state: str | None, cookie_state: str | None) -> None:
        if not state or not cookie_state or len(state) > 128 or len(cookie_state) > 128:
            raise JiraLoginDenied("Invalid Jira login state")
        if not hmac.compare_digest(state.encode("utf-8"), cookie_state.encode("utf-8")):
            raise JiraLoginDenied("Invalid Jira login state")
        with self._jira_state_lock:
            expiry = self._jira_states.pop(state, None)
        if expiry is None or expiry <= monotonic():
            raise JiraLoginDenied("Expired Jira login state")

    async def authenticate_jira(self, code: str) -> AuthIdentity:
        if not self.jira_enabled:
            raise JiraLoginUnavailable("Jira login is not configured")
        if not code or len(code) > 4096:
            raise JiraLoginDenied("Invalid Jira authorization code")
        identity = await self._jira_oauth.authenticate(code)
        if identity.auth_provider != "jira" or identity.username in {self.admin_username, self.superadmin_username}:
            raise JiraLoginDenied("Invalid Jira account identity")
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
