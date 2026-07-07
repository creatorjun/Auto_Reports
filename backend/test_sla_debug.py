"""
SLA 디버그 진단 스크립트
실행: docker exec tac_backend python test_sla_debug.py
실행: docker exec tac_backend python test_sla_debug.py > /tmp/sla_debug.log 2>&1
결과: /tmp/sla_debug.log 확인
"""
import asyncio
import json
import os
import sys
from datetime import datetime

import httpx

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_TOKEN    = os.environ["JIRA_API_TOKEN"]
PROJECT_KEY   = os.environ.get("PROJECT_KEY", "TACEA")

SLA_SCHEMA_TYPE = "sd-servicelevelagreement"

LOG_FILE = "/tmp/sla_debug.log"


def log(msg: str):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


async def main():
    open(LOG_FILE, "w").close()  # 초기화
    log("=" * 70)
    log("SLA 디버그 시작")
    log(f"JIRA_BASE_URL : {JIRA_BASE_URL}")
    log(f"PROJECT_KEY   : {PROJECT_KEY}")
    log("=" * 70)

    auth = (JIRA_EMAIL, JIRA_TOKEN)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    async with httpx.AsyncClient(auth=auth, headers=headers, timeout=30.0) as client:

        # ── STEP 1: 전체 필드 목록 조회 ──────────────────────────────────────
        log("\n[STEP 1] /rest/api/3/field 조회")
        resp = await client.get(f"{JIRA_BASE_URL}/rest/api/3/field")
        resp.raise_for_status()
        all_fields = resp.json()
        log(f"  전체 필드 수: {len(all_fields)}")

        # schema.type == sd-servicelevelagreement 필터
        sla_fields = {
            f["name"]: f["id"]
            for f in all_fields
            if (f.get("schema") or {}).get("type") == SLA_SCHEMA_TYPE
            and f.get("id", "").startswith("customfield_")
        }
        log(f"\n[STEP 1] schema.type=={SLA_SCHEMA_TYPE} 필드 ({len(sla_fields)}개):")
        for name, fid in sla_fields.items():
            log(f"  {fid}  {name}")

        if not sla_fields:
            # fallback
            log("\n[STEP 1] ⚠️  sd-servicelevelagreement 필드 없음 → schema.custom 'sd-sla' fallback")
            sla_fields = {
                f["name"]: f["id"]
                for f in all_fields
                if "sd-sla" in (f.get("schema") or {}).get("custom", "").lower()
                and f.get("id", "").startswith("customfield_")
            }
            log(f"  fallback 필드 ({len(sla_fields)}개): {list(sla_fields.keys())}")

        # 키워드 매칭 확인
        initial_keywords    = ["최초 응답", "첫 응답", "초기 대응", "First Response", "Time to first response", "Initial"]
        resolution_keywords = ["해결 시간 SLA", "해결시간 SLA", "해결 시간", "Resolution", "Time to resolution", "Time to close"]

        def find_best(keywords):
            for kw in keywords:
                for fname, fid in sla_fields.items():
                    if kw.lower() in fname.lower():
                        return fname, fid
            return None

        w15_field = find_best(initial_keywords)
        w16_field = find_best(resolution_keywords)
        log(f"\n[STEP 1] W15 매칭 필드 : {w15_field}")
        log(f"[STEP 1] W16 매칭 필드 : {w16_field}")

        if not w15_field:
            log("\n❌ W15 필드 매칭 실패!")
            log("   아래 SLA 필드명에 맞는 키워드를 settings.py에 추가하세요:")
            for name in sla_fields:
                log(f"   - '{name}'")
            return

        # ── STEP 2: 실제 이슈 1건 조회 → SLA 필드 구조 덤프 ────────────────────
        log(f"\n[STEP 2] 이슈 1건 조회 (W15 필드={w15_field})")
        sla_fids = list(sla_fields.values())
        fields_param = "summary,created,resolutiondate," + ",".join(sla_fids)
        jql = f"project = {PROJECT_KEY} AND created >= \"2026-01-01\" ORDER BY created DESC"

        resp2 = await client.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            json={"jql": jql, "maxResults": 3, "fields": fields_param.split(",")}
        )
        resp2.raise_for_status()
        issues = resp2.json().get("issues", [])
        log(f"  조회된 이슈 수: {len(issues)}")

        for issue in issues:
            key = issue["key"]
            fields = issue.get("fields", {})
            log(f"\n  이슈: {key}")
            for fname, fid in sla_fields.items():
                val = fields.get(fid)
                if val is None:
                    log(f"    [{fid}] {fname}: null")
                else:
                    completed = val.get("completedCycles", [])
                    ongoing   = val.get("ongoingCycle")
                    log(f"    [{fid}] {fname}:")
                    log(f"      completedCycles ({len(completed)}개): " +
                        json.dumps([{"breached": c.get("breached"), "goalDuration": c.get("goalDuration")} for c in completed], ensure_ascii=False))
                    if ongoing:
                        log(f"      ongoingCycle: breached={ongoing.get('breached')}, "
                            f"remainingTime={ongoing.get('remainingTime')}")
                    else:
                        log(f"      ongoingCycle: null")

        # ── STEP 3: 6개월 월별 집계 미리보기 ─────────────────────────────────────
        log(f"\n[STEP 3] W15 필드 ({w15_field[1]}) 6개월 집계")
        now = datetime.now()
        months = []
        y, m = now.year, now.month
        for _ in range(6):
            months.append((y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        months = list(reversed(months))

        _, target_fid = w15_field
        for year, month in months:
            start = f"{year}-{month:02d}-01"
            end   = f"{year}-{month+1:02d}-01" if month < 12 else f"{year+1}-01-01"
            jql_m = (
                f"project = {PROJECT_KEY} AND issuetype IN (\"인시던트\",\"개선\",\"CVE\",\"서비스 요청\")"
                f" AND created >= \"{start}\" AND created < \"{end}\""
            )
            resp_m = await client.post(
                f"{JIRA_BASE_URL}/rest/api/3/search/jql",
                json={"jql": jql_m, "maxResults": 500, "fields": [target_fid]}
            )
            resp_m.raise_for_status()
            issues_m = resp_m.json().get("issues", [])

            met = breached = no_sla = 0
            for iss in issues_m:
                sla_val = (iss.get("fields") or {}).get(target_fid)
                if not sla_val:
                    no_sla += 1
                    continue
                for c in sla_val.get("completedCycles") or []:
                    if c.get("breached"):
                        breached += 1
                    else:
                        met += 1
                og = sla_val.get("ongoingCycle")
                if og:
                    if og.get("breached"):
                        breached += 1
                    else:
                        met += 1

            total = met + breached
            rate  = round(met / total * 100, 1) if total else 0.0
            log(f"  {year}-{month:02d}: 이슈 {len(issues_m)}건 / SLA있음 {total}건 / met={met} breached={breached} / 달성률={rate}% / SLA없음={no_sla}건")

    log("\n[DONE] 디버그 완료. 로그: " + LOG_FILE)


if __name__ == "__main__":
    asyncio.run(main())
