# backend/src/infrastructure/security/jwt_service.py
from datetime import datetime, timedelta, timezone
from threading import Lock

from jose import JWTError, jwt

from src.application.ports.token_service_port import TokenServicePort
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
        return self._create(
            subject, ACCESS_TOKEN_TYPE,
            timedelta(minutes=self._settings.jwt_access_expire_minutes),
            generation=generation,
        )

    def create_refresh_token(self, subject: str, generation: int | None = None) -> str:
        return self._create(
            subject, REFRESH_TOKEN_TYPE,
            timedelta(days=self._settings.jwt_refresh_expire_days),
            generation=generation,
        )

    def decode_access_token(self, token: str) -> str:
        return self._decode(token, ACCESS_TOKEN_TYPE)

    def decode_refresh_token(self, token: str) -> str:
        return self._decode(token, REFRESH_TOKEN_TYPE)

    def _create(
        self,
        subject: str,
        token_type: str,
        expire_delta: timedelta,
        generation: int | None = None,
    ) -> str:
        expire = datetime.now(timezone.utc) + expire_delta
        payload: dict = {"sub": subject, "type": token_type, "exp": expire}
        if generation is not None:
            payload["gen"] = generation
        return jwt.encode(payload, self._settings.jwt_secret, algorithm="HS256")

    def _decode(self, token: str, expected_type: str) -> str:
        try:
            payload = jwt.decode(token, self._settings.jwt_secret, algorithms=["HS256"])
            if payload.get("type") != expected_type:
                raise ValueError("Token type mismatch")
            subject: str = payload["sub"]
            gen = payload.get("gen")
            if gen is not None and gen != self._superadmin_generation:
                raise ValueError("Superadmin session invalidated")
            return subject
        except (JWTError, ValueError, KeyError) as e:
            raise ValueError("Invalid or expired token") from e
