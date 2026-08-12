# backend/src/application/ports/token_service_port.py
from abc import ABC, abstractmethod


class TokenServicePort(ABC):
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
