# backend/src/domain/entities/solution_package.py
from dataclasses import dataclass


@dataclass(frozen=True)
class SolutionPackage:
    id: str
    name: str
    version: str
    category: str
    evidence: str
    cve_ids: tuple[str, ...] | None = None
