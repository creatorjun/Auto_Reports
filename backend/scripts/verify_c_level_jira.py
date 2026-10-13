# backend/scripts/verify_c_level_jira.py
import argparse
import asyncio
import json
import os
from datetime import date
from pathlib import Path
import sys
from time import perf_counter

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application.use_cases.c_level_report import CLevelReportUseCase
from src.infrastructure.external.c_level_jira_source import CLevelJiraSource


async def verify(period: str, selected_date: date | None, output: Path | None) -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    base = os.environ["JIRA_BASE_URL"].rstrip("/")
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_API_TOKEN"]
    started = perf_counter()
    print(json.dumps({"stage": "jira_collection_started", "period": period, "date": str(selected_date)}, ensure_ascii=False), flush=True)
    async with CLevelJiraSource(base, email, token, project_key=os.environ.get("PROJECT_KEY", "TACEA")) as source:
        report = await CLevelReportUseCase(source).execute(period=period, end_date=selected_date)
    assert len(report["trend"]) == 8
    assert len(report["summary"]) == 4
    details = {issue["key"]: issue for issue in report["issues"]}
    assert len(details) == len(report["issues"])
    assert report["summary"][0]["created"] == sum(card["created"] for card in report["summary"][1:])
    for issue in details.values():
        segments = issue["timeline"]
        for first, second in zip(segments, segments[1:]):
            assert first["end_at"] == second["start_at"], issue["key"]
        for cycle in issue["sla_cycles"]:
            if not cycle["historical_elapsed_known"]:
                assert cycle["elapsed_hours"] is None and cycle["excess_hours"] is None, issue["key"]
    sample_keys = [key for key in ("TACEA-3340", "TACEA-4859", "TACEA-3290", "TACEA-3431") if key in details]
    comparisons = []
    async with httpx.AsyncClient(auth=(email, token), timeout=30) as client:
        for key in sample_keys:
            response = await client.get(f"{base}/rest/api/3/issue/{key}", params={"fields": "status,resolutiondate,customfield_12152,customfield_12151"})
            response.raise_for_status()
            fields = response.json()["fields"]
            raw_first = fields.get("customfield_12152") or {}
            if not raw_first.get("completedCycles") and not raw_first.get("ongoingCycle"):
                assert not any(cycle["metric"] == "initial_response" for cycle in details[key]["sla_cycles"])
            comparisons.append({
                "key": key, "jira_current_status_category": fields["status"]["statusCategory"]["key"],
                "report_status_category": details[key]["status_category"],
                "jira_resolution_date_present": bool(fields.get("resolutiondate")),
                "report_unresolved": details[key]["is_unresolved"], "reopen_count": details[key]["reopen_count"],
                "initial_sla_cycles": len(raw_first.get("completedCycles", [])) + int(bool(raw_first.get("ongoingCycle"))),
            })
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "stage": "verified", "seconds": round(perf_counter() - started, 2),
        "period": report["period"], "start_date": report["start_date"], "end_date": report["end_date"],
        "issue_count": len(details), "summary": report["summary"],
        "sla": report["sla"], "warning_count": len(report["warnings"]),
        "sample_comparisons": comparisons,
    }, ensure_ascii=False), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", choices=("week", "month"), default="week")
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    asyncio.run(verify(arguments.period, arguments.date, arguments.output))


if __name__ == "__main__":
    main()
