# backend/src/domain/value_objects/date_range.py
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    @classmethod
    def last_7_days(cls, today: date) -> "DateRange":
        return cls(start=today - timedelta(days=6), end=today)

    def format_start(self) -> str:
        return self.start.strftime("%Y-%m-%d")

    def format_end(self) -> str:
        return self.end.strftime("%Y-%m-%d")
