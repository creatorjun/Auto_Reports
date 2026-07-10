# backend/src/infrastructure/security/jwt_service.py
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from jose import JWTError, jwt

from src.infrastructure.config.settings import Settings, get_settings

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class JwtService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_access_token(self, subject: str) -> str:
        return self._create(
            subject, ACCESS_TOKEN_TYPE,
            timedelta(minutes=self._settings.jwt_access_expire_minutes),
        )

    def create_refresh_token(self, subject: str) -> str:
        return self._create(
            subject, REFRESH_TOKEN_TYPE,
            timedelta(days=self._settings.jwt_refresh_expire_days),
        )

    def decode_access_token(self, token: str) -> str:
        return self._decode(token, ACCESS_TOKEN_TYPE)

    def decode_refresh_token(self, token: str) -> str:
        return self._decode(token, REFRESH_TOKEN_TYPE)

    def _create(self, subject: str, token_type: str, expire_delta: timedelta) -> str:
        expire = datetime.now(timezone.utc) + expire_delta
        payload = {"sub": subject, "type": token_type, "exp": expire}
        return jwt.encode(payload, self._settings.jwt_secret, algorithm="HS256")

    def _decode(self, token: str, expected_type: str) -> str:
        try:
            payload = jwt.decode(token, self._settings.jwt_secret, algorithms=["HS256"])
            if payload.get("type") != expected_type:
                raise ValueError("Token type mismatch")
            return payload["sub"]
        except (JWTError, ValueError, KeyError) as e:
            raise ValueError("Invalid or expired token") from e


@lru_cache
def get_jwt_service() -> JwtService:
    return JwtService(get_settings())
