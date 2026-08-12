# backend/src/application/services/auth_service.py
import hmac

from src.application.ports.token_service_port import TokenServicePort


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
    ) -> None:
        self._tokens = tokens
        self.enabled = enabled
        self.admin_username = admin_username
        self._admin_password = admin_password
        self.superadmin_username = superadmin_username
        self._superadmin_password = superadmin_password
        self.refresh_expire_days = refresh_expire_days
        self.cookie_secure = cookie_secure

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
            self.superadmin_username
            and self._matches(
                username,
                password,
                self.superadmin_username,
                self._superadmin_password,
            )
        )

    def create_access_token(self, username: str, generation: int | None = None) -> str:
        return self._tokens.create_access_token(username, generation)

    def create_refresh_token(self, username: str, generation: int | None = None) -> str:
        return self._tokens.create_refresh_token(username, generation)

    def decode_access_token(self, token: str) -> str:
        return self._tokens.decode_access_token(token)

    def decode_refresh_token(self, token: str) -> str:
        return self._tokens.decode_refresh_token(token)

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
        return hmac.compare_digest(username, expected_username) and hmac.compare_digest(
            password,
            expected_password,
        )
