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
        break

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL    = os.environ["JIRA_EMAIL"]
JIRA_TOKEN    = os.environ["JIRA_API_TOKEN"]
PROJECT_KEY   = os.environ.get("PROJECT_KEY", "TACEA")
ISSUE_TYPES   = os.environ.get("ISSUE_TYPES", '"\uc778\uc2dc\ub358\ud2b8", "\uac1c\uc120", "CVE", "\uc11c\ube44\uc2a4 \uc694\uccad"')

AUTH    = (JIRA_EMAIL, JIRA_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

OUT_DIR  = _here.parent / "docs"
OUT_PATH = OUT_DIR / "datastructure.md"

ISSUE_KEY = sys.argv[1] if len(sys.argv) > 1 else "TACEA-4547"


async def main() -> None:
    buf = StringIO()

    def w(line: str = "") -> None:
        buf.write(line + "\n")

    async with httpx.AsyncClient(auth=AUTH, headers=HEADERS, timeout=30.0) as client:

        if ISSUE_KEY:
            resp = await client.get(
                f"{JIRA_BASE_URL}/rest/api/3/issue/{ISSUE_KEY}",
                params={"expand": "names,schema"},
            )
            resp.raise_for_status()
            issue_data = resp.json()
        else:
            jql = (
                f"project = {PROJECT_KEY} AND issuetype IN ({ISSUE_TYPES})"
                f" AND status NOT IN (\"\uc885\ub8cc\",\"\ub2eb\ud78c\") ORDER BY issuekey DESC"
            )
            payload = {
                "jql": jql,
                "maxResults": 1,
                "fields": ["*all"],
                "fieldsByKeys": False,
                "expand": "names,schema",
            }
            resp = await client.post(
                f"{JIRA_BASE_URL}/rest/api/3/search/jql",
                json=payload,
            )
            resp.raise_for_status()
            issues = resp.json().get("issues", [])
            if not issues:
                print("[ERROR] \uc870\ud68c\ub41c \uc774\uc288\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.")
                return
            issue_data = issues[0]

        key    = issue_data.get("key", "unknown")
        fields = issue_data.get("fields") or {}
        names  = issue_data.get("names") or {}

        w(f"# Issue Data Structure")
        w(f"")
        w(f"> \uc0dd\uc131: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  issue: `{key}`")
        w(f"")

        w(f"## \uc774\uc288 \uc815\ubcf4")
        w(f"")
        w(f"| \ud56d\ubaa9 | \uac12 |")
        w(f"|---|---|")
        w(f"| key | `{key}` |")
        w(f"| \ud544\ub4dc \uc218 | {len(fields)}\uac1c |")
        w(f"")

        w(f"## \uc8fc\uc694 \ud544\ub4dc (assignee / reporter / customfield)")
        w(f"")
        targets = ["assignee", "reporter", "customfield"]
        for fname, val in fields.items():
            if any(t in fname.lower() for t in targets):
                label = names.get(fname, fname)
                w(f"### `{fname}` \u2014 {label}")
                w(f"")
                w(f"```json")
                w(json.dumps(val, ensure_ascii=False, indent=2))
                w(f"```")
                w(f"")

        w(f"## \uc804\uccb4 fields raw JSON")
        w(f"")
        w(f"```json")
        w(json.dumps(fields, ensure_ascii=False, indent=2))
        w(f"```")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(buf.getvalue(), encoding="utf-8")
    print(f"\u2705 \uc800\uc7a5 \uc644\ub8cc: {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
