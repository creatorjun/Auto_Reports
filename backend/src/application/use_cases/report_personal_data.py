# backend/src/application/use_cases/report_personal_data.py
from datetime import datetime, timedelta, timezone

from src.application.ports.personal_data_port import PersonalDataReporterPort, PersonalDataRepositoryPort, PersonalDataSnapshotPort


class ReportPersonalDataUseCase:
    def __init__(self, repository: PersonalDataRepositoryPort, reporter: PersonalDataReporterPort, snapshots: PersonalDataSnapshotPort) -> None:
        self._repository = repository
        self._reporter = reporter
        self._snapshots = snapshots

    async def erase_pending(self) -> int:
        actions = await self._repository.pending_actions()
        if not actions:
            return 0
        count = await self._snapshots.erase_personal_data(tuple(action.account_id for action in actions))
        await self._repository.finish_actions(actions)
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
