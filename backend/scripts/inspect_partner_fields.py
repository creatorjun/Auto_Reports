# backend/scripts/inspect_partner_fields.py
import asyncio
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

_here = Path(__file__).parent.parent
for _candidate in [_here / ".env", _here.parent / ".env"]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_TOKEN    = os.environ["JIRA_API_TOKEN"]
PROJECT_KEY   = os.environ.get("PROJECT_KEY", "TACEA")

AUTH    = (JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

OUT_DIR  = _here.parent / "docs"
OUT_PATH = OUT_DIR / "partner_fields.json"


async def fetch_latest_issue(client: httpx.AsyncClient) -> tuple[str, dict, dict]:
    payload = {
        "jql": f"project = {PROJECT_KEY} ORDER BY created DESC",
        "maxResults": 1,
        "fields": ["*all"],
        "expand": "names,schema",
    }
    resp = await client.post(f"{JIRA_BASE_URL}/rest/api/3/search/jql", json=payload)
    resp.raise_for_status()
    issues = resp.json().get("issues", [])
    assert issues, "조회된 이슈가 없습니다."
    issue = issues[0]
    return issue.get("key", ""), issue.get("fields") or {}, issue.get("names") or {}


async def fetch_all_fields(client: httpx.AsyncClient) -> list[dict]:
    resp = await client.get(f"{JIRA_BASE_URL}/rest/api/3/field")
    resp.raise_for_status()
    return resp.json()


async def fetch_organizations(client: httpx.AsyncClient) -> list[dict]:
    results, start = [], 0
    while True:
        resp = await client.get(
            f"{JIRA_BASE_URL}/rest/servicedeskapi/organization",
            params={"start": start, "limit": 50},
            headers={**HEADERS, "X-ExperimentalApi": "opt-in"},
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        values = data.get("values", [])
        results.extend(values)
        if data.get("isLastPage", True):
            break
        start += len(values)
    return results


async def main() -> None:
    async with httpx.AsyncClient(auth=AUTH, headers=HEADERS, timeout=30.0) as client:
        issue_result, all_fields, orgs = await asyncio.gather(
            fetch_latest_issue(client),
            fetch_all_fields(client),
            fetch_organizations(client),
            return_exceptions=True,
        )

    if isinstance(issue_result, BaseException):
        print(f"[WARN] 이슈 조회 실패: {issue_result}")
        key, fields, names = "ERROR", {}, {}
    else:
        key, fields, names = issue_result

    if isinstance(all_fields, BaseException):
        print(f"[WARN] field 메타 조회 실패: {all_fields}")
        all_fields = []

    if isinstance(orgs, BaseException):
        print(f"[WARN] 조직 목록 조회 실패: {orgs}")
        orgs = []

    # 1. 이슈 내 커스텀 필드 전체 (non-null)
    custom_from_issue = [
        {
            "field_id":   fid,
            "field_name": names.get(fid, fid),
            "value":      val,
        }
        for fid, val in sorted(fields.items())
        if fid.startswith("customfield_") and val is not None
    ]

    # 2. /rest/api/3/field 에서 customfield_* 전체
    custom_from_meta = [
        {
            "field_id":   f["id"],
            "field_name": f["name"],
            "type":       (f.get("schema") or {}).get("type", ""),
            "custom":     f.get("custom", False),
        }
        for f in all_fields
        if f["id"].startswith("customfield_")
    ]

    # 3. 파트너/조직/회사 관련 키워드 필터
    KEYWORDS = ["파트너", "조직", "회사", "기관", "partner", "org", "company", "organization"]
    def has_keyword(name: str) -> bool:
        nl = name.lower()
        return any(k in nl for k in KEYWORDS)

    partner_candidates_issue = [c for c in custom_from_issue if has_keyword(c["field_name"])]
    partner_candidates_meta  = [c for c in custom_from_meta  if has_keyword(c["field_name"])]

    result = {
        "sampled_issue_key": key,
        "service_desk_organizations": orgs,
        "partner_candidate_fields_from_issue": partner_candidates_issue,
        "partner_candidate_fields_from_meta":  partner_candidates_meta,
        "all_custom_fields_from_issue": custom_from_issue,
        "all_custom_fields_from_meta":  custom_from_meta,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== 샘플 이슈: {key} ===")

    print(f"\n[Service Desk 조직 목록] {len(orgs)}개")
    for o in orgs:
        print(f"  id={str(o.get('id')):>4}  name={o.get('name')}")

    print(f"\n[파트너/조직 관련 커스텀 필드 — 이슈 내 non-null] {len(partner_candidates_issue)}개")
    for c in partner_candidates_issue:
        print(f"  {c['field_id']:30s} | {c['field_name']:30s} | {json.dumps(c['value'], ensure_ascii=False)[:80]}")

    print(f"\n[파트너/조직 관련 커스텀 필드 — /field 메타] {len(partner_candidates_meta)}개")
    for c in partner_candidates_meta:
        print(f"  {c['field_id']:30s} | {c['field_name']:30s} | type={c['type']}")

    print(f"\n[전체 커스텀 필드 — 이슈 내 non-null] {len(custom_from_issue)}개")
    for c in custom_from_issue:
        print(f"  {c['field_id']:30s} | {c['field_name']:30s} | {json.dumps(c['value'], ensure_ascii=False)[:60]}")

    print(f"\n✅ 전체 결과 저장: {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
