# backend/src/infrastructure/external/solution_osv_versions.py
import re


_NUM = r"(?:0|[1-9][0-9]*)"
_PRE = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
_SEMVER = re.compile(rf"({_NUM})\.({_NUM})\.({_NUM})(?:-({_PRE}(?:\.{_PRE})*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")
_MAVEN_NUMERIC = re.compile(r"[0-9]+(?:\.[0-9]+)*")


def _semver_key(version: str) -> tuple | None:
    match = _SEMVER.fullmatch(version)
    if not match:
        return None
    major, minor, patch, prerelease = match.groups()
    identifiers = tuple((0, int(v)) if v.isdigit() else (1, v) for v in (prerelease or "").split("."))
    return (int(major), int(minor), int(patch), prerelease is None, identifiers)


def _maven_numeric_key(version: str) -> tuple | None:
    """Only the dotted numeric subset has this ordering; qualified builds require exact evidence."""
    if not _MAVEN_NUMERIC.fullmatch(version):
        return None
    parts = [int(part) for part in version.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def _in_range(version: str, ecosystem: str, affected_range: dict) -> bool | None:
    kind = affected_range.get("type")
    if kind == "SEMVER" or (kind == "ECOSYSTEM" and ecosystem == "npm"):
        order = _semver_key
    elif kind == "ECOSYSTEM" and ecosystem == "Maven":
        order = _maven_numeric_key
    else:
        return None
    current = order(version)
    if current is None:
        return None
    events = []
    limits = []
    for event in affected_range.get("events", ()):
        if not isinstance(event, dict) or len(event) != 1:
            return None
        event_type, boundary = next(iter(event.items()))
        if event_type not in {"introduced", "fixed", "last_affected", "limit"} or not isinstance(boundary, str):
            return None
        if event_type == "limit" and boundary == "*":
            limits.append(True)
            continue
        before_all = event_type == "introduced" and boundary == "0"
        key = () if before_all else order(boundary)
        if key is None:
            return None
        if event_type == "limit":
            limits.append(current < key)
        else:
            events.append((key, event_type))
    if not any(event_type == "introduced" for _, event_type in events):
        return None
    if limits and not any(limits):
        return False
    if len({key for key, _ in events}) != len(events):
        return None
    vulnerable = False
    for key, event_type in sorted(events):
        if key > current:
            break
        if event_type == "last_affected" and key == current:
            continue
        vulnerable = event_type == "introduced"
    return vulnerable


def affected_version(version: str, ecosystem: str, entry: dict) -> bool | None:
    versions = entry.get("versions", [])
    ranges = entry.get("ranges", [])
    if not isinstance(versions, list) or not isinstance(ranges, list):
        return None
    if version in versions:
        return True
    if not ranges:
        return False if versions and all(isinstance(v, str) for v in versions) else None
    statuses = [_in_range(version, ecosystem, r) if isinstance(r, dict) else None for r in ranges]
    if True in statuses:
        return True
    return None if None in statuses else False
