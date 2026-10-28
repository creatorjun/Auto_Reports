# backend/src/infrastructure/external/oracle_cve_source.py
import asyncio
import bz2
import io
import re
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from urllib.parse import urlsplit

import httpx
from defusedxml import ElementTree

from src.application.ports.cve_inventory_port import CvePackageSourcePort
from src.domain.entities.cve_inventory import CveFinding, CveInventoryPackage, CveVersionRange


ORACLE_OL8_OVAL_URL = "https://linux.oracle.com/security/oval/com.oracle.elsa-ol8.xml.bz2"
MAX_COMPRESSED_BYTES = 24 * 1024 * 1024
MAX_XML_BYTES = 256 * 1024 * 1024
OVAL = "http://oval.mitre.org/XMLSchema/oval-definitions-5"
LINUX = OVAL + "#linux"
CVE_ID = re.compile(r"CVE-\d{4}-\d{4,}\Z")
RPM_NAME = re.compile(r"[A-Za-z0-9_+][A-Za-z0-9_.+-]*\Z")
SEVERITIES = {"critical": "critical", "important": "high", "high": "high", "moderate": "medium", "medium": "medium", "low": "low"}
SEVERITY_ORDER = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class _BoundedReader:
    def __init__(self, stream):
        self.stream = stream
        self.total = 0

    def read(self, size=-1):
        remaining = MAX_XML_BYTES - self.total
        content = self.stream.read(min(size if size >= 0 else remaining + 1, remaining + 1))
        self.total += len(content)
        if self.total > MAX_XML_BYTES:
            raise ValueError("Oracle OVAL XML exceeds size limit")
        return content


def _value(node, name):
    child = node.find(f"{{{OVAL}}}{name}")
    return " ".join(child.itertext()).strip() if child is not None else ""


def _date(value):
    if not isinstance(value, str):
        return None
    for pattern in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass
    return None


def _url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return None
    parsed = urlsplit(value)
    if parsed.scheme == "https" and parsed.hostname in {"linux.oracle.com", "nvd.nist.gov"} and not parsed.username and not parsed.password:
        return value
    return None


def _leaves(node, inherited=(), negated=False):
    negated = negated or node.get("negate", "false") == "true"
    if negated:
        return []
    local = tuple(child.get("comment", "") for child in node if child.tag == f"{{{OVAL}}}criterion" and child.get("negate", "false") != "true") if node.get("operator", "AND") == "AND" else ()
    context = tuple(dict.fromkeys(inherited + local))
    output = []
    for child in node:
        if child.tag == f"{{{OVAL}}}criterion" and child.get("negate", "false") != "true":
            output.append((child.get("test_ref"), tuple(c for c in context if c and c != child.get("comment"))))
        elif child.tag == f"{{{OVAL}}}criteria":
            output.extend(_leaves(child, context, negated))
    return output


def _definition(node):
    metadata = node.find(f"{{{OVAL}}}metadata")
    criteria = node.find(f"{{{OVAL}}}criteria")
    if metadata is None or criteria is None:
        raise ValueError("Incomplete Oracle OVAL definition")
    platforms = metadata.findall(f"{{{OVAL}}}affected/{{{OVAL}}}platform")
    if not any((platform.text or "").strip() == "Oracle Linux 8" for platform in platforms):
        return None
    advisory = metadata.find(f"{{{OVAL}}}advisory")
    if advisory is None:
        return None
    references = tuple(dict.fromkeys(url for ref in metadata.findall(f"{{{OVAL}}}reference") if (url := _url(ref.get("ref_url")))))
    advisory_ids = tuple(ref.get("ref_id") for ref in metadata.findall(f"{{{OVAL}}}reference") if ref.get("source", "").lower() == "elsa" and ref.get("ref_id"))
    severity = SEVERITIES.get(_value(advisory, "severity").lower(), "unknown")
    issued = advisory.find(f"{{{OVAL}}}issued")
    updated = advisory.find(f"{{{OVAL}}}updated")
    issued_date = _date(issued.get("date")) if issued is not None else None
    modified_date = _date(updated.get("date")) if updated is not None else issued_date
    cves = {}
    for cve in advisory.findall(f"{{{OVAL}}}cve"):
        identifier = (cve.text or "").strip()
        if not CVE_ID.fullmatch(identifier):
            continue
        score, version = None, None
        metric = cve.get("cvss3") or cve.get("cvss2") or cve.get("cvss")
        if metric:
            try:
                candidate = float(metric.split("/")[0])
                if 0 <= candidate <= 10:
                    score = candidate
                    version = "3.1" if "CVSS:3.1" in metric else "3.0" if cve.get("cvss3") else "2.0"
            except ValueError:
                pass
        risk = severity
        if score is not None and version != "2.0":
            risk = "critical" if score >= 9 else "high" if score >= 7 else "medium" if score >= 4 else "low" if score > 0 else "unknown"
        cves[identifier] = (risk, score, version, _date(cve.get("public")) or issued_date)
    for ref in metadata.findall(f"{{{OVAL}}}reference"):
        identifier = ref.get("ref_id", "")
        if ref.get("source", "").upper() == "CVE" and CVE_ID.fullmatch(identifier):
            cves.setdefault(identifier, (severity, None, None, issued_date))
    return dict(title=" ".join(_value(metadata, "title").split())[:1000], references=references, source_ids=advisory_ids or (node.get("id", "oracle-oval"),), cves=cves, modified_at=modified_date, leaves=_leaves(criteria))


