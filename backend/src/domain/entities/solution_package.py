# backend/src/domain/entities/solution_package.py
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SolutionPackage:
    id: str
    name: str
    version: str
    category: str
    evidence: str
    cve_ids: tuple[str, ...] | None = None
    cve_basis: Literal["advisory", "inventory"] = "inventory"


@dataclass(frozen=True)
class SolutionFeedData:
    ecosystem: str
    matches: dict[str, tuple[str, ...] | None]

    @property
    def complete(self) -> bool:
        return True

    @property
    def note(self) -> str:
        checked = sum(result is not None for result in self.matches.values())
        return f"정확한 버전으로 대조한 항목 {checked}개 · 대조 제한 {len(self.matches) - checked}개"
