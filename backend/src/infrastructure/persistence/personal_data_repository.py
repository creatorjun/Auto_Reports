# backend/src/infrastructure/persistence/personal_data_repository.py
import hmac
import re
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from src.application.ports.personal_data_port import PersonalDataRepositoryPort, PersonalDataReportingFailure
from src.application.services.snapshot_personal_data import is_person_name, utc, valid_account_id
from src.domain.entities.auth_identity import AuthIdentity
from src.domain.entities.personal_data import PersonalDataAccount, PersonalDataAction, PersonalDataProfile
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.personal_data_models import PersonalDataAccountORM, PersonalDataGrantORM
from src.infrastructure.persistence.personal_data_snapshot_store import PersonalDataSnapshotStore
from src.infrastructure.persistence.personal_data_suppression import lock_personal_data_writes
from src.infrastructure.security.personal_data_cipher import PersonalDataCipher


def _aware(value: datetime | None) -> datetime | None:
    return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value


class PersonalDataRepository(PersonalDataRepositoryPort):
    def __init__(
        self, database: Database, server_secret: str, owner_account_id: str,
        on_profiles_refreshed: Callable[[], Awaitable[None]] | None = None,
        on_actions_staged: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._database = database
        self._server_secret = server_secret
        self._owner_account_id = owner_account_id
        self._on_profiles_refreshed = on_profiles_refreshed
        self._on_actions_staged = on_actions_staged

    async def record_result(self, account_ids: tuple[str, ...], actions: tuple[PersonalDataAction, ...], checked_at: datetime, next_report_at: datetime) -> None:
        staged = False
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            for action in actions:
                result = await session.execute(update(PersonalDataAccountORM).where(
                    PersonalDataAccountORM.account_id == action.account_id,
                    PersonalDataAccountORM.status == "active",
                ).values(
                    display_name=None, email_address=None, profile_retrieved_at=None, status=f"pending_{action.status}",
                    profile_version=PersonalDataAccountORM.profile_version + 1,
                ))
                staged = result.rowcount > 0 or staged
                if action.status == "closed":
                    await session.execute(update(PersonalDataGrantORM).where(
                        PersonalDataGrantORM.account_id == action.account_id,
                    ).values(account_id=None, refresh_token_encrypted=None, last_error="owner_authorization_required"))
            await session.execute(update(PersonalDataAccountORM).where(
                PersonalDataAccountORM.account_id.in_(account_ids),
            ).values(last_reported_at=checked_at, next_report_at=next_report_at))
        if staged and self._on_actions_staged is not None:
            await self._on_actions_staged()

    @staticmethod
    def _account_id(identity: AuthIdentity) -> str:
        parts = identity.username.split(":", 2)
        if identity.auth_provider != "jira" or len(parts) != 3 or not parts[1]:
            raise ValueError("Invalid Jira identity")
        account_id = parts[2]
        if not re.fullmatch(r"[a-zA-Z0-9:_-]{1,128}", account_id) or account_id == "unknown":
            raise ValueError("Invalid Jira account")
        return account_id

    async def register_identity(self, identity: AuthIdentity) -> AuthIdentity:
        account_id = self._account_id(identity)
        now = datetime.now(timezone.utc)
        refreshed = False
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            await session.execute(insert(PersonalDataAccountORM).values(
                account_id=account_id, display_name=None, oldest_retrieved_at=now,
                profile_version=1, status="active", next_report_at=now,
            ).on_conflict_do_nothing(index_elements=["account_id"]))
            row = (await session.execute(select(PersonalDataAccountORM).where(
                PersonalDataAccountORM.account_id == account_id,
            ).with_for_update())).scalar_one()
            if row.status in {"closed", "pending_closed", "pending_updated"}:
                raise ValueError("Jira profile is unavailable")
            if row.status == "updated":
                await PersonalDataSnapshotStore(session).refresh_personal_data((PersonalDataProfile(account_id, identity.display_name, now),))
                row.oldest_retrieved_at = now
                row.next_report_at = row.next_report_at or now
                refreshed = True
            row.display_name = identity.display_name
            row.email_address = identity.email_address
            row.profile_retrieved_at = now
            row.status = "active"
            registered = replace(identity, profile_version=row.profile_version)
        if refreshed and self._on_profiles_refreshed is not None:
            await self._on_profiles_refreshed()
        return registered

    async def apply_refreshed_profiles(self, profiles: tuple[PersonalDataProfile, ...]) -> int:
        if not profiles:
            return 0
        if len({profile.account_id for profile in profiles}) != len(profiles) or any(
            not valid_account_id(profile.account_id) or not is_person_name(profile.display_name)
            or len(profile.display_name) > 200 or profile.display_name != profile.display_name.strip()
            or profile.retrieved_at.tzinfo is None
            for profile in profiles
        ):
            raise ValueError("Invalid refreshed personal data profiles")
        profile_map = {profile.account_id: profile for profile in profiles}
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            result = await session.execute(select(PersonalDataAccountORM).where(
                PersonalDataAccountORM.account_id.in_(profile_map),
                PersonalDataAccountORM.status.in_(("updated", "pending_updated")),
            ).order_by(PersonalDataAccountORM.account_id).with_for_update())
            rows = result.scalars().all()
            if not rows:
                return 0
            await PersonalDataSnapshotStore(session).refresh_personal_data(tuple(profile_map[row.account_id] for row in rows))
            for row in rows:
                profile = profile_map[row.account_id]
                row.display_name = profile.display_name
                row.email_address = profile.email_address
                row.profile_retrieved_at = utc(profile.retrieved_at)
                row.oldest_retrieved_at = utc(profile.retrieved_at)
                row.status = "active"
        if self._on_profiles_refreshed is not None:
            await self._on_profiles_refreshed()
        return len(rows)

    async def resolve_identity(self, identity: AuthIdentity) -> AuthIdentity:
        account_id = self._account_id(identity)
        async with self._database.session() as session:
            row = await session.get(PersonalDataAccountORM, account_id)
            if row is None or row.status != "active" or row.profile_version != identity.profile_version or not row.display_name:
                raise ValueError("Jira profile is unavailable")
            return replace(identity, display_name=row.display_name, profile_version=row.profile_version, email_address=row.email_address)

    async def register_accounts(self, accounts: tuple[PersonalDataAccount, ...]) -> None:
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            records = (await session.execute(select(PersonalDataAccountORM).where(
                PersonalDataAccountORM.account_id.in_(tuple(account.account_id for account in accounts)),
            ).order_by(PersonalDataAccountORM.account_id).with_for_update())).scalars().all()
            existing = {record.account_id: record for record in records}
            snapshot_times = None
            for account in accounts:
                if account.account_id == "unknown" or not re.fullmatch(r"[a-zA-Z0-9:_-]{1,128}", account.account_id):
                    continue
                retrieved_at = utc(account.updated_at)
                current = existing.get(account.account_id)
                if current is not None and current.status == "active" and current.profile_retrieved_at is not None and retrieved_at < utc(current.oldest_retrieved_at):
                    if snapshot_times is None:
                        snapshot_times = {item.account_id: utc(item.updated_at) for item in await PersonalDataSnapshotStore(session).collect_accounts()}
                    profile_time = utc(current.profile_retrieved_at)
                    retrieved_at = min(profile_time, snapshot_times.get(account.account_id, profile_time))
                statement = insert(PersonalDataAccountORM).values(
                    account_id=account.account_id, display_name=None,
                    oldest_retrieved_at=retrieved_at, profile_version=1,
                    status="active", next_report_at=now,
                )
                await session.execute(statement.on_conflict_do_update(
                    index_elements=["account_id"],
                    set_={"oldest_retrieved_at": func.least(PersonalDataAccountORM.oldest_retrieved_at, statement.excluded.oldest_retrieved_at)},
                    where=PersonalDataAccountORM.status == "active",
                ))

    async def due_accounts(self, now: datetime, limit: int) -> tuple[PersonalDataAccount, ...]:
        async with self._database.session() as session:
            rows = (await session.execute(select(PersonalDataAccountORM).where(
                PersonalDataAccountORM.status == "active",
                PersonalDataAccountORM.next_report_at <= now,
            ).order_by(PersonalDataAccountORM.next_report_at, PersonalDataAccountORM.account_id).limit(min(limit, 90)))).scalars()
            return tuple(PersonalDataAccount(row.account_id, _aware(row.oldest_retrieved_at)) for row in rows)

    async def pending_actions(self) -> tuple[PersonalDataAction, ...]:
        async with self._database.session() as session:
            rows = (await session.execute(select(PersonalDataAccountORM).where(
                PersonalDataAccountORM.status.in_(("pending_updated", "pending_closed", "updated", "closed")),
            ))).scalars()
            return tuple(PersonalDataAction(row.account_id, row.status.removeprefix("pending_")) for row in rows)

    async def stage_actions(self, actions: tuple[PersonalDataAction, ...]) -> None:
        staged = False
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            for action in actions:
                result = await session.execute(update(PersonalDataAccountORM).where(
                    PersonalDataAccountORM.account_id == action.account_id,
                    PersonalDataAccountORM.status == "active",
                ).values(
                    display_name=None, email_address=None, profile_retrieved_at=None, status=f"pending_{action.status}",
                    profile_version=PersonalDataAccountORM.profile_version + 1,
                ))
                staged = result.rowcount > 0 or staged
        if staged and self._on_actions_staged is not None:
            await self._on_actions_staged()

    async def finish_actions(self, actions: tuple[PersonalDataAction, ...]) -> None:
        async with self._database.session() as session:
            await lock_personal_data_writes(session)
            for action in actions:
                await session.execute(update(PersonalDataAccountORM).where(
                    PersonalDataAccountORM.account_id == action.account_id,
                    PersonalDataAccountORM.status == f"pending_{action.status}",
                ).values(status=action.status, display_name=None, email_address=None))

    async def mark_reported(self, account_ids: tuple[str, ...], checked_at: datetime, next_report_at: datetime) -> None:
        async with self._database.session() as session:
            await session.execute(update(PersonalDataAccountORM).where(
                PersonalDataAccountORM.account_id.in_(account_ids),
            ).values(last_reported_at=checked_at, next_report_at=next_report_at))

    async def save_reporting_grant(self, account_id: str, refresh_token: str) -> None:
        if not self._owner_account_id or not hmac.compare_digest(account_id, self._owner_account_id):
            raise ValueError("The configured app owner must authorize reporting")
        encrypted = PersonalDataCipher(self._server_secret).encrypt(refresh_token)
        now = datetime.now(timezone.utc)
        async with self._database.session() as session:
            await session.execute(insert(PersonalDataAccountORM).values(
                account_id=account_id, display_name=None, oldest_retrieved_at=now,
                profile_version=1, status="active", next_report_at=now,
            ).on_conflict_do_nothing(index_elements=["account_id"]))
            owner_status = await session.scalar(select(PersonalDataAccountORM.status).where(PersonalDataAccountORM.account_id == account_id))
            if owner_status in {"closed", "pending_closed"}:
                raise ValueError("The reporting owner is unavailable")
            statement = insert(PersonalDataGrantORM).values(
                id=1, account_id=account_id, refresh_token_encrypted=encrypted, updated_at=now,
            )
            await session.execute(statement.on_conflict_do_update(
                index_elements=["id"], set_={
                    "account_id": account_id, "refresh_token_encrypted": encrypted,
                    "updated_at": now, "next_attempt_at": None, "last_error": None,
                },
            ))

    async def get_reporting_grant(self) -> tuple[str, str]:
        async with self._database.session() as session:
            row = await session.get(PersonalDataGrantORM, 1)
            if row is None or not row.refresh_token_encrypted or row.account_id != self._owner_account_id:
                raise PersonalDataReportingFailure("owner_authorization_required", 3600)
            try:
                token = PersonalDataCipher(self._server_secret).decrypt(row.refresh_token_encrypted)
            except ValueError:
                raise PersonalDataReportingFailure("owner_credential_unreadable", 3600) from None
            return row.account_id, token

    async def status(self) -> dict:
        async with self._database.session() as session:
            grant = await session.get(PersonalDataGrantORM, 1)
            states = dict((await session.execute(select(PersonalDataAccountORM.status, func.count()).group_by(PersonalDataAccountORM.status))).all())
            configured = bool(grant and grant.refresh_token_encrypted and grant.account_id == self._owner_account_id)
            unreported = await session.scalar(select(func.count()).select_from(PersonalDataAccountORM).where(
                PersonalDataAccountORM.status == "active", PersonalDataAccountORM.last_reported_at.is_(None),
            ))
            overdue = await session.scalar(select(func.count()).select_from(PersonalDataAccountORM).where(
                PersonalDataAccountORM.status == "active", PersonalDataAccountORM.next_report_at <= datetime.now(timezone.utc),
            ))
            return {
                "owner_authorized": configured,
                "registered_accounts": sum(states.values()), "account_states": states,
                "unreported_accounts": unreported, "due_accounts": overdue,
                "next_attempt_at": _aware(grant.next_attempt_at).isoformat() if grant and grant.next_attempt_at else None,
                "last_success_at": _aware(grant.last_success_at).isoformat() if grant and grant.last_success_at else None,
                "last_error": grant.last_error if grant else None,
            }

    async def record_attempt(self, now: datetime, *, error: str | None = None, next_attempt_at: datetime | None = None) -> None:
        async with self._database.session() as session:
            values = {"next_attempt_at": next_attempt_at, "last_error": error}
            if error is None:
                values["last_success_at"] = now
            await session.execute(update(PersonalDataGrantORM).where(PersonalDataGrantORM.id == 1).values(**values))
