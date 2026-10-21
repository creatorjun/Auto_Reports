# backend/src/application/use_cases/report_personal_data.py
from datetime import datetime, timedelta, timezone

from src.application.ports.personal_data_port import PersonalDataReporterPort, PersonalDataRepositoryPort, PersonalDataReportingFailure, PersonalDataSnapshotPort, PersonalDataUserSourcePort


class ReportPersonalDataUseCase:
    def __init__(self, repository: PersonalDataRepositoryPort, reporter: PersonalDataReporterPort, snapshots: PersonalDataSnapshotPort, profiles: PersonalDataUserSourcePort) -> None:
        self._repository = repository
        self._reporter = reporter
        self._snapshots = snapshots
        self._profiles = profiles

    async def erase_pending(self, *, refresh_profiles: bool = True) -> int:
        actions = await self._repository.pending_actions()
        if not actions:
            return 0
        closed = tuple(action for action in actions if action.status == "closed")
        updated = tuple(action for action in actions if action.status == "updated")
        count = 0
        if closed:
            count = await self._snapshots.erase_personal_data(tuple(action.account_id for action in closed))
            await self._repository.finish_actions(closed)
        if updated:
            await self._snapshots.mark_personal_data_updated(tuple(action.account_id for action in updated))
            await self._repository.finish_actions(updated)
            if not refresh_profiles:
                return count
            refreshed = []
            failure = None
            for action in updated[:90]:
                try:
                    refreshed.append(await self._profiles.get_profile(action.account_id))
                except PersonalDataReportingFailure as error:
                    failure = failure or error
                    if error.code == "profile_rate_limited":
                        failure = error
                        break
            if refreshed:
                await self._repository.apply_refreshed_profiles(tuple(refreshed))
            if failure is not None:
                raise failure
        return count

    async def execute(self, now: datetime | None = None) -> dict:
        fixed_now = now
        now = now or datetime.now(timezone.utc)
        erased = await self.erase_pending()
        await self._repository.register_accounts(await self._snapshots.collect_accounts())
        reported = 0
        for _ in range(10):
            accounts = await self._repository.due_accounts(now, 90)
            if not accounts:
                break
            result = await self._reporter.report(accounts)
            checked_at = fixed_now or datetime.now(timezone.utc)
            await self._repository.record_result(
                tuple(account.account_id for account in accounts), result.actions, checked_at,
                checked_at + timedelta(seconds=result.cycle_period_seconds),
            )
            reported += len(accounts)
            erased += await self.erase_pending()
        return {"reported_accounts": reported, "erased_report_rows": erased}
