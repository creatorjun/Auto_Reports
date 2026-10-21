# backend/src/application/ports/personal_data_port.py
from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.auth_identity import AuthIdentity
from src.domain.entities.personal_data import PersonalDataAccount, PersonalDataAction, PersonalDataProfile, PersonalDataReportResult


class PersonalDataProfilePort(ABC):
    @abstractmethod
    async def register_identity(self, identity: AuthIdentity) -> AuthIdentity: ...

    @abstractmethod
    async def resolve_identity(self, identity: AuthIdentity) -> AuthIdentity: ...


class PersonalDataReportingPort(ABC):
    @abstractmethod
    async def save_reporting_grant(self, account_id: str, refresh_token: str) -> None: ...

    @abstractmethod
    async def reporting_status(self) -> dict: ...

    @abstractmethod
    async def run_reporting(self) -> dict: ...


class PersonalDataSnapshotPort(ABC):
    @abstractmethod
    async def collect_accounts(self) -> tuple[PersonalDataAccount, ...]: ...

    @abstractmethod
    async def erase_personal_data(self, account_ids: tuple[str, ...]) -> int: ...

    @abstractmethod
    async def mark_personal_data_updated(self, account_ids: tuple[str, ...]) -> int: ...

    @abstractmethod
    async def coverage(self) -> dict[str, int]: ...


class PersonalDataRepositoryPort(ABC):
    @abstractmethod
    async def apply_refreshed_profiles(self, profiles: tuple[PersonalDataProfile, ...]) -> int: ...

    @abstractmethod
    async def record_result(self, account_ids: tuple[str, ...], actions: tuple[PersonalDataAction, ...], checked_at: datetime, next_report_at: datetime) -> None: ...

    @abstractmethod
    async def register_accounts(self, accounts: tuple[PersonalDataAccount, ...]) -> None: ...

    @abstractmethod
    async def due_accounts(self, now: datetime, limit: int) -> tuple[PersonalDataAccount, ...]: ...

    @abstractmethod
    async def pending_actions(self) -> tuple[PersonalDataAction, ...]: ...

    @abstractmethod
    async def stage_actions(self, actions: tuple[PersonalDataAction, ...]) -> None: ...

    @abstractmethod
    async def finish_actions(self, actions: tuple[PersonalDataAction, ...]) -> None: ...

    @abstractmethod
    async def mark_reported(self, account_ids: tuple[str, ...], checked_at: datetime, next_report_at: datetime) -> None: ...


class PersonalDataReportingFailure(RuntimeError):
    def __init__(self, code: str, retry_after_seconds: int = 300) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after_seconds = retry_after_seconds


class PersonalDataReporterPort(ABC):
    @abstractmethod
    async def report(self, accounts: tuple[PersonalDataAccount, ...]) -> PersonalDataReportResult: ...


class PersonalDataUserSourcePort(ABC):
    @abstractmethod
    async def get_profile(self, account_id: str) -> PersonalDataProfile: ...
