# backend/src/infrastructure/persistence/personal_data_suppression.py
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.snapshot_personal_data import PERSON_FIELDS, erase_snapshot_people, mark_snapshot_people_updated, refresh_snapshot_people, valid_account_id
from src.domain.entities.personal_data import PersonalDataProfile
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM


async def lock_personal_data_writes(session: AsyncSession) -> None:
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(20261016, 310)"))


async def suppress_erased_people(session: AsyncSession, payload: dict) -> bool:
    def account_ids(value: object) -> set[str]:
        if isinstance(value, list):
            return set().union(*(account_ids(item) for item in value))
        if not isinstance(value, dict):
            return set()
        own = {
            value[f"{field}_account_id"] for field in PERSON_FIELDS
            if field in value and valid_account_id(value.get(f"{field}_account_id"))
        }
        return own.union(*(account_ids(item) for item in value.values() if isinstance(item, (dict, list))))
    accounts = account_ids(payload)
    if not accounts:
        return False
    await lock_personal_data_writes(session)
    result = await session.execute(select(PersonalDataAccountORM).where(PersonalDataAccountORM.account_id.in_(accounts)))
    records = result.scalars().all()
    erased = erase_snapshot_people(payload, {row.account_id for row in records if row.status in {"closed", "pending_closed"}})
    updated = mark_snapshot_people_updated(payload, {row.account_id for row in records if row.status in {"updated", "pending_updated"}})
    profiles = {
        row.account_id: PersonalDataProfile(row.account_id, row.display_name, row.profile_retrieved_at or row.oldest_retrieved_at)
        for row in records if row.status == "active" and row.display_name
    }
    refreshed = refresh_snapshot_people(payload, profiles, datetime.min.replace(tzinfo=timezone.utc), only_if_older=True)
    return erased or updated or refreshed
