# backend/scripts/verify_rovo_automation.py
import argparse
import asyncio
import json
import logging

from src.infrastructure.config.settings import Settings
from src.infrastructure.external.rovo_automation_client import RovoAutomationClient


async def verify(execute: bool) -> int:
    try:
        settings = Settings()
        client = RovoAutomationClient(
            webhook_url=settings.rovo_automation_webhook_url,
            webhook_token=settings.rovo_automation_webhook_token,
            result_issue_key=settings.rovo_automation_result_issue_key,
            jira_base_url=settings.jira_base_url,
            jira_email=settings.jira_email,
            jira_api_token=settings.jira_api_token,
            timeout_seconds=settings.rovo_automation_timeout_seconds,
            poll_seconds=settings.rovo_automation_poll_seconds,
        )
    except ValueError:
        print(json.dumps({"configured": False, "error": "Rovo 설정값을 확인하세요."}, ensure_ascii=False))
        return 1
    try:
        if not execute:
            print(json.dumps({"configured": True, "executed": False, "note": "연결 시험은 --execute 옵션이 필요합니다."}, ensure_ascii=False))
            return 0
        prompt = (
            '합성 데이터 연결 시험입니다. 실제 회사 자료를 조회하거나 변경하지 마세요. '
            '테스트 기간 2026-01-01~2026-01-31, 생성 20건, 완료 15건입니다. '
            '실제 병목 이력과 SLA 분모는 제공되지 않았습니다. '
            '고객명이나 티켓 번호를 지어내지 마세요. '
            'JSON 객체만 출력하세요. summary는 한국어 요약 문자열, risks는 확인 한계 문자열 배열, '
            'bottlenecks는 빈 배열, recommendations는 점검 제안 문자열 배열, sentiment는 warning입니다. '
            '배열은 각각 최대 5개, 원소는 300자 이하, summary는 1000자 이하입니다.'
        )
        analysis = await client.analyze(prompt)
        print(json.dumps({
            "configured": True, "executed": True, "verified_result": analysis is not None,
            "provider": analysis.provider if analysis else None,
            "analyzed_at": analysis.analyzed_at if analysis else None,
            "company_report_transmitted": False,
        }, ensure_ascii=False))
        return 0 if analysis else 1
    finally:
        await client.aclose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Rovo Automation 합성 데이터 연결 검증")
    parser.add_argument("--execute", action="store_true", help="웹훅을 1회 실행합니다. Rovo 사용량이 발생할 수 있습니다.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    return asyncio.run(verify(args.execute))


if __name__ == "__main__":
    raise SystemExit(main())
