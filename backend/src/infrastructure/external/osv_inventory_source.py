# backend/src/infrastructure/external/osv_inventory_source.py
import asyncio
import re
from contextlib import AsyncExitStack
from dataclasses import replace
from datetime import datetime
from urllib.parse import urlsplit

import httpx
from cvss import CVSS2, CVSS3, CVSS4

from src.application.ports.cve_inventory_port import CvePackageSourcePort
from src.domain.entities.cve_inventory import CveFinding, CveInventoryPackage, CveVersionRange


CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
SEVERITY_ORDER = {"unknown": -1, "low": 0, "medium": 1, "high": 2, "critical": 3}
SEMVER_NUMBER = r"(?:0|[1-9][0-9]*)"
SEMVER_PRERELEASE = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
NPM_EXACT_VERSION = re.compile(
    rf"{SEMVER_NUMBER}\.{SEMVER_NUMBER}\.{SEMVER_NUMBER}"
    rf"(?:-{SEMVER_PRERELEASE}(?:\.{SEMVER_PRERELEASE})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z"
)


def safe_reference(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in {"https", "http"} and parsed.hostname and not parsed.username and not parsed.password else None
    except ValueError:
        return None


def cve_identifiers(record: dict) -> tuple[str, ...]:
    values = [record.get("id"), *(record.get("aliases") or [])]
    return tuple(sorted({value.upper() for value in values if isinstance(value, str) and CVE_PATTERN.fullmatch(value)}))


def _package_name(value: str, ecosystem: str) -> str:
    if ecosystem == "PyPI":
        return re.sub(r"[-_.]+", "-", value).lower()
    if ecosystem in {"NuGet", "crates.io"}:
        return value.lower().replace("_", "-") if ecosystem == "crates.io" else value.lower()
    return value


def _matching_affected(record: dict, package: CveInventoryPackage) -> tuple[dict, ...]:
    ecosystem = package.query_ecosystem or package.ecosystem
    name = _package_name(package.query_name or package.name, ecosystem)
    return tuple(
        value for value in record.get("affected", ()) if isinstance(value, dict)
        and isinstance(value.get("package"), dict)
        and value["package"].get("ecosystem") == ecosystem
        and _package_name(str(value["package"].get("name", "")), ecosystem) == name
    )


def validate_osv_record(record: object, package: CveInventoryPackage) -> None:
    if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not record["id"]:
        raise ValueError("Invalid OSV vulnerability identity")
    for field in ("published", "modified", "withdrawn"):
        if field in record and record[field] is not None:
            if not isinstance(record[field], str):
                raise ValueError("Invalid OSV vulnerability timestamp")
            parsed = datetime.fromisoformat(record[field].replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("OSV vulnerability timestamp needs timezone")
    aliases = record.get("aliases", [])
    if not isinstance(aliases, list) or any(not isinstance(value, str) for value in aliases):
        raise ValueError("Invalid OSV vulnerability aliases")
    if record.get("withdrawn"):
        return
    affected = record.get("affected")
    if not isinstance(affected, list) or not affected:
        raise ValueError("Missing OSV affected package information")
    for entry in affected:
        identity = entry.get("package") if isinstance(entry, dict) else None
        if not isinstance(identity, dict) or any(not isinstance(identity.get(field), str) or not identity[field] for field in ("name", "ecosystem")):
            raise ValueError("Invalid OSV affected package identity")
        versions = entry.get("versions", [])
        ranges = entry.get("ranges", [])
        if not isinstance(versions, list) or any(not isinstance(value, str) for value in versions) or not isinstance(ranges, list):
            raise ValueError("Invalid OSV affected versions")
        for value in ranges:
            if not isinstance(value, dict) or value.get("type") not in {"ECOSYSTEM", "SEMVER", "GIT"} or not isinstance(value.get("events"), list):
                raise ValueError("Invalid OSV version range")
            for event in value["events"]:
                if not isinstance(event, dict) or len(event) != 1 or not set(event).issubset({"introduced", "fixed", "last_affected", "limit"}) or any(not isinstance(item, str) for item in event.values()):
                    raise ValueError("Invalid OSV version range event")
    if not _matching_affected(record, package):
        raise ValueError("OSV response does not match requested package")


def _ranges(affected: tuple[dict, ...]) -> tuple[CveVersionRange, ...]:
    result = []
    for item in affected:
        start = len(result)
        for value in item.get("ranges", ()):
            if not isinstance(value, dict):
                continue
            kind = str(value.get("type", "ECOSYSTEM"))
            introduced = None
            for event in value.get("events", ()):
                if not isinstance(event, dict):
                    continue
                if "introduced" in event:
                    introduced = str(event["introduced"])
                    continue
                if introduced is None:
                    continue
                prefix = "" if introduced == "0" else f">= {introduced}, "
                if "fixed" in event:
                    fixed = str(event["fixed"])
                    result.append(CveVersionRange(f"{prefix}< {fixed}", fixed, kind))
                    introduced = None
                elif "last_affected" in event:
                    result.append(CveVersionRange(f"{prefix}<= {event['last_affected']}", None, kind))
                    introduced = None
                elif "limit" in event:
                    result.append(CveVersionRange(f"{prefix}< {event['limit']} (범위 상한)", None, kind))
                    introduced = None
            if introduced is not None:
                result.append(CveVersionRange("모든 버전" if introduced == "0" else f">= {introduced}", None, kind))
        if len(result) == start:
            versions = tuple(str(version) for version in item.get("versions", ()) if isinstance(version, str))
            if versions:
                result.append(CveVersionRange(", ".join(versions)))
    return tuple(dict.fromkeys(result))


def cvss_details(record: dict, affected: tuple[dict, ...] = ()) -> tuple[str, float | None, str | None, str | None]:
    scores = []
    values = [*(record.get("severity") or [])]
    for entry in affected:
        values.extend(entry.get("severity") or [])
    for value in values:
        if not isinstance(value, dict) or not isinstance(value.get("score"), str):
            continue
        vector = value["score"]
        try:
            if vector.startswith("CVSS:4."):
                score, version = float(CVSS4(vector).scores()[0]), "4.0"
            elif vector.startswith("CVSS:3."):
                score, version = float(CVSS3(vector).scores()[0]), vector.split("/")[0].split(":")[1]
            elif value.get("type") == "CVSS_V2":
                score, version = float(CVSS2(vector).scores()[0]), "2.0"
            else:
                continue
        except Exception:
            continue
        if 0 <= score <= 10:
            scores.append((score, version))
    if scores:
        score, version = max(scores, key=lambda entry: (entry[1], entry[0]))
        severity = "critical" if score >= 9 and version != "2.0" else "high" if score >= 7 else "medium" if score >= 4 else "low" if score > 0 else "unknown"
        return severity, score, version, "OSV CVSS"
    database = record.get("database_specific") or {}
    severity = str(database.get("severity", "")).lower() if isinstance(database, dict) else ""
    severity = "medium" if severity == "moderate" else severity
    if severity not in SEVERITY_ORDER:
        for entry in affected:
            details = entry.get("ecosystem_specific") or {}
            candidate = str(details.get("severity", "")).lower() if isinstance(details, dict) else ""
            candidate = "medium" if candidate == "moderate" else candidate
            if candidate in SEVERITY_ORDER:
                severity = candidate
                break
    return (severity if severity in SEVERITY_ORDER else "unknown"), None, None, "OSV advisory"


def merge_findings(findings: tuple[CveFinding, ...]) -> tuple[CveFinding, ...]:
    result: dict[str, CveFinding] = {}
    for item in findings:
        existing = result.get(item.cve_id)
        if existing is None:
            result[item.cve_id] = item
            continue
        chosen = max((existing, item), key=lambda value: (SEVERITY_ORDER[value.severity], value.cvss_score or 0))
        result[item.cve_id] = replace(
            chosen,
            affected_versions=tuple(dict.fromkeys((*existing.affected_versions, *item.affected_versions))),
            fixed_versions=tuple(dict.fromkeys((*existing.fixed_versions, *item.fixed_versions))),
            ranges=tuple(dict.fromkeys((*existing.ranges, *item.ranges))),
            references=tuple(dict.fromkeys((*existing.references, *item.references))),
            source_ids=tuple(dict.fromkeys((*existing.source_ids, *item.source_ids))),
            published_at=min(filter(None, (existing.published_at, item.published_at)), default=None),
            modified_at=max(filter(None, (existing.modified_at, item.modified_at)), default=None),
        )
    return tuple(result.values())


def parse_osv_records(records: tuple[dict, ...], package: CveInventoryPackage) -> tuple[CveFinding, ...]:
    findings = []
    for record in records:
        if record.get("withdrawn"):
            continue
        identifiers = cve_identifiers(record)
        affected = _matching_affected(record, package)
        if not identifiers or not affected:
            continue
        ranges = _ranges(affected)
        severity, score, version, basis = cvss_details(record, affected)
        references = tuple(dict.fromkeys(
            url for ref in record.get("references", ()) if isinstance(ref, dict)
            if (url := safe_reference(ref.get("url"))) is not None
        ))
        source_id = str(record.get("id", ""))
        if source_id:
            references = tuple(dict.fromkeys((*references, f"https://osv.dev/vulnerability/{source_id}")))
        for identifier in identifiers:
            findings.append(CveFinding(
                cve_id=identifier, title=str(record.get("summary") or identifier),
                affected_versions=tuple(dict.fromkeys(value.affected for value in ranges if value.type != "GIT")),
                fixed_versions=tuple(dict.fromkeys(value.fixed for value in ranges if value.fixed and value.type != "GIT")),
                ranges=ranges, severity=severity, cvss_score=score, cvss_version=version,
                references=references, source_ids=(source_id,) if source_id else (),
                published_at=record.get("published"), modified_at=record.get("modified"), severity_source=basis,
            ))
    return merge_findings(tuple(findings))


class OsvInventorySource(CvePackageSourcePort):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=60, follow_redirects=False)
        self._owned = client is None

    async def _query(self, package: CveInventoryPackage, version: str | None = None) -> tuple[dict, ...]:
        payload = {"package": {"name": package.query_name or package.name, "ecosystem": package.query_ecosystem or package.ecosystem}}
        if version is not None:
            payload["version"] = version
        records = []
        tokens = set()
        while True:
            for attempt in range(3):
                try:
                    response = await self._client.post("https://api.osv.dev/v1/query", json=payload)
                    if response.status_code == 429 or response.status_code >= 500:
                        response.raise_for_status()
                    response.raise_for_status()
                    break
                except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as error:
                    retryable = not isinstance(error, httpx.HTTPStatusError) or error.response.status_code == 429 or error.response.status_code >= 500
                    if attempt == 2 or not retryable:
                        raise
                    await asyncio.sleep(2 ** attempt)
            document = response.json()
            if not isinstance(document, dict) or "error" in document or ("vulns" in document and not isinstance(document["vulns"], list)):
                raise ValueError("Invalid OSV query response")
            entries = document.get("vulns", [])
            for entry in entries:
                validate_osv_record(entry, package)
            records.extend(entries)
            token = document.get("next_page_token")
            if token is not None and not isinstance(token, str):
                raise ValueError("Invalid OSV pagination token")
            if not token:
                return tuple(records)
            if not isinstance(token, str) or token in tokens:
                raise ValueError("OSV pagination did not advance")
            tokens.add(token)
            payload["page_token"] = token

    async def fetch(self, package: CveInventoryPackage) -> tuple[CveFinding, ...]:
        records = await self._query(package)
        findings = parse_osv_records(records, package)
        if not findings or not package.versions or package.version_confidence != "confirmed":
            return findings
        if (package.query_ecosystem or package.ecosystem) == "npm" and any(not NPM_EXACT_VERSION.fullmatch(version) for version in package.versions):
            return findings
        affected: dict[str, set[str]] = {}
        try:
            for version in package.versions:
                for record in await self._query(package, version):
                    if record.get("withdrawn"):
                        continue
                    for identifier in (*cve_identifiers(record), str(record.get("id", ""))):
                        affected.setdefault(identifier, set()).add(version)
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return findings
        result = []
        for item in findings:
            matches = set().union(*(affected.get(identifier, set()) for identifier in (item.cve_id, *item.source_ids)))
            result.append(replace(
                item, inventory_impact="affected" if matches else "not_affected",
                affected_inventory_versions=tuple(version for version in package.versions if version in matches),
            ))
        return tuple(result)

    async def begin_refresh(self) -> frozenset[str] | None:
        try:
            response = await self._client.get("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
            response.raise_for_status()
            document = response.json()
            if not isinstance(document, dict):
                return None
            values = document.get("vulnerabilities")
            if not isinstance(values, list):
                return None
            count = document.get("count")
            if count is not None and (type(count) is not int or count != len(values)):
                return None
            if any(not isinstance(item, dict) or not isinstance(item.get("cveID"), str) or not CVE_PATTERN.fullmatch(item["cveID"]) for item in values):
                return None
            return frozenset(
                item["cveID"].upper() for item in values
            )
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            return None

    async def aclose(self) -> None:
        if self._owned:
            await self._client.aclose()


class InventoryCveSources(CvePackageSourcePort):
    def __init__(self, sources: dict[str, CvePackageSourcePort]) -> None:
        self._sources = sources

    async def configure(self, packages: tuple[CveInventoryPackage, ...]) -> None:
        for name, source in self._sources.items():
            await source.configure(tuple(package for package in packages if package.source == name))

    async def fetch(self, package: CveInventoryPackage) -> tuple[CveFinding, ...]:
        if package.source not in self._sources:
            raise ValueError("Unsupported vulnerability source")
        return await self._sources[package.source].fetch(package)

    async def begin_refresh(self) -> frozenset[str] | None:
        results = await asyncio.gather(*(source.begin_refresh() for source in self._sources.values()), return_exceptions=True)
        values = [result for result in results if isinstance(result, frozenset)]
        return frozenset().union(*values) if values else None

    async def aclose(self) -> None:
        async with AsyncExitStack() as stack:
            for source in self._sources.values():
                stack.push_async_callback(source.aclose)