def _merge(findings):
    output = {}
    for finding in findings:
        previous = output.get(finding.cve_id)
        if previous is None:
            output[finding.cve_id] = finding
            continue
        chosen = max((previous, finding), key=lambda item: (SEVERITY_ORDER[item.severity], item.cvss_score or -1))
        published = [value for value in (previous.published_at, finding.published_at) if value]
        modified = [value for value in (previous.modified_at, finding.modified_at) if value]
        output[finding.cve_id] = replace(chosen,
            affected_versions=tuple(dict.fromkeys(previous.affected_versions + finding.affected_versions)),
            fixed_versions=tuple(dict.fromkeys(previous.fixed_versions + finding.fixed_versions)),
            ranges=tuple(dict.fromkeys(previous.ranges + finding.ranges)),
            references=tuple(dict.fromkeys(previous.references + finding.references)),
            source_ids=tuple(dict.fromkeys(previous.source_ids + finding.source_ids)),
            published_at=min(published) if published else None,
            modified_at=max(modified) if modified else None,
        )
    return tuple(sorted(output.values(), key=lambda row: row.cve_id))


def parse_oracle_oval(payload: bytes, package_names: frozenset[str] | None = None) -> dict[str, tuple[CveFinding, ...]]:
    compressed = payload.startswith(b"BZh")
    if len(payload) > (MAX_COMPRESSED_BYTES if compressed else MAX_XML_BYTES):
        raise ValueError("Oracle OVAL payload exceeds size limit")
    source = bz2.BZ2File(io.BytesIO(payload)) if compressed else io.BytesIO(payload)
    definitions, tests, objects, states = [], {}, {}, {}
    root_seen = False
    with source:
        for event, node in ElementTree.iterparse(_BoundedReader(source), events=("start", "end"), forbid_dtd=True, forbid_entities=True, forbid_external=True):
            if not root_seen:
                if node.tag != f"{{{OVAL}}}oval_definitions":
                    raise ValueError("Invalid Oracle OVAL root")
                root_seen = True
            if event != "end":
                continue
            local = node.tag.rsplit("}", 1)[-1]
            if node.tag == f"{{{OVAL}}}definition":
                row = _definition(node)
                if row is not None:
                    definitions.append(row)
                node.clear()
            elif local.endswith("_test"):
                object_refs = tuple(child.get("object_ref") for child in node if child.tag.rsplit("}", 1)[-1] == "object")
                state_refs = tuple(child.get("state_ref") for child in node if child.tag.rsplit("}", 1)[-1] == "state")
                tests[node.get("id")] = (node.tag == f"{{{LINUX}}}rpminfo_test", object_refs, state_refs)
                node.clear()
            elif local.endswith("_object"):
                name = node.find(f"{{{LINUX}}}name")
                objects[node.get("id")] = (name.text or "").strip() if name is not None and name.get("operation", "equals") == "equals" else None
                node.clear()
            elif local.endswith("_state"):
                evr = node.find(f"{{{LINUX}}}evr")
                states[node.get("id")] = ((evr.text or "").strip(), evr.get("operation", "equals")) if evr is not None else None
                node.clear()
    if not definitions or not tests or not objects or not states:
        raise ValueError("Incomplete Oracle OVAL feed")
    by_package = defaultdict(list)
    operators = {"less than": "<", "less than or equal": "<=", "equals": "=", "greater than": ">", "greater than or equal": ">="}
    for definition in definitions:
        ranges = defaultdict(set)
        for test_id, context in definition["leaves"]:
            if test_id not in tests:
                raise ValueError("Unresolved Oracle OVAL test")
            is_rpm, object_refs, state_refs = tests[test_id]
            if not is_rpm:
                continue
            for object_id in object_refs:
                if object_id not in objects:
                    raise ValueError("Unresolved Oracle OVAL object")
                name = objects[object_id]
                if not name or not RPM_NAME.fullmatch(name):
                    continue
                if package_names is not None and name not in package_names:
                    continue
                for state_id in state_refs:
                    if state_id not in states:
                        raise ValueError("Unresolved Oracle OVAL state")
                    state = states[state_id]
                    if state is None:
                        continue
                    evr, operation = state
                    if not evr or operation not in operators:
                        continue
                    guards = "; ".join(dict.fromkeys(("Oracle Linux 8", *definition["source_ids"], *context)))
                    affected = f"{operators[operation]} {evr} ({guards})"
                    ranges[name].add(CveVersionRange(affected=affected, fixed=evr if operation == "less than" else None, type="RPM_EVR"))
        for name, package_ranges in ranges.items():
            ordered = tuple(sorted(package_ranges, key=lambda row: (row.affected, row.fixed or "")))
            for cve_id, (severity, score, version, published) in definition["cves"].items():
                by_package[name].append(CveFinding(
                    cve_id=cve_id, title=definition["title"],
                    affected_versions=tuple(row.affected for row in ordered),
                    fixed_versions=tuple(dict.fromkeys(row.fixed for row in ordered if row.fixed)), ranges=ordered,
                    severity=severity, cvss_score=score, cvss_version=version,
                    references=definition["references"], source_ids=definition["source_ids"],
                    published_at=published, modified_at=definition["modified_at"],
                    inventory_impact="unknown", severity_source="oracle_cvss" if score is not None else "oracle_advisory",
                ))
    return {name: _merge(rows) for name, rows in by_package.items()}


