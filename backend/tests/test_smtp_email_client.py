# backend/tests/test_smtp_email_client.py
import unittest
from unittest.mock import AsyncMock, patch

from aiosmtplib.errors import SMTPConnectError, SMTPRecipientRefused

from src.infrastructure.external.smtp_email_client import SmtpEmailClient


class SmtpEmailClientTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.client = SmtpEmailClient(
            host="smtp.example.test", port=587, username="smtp-user", password="smtp-password",
            from_addr="noreply@example.test", start_tls=True,
        )
        self.recipients = [f"recipient-{index}@example.test" for index in range(5)]

    async def test_all_recipients_accepted_sends_one_message_and_logs_success(self) -> None:
        send = AsyncMock(return_value=({}, "accepted"))
        with (
            patch("src.infrastructure.external.smtp_email_client.aiosmtplib.send", send),
            patch("src.infrastructure.external.smtp_email_client.logger") as logger,
        ):
            await self.client.send(self.recipients, "SLA daily", "<p>임박 티켓</p>")

        send.assert_awaited_once()
        message = send.await_args.args[0]
        self.assertEqual(", ".join(self.recipients), message["To"])
        self.assertEqual("noreply@example.test", message["From"])
        self.assertEqual("SLA daily", message["Subject"])
        self.assertEqual("<p>임박 티켓</p>", message.get_payload()[0].get_payload(decode=True).decode("utf-8"))
        self.assertEqual({
            "hostname": "smtp.example.test", "port": 587, "use_tls": False, "start_tls": True,
            "username": "smtp-user", "password": "smtp-password",
        }, send.await_args.kwargs)
        logger.info.assert_called_once()

    async def test_partial_refusal_raises_without_exposing_addresses_or_logging_success(self) -> None:
        rejected = self.recipients[2]
        send = AsyncMock(return_value=({
            rejected: SMTPRecipientRefused(550, f"rejected {rejected}", rejected),
        }, "accepted other recipients"))
        with (
            patch("src.infrastructure.external.smtp_email_client.aiosmtplib.send", send),
            patch("src.infrastructure.external.smtp_email_client.logger") as logger,
        ):
            with self.assertRaises(RuntimeError) as error:
                await self.client.send(self.recipients, "SLA daily", "<p>임박 티켓</p>")

        self.assertEqual("SMTP delivery refused for 1 of 5 recipients", str(error.exception))
        for value in (*self.recipients, "smtp-password", "smtp-user"):
            self.assertNotIn(value, str(error.exception))
        send.assert_awaited_once()
        logger.info.assert_not_called()

    async def test_transport_failure_propagates_without_logging_success(self) -> None:
        failure = SMTPConnectError("SMTP connection failed")
        send = AsyncMock(side_effect=failure)
        with (
            patch("src.infrastructure.external.smtp_email_client.aiosmtplib.send", send),
            patch("src.infrastructure.external.smtp_email_client.logger") as logger,
        ):
            with self.assertRaises(SMTPConnectError) as error:
                await self.client.send(self.recipients, "SLA daily", "<p>임박 티켓</p>")

        self.assertIs(failure, error.exception)
        send.assert_awaited_once()
        logger.info.assert_not_called()
