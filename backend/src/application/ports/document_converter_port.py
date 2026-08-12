# backend/src/application/ports/document_converter_port.py
from abc import ABC, abstractmethod


class DocumentConverterPort(ABC):
    @abstractmethod
    def supports(self, filename: str) -> bool: ...

    @abstractmethod
    async def convert_to_pdf(self, source_path: str) -> bytes: ...