class OracleCveSource(CvePackageSourcePort):
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15), follow_redirects=False)
        self._lock = asyncio.Lock()
        self._index = None
        self._failure = None
        self._package_names = None

    async def configure(self, packages: tuple[CveInventoryPackage, ...]) -> None:
        names = frozenset(package.query_name for package in packages if package.source == "oracle" and package.query_name)
        async with self._lock:
            if names != self._package_names:
                self._package_names = names
                self._index = None
                self._failure = None

    async def begin_refresh(self) -> None:
        async with self._lock:
            self._index = None
            self._failure = None

    async def _read(self):
        payload = bytearray()
        async with self._client.stream("GET", ORACLE_OL8_OVAL_URL) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                payload.extend(chunk)
                if len(payload) > MAX_COMPRESSED_BYTES:
                    raise ValueError("Oracle OVAL download exceeds size limit")
        return await asyncio.to_thread(parse_oracle_oval, bytes(payload), self._package_names)

    async def fetch(self, package: CveInventoryPackage) -> tuple[CveFinding, ...]:
        if package.source != "oracle" or package.distribution_id != "ol" or package.distribution_version != "8" or not package.query_name:
            raise ValueError("Unsupported Oracle inventory package")
        async with self._lock:
            if self._failure is not None:
                raise RuntimeError("Oracle OVAL refresh failed") from self._failure
            if self._index is None:
                try:
                    self._index = await self._read()
                except Exception as error:
                    self._failure = error
                    raise
            return self._index.get(package.query_name, ())

    async def aclose(self) -> None:
        self._index = None
        if self._owns_client:
            await self._client.aclose()
