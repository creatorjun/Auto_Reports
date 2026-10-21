# backend/src/infrastructure/security/jwt_service.py
from datetime import datetime, timedelta, timezone
from threading import Lock
import re

from jose import JWTError, jwt

from src.application.ports.token_service_port import TokenServicePort
from src.domain.entities.auth_identity import AuthIdentity
from src.infrastructure.config.settings import Settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class JwtService(TokenServicePort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._superadmin_generation: int = 0
        self._lock = Lock()

    def bump_superadmin_generation(self) -> int:
        with self._lock:
            self._superadmin_generation += 1
            return self._superadmin_generation

    def current_superadmin_generation(self) -> int:
        return self._superadmin_generation

    def create_access_token(self, subject: str, generation: int | None = None) -> str:
        return self.create_identity_access_token(AuthIdentity(subject, subject), generation)

    def create_identity_access_token(self, identity: AuthIdentity, generation: int | None = None) -> str:
        return self._create(
            identity, ACCESS_TOKEN_TYPE,
            timedelta(minutes=self._settings.jwt_access_expire_minutes),
            generation=generation,
        )

    def create_refresh_token(self, subject: str, generation: int | None = None) -> str:
        return self.create_identity_refresh_token(AuthIdentity(subject, subject), generation)

    def create_identity_refresh_token(self, identity: AuthIdentity, generation: int | None = None) -> str:
        return self._create(
            identity, REFRESH_TOKEN_TYPE,
            timedelta(days=self._settings.jwt_refresh_expire_days),
            generation=generation,
        )

    def decode_access_token(self, token: str) -> str:
        return self.decode_access_identity(token).username

    def decode_refresh_token(self, token: str) -> str:
        return self.decode_refresh_identity(token).username

    def decode_access_identity(self, token: str) -> AuthIdentity:
        return self._decode(token, ACCESS_TOKEN_TYPE)

    def decode_refresh_identity(self, token: str) -> AuthIdentity:
        return self._decode(token, REFRESH_TOKEN_TYPE)

    def _create(
        self,
        identity: AuthIdentity,
        token_type: str,
        expire_delta: timedelta,
        generation: int | None = None,
    ) -> str:
        expire = datetime.now(timezone.utc) + expire_delta
        if identity.auth_provider == "jira":
            if type(identity.session_expires_at) is not int:
                raise ValueError("Jira session expiration required")
            expire = min(expire, datetime.fromtimestamp(identity.session_expires_at, timezone.utc))
        payload: dict = {
            "sub": identity.username,
            "type": token_type,
            "exp": expire,
            "auth_provider": identity.auth_provider,
        }
        if generation is not None:
            payload["gen"] = generation
        if identity.auth_provider == "jira":
            if type(identity.profile_version) is not int or identity.profile_version < 1:
                raise ValueError("Jira profile version required")
            payload["session_exp"] = identity.session_expires_at
            payload["profile_ver"] = identity.profile_version
            if identity.jira_grant_id is not None:
                if not isinstance(identity.jira_grant_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", identity.jira_grant_id):
                    raise ValueError("Invalid Jira grant identifier")
                payload["jira_grant_id"] = identity.jira_grant_id
        else:
            if identity.jira_grant_id is not None:
                raise ValueError("Local identity cannot contain a Jira grant")
            payload["display_name"] = identity.display_name
        return jwt.encode(payload, self._settings.jwt_secret, algorithm="HS256")

    def _decode(self, token: str, expected_type: str) -> AuthIdentity:
        try:
            payload = jwt.decode(
                token, self._settings.jwt_secret, algorithms=["HS256"],
                options={"require_exp": True, "require_sub": True},
            )
            if payload.get("type") != expected_type:
                raise ValueError("Token type mismatch")
            subject: str = payload["sub"]
            if not isinstance(subject, str) or not subject:
                raise ValueError("Invalid subject")
            provider = payload.get("auth_provider", "local")
            display_name = payload.get("display_name", subject)
            if provider not in {"local", "jira"} or not isinstance(display_name, str) or not display_name:
                raise ValueError("Invalid identity")
            if provider == "jira" and (not subject.startswith("jira:") or payload.get("gen") is not None):
                raise ValueError("Invalid Jira identity")
            session_exp = payload.get("session_exp") if provider == "jira" else None
            profile_version = payload.get("profile_ver") if provider == "jira" else None
            grant_id = payload.get("jira_grant_id")
            if grant_id is not None and (
                provider != "jira" or not isinstance(grant_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", grant_id)
            ):
                raise ValueError("Invalid Jira grant identifier")
            if provider == "jira" and (
                type(session_exp) is not int or payload["exp"] > session_exp
                or session_exp <= datetime.now(timezone.utc).timestamp()
                or type(profile_version) is not int or profile_version < 1
                or "display_name" in payload
            ):
                raise ValueError("Invalid Jira session expiration")
            gen = payload.get("gen")
            superadmin_enabled = bool(
                self._settings.login
                and self._settings.superadmin_username
                and self._settings.superadmin_password
                and self._settings.superadmin_username != self._settings.admin_username
            )
            if superadmin_enabled and subject == self._settings.superadmin_username and type(gen) is not int:
                raise ValueError("Superadmin session required")
            if gen is not None and gen != self._superadmin_generation:
                raise ValueError("Superadmin session invalidated")
            return AuthIdentity(subject, display_name, provider, session_exp, profile_version, grant_id)
        except (JWTError, ValueError, KeyError, TypeError) as e:
            raise ValueError("Invalid or expired token") from e
