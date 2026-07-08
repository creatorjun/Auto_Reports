# backend/scripts/get_data.py
import asyncio
import json
import os
import sys
from datetime import datetime
from io import StringIO
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
    print("[WARN] .env 파일을 찾지 못했습니다. 환경변수가 이미 설정돼 있어야 합니다.")

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_TOKEN    = os.environ["JIRA_API_TOKEN"]
PROJECT_KEY   = os.environ.get("PROJECT_KEY", "TACEA")
ISSUE_TYPES   = os.environ.get("ISSUE_TYPES", '"\uc778\uc2dc던\ud2b8", "\uac1c\uc120", "CVE", "\uc11c\ube44\uc2a4 \uc694\uccad"')

INITIAL_KEYWORDS    = ["\uccab \uc751\ub2f5", "\ucd08\uae30 \ub300\uc751", "First Response", "Time to first response", "Initial"]
RESOLUTION_KEYWORDS = ["\ud574\uacb0", "Resolution", "Time to resolution", "Time to close"]

AUTH    = (JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

OUT_PATH = _here.parent / "DataStructure.md"

_buf = StringIO()

def p(*args, **kwargs):
    msg = " ".join(str(a) for a in args)
    print(msg, **kwargs)
    print(msg, file=_buf)

SEP = "\n" + "=" * 70 + "\n"


async def main() -> None:
    async with httpx.AsyncClient(auth=AUTH, headers=HEADERS, timeout=30.0) as client:

        p(f"# DataStructure\n")
        p(f"> \uc0dd\uc131: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  project: `{PROJECT_KEY}`\n")

        p(SEP + "## STEP 1 \u2014 Jira customfield \ubaa9\ub85d (SLA \ud6c4\ubcf4)" + SEP)
        resp = await client.get(f"{JIRA_BASE_URL}/rest/api/3/field")
        resp.raise_for_status()
        all_fields: list[dict] = resp.json()

        custom_fields = [f for f in all_fields if f.get("id", "").startswith("customfield_")]
        p(f"customfield \uc5f4 {len(custom_fields)}\uac1c\n")

        sla_candidates: list[dict] = []
        for f in custom_fields:
            schema      = f.get("schema") or {}
            custom_type = schema.get("custom", "")
            name        = f.get("name", "")
            fid         = f.get("id", "")
            is_sla_type = "sla" in custom_type.lower() or "servicedesk" in custom_type.lower()
            is_sla_name = any(k in name for k in ["SLA", "\uc2dc\uac04", "Time", "time", "response", "Response", "resolution", "Resolution"])
            if is_sla_type or is_sla_name:
                sla_candidates.append(f)
                p(f"### [{fid}] {name}")
                p(f"- schema.custom : `{custom_type or '(\uc5c6\uc74c)'}`")
                p(f"- schema.type   : `{schema.get('type', '(\uc5c6\uc74c)')}`\n")

        if not sla_candidates:
            p("> \u26a0\ufe0f SLA \ud6c4\ubcf4 \ud544\ub4dc\ub97c \ubc1c\uacac\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4. \uc804\uccb4 customfield \ubaa9\ub85d\uc73c\ub85c \ud30c\ub77c\ud569\ub2c8\ub2e4.\n")
            p("| id | name | schema.custom |")
            p("|---|---|---|")
            for f in custom_fields:
                schema = f.get("schema") or {}
                p(f"| {f['id']} | {f.get('name','')} | {schema.get('custom','')} |")

        p(SEP + "## STEP 2 \u2014 get_sla_field_ids() \ub85c\uc9c1 \uacb0\uacfc" + SEP)
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
                if fid.startswith("customfield_") and ("SLA" in fname or "\uc2dc\uac04" in fname or "Time" in fname):
                    sla_field_ids[fname] = fid

        if sla_field_ids:
            p("| field_id | field_name |")
            p("|---|---|")
            for name, fid in sla_field_ids.items():
                p(f"| `{fid}` | {name} |")
        else:
            p("> \u274c SLA \ud544\ub4dc\ub97c \ud558\ub098\ub3c4 \ubc1c\uacac\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4!")
            p("> STEP 1 \uacb0\uacfc\uc758 schema.custom \uac12\uc744 \ud655\uc778 \ud6c4 `jira_client.py` \uac80\uce60 \uc870\uac74\uc744 \uc218\uc815\ud558\uc138\uc694.")

        p(SEP + "## STEP 3 \u2014 \ud0a4\uc6cc\ub4dc \ub9e4\uce6d \uc9c4\ub2e8" + SEP)
        p(f"- INITIAL\\_KEYWORDS    : `{INITIAL_KEYWORDS}`")
        p(f"- RESOLUTION\\_KEYWORDS : `{RESOLUTION_KEYWORDS}`\n")

        p("| field_id | field_name | W15 \ucd08\uae30\ub300\uc751 | W16 \ud574\uacb0\uc2dc\uac04 |")
        p("|---|---|---|---|")
        for fname, fid in sla_field_ids.items():
            matched_i = [kw for kw in INITIAL_KEYWORDS    if kw.lower() in fname.lower()]
            matched_r = [kw for kw in RESOLUTION_KEYWORDS if kw.lower() in fname.lower()]
            w15 = "\u2705 " + str(matched_i) if matched_i else "\u274c"
            w16 = "\u2705 " + str(matched_r) if matched_r else "\u274c"
            p(f"| `{fid}` | {fname} | {w15} | {w16} |")

        p(SEP + "## STEP 4 \u2014 \ucd5c\uadfc 5\uac1c \uc774\uc288 raw SLA \ud544\ub4dc \uac12" + SEP)
        if not sla_field_ids:
            p("> SLA \ud544\ub4dc\uac00 \uc5c6\uc5b4 \uc0dd\ub7b5\ud569\ub2c8\ub2e4.")
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
            p(f"\uc870\ud68c\ub41c \uc774\uc288: **{len(issues)}\uac1c**")
            p(f"```\n{jql}\n```\n")

            for issue in issues:
                key = issue.get("key", "")
                f   = issue.get("fields") or {}
                itype = (f.get("issuetype") or {}).get("name", "")
                p(f"### {key} | {itype} | \uc0dd\uc131: {str(f.get('created',''))[:10]}\n")
                for fname, fid in sla_field_ids.items():
                    val = f.get(fid)
                    p(f"**[{fid}] {fname}**")
                    if val is None:
                        p("`null`\n")
                    else:
                        p(f"```json\n{json.dumps(val, ensure_ascii=False, indent=2)}\n```\n")

        if "--dump-all" in sys.argv:
            p(SEP + "## STEP 5 \u2014 \uc804\uccb4 customfield JSON \ub364\ud504" + SEP)
            p(f"```json\n{json.dumps(custom_fields, ensure_ascii=False, indent=2)}\n```")

    OUT_PATH.write_text(_buf.getvalue(), encoding="utf-8")
    print(f"\n\u2705 \uc800\uc7a5 \uc644\ub8cc: {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
