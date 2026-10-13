# backend/src/infrastructure/logging/audit_logger.py
import logging
import json
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from src.application.ports.audit_port import AuditPort
from src.domain.constants import KST
from src.infrastructure.logging.audit_format import safe_fields, safe_text

AUDIT_LEVEL = 25
logging.addLevelName(AUDIT_LEVEL, "AUDIT")


class AuditLogger(AuditPort):
    def __init__(self, log_dir: str = "logs") -> None:
        self._logger = logging.getLogger("audit")
        self._handlers: list[logging.Handler] = []
        if self._logger.handlers:
            return
        self._logger.setLevel(AUDIT_LEVEL)
        self._logger.propagate = False
        formatter = logging.Formatter(
            "%(asctime)s [AUDIT] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        self._logger.addHandler(stream_handler)
        self._handlers.append(stream_handler)
        try:
            os.makedirs(log_dir, exist_ok=True)
            file_handler = TimedRotatingFileHandler(
                filename=os.path.join(log_dir, "audit.log"),
                when="midnight",
                interval=1,
                backupCount=90,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
            self._handlers.append(file_handler)
        except OSError as error:
            self._logger.warning("감사 로그 파일을 열 수 없습니다: %s", error)

    def record(self, event: str, **fields: object) -> None:
        message = json.dumps({
            "timestamp": datetime.now(KST).isoformat(),
            "event": safe_text(event, 100),
            "fields": safe_fields(fields),
        }, ensure_ascii=False)
        self._logger.log(AUDIT_LEVEL, message)

    def close(self) -> None:
        for handler in self._handlers:
            self._logger.removeHandler(handler)
            handler.close()
        self._handlers.clear()
