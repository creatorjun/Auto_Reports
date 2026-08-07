# mail_test.py
import asyncio
import os
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[.env] {env_path} 로드 완료")
    else:
        print(f"[.env] 파일 없음: {env_path}")
except ImportError:
    print("[.env] python-dotenv 미설치 — 환경변수에서 직접 읽기")

try:
    import aiosmtplib
except ImportError:
    print("[ERROR] aiosmtplib 미설치: pip install aiosmtplib")
    raise

SMTP_HOST      = os.getenv("SMTP_HOST", "")
SMTP_PORT      = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER      = os.getenv("SMTP_USER", "")
SMTP_PASSWORD  = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM      = os.getenv("SMTP_FROM") or SMTP_USER
SMTP_USE_TLS   = os.getenv("SMTP_USE_TLS", "false").lower() == "true"
SMTP_START_TLS = os.getenv("SMTP_START_TLS", "true").lower() == "true"
NOTIFY_TO_RAW  = os.getenv("NOTIFY_TODO_TO", "")

import json, re
try:
    NOTIFY_TO: list[str] = json.loads(NOTIFY_TO_RAW) if NOTIFY_TO_RAW.strip().startswith("[") else [NOTIFY_TO_RAW]
except Exception:
    NOTIFY_TO = [NOTIFY_TO_RAW]

SUBJECT = "[TAC] SMTP 메일 테스트"
BODY = """
<html><body style='font-family:sans-serif;'>
<h2>&#9989; TAC Auto Reports 메일 연결 테스트</h2>
<p>SMTP 설정이 정상적으로 동작하고 있습니다.</p>
<table style='border-collapse:collapse;font-size:14px;'>
  <tr><td style='padding:4px 12px;color:#6b7280;'>SMTP_HOST</td><td style='padding:4px 12px;'>{host}</td></tr>
  <tr><td style='padding:4px 12px;color:#6b7280;'>SMTP_PORT</td><td style='padding:4px 12px;'>{port}</td></tr>
  <tr><td style='padding:4px 12px;color:#6b7280;'>SMTP_USER</td><td style='padding:4px 12px;'>{user}</td></tr>
  <tr><td style='padding:4px 12px;color:#6b7280;'>USE_TLS</td><td style='padding:4px 12px;'>{use_tls}</td></tr>
  <tr><td style='padding:4px 12px;color:#6b7280;'>START_TLS</td><td style='padding:4px 12px;'>{start_tls}</td></tr>
</table>
</body></html>
""".format(
    host=SMTP_HOST, port=SMTP_PORT, user=SMTP_USER,
    use_tls=SMTP_USE_TLS, start_tls=SMTP_START_TLS,
)


async def main() -> None:
    print("\n=== SMTP 설정 ===")
    print(f"  SMTP_HOST      : {SMTP_HOST!r}")
    print(f"  SMTP_PORT      : {SMTP_PORT}")
    print(f"  SMTP_USER      : {SMTP_USER!r}")
    print(f"  SMTP_FROM      : {SMTP_FROM!r}")
    print(f"  SMTP_USE_TLS   : {SMTP_USE_TLS}")
    print(f"  SMTP_START_TLS : {SMTP_START_TLS}")
    print(f"  NOTIFY_TO      : {NOTIFY_TO}")

    if not SMTP_HOST:
        print("\n[ERROR] SMTP_HOST 가 비어 있습니다. .env 파일을 확인하세요.")
        return
    if not NOTIFY_TO or not NOTIFY_TO[0]:
        print("\n[ERROR] NOTIFY_TODO_TO 가 비어 있습니다. .env 파일을 확인하세요.")
        return

    msg = MIMEMultipart("alternative")
    msg["From"]    = SMTP_FROM
    msg["To"]      = ", ".join(NOTIFY_TO)
    msg["Subject"] = SUBJECT
    msg.attach(MIMEText(BODY, "html", "utf-8"))

    print(f"\n[INFO] 메일 발송 시도 → {NOTIFY_TO} ...")
    try:
        response = await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=SMTP_USE_TLS,
            start_tls=SMTP_START_TLS,
        )
        print(f"[SUCCESS] 메일 발송 성공 \u2705")
        print(f"  SMTP 응답: {response}")
    except aiosmtplib.SMTPException as e:
        print(f"[FAIL] SMTP 오류: {type(e).__name__}: {e}")
        traceback.print_exc()
    except OSError as e:
        print(f"[FAIL] 네트워크 오류 (호스트/포트 확인): {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"[FAIL] 예상치 못한 오류: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
