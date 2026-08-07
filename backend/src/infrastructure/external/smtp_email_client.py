# backend/src/infrastructure/external/smtp_email_client.py
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from src.domain.ports.email_port import EmailPort

logger = logging.getLogger(__name__)


class SmtpEmailClient(EmailPort):
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        use_tls: bool = False,
        start_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_addr = from_addr
        self._use_tls = use_tls
        self._start_tls = start_tls

    async def send(self, to: list[str], subject: str, body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = self._from_addr
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            use_tls=self._use_tls,
            start_tls=self._start_tls,
        )
        logger.info(f"[메일 발송] to={to} subject={subject!r}")
