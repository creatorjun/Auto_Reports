# backend/scripts/test_sla_debug.py
import asyncio
import json
import os
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
    open(LOG_FILE, "w").close()
    log("=" * 70)
    log("SLA \ub514\ubc84\uadf8 \uc2dc\uc791")
    log(f"JIRA_BASE_URL : {JIRA_BASE_URL}")
    log(f"PROJECT_KEY   : {PROJECT_KEY}")
    log("=" * 70)

    auth = (JIRA_EMAIL, JIRA_TOKEN)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    async with httpx.AsyncClient(auth=auth, headers=headers, timeout=30.0) as client:

        log("\n[STEP 1] /rest/api/3/field \uc870\ud68c")
        resp = await client.get(f"{JIRA_BASE_URL}/rest/api/3/field")
        resp.raise_for_status()
        all_fields = resp.json()
        log(f"  \uc804\uccb4 \ud544\ub4dc \uc218: {len(all_fields)}")

        sla_fields = {
            f["name"]: f["id"]
            for f in all_fields
            if (f.get("schema") or {}).get("type") == SLA_SCHEMA_TYPE
            and f.get("id", "").startswith("customfield_")
        }
        log(f"\n[STEP 1] schema.type=={SLA_SCHEMA_TYPE} \ud544\ub4dc ({len(sla_fields)}\uac1c):")
        for name, fid in sla_fields.items():
            log(f"  {fid}  {name}")

        if not sla_fields:
            log("\n[STEP 1] \u26a0\ufe0f  sd-servicelevelagreement \ud544\ub4dc \uc5c6\uc74c \u2192 schema.custom 'sd-sla' fallback")
            sla_fields = {
                f["name"]: f["id"]
                for f in all_fields
                if "sd-sla" in (f.get("schema") or {}).get("custom", "").lower()
                and f.get("id", "").startswith("customfield_")
            }
            log(f"  fallback \ud544\ub4dc ({len(sla_fields)}\uac1c): {list(sla_fields.keys())}")

        initial_keywords    = ["\ucd5c\uc18c \uc751\ub2f5", "\uccab \uc751\ub2f5", "\ucd08\uae30 \ub300\uc751", "First Response", "Time to first response", "Initial"]
        resolution_keywords = ["\ud574\uacb0 \uc2dc\uac04 SLA", "\ud574\uacb0\uc2dc\uac04 SLA", "\ud574\uacb0 \uc2dc\uac04", "Resolution", "Time to resolution", "Time to close"]

        def find_best(keywords):
            for kw in keywords:
                for fname, fid in sla_fields.items():
                    if kw.lower() in fname.lower():
                        return fname, fid
            return None

        w15_field = find_best(initial_keywords)
        w16_field = find_best(resolution_keywords)
        log(f"\n[STEP 1] W15 \ub9e4\uce6d \ud544\ub4dc : {w15_field}")
        log(f"[STEP 1] W16 \ub9e4\uce6d \ud544\ub4dc : {w16_field}")

        if not w15_field:
            log("\n\u274c W15 \ud544\ub4dc \ub9e4\uce6d \uc2e4\ud328!")
            log("   \uc544\ub798 SLA \ud544\ub4dc\uba85\uc5d0 \ub9de\ub294 \ud0a4\uc6cc\ub4dc\ub97c settings.py\uc5d0 \ucd94\uac00\ud558\uc138\uc694:")
            for name in sla_fields:
                log(f"   - '{name}'")
            return

        log(f"\n[STEP 2] \uc774\uc288 1\uac74 \uc870\ud68c (W15 \ud544\ub4dc={w15_field})")
        sla_fids = list(sla_fields.values())
        fields_param = "summary,created,resolutiondate," + ",".join(sla_fids)
        jql = f"project = {PROJECT_KEY} AND created >= \"2026-01-01\" ORDER BY created DESC"

        resp2 = await client.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            json={"jql": jql, "maxResults": 3, "fields": fields_param.split(",")}
        )
        resp2.raise_for_status()
        issues = resp2.json().get("issues", [])
        log(f"  \uc870\ud68c\ub41c \uc774\uc288 \uc218: {len(issues)}")

        for issue in issues:
            key = issue["key"]
            fields = issue.get("fields", {})
            log(f"\n  \uc774\uc288: {key}")
            for fname, fid in sla_fields.items():
                val = fields.get(fid)
                if val is None:
                    log(f"    [{fid}] {fname}: null")
                else:
                    completed = val.get("completedCycles", [])
                    ongoing   = val.get("ongoingCycle")
                    log(f"    [{fid}] {fname}:")
                    log(f"      completedCycles ({len(completed)}\uac1c): " +
                        json.dumps([{"breached": c.get("breached"), "goalDuration": c.get("goalDuration")} for c in completed], ensure_ascii=False))
                    if ongoing:
                        log(f"      ongoingCycle: breached={ongoing.get('breached')}, "
                            f"remainingTime={ongoing.get('remainingTime')}")
                    else:
                        log(f"      ongoingCycle: null")

        log(f"\n[STEP 3] W15 \ud544\ub4dc ({w15_field[1]}) 6\uac1c\uc6d4 \uc9d1\uacc4")
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
                f"project = {PROJECT_KEY} AND issuetype IN (\"\uc778\uc2dc\ub358\ud2b8\",\"\uac1c\uc120\",\"CVE\",\"\uc11c\ube44\uc2a4 \uc694\uccad\")"
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
            log(f"  {year}-{month:02d}: \uc774\uc288 {len(issues_m)}\uac74 / SLA\uc788\uc74c {total}\uac74 / met={met} breached={breached} / \ub2ec\uc131\ub960={rate}% / SLA\uc5c6\uc74c={no_sla}\uac74")

    log("\n[DONE] \ub514\ubc84\uadf8 \uc644\ub8cc. \ub85c\uadf8: " + LOG_FILE)


if __name__ == "__main__":
    asyncio.run(main())
