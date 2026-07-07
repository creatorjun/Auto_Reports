# backend/get_data.py
import asyncio
import json
import os
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

import httpx
from dotenv import load_dotenv

# .env 탐색: backend/.env → 프로젝트 루트 .env
_here = Path(__file__).parent
for _candidate in [_here / ".env", _here.parent / ".env"]:
    if _candidate.exists():
        load_dotenv(_candidate)
        print(f"[INFO] .env 로드: {_candidate}")
        break
else:
    print("[WARN] .env 파일을 찾지 못했습니다. 환경변수가 이미 설정돼 있어야 합니다.")

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_TOKEN    = os.environ["JIRA_API_TOKEN"]
PROJECT_KEY   = os.environ.get("PROJECT_KEY", "TACEA")
ISSUE_TYPES   = os.environ.get("ISSUE_TYPES", '"인시던트", "개선", "CVE", "서비스 요청"')

INITIAL_KEYWORDS    = ["첫 응답", "초기 대응", "First Response", "Time to first response", "Initial"]
RESOLUTION_KEYWORDS = ["해결", "Resolution", "Time to resolution", "Time to close"]

AUTH    = (JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

OUT_PATH = _here.parent / "DataStructure.md"

# 스트림: 콘솔 + 파일 동시 출력
_buf = StringIO()

def p(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    print(msg, **kwargs)
    print(msg, file=_buf)

SEP = "\n" + "=" * 70 + "\n"


async def main() -> None:
    async with httpx.AsyncClient(auth=AUTH, headers=HEADERS, timeout=30.0) as client:

        p(f"# DataStructure\n")
        p(f"> 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  project: `{PROJECT_KEY}`\n")

        # ── STEP 1: 전체 customfield ─────────────────────────────────────────
        p(SEP + "## STEP 1 — Jira customfield 목록 (SLA 후보)" + SEP)
        resp = await client.get(f"{JIRA_BASE_URL}/rest/api/3/field")
        resp.raise_for_status()
        all_fields: list[dict] = resp.json()

        custom_fields = [f for f in all_fields if f.get("id", "").startswith("customfield_")]
        p(f"customfield 총 {len(custom_fields)}개\n")

        sla_candidates: list[dict] = []
        for f in custom_fields:
            schema      = f.get("schema") or {}
            custom_type = schema.get("custom", "")
            name        = f.get("name", "")
            fid         = f.get("id", "")
            is_sla_type = "sla" in custom_type.lower() or "servicedesk" in custom_type.lower()
            is_sla_name = any(k in name for k in ["SLA", "시간", "Time", "time", "response", "Response", "resolution", "Resolution"])
            if is_sla_type or is_sla_name:
                sla_candidates.append(f)
                p(f"### [{fid}] {name}")
                p(f"- schema.custom : `{custom_type or '(없음)'}`")
                p(f"- schema.type   : `{schema.get('type', '(없음)')}`\n")

        if not sla_candidates:
            p("> ⚠️ SLA 후보 필드를 발견하지 못했습니다. 전체 customfield 목록로 파라합니다.\n")
            p("| id | name | schema.custom |")
            p("|---|---|---|")
            for f in custom_fields:
                schema = f.get("schema") or {}
                p(f"| {f['id']} | {f.get('name','')} | {schema.get('custom','')} |")

        # ── STEP 2: get_sla_field_ids 로직 ───────────────────────────────────
        p(SEP + "## STEP 2 — get_sla_field_ids() 로직 결과" + SEP)
        sla_field_ids: dict[str, str] = {}
        for f in all_fields:
            schema      = f.get("schema") or {}
            custom_type = schema.get("custom", "")
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
            p("| field_id | field_name |")
            p("|---|---|")
            for name, fid in sla_field_ids.items():
                p(f"| `{fid}` | {name} |")
        else:
            p("> ❌ SLA 필드를 하나도 발견하지 못했습니다!")
            p("> STEP 1 결과의 schema.custom 값을 확인 후 `jira_client.py` 검출 조건을 수정하세요.")

        # ── STEP 3: 키워드 매칭 진단 ───────────────────────────────────────
        p(SEP + "## STEP 3 — 키워드 매칭 진단" + SEP)
        p(f"- INITIAL\_KEYWORDS    : `{INITIAL_KEYWORDS}`")
        p(f"- RESOLUTION\_KEYWORDS : `{RESOLUTION_KEYWORDS}`\n")

        p("| field_id | field_name | W15 초기대응 | W16 해결시간 |")
        p("|---|---|---|---|")
        for fname, fid in sla_field_ids.items():
            matched_i = [kw for kw in INITIAL_KEYWORDS    if kw.lower() in fname.lower()]
            matched_r = [kw for kw in RESOLUTION_KEYWORDS if kw.lower() in fname.lower()]
            w15 = "✅ " + str(matched_i) if matched_i else "❌"
            w16 = "✅ " + str(matched_r) if matched_r else "❌"
            p(f"| `{fid}` | {fname} | {w15} | {w16} |")

        # ── STEP 4: raw SLA 필드 값 ──────────────────────────────────────────
        p(SEP + "## STEP 4 — 최근 5개 이슈 raw SLA 필드 값" + SEP)
        if not sla_field_ids:
            p("> SLA 필드가 없어 생략합니다.")
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
            p(f"조회된 이슈: **{len(issues)}개**")
            p(f"```\n{jql}\n```\n")

            for issue in issues:
                key = issue.get("key", "")
                f   = issue.get("fields") or {}
                itype = (f.get("issuetype") or {}).get("name", "")
                p(f"### {key} | {itype} | 생성: {str(f.get('created',''))[:10]}\n")
                for fname, fid in sla_field_ids.items():
                    val = f.get(fid)
                    p(f"**[{fid}] {fname}**")
                    if val is None:
                        p("`null`\n")
                    else:
                        p(f"```json\n{json.dumps(val, ensure_ascii=False, indent=2)}\n```\n")

        # ── STEP 5: 전체 customfield JSON (--dump-all) ─────────────────────
        if "--dump-all" in sys.argv:
            p(SEP + "## STEP 5 — 전체 customfield JSON 덤프" + SEP)
            p(f"```json\n{json.dumps(custom_fields, ensure_ascii=False, indent=2)}\n```")

    # 파일 저장
    OUT_PATH.write_text(_buf.getvalue(), encoding="utf-8")
    print(f"\n✅ 저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
