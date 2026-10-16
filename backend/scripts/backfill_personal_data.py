# backend/scripts/backfill_personal_data.py
import argparse
import asyncio
import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.application.services.snapshot_identity_backfill import backfill_snapshot_identities
from src.infrastructure.config.settings import get_settings
from src.infrastructure.external.jira_identity_history_source import JiraIdentityHistorySource
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.personal_data_snapshot_store import PersonalDataSnapshotStore
from src.infrastructure.persistence.personal_data_suppression import lock_personal_data_writes


async def backfill(apply: bool) -> dict:
    settings = get_settings()
    database = Database(settings.database_url)
    field_ids = {
        "reporter": ("reporter",), "assignee": ("assignee",),
        "tac_assignee": (settings.jira_recent_tac_assignee_field_id,),
        "tac_team": (settings.jira_tac_assignee_field_id, settings.jira_qa_assignee_field_id, "assignee"),
    }
    try:
        async with httpx.AsyncClient(auth=(settings.jira_email, settings.jira_api_token), timeout=30) as client:
            source = JiraIdentityHistorySource(settings.jira_base_url, client, tuple(dict.fromkeys(item for values in field_ids.values() for item in values)))
            await source.prepare()
            async with database.session() as session:
                if apply:
                    await lock_personal_data_writes(session)
                store = PersonalDataSnapshotStore(session)
                documents = await store.documents(lock=apply)
                result = await backfill_snapshot_identities([(document.kind, document.row_id, document.generated_at, document.payload) for document in documents], source, field_ids)
                if apply:
                    await store.save_identity_metadata(documents)
                return {"mode": "apply" if apply else "read_only", **result.summary()}
    finally:
        await database.aclose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(backfill(args.apply)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
