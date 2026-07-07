# backend/get_data.py
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_TOKEN    = os.environ["JIRA_API_TOKEN"]
PROJECT_KEY   = os.environ.get("PROJECT_KEY", "TACEA")

ISSUE_TYPES = os.environ.get(
    "ISSUE_TYPES", '"인시던트", "개선", "CVE", "서비스 요청"'
)

INITIAL_KEYWORDS  = ["\uccab \uc751\ub2f5", "\ucd08\uae30 \ub300\uc751", "First Response", "Time to first response", "Initial"]
RESOLUTION_KEYWORDS = ["\ud574\uacb0", "Resolution", "Time to resolution", "Time to close"]

AUTH = (JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

SEP = "\n" + "=" * 70 + "\n"


async def main() -> None:
    async with httpx.AsyncClient(auth=AUTH, headers=HEADERS, timeout=30.0) as client:

        # ── STEP 1: 전체 필드 목록 ──────────────────────────────────────
        print(SEP + "[STEP 1] Jira 전체 customfield 목록 (schema 포함)" + SEP)
        resp = await client.get(f"{JIRA_BASE_URL}/rest/api/3/field")
        resp.raise_for_status()
        all_fields: list[dict] = resp.json()

        custom_fields = [
            f for f in all_fields
            if f.get("id", "").startswith("customfield_")
        ]
        print(f"  customfield 총 {len(custom_fields)}개\n")

        sla_candidates: list[dict] = []
        for f in custom_fields:
            schema = f.get("schema") or {}
            custom_type: str = schema.get("custom", "")
            name: str = f.get("name", "")
            fid: str  = f.get("id", "")
            is_sla_type = "sla" in custom_type.lower() or "servicedesk" in custom_type.lower()
            is_sla_name = "SLA" in name or "시간" in name or "Time" in name or "time" in name or "response" in name.lower() or "resolution" in name.lower()
            if is_sla_type or is_sla_name:
                sla_candidates.append(f)
                print(f"  [{fid}] {name}")
                print(f"    schema.custom = {custom_type or '(없음)'}")
                print(f"    schema.type   = {schema.get('type', '(없음)')}")
                print()

        if not sla_candidates:
            print("  ⚠️  SLA 후보 필드를 발견하지 못했습니다.")
            print("  아래에 전체 customfield 목록을 출력합니다.")
            for f in custom_fields:
                schema = f.get("schema") or {}
                print(f"  [{f['id']}] {f.get('name','')}  custom={schema.get('custom','')}")

        # ── STEP 2: get_sla_field_ids 로직 실행 ──────────────────────────
        print(SEP + "[STEP 2] get_sla_field_ids() 로직 결과" + SEP)
        sla_field_ids: dict[str, str] = {}
        for f in all_fields:
            schema = f.get("schema") or {}
            custom_type: str = schema.get("custom", "")
            fid  = f.get("id", "")
            name = f.get("name", "")
            if "sla" in custom_type.lower() or "servicedesk" in custom_type.lower():
                if fid.startswith("customfield_") and name:
                    sla_field_ids[name] = fid
        if not sla_field_ids:
            for f in all_fields:
                fname = f.get("name", "")
                fid   = f.get("id", "")
                if fid.startswith("customfield_") and ("SLA" in fname or "시간" in fname or "Time" in fname):
                    sla_field_ids[fname] = fid

        if sla_field_ids:
            for name, fid in sla_field_ids.items():
                print(f"  {fid}  ->  {name}")
        else:
            print("  ❌  SLA 필드를 하나도 발견하지 못했습니다!")
            print("  STEP 1 결과를 참고하여 SLA 필드의 schema.custom 값을 확인하세요.")

        # ── STEP 3: 키워드 매칭 진단 ──────────────────────────────────────
        print(SEP + "[STEP 3] 키워드 매칭 진단" + SEP)
        print(f"  INITIAL_KEYWORDS  = {INITIAL_KEYWORDS}")
        print(f"  RESOLUTION_KEYWORDS = {RESOLUTION_KEYWORDS}\n")
        for fname, fid in sla_field_ids.items():
            matched_initial    = [kw for kw in INITIAL_KEYWORDS    if kw.lower() in fname.lower()]
            matched_resolution = [kw for kw in RESOLUTION_KEYWORDS if kw.lower() in fname.lower()]
            tag = []
            if matched_initial:    tag.append(f"W15(키워드={matched_initial})")
            if matched_resolution: tag.append(f"W16(키워드={matched_resolution})")
            status = " | ".join(tag) if tag else "❌ 매칭 없음"
            print(f"  [{fid}] {fname}  ->  {status}")

        # ── STEP 4: 이슈 raw SLA 필드 값 ──────────────────────────────────────
        print(SEP + "[STEP 4] 최근 5개 이슈의 SLA 필드 raw 값" + SEP)
        if not sla_field_ids:
            print("  SLA 필드가 없어 생략합니다.")
        else:
            sla_field_list = list(sla_field_ids.values())
            fields_param   = "summary,issuetype,created,resolutiondate," + ",".join(sla_field_list)
            jql = (
                f"project = {PROJECT_KEY} AND issuetype IN ("
                + ISSUE_TYPES
                + ") AND created >= \"-30d\" ORDER BY created DESC"
            )
            payload = {
                "jql": jql,
                "maxResults": 5,
                "fields": fields_param.split(","),
                "fieldsByKeys": False,
            }
            resp2 = await client.post(
                f"{JIRA_BASE_URL}/rest/api/3/search/jql", json=payload
            )
            resp2.raise_for_status()
            issues = resp2.json().get("issues", [])
            print(f"  조회된 이슈: {len(issues)}개  (JQL: {jql[:80]}...)\n")

            for issue in issues:
                key = issue.get("key", "")
                f   = issue.get("fields") or {}
                print(f"  ▶ {key}  |  생성: {str(f.get('created',''))[:10]}")
                for fname, fid in sla_field_ids.items():
                    val = f.get(fid)
                    if val is None:
                        print(f"    [{fid}] {fname}: null")
                    else:
                        print(f"    [{fid}] {fname}:")
                        print(json.dumps(val, ensure_ascii=False, indent=6))
                print()

        # ── STEP 5: 필드 리스트 전체 JSON 덤프 (선택) ────────────────────────────
        if "--dump-all" in sys.argv:
            print(SEP + "[STEP 5] 전체 필드 JSON 덤프 (--dump-all 옵션)" + SEP)
            print(json.dumps(all_fields, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
