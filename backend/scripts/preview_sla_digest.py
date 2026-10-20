# backend/scripts/preview_sla_digest.py
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application.ports.email_port import EmailPort
from src.application.use_cases.notify_sla_digest import NotifySlaDigestUseCase
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.sla_digest_jira_source import SlaDigestJiraSource
from src.presentation.email.sla_digest_renderer import SlaDigestRenderer


class PreviewEmail(EmailPort):
    def __init__(self) -> None:
        self.body: str | None = None
        self.subject: str | None = None
        self.recipient_count = 0

    async def send(self, to: list[str], subject: str, body: str) -> None:
        self.body = body
        self.subject = subject
        self.recipient_count = len(to)


async def preview(output: Path, env_file: Path) -> dict:
    settings = Settings(_env_file=env_file)
    email = PreviewEmail()
    async with SlaDigestJiraSource(
        settings.jira_base_url, settings.jira_email, settings.jira_api_token, settings.project_key,
    ) as source:
        use_case = NotifySlaDigestUseCase(
            source, email, SlaDigestRenderer(), settings.notify_todo_to, settings.jira_base_url,
        )
        count = await use_case.execute()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        email.body or '<!doctype html><html lang="ko"><meta charset="utf-8"><title>SLA 미리보기</title><p>발송 대상 또는 수신자가 없습니다.</p></html>',
        encoding="utf-8",
    )
    return {
        "mode": "preview_only", "email_sent": False, "ticket_count": count,
        "recipient_count": email.recipient_count, "subject": email.subject, "output": str(output),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="실제 메일을 보내지 않고 Jira SLA 일일 메일 HTML을 생성합니다.")
    parser.add_argument("--output", type=Path, default=root / "output/sla-digest-validation/preview.html")
    parser.add_argument("--env-file", type=Path, default=root / ".env")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(preview(args.output, args.env_file)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
