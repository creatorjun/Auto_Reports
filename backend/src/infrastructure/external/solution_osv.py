# backend/src/infrastructure/external/solution_osv.py
import asyncio
import json
import re
import tempfile
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from threading import Event
from typing import BinaryIO
from zipfile import ZipFile

import httpx

from src.domain.entities.solution_package import SolutionPackage
from src.infrastructure.external.solution_osv_versions import affected_version


_SOURCES = {
    "Maven": ("Java 라이브러리와 JDBC 드라이버", re.compile(r"[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+")),
    "npm": ("웹 라이브러리", re.compile(r"(?:@[a-z0-9~][a-z0-9._~-]*/)?[a-z0-9~][a-z0-9._~-]*")),
}
_CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,}")
_MAX_DOWNLOAD = 384 * 1024 * 1024
_MAX_RECORD = 16 * 1024 * 1024
_MAX_EXPANDED = 2 * 1024**3


@dataclass
class _Matches:
    package: SolutionPackage
    seen: bool = False
    confirmed: set[str] = field(default_factory=set)
    uncertain: set[str] = field(default_factory=set)

    def result(self, withdrawn: set[str]) -> tuple[str, ...] | None:
        if not self.seen or self.uncertain - self.confirmed - withdrawn:
            return None
        return tuple(sorted(self.confirmed - withdrawn))


def _scan_archive(
    stream: BinaryIO, ecosystem: str, targets: dict[str, list[_Matches]], cancelled: Event,
) -> dict[str, tuple[str, ...] | None]:
    withdrawn: set[str] = set()
    has_ecosystem_cves = False
    with ZipFile(stream) as archive:
        entries = archive.infolist()
        if len(entries) > 500_000 or sum(entry.file_size for entry in entries) > _MAX_EXPANDED:
            raise ValueError("OSV archive exceeds the processing limit")
        for entry in entries:
            if cancelled.is_set():
                raise InterruptedError("OSV collection cancelled")
            if not entry.filename.endswith(".json"):
                continue
            if entry.file_size > _MAX_RECORD:
                raise ValueError("OSV record exceeds the processing limit")
            record = json.loads(archive.read(entry))
            identifier = record["id"]
            if record.get("withdrawn"):
                if _CVE.fullmatch(identifier):
                    withdrawn.add(identifier)
                continue
            cves = {v for v in (identifier, *record.get("aliases", [])) if _CVE.fullmatch(v)}
            if not cves:
                continue
            for affected in record.get("affected", []):
                identity = affected.get("package") or {}
                if identity.get("ecosystem") != ecosystem:
                    continue
                has_ecosystem_cves = True
                for match in targets.get(identity["name"], ()):
                    match.seen = True
                    status = affected_version(match.package.version, ecosystem, affected)
                    if status is True:
                        match.confirmed.update(cves)
                    elif status is None:
                        match.uncertain.update(cves)
    if not has_ecosystem_cves:
        raise ValueError("OSV archive contains no active CVEs for the requested ecosystem")
    return {match.package.id: match.result(withdrawn) for matches in targets.values() for match in matches}


def _collect(packages: Sequence[SolutionPackage], ecosystem: str, cancelled: Event) -> dict[str, tuple[str, ...] | None]:
    category, name_pattern = _SOURCES[ecosystem]
    targets: dict[str, list[_Matches]] = defaultdict(list)
    result = {}
    for item in packages:
        if item.category != category:
            continue
        result[item.id] = None
        if not name_pattern.fullmatch(item.name):
            continue
        if ecosystem == "npm" and (item.cve_ids is None or "CSS" in item.evidence):
            continue
        targets[item.name].append(_Matches(item))
    if not targets:
        return result
    url = f"https://storage.googleapis.com/osv-vulnerabilities/{ecosystem}/all.zip"
    with tempfile.TemporaryFile() as stream:
        with httpx.stream("GET", url, timeout=60, follow_redirects=False) as response:
            response.raise_for_status()
            if int(response.headers.get("content-length", "0")) > _MAX_DOWNLOAD:
                raise ValueError("OSV archive exceeds the download limit")
            for chunk in response.iter_bytes(256 * 1024):
                if cancelled.is_set():
                    raise InterruptedError("OSV collection cancelled")
                if stream.tell() + len(chunk) > _MAX_DOWNLOAD:
                    raise ValueError("OSV archive exceeds the download limit")
                stream.write(chunk)
        stream.seek(0)
        result.update(_scan_archive(stream, ecosystem, targets, cancelled))
    return result


async def match_solution_packages(packages: Sequence[SolutionPackage], ecosystem: str) -> dict[str, tuple[str, ...] | None]:
    """Fetch only the public ecosystem dump and match the supplied inventory inside the process."""
    if ecosystem not in _SOURCES:
        raise ValueError("Unsupported OSV solution ecosystem")
    cancelled = Event()
    try:
        return await asyncio.wait_for(asyncio.to_thread(_collect, packages, ecosystem, cancelled), timeout=600)
    finally:
        cancelled.set()
