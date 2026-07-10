# backend/src/shared/audit_logger.py
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

AUDIT_LEVEL = 25
logging.addLevelName(AUDIT_LEVEL, "AUDIT")


class AuditLogger(logging.Logger):
    def audit(self, msg: str, *args, **kwargs):
        if self.isEnabledFor(AUDIT_LEVEL):
            self._log(AUDIT_LEVEL, msg, args, **kwargs)


logging.setLoggerClass(AuditLogger)

_AUDIT_FMT = "%(asctime)s [AUDIT] %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def get_audit_logger(log_dir: str = "logs") -> AuditLogger:
    logger: AuditLogger = logging.getLogger("audit")  # type: ignore[assignment]

    if logger.handlers:
        return logger

    logger.setLevel(AUDIT_LEVEL)
    logger.propagate = False

    formatter = logging.Formatter(_AUDIT_FMT, datefmt=_DATE_FMT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

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
        logger.addHandler(file_handler)
    except OSError:
        pass

    return logger
