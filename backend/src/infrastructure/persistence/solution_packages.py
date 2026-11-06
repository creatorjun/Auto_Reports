# backend/src/infrastructure/persistence/solution_packages.py
from functools import cache
import json
from pathlib import Path

from src.domain.entities.solution_package import SolutionPackage


_INVENTORY_DIR = Path(__file__).resolve().parents[1] / "data" / "solution_packages"
_INVENTORIES: dict[tuple[str, str | None], str | None] = {
    ("eyeCloudSIM", "3.1.0"): None,
    ("eyeCloudSIM", "3.1.03"): None,
    ("eyeCloudXoar", "4.0_R1"): None,
    ("eyeCloudXoar", "4.0_R2"): "eyecloudxoar_4_0_r2.json",
    ("eyeCloudXoar", "4.0_R3"): None,
    ("eyeCloudAI", None): None,
}


@cache
def _load_inventory(path: Path) -> tuple[SolutionPackage, ...]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        if row.get("cve_ids") is not None:
            row["cve_ids"] = tuple(row["cve_ids"])
    return tuple(SolutionPackage(**row) for row in rows)


def read_solution_packages(product: str, version: str | None) -> tuple[SolutionPackage, ...] | None:
    selection = (product, version)
    if selection not in _INVENTORIES:
        return None
    filename = _INVENTORIES[selection]
    if filename is None:
        return ()
    try:
        return _load_inventory(_INVENTORY_DIR / filename)
    except FileNotFoundError:
        return ()
