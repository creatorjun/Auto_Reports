# backend/src/infrastructure/external/security_cve_remediation.py
import re
from collections import deque
from dataclasses import replace

from src.domain.entities.security_news import SecurityCveRemediation


VERSION = r"v?\d+(?:\.[A-Za-z0-9]+)+(?:[-+][A-Za-z0-9.]+)?"
PRODUCT = r"[A-Za-z0-9@][A-Za-z0-9@_ .:/()+-]{0,99}?"
RANGE = re.compile(
    rf"^(?P<product>{PRODUCT})\s+(?:versions?\s+)?(?P<bound>before|prior to|through|up to and including)\s+(?:version\s+)?(?P<version>{VERSION})(?=[\s,.;]|$)",
    re.IGNORECASE,
)
FIX = re.compile(
    rf"(?:^|[.!?]\s+)(?:This (?:issue|vulnerability)|The (?:issue|vulnerability))\s+(?:is|was|has been)\s+(?:fixed|patched|resolved)\s+in\s+(?:version\s+)?(?P<version>{VERSION})\s*[.!]?(?=$|\s+[A-Z])",
)


def _cpe_parts(value: object) -> list[str]:
    if not isinstance(value, str) or len(value) > 4096:
        return []
    parts, current, escaped = [], [], False
    for character in value:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    parts.append("".join(current))
    return parts if not escaped and len(parts) == 13 and parts[:2] == ["cpe", "2.3"] else []


def _version(value: object) -> str | None:
    return value if isinstance(value, str) and 0 < len(value) <= 100 and value not in {"*", "-"} and not any(ord(char) < 32 for char in value) else None


def _matches(configurations: object):
    pending = deque(configurations) if isinstance(configurations, list) else deque()
    visited = 0
    while pending and visited < 10000:
        node = pending.popleft()
        visited += 1
        if not isinstance(node, dict) or node.get("negate") is True:
            continue
        matches = node.get("cpeMatch")
        if isinstance(matches, list):
            yield from (match for match in matches if isinstance(match, dict) and match.get("vulnerable") is True)
        for key in ("nodes", "children"):
            if isinstance(node.get(key), list):
                pending.extend(node[key])


def _affected(match: dict, parts: list[str]) -> str:
    bounds = []
    for key, operator in (("versionStartIncluding", ">="), ("versionStartExcluding", ">"), ("versionEndIncluding", "<="), ("versionEndExcluding", "<")):
        version = _version(match.get(key))
        if version:
            bounds.append(f"{operator} {version}")
    version = _version(parts[5])
    if version:
        update = _version(parts[6])
        bounds.insert(0, f"{version} ({update})" if update else version)
    return ", ".join(bounds) or "버전 확인 필요"


def _description_range(description: str, product: str | None) -> tuple[str, str] | None:
    match = RANGE.match(description)
    if match is None:
        return None
    name = match["product"].strip()
    if re.search(r"\b(?:and|or|is|are|in|vulnerability|issue|affects|allows|the|this)\b", name, re.IGNORECASE):
        return None
    if product and re.sub(r"[\W_]", "", name).lower() != re.sub(r"[\W_]", "", product).lower():
        return None
    operator = "<" if match["bound"].lower() in {"before", "prior to"} else "<="
    return name, f"{operator} {match['version']}"


def _same_product(name: str, entry: SecurityCveRemediation) -> bool:
    normalized = lambda value: re.sub(r"[\W_]", "", value).lower()
    return normalized(name) in {normalized(entry.product), normalized(f"{entry.vendor or ''} {entry.product}")}


def cve_remediations(configurations: object, description: str, reference_url: str, *, product: str | None = None, vendor: str | None = None) -> tuple[SecurityCveRemediation, ...]:
    entries = []
    for match in _matches(configurations):
        parts = _cpe_parts(match.get("criteria"))
        if not parts or parts[2] not in {"a", "o", "h"} or not _version(parts[4]):
            continue
        entries.append(SecurityCveRemediation(
            product=parts[4].replace("_", " "), vendor=parts[3].replace("_", " ") if _version(parts[3]) else None,
            affected_versions=_affected(match, parts), reference_url=reference_url,
        ))
    entries = list(dict.fromkeys(entries))
    described = _description_range(description, product)
    if not entries:
        if described:
            entries.append(SecurityCveRemediation(product=product or described[0], vendor=vendor, affected_versions=described[1], reference_url=reference_url))
        elif product:
            entries.append(SecurityCveRemediation(product=product, vendor=vendor, affected_versions="버전 확인 필요", reference_url=reference_url))
    fixes = {match["version"] for match in FIX.finditer(description)}
    named_range = _description_range(description, None)
    ranges = re.findall(rf"\b(?:before|prior to|through|up to and including)\s+(?:version\s+)?{VERSION}", description, re.IGNORECASE)
    if len(entries) == 1 and len(fixes) == 1 and len(ranges) == 1 and named_range and _same_product(named_range[0], entries[0]):
        fixed = next(iter(fixes))
        if named_range[1] == f"< {fixed}":
            entries = [replace(entries[0], fixed_version=fixed)]
    return tuple(entries)
