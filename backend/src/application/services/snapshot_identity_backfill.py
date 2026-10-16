# backend/src/application/services/snapshot_identity_backfill.py
import asyncio
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from src.application.ports.jira_identity_history_port import JiraIdentityHistoryPort, JiraIdentityHistoryUnavailable
from src.application.services.snapshot_personal_data import aggregate_gaps, resolve_snapshot_account, snapshot_people
from src.domain.entities.jira_identity_history import JiraIdentityHistory, SnapshotPerson


@dataclass
class IdentityBackfillResult:
    documents: int = 0
    issues: int = 0
    personal_fields: int = 0
    previously_mapped: int = 0
    verified_fields: int = 0
    aggregate_gaps: int = 0
    failures: list[dict[str, str | int]] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "documents": self.documents,
            "issues": self.issues,
            "personal_fields": self.personal_fields,
            "previously_mapped": self.previously_mapped,
            "verified_fields": self.verified_fields,
            "unmapped_personal_fields": len(self.failures) + self.aggregate_gaps,
            "aggregate_gaps": self.aggregate_gaps,
            "failure_reasons": dict(Counter(str(item["reason"]) for item in self.failures)),
            "unresolved": self.failures,
        }


async def backfill_snapshot_identities(
    documents: list[tuple[str, int, datetime, dict]],
    source: JiraIdentityHistoryPort,
    field_ids: dict[str, tuple[str, ...]],
    concurrency: int = 4,
) -> IdentityBackfillResult:
    result = IdentityBackfillResult(documents=len(documents))
    people: dict[str, list[tuple[str, int, SnapshotPerson]]] = {}
    for kind, row_id, generated_at, payload in documents:
        result.aggregate_gaps += aggregate_gaps(payload)
        for person in snapshot_people(payload, generated_at):
            result.personal_fields += 1
            if person.account_id:
                result.previously_mapped += 1
            else:
                people.setdefault(person.issue_key, []).append((kind, row_id, person))
    result.issues = len(people)
    semaphore = asyncio.Semaphore(concurrency)

    async def resolve(key: str, references: list[tuple[str, int, SnapshotPerson]]) -> None:
        history: JiraIdentityHistory | None = None
        async with semaphore:
            try:
                history = await source.fetch(key)
            except JiraIdentityHistoryUnavailable:
                pass
        for kind, row_id, person in references:
            account_id, reason = resolve_snapshot_account(person, history, field_ids, refreshed_snapshot=kind == "dashboard") if history else (None, "jira_history_unavailable")
            if account_id:
                person.item[f"{person.field}_account_id"] = account_id
                result.verified_fields += 1
            else:
                result.failures.append({"kind": kind, "report_id": row_id, "issue_key": key, "field": person.field, "reason": reason})

    await asyncio.gather(*(resolve(key, refs) for key, refs in sorted(people.items())))
    result.failures.sort(key=lambda item: (str(item["kind"]), int(item["report_id"]), str(item["issue_key"]), str(item["field"])))
    return result
