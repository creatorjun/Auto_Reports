# backend/src/infrastructure/persistence/personal_data_suppression.py
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.snapshot_personal_data import erase_snapshot_people, snapshot_people
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM


async def lock_personal_data_writes(session: AsyncSession) -> None:
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(20261016, 310)"))


async def suppress_erased_people(session: AsyncSession, payload: dict) -> bool:
    accounts = {person.account_id for person in snapshot_people(payload, datetime.now(timezone.utc)) if person.account_id}
    if not accounts:
        return False
    await lock_personal_data_writes(session)
    result = await session.execute(select(PersonalDataAccountORM.account_id).where(
        PersonalDataAccountORM.account_id.in_(accounts), PersonalDataAccountORM.status != "active",
    ))
    return erase_snapshot_people(payload, set(result.scalars().all()))
