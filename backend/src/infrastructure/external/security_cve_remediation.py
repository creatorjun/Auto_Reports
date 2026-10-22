# backend/src/infrastructure/external/security_cve_remediation.py
import re
from collections import deque
from dataclasses import dataclass, replace

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
SEPARATOR = r"(?:\s*,\s*(?:(?:and|or)\s+)?|\s+(?:and|or)\s+)"
AFFECTED_VERSION = rf"(?:versions?\s+)?(?:(?:from\s+)?{VERSION}\s+(?:through|to|up to and including|before|prior to)\s+{VERSION}|{VERSION})"
AFFECTED_LIST = re.compile(
    rf"\b(?:This|The)\s+(?:issue|vulnerability)\s+affects\s+(?P<product>{PRODUCT})\s*:\s*(?P<versions>{AFFECTED_VERSION}(?:{SEPARATOR}{AFFECTED_VERSION})*)(?=\s*\.(?:\s|$)|\s*$)",
    re.IGNORECASE,
)
FIX_LIST = re.compile(
    rf"\b(?:Users\s+(?:are\s+(?:recommended|advised)\s+to|should)\s+upgrade\s+to\s+versions?\s+(?P<recommended>{VERSION}(?:{SEPARATOR}{VERSION})*)\s*,\s*which\s+fix(?:es)?\s+(?:the|this)\s+(?:issue|vulnerability)|(?:This|The)\s+(?:issue|vulnerability)\s+(?:is|was|has been)\s+(?:fixed|patched|resolved)\s+in\s+versions?\s+(?P<fixed>{VERSION}(?:{SEPARATOR}{VERSION})*))(?=\s*\.(?:\s|$)|\s*$)",
    re.IGNORECASE,
)
AFFECTED_RANGE = re.compile(
    rf"(?:versions?\s+)?(?:from\s+)?(?P<start>{VERSION})\s+(?P<bound>through|to|up to and including|before|prior to)\s+(?P<end>{VERSION})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _AffectedBranch:
    affected_versions: str
    branch: tuple[int, int]
    upper: tuple[int, ...]
    upper_inclusive: bool


def _numeric_version(value: str) -> tuple[int, ...] | None:
    if not re.fullmatch(r"[vV]?\d+(?:\.\d+){2,}", value):
        return None
    return tuple(int(part) for part in value.lstrip("vV").split("."))


def _version_order(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    length = max(len(left), len(right))
    left, right = left + (0,) * (length - len(left)), right + (0,) * (length - len(right))
    return (left > right) - (left < right)


def _affected_branch(value: str) -> _AffectedBranch | None:
    ranged = AFFECTED_RANGE.fullmatch(value.strip())
    if ranged:
        upper = _numeric_version(ranged["end"])
        lower_branch = re.match(r"[vV]?(\d+)\.(\d+)\.", ranged["start"])
        lower = _numeric_version(ranged["start"])
        if upper is None or lower_branch is None or tuple(map(int, lower_branch.groups())) != upper[:2] or (lower and _version_order(lower, upper) > 0):
            return None
        inclusive = ranged["bound"].lower() not in {"before", "prior to"}
        return _AffectedBranch(f">= {ranged['start']}, {'<=' if inclusive else '<'} {ranged['end']}", upper[:2], upper, inclusive)
    version = re.sub(r"^versions?\s+", "", value.strip(), flags=re.IGNORECASE)
    upper = _numeric_version(version)
    return _AffectedBranch(version, upper[:2], upper, True) if upper else None


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


def _entry_branch(entry: SecurityCveRemediation) -> _AffectedBranch | None:
    numeric = _numeric_version(entry.affected_versions)
    if numeric:
        return _AffectedBranch(entry.affected_versions, numeric[:2], numeric, True)
    match = re.fullmatch(rf">=?\s+({VERSION}),\s+(<|<=)\s+({VERSION})", entry.affected_versions)
    if match:
        upper = _numeric_version(match[3])
        lower_branch = re.match(r"[vV]?(\d+)\.(\d+)\.", match[1])
        lower = _numeric_version(match[1])
        if upper and lower_branch and tuple(map(int, lower_branch.groups())) == upper[:2] and (not lower or _version_order(lower, upper) <= 0):
            return _AffectedBranch(entry.affected_versions, upper[:2], upper, match[2] == "<=")
    return None


def _before_fix(affected: _AffectedBranch, fixed: str) -> bool:
    version = _numeric_version(fixed)
    if version is None:
        return False
    comparison = _version_order(affected.upper, version)
    return comparison < 0 or (comparison == 0 and not affected.upper_inclusive)


def _branch_fixes(description: str, affected_match: re.Match, affected: list[_AffectedBranch]) -> dict[tuple[int, int], str]:
    matches = list(FIX_LIST.finditer(description))
    if len(matches) != 1:
        return {}
    fix_match = matches[0]
    remaining = description
    for match in sorted((affected_match, fix_match), key=lambda value: value.start(), reverse=True):
        remaining = remaining[:match.start()] + " " + remaining[match.end():]
    if re.search(VERSION, remaining) or re.search(r"\b(?:fixed|patched|resolved|affected|affects)\b", remaining, re.IGNORECASE):
        return {}
    values = re.split(SEPARATOR, fix_match["recommended"] or fix_match["fixed"], flags=re.IGNORECASE)
    fixes = {}
    for value in values:
        version = _numeric_version(value)
        if version is None or version[:2] in fixes:
            return {}
        fixes[version[:2]] = value
    if len({value.branch for value in affected}) != len(affected) or set(fixes) != {value.branch for value in affected}:
        return {}
    if not all(_before_fix(value, fixes[value.branch]) for value in affected):
        return {}
    return fixes


def _branch_remediations(entries: list[SecurityCveRemediation], description: str, reference_url: str, product: str | None, vendor: str | None) -> list[SecurityCveRemediation] | None:
    affected_matches = list(AFFECTED_LIST.finditer(description))
    if len(affected_matches) != 1:
        return None
    affected_match = affected_matches[0]
    name = affected_match["product"].strip()
    if re.search(r"\b(?:and|or|is|are|in|vulnerability|issue|affects|allows|the|this)\b", name, re.IGNORECASE):
        return None
    if product and not _same_product(name, SecurityCveRemediation(product, "", vendor)):
        return None
    affected = []
    for value in re.split(SEPARATOR, affected_match["versions"], flags=re.IGNORECASE):
        branch = _affected_branch(value)
        if branch is None:
            return None
        affected.append(branch)
    fixes = _branch_fixes(description, affected_match, affected)
    matching = [entry for entry in entries if _same_product(name, entry)]
    for entry in matching:
        if entry.affected_versions == "버전 확인 필요":
            continue
        branch = _entry_branch(entry)
        if branch is None:
            fixes = {}
            break
        if branch.branch in fixes and not _before_fix(branch, fixes[branch.branch]):
            fixes.pop(branch.branch)
    output, represented = [], set()
    for entry in entries:
        if entry not in matching:
            output.append(entry)
            continue
        if entry.affected_versions == "버전 확인 필요":
            continue
        branch = _entry_branch(entry)
        output.append(replace(entry, fixed_version=fixes.get(branch.branch) if branch else None))
        if branch:
            represented.add(branch.branch)
    template = matching[0] if matching else SecurityCveRemediation(product or name, "", vendor, reference_url=reference_url)
    for value in affected:
        if value.branch not in represented:
            output.append(replace(template, affected_versions=value.affected_versions, fixed_version=fixes.get(value.branch)))
    return list(dict.fromkeys(output))


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
    branched = _branch_remediations(entries, description, reference_url, product, vendor)
    if branched is not None:
        return tuple(branched)
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
