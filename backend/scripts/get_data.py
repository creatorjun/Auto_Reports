# backend/scripts/get_data.py
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

_here = Path(__file__).parent.parent
for _candidate in [_here / ".env", _here.parent / ".env"]:
    if _candidate.exists():
        load_dotenv(_candidate)
        print(f"[INFO] .env 로드: {_candidate}")
        break
else:
    print("[WARN] .env 파일을 찾지 못했습니다.")

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_TOKEN    = os.environ["JIRA_API_TOKEN"]
PROJECT_KEY   = os.environ.get("PROJECT_KEY", "TACEA")
ISSUE_TYPES   = os.environ.get("ISSUE_TYPES", '"\uc778\uc2dc\ub358\ud2b8", "\uac1c\uc120", "CVE", "\uc11c\ube44\uc2a4 \uc694\uccad"')

AUTH    = (JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

OUT_PATH = _here.parent / "IssueStructure.json"

ISSUE_KEY = sys.argv[1] if len(sys.argv) > 1 else None


async def main() -> None:
    async with httpx.AsyncClient(auth=AUTH, headers=HEADERS, timeout=30.0) as client:

        if ISSUE_KEY:
            print(f"[INFO] 지정 이슈 조회: {ISSUE_KEY}")
            resp = await client.get(
                f"{JIRA_BASE_URL}/rest/api/3/issue/{ISSUE_KEY}",
                params={"expand": "renderedFields,names,schema,operations,editmeta,changelog"},
            )
            resp.raise_for_status()
            issue_data = resp.json()
        else:
            print(f"[INFO] 이슈 키 미지정 — 프로젝트 최신 1건 자동 선택")
            jql = (
                f"project = {PROJECT_KEY} AND issuetype IN ({ISSUE_TYPES})"
                f" AND status NOT IN (\"종료\",\"닫힌\") ORDER BY issuekey DESC"
            )
            payload = {
                "jql": jql,
                "maxResults": 1,
                "fields": ["*all"],
                "fieldsByKeys": False,
                "expand": "renderedFields,names,schema",
            }
            resp = await client.post(
                f"{JIRA_BASE_URL}/rest/api/3/search/jql",
                json=payload,
            )
            resp.raise_for_status()
            issues = resp.json().get("issues", [])
            if not issues:
                print("[ERROR] 조회된 이슈가 없습니다.")
                return
            issue_data = issues[0]

        key    = issue_data.get("key", "unknown")
        fields = issue_data.get("fields") or {}

        print(f"\n{'='*60}")
        print(f"  이슈 키 : {key}")
        print(f"  필드 수  : {len(fields)}개")
        print(f"{'='*60}\n")

        print("[[주요 필드 확인]]")
        for target in ["assignee", "reporter", "customfield"]:
            for fname, val in fields.items():
                if target in fname.lower():
                    preview = json.dumps(val, ensure_ascii=False)[:200] if val else "null"
                    print(f"  {fname}: {preview}")

        OUT_PATH.write_text(
            json.dumps(issue_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n✅ 전체 JSON 저장 완료: {OUT_PATH}")
        print("힘트: IssueStructure.json 에서 assignee / customfield_ 필드명 확인 후 recent_collector.py 수정")


if __name__ == "__main__":
    asyncio.run(main())
