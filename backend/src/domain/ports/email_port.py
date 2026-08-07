# backend/src/domain/ports/email_port.py
from abc import ABC, abstractmethod


class EmailPort(ABC):
    @abstractmethod
    async def send(self, to: list[str], subject: str, body: str) -> None: ...
