# backend/src/domain/entities/personal_data.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class PersonalDataAccount:
    account_id: str
    updated_at: datetime


@dataclass(frozen=True)
class PersonalDataAction:
    account_id: str
    status: Literal["updated", "closed"]


@dataclass(frozen=True)
class PersonalDataProfile:
    account_id: str
    display_name: str
    retrieved_at: datetime


@dataclass(frozen=True)
class PersonalDataReportResult:
    actions: tuple[PersonalDataAction, ...] = ()
    cycle_period_seconds: int = 604800
