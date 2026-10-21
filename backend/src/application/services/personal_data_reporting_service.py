# backend/src/application/services/personal_data_reporting_service.py
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from src.application.ports.personal_data_port import (
    PersonalDataProfilePort,
    PersonalDataRepositoryPort,
    PersonalDataReportingFailure,
    PersonalDataReportingLockPort,
    PersonalDataReportingPort,
    PersonalDataSnapshotPort,
)
from src.application.use_cases.report_personal_data import ReportPersonalDataUseCase
from src.domain.entities.auth_identity import AuthIdentity

logger = logging.getLogger(__name__)


class PersonalDataReportingService(PersonalDataProfilePort, PersonalDataReportingPort):
    def __init__(
        self,
        repository: PersonalDataRepositoryPort,
        snapshots: PersonalDataSnapshotPort,
        use_case: ReportPersonalDataUseCase,
        reporting_lock: PersonalDataReportingLockPort,
    ) -> None:
        self._repository = repository
        self._snapshots = snapshots
        self._use_case = use_case
        self._reporting_lock = reporting_lock
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
                and not status["account_states"].get("updated")
            ),
        }

    async def run_reporting(self) -> dict:
        if self._lock.locked():
            return {"status": "already_running"}
        async with self._lock:
            async with self._reporting_lock.acquire() as acquired:
                if not acquired:
                    return {"status": "already_running"}
                now = datetime.now(timezone.utc)
                retry_not_before = None
                try:
                    status = await self._repository.status()
                    retry_not_before = datetime.fromisoformat(status["next_attempt_at"]) if status["next_attempt_at"] else None
                    retry_scheduled = retry_not_before is not None and retry_not_before > now
                    await self._use_case.erase_pending(refresh_profiles=not retry_scheduled)
                    if retry_scheduled:
                        return {"status": "retry_scheduled", "next_attempt_at": status["next_attempt_at"]}
                    await self._repository.register_accounts(await self._snapshots.collect_accounts())
                    status = await self._repository.status()
                    if not status["owner_authorized"]:
                        return {"status": "owner_authorization_required"}
                    if status["next_attempt_at"] and datetime.fromisoformat(status["next_attempt_at"]) > now:
                        return {"status": "retry_scheduled", "next_attempt_at": status["next_attempt_at"]}
                    result = await self._use_case.execute()
                    completed_status = await self._repository.status()
                except PersonalDataReportingFailure as error:
                    now = datetime.now(timezone.utc)
                    retry_at = max(now + timedelta(seconds=error.retry_after_seconds), retry_not_before or now)
                    await self._repository.record_attempt(now, error=error.code, next_attempt_at=retry_at)
                    logger.warning("Personal data reporting deferred: %s", error.code)
                    return {"status": error.code, "next_attempt_at": retry_at.isoformat()}
                except Exception:
                    now = datetime.now(timezone.utc)
                    await self._repository.record_attempt(now, error="reporting_processing_failed", next_attempt_at=max(now + timedelta(minutes=5), retry_not_before or now))
                    logger.error("Personal data reporting processing failed")
                    return {"status": "reporting_processing_failed"}
                pending = any(completed_status["account_states"].get(state) for state in ("pending_closed", "pending_updated", "updated"))
                if not pending and (result["reported_accounts"] > 0 or completed_status["last_error"]):
                    await self._repository.record_attempt(datetime.now(timezone.utc))
                return {"status": "ok", **result}
