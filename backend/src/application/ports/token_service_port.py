# backend/src/application/ports/token_service_port.py
from abc import ABC, abstractmethod

from src.domain.entities.auth_identity import AuthIdentity


class TokenServicePort(ABC):
    @abstractmethod
    def create_identity_access_token(self, identity: AuthIdentity, generation: int | None = None) -> str: ...

    @abstractmethod
    def create_identity_refresh_token(self, identity: AuthIdentity, generation: int | None = None) -> str: ...

    @abstractmethod
    def decode_access_identity(self, token: str) -> AuthIdentity: ...

    @abstractmethod
    def decode_refresh_identity(self, token: str) -> AuthIdentity: ...

    @abstractmethod
    def create_access_token(self, subject: str, generation: int | None = None) -> str: ...

    @abstractmethod
    def create_refresh_token(self, subject: str, generation: int | None = None) -> str: ...

    @abstractmethod
    def decode_access_token(self, token: str) -> str: ...

    @abstractmethod
    def decode_refresh_token(self, token: str) -> str: ...

    @abstractmethod
    def bump_superadmin_generation(self) -> int: ...

    @abstractmethod
    def current_superadmin_generation(self) -> int: ...
