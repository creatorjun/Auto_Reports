# backend/src/infrastructure/personal_data_runtime.py
import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from src.application.ports.personal_data_port import PersonalDataProfilePort, PersonalDataReportingFailure, PersonalDataReportingPort, PersonalDataSnapshotPort
from src.application.use_cases.report_personal_data import ReportPersonalDataUseCase
from src.domain.entities.auth_identity import AuthIdentity
from src.domain.entities.personal_data import PersonalDataAccount
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.personal_data_client import AtlassianPersonalDataClient
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.personal_data_repository import PersonalDataRepository
from src.infrastructure.persistence.personal_data_snapshot_store import PersonalDataSnapshotStore

logger = logging.getLogger(__name__)


class _Snapshots(PersonalDataSnapshotPort):
    def __init__(self, database: Database, clear_caches: Callable[[], Awaitable[None]] | None = None) -> None:
        self._database = database
        self._clear_caches = clear_caches

    async def collect_accounts(self) -> tuple[PersonalDataAccount, ...]:
        async with self._database.session() as session:
            return await PersonalDataSnapshotStore(session).collect_accounts()

    async def erase_personal_data(self, account_ids: tuple[str, ...]) -> int:
        async with self._database.session() as session:
            count = await PersonalDataSnapshotStore(session).erase_personal_data(account_ids)
        if self._clear_caches:
            await self._clear_caches()
        return count

    async def coverage(self) -> dict[str, int]:
        async with self._database.session() as session:
            return await PersonalDataSnapshotStore(session).coverage()


class PersonalDataRuntime(PersonalDataProfilePort, PersonalDataReportingPort):
    def __init__(self, settings: Settings, database: Database, clear_caches: Callable[[], Awaitable[None]] | None = None) -> None:
        self._database = database
        self._repository = PersonalDataRepository(database, settings.jwt_secret, settings.jira_privacy_owner_account_id)
        self._snapshots = _Snapshots(database, clear_caches)
        self._reporter = AtlassianPersonalDataClient(settings.jira_oauth_client_id, settings.jira_oauth_client_secret, self._repository)
        self._use_case = ReportPersonalDataUseCase(self._repository, self._reporter, self._snapshots)
        self._lock = asyncio.Lock()

    async def register_identity(self, identity: AuthIdentity) -> AuthIdentity:
        return await self._repository.register_identity(identity)

    async def resolve_identity(self, identity: AuthIdentity) -> AuthIdentity:
        return await self._repository.resolve_identity(identity)

    async def save_reporting_grant(self, account_id: str, refresh_token: str) -> None:
        async with self._lock:
            try:
                await self._repository.save_reporting_grant(account_id, refresh_token)
            except ValueError:
                raise PersonalDataReportingFailure("owner_grant_configuration_invalid") from None
            except Exception:
                raise PersonalDataReportingFailure("owner_grant_storage_failed") from None

    async def reporting_status(self) -> dict:
        status = await self._repository.status()
        coverage = await self._snapshots.coverage()
        return {
            **status, "coverage": coverage,
            "reporting_ready": bool(
                status["owner_authorized"] and status["last_success_at"] and not status["last_error"]
                and coverage.get("unmapped_personal_fields", 0) == 0
                and status["unreported_accounts"] == 0 and status["due_accounts"] == 0
                and not status["account_states"].get("pending_closed")
                and not status["account_states"].get("pending_updated")
            ),
        }

    async def run_reporting(self) -> dict:
        if self._lock.locked():
            return {"status": "already_running"}
        async with self._lock:
            async with self._database.session() as lock_session:
                acquired = await lock_session.scalar(text("SELECT pg_try_advisory_xact_lock(20261016, 1900)"))
                if not acquired:
                    return {"status": "already_running"}
                now = datetime.now(timezone.utc)
                try:
                    await self._use_case.erase_pending()
                    await self._repository.register_accounts(await self._snapshots.collect_accounts())
                    status = await self._repository.status()
                    if not status["owner_authorized"]:
                        return {"status": "owner_authorization_required"}
                    if status["next_attempt_at"] and datetime.fromisoformat(status["next_attempt_at"]) > now:
                        return {"status": "retry_scheduled", "next_attempt_at": status["next_attempt_at"]}
                    result = await self._use_case.execute()
                except PersonalDataReportingFailure as error:
                    now = datetime.now(timezone.utc)
                    retry_at = now + timedelta(seconds=error.retry_after_seconds)
                    await self._repository.record_attempt(now, error=error.code, next_attempt_at=retry_at)
                    logger.warning("Personal data reporting deferred: %s", error.code)
                    return {"status": error.code, "next_attempt_at": retry_at.isoformat()}
                except Exception:
                    now = datetime.now(timezone.utc)
                    await self._repository.record_attempt(now, error="reporting_processing_failed", next_attempt_at=now + timedelta(minutes=5))
                    logger.error("Personal data reporting processing failed")
                    return {"status": "reporting_processing_failed"}
                if result["reported_accounts"] > 0:
                    await self._repository.record_attempt(datetime.now(timezone.utc))
                return {"status": "ok", **result}
