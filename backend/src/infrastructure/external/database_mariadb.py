# backend/src/infrastructure/external/database_mariadb.py
import asyncio
import json
import re
from datetime import date, datetime, timezone

from src.domain.entities.database_cve import DatabaseAdvisory, DatabaseBuild, DatabaseFeed, DatabaseFeedData, DatabaseTarget
from src.infrastructure.external.database_version import score_severity, series_for
from src.infrastructure.external.kernel_feed_http import fetch_bytes


_DOC = "https://mariadb.com/docs/server/security/cve/community-server"
_ISSUES = DatabaseFeed("mariadb-community-cves", "MariaDB Community Server 보안 권고", _DOC)
_RELEASES = DatabaseFeed("mariadb-releases", "MariaDB 공식 릴리스", "https://downloads.mariadb.org/rest-api/mariadb/", releases_only=True)
MARIADB_TARGET = DatabaseTarget("mariadb", "MariaDB", (_ISSUES, _RELEASES),
    "MariaDB Community Server가 CVE별로 공개한 같은 계열의 수정 버전보다 이전인 빌드를 표시합니다. 최초 영향 버전과 배포판 백포트 적용 여부는 이 표에서 확인할 수 없습니다.")
_CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,}")
_FIX = re.compile(r"\[([0-9]+\.[0-9]+(?:\.[0-9]+[a-z]?)?)\]\(([^)]*)\)(?:\s*\(([0-9]{4}-[0-9]{2}-[0-9]{2})\))?")


def parse_mariadb(payload: bytes) -> DatabaseFeedData:
    text = payload.decode("utf-8")
    if "# Security Vulnerabilities (CVE) Fixed in MariaDB Community Server" not in text:
        raise ValueError("Unexpected MariaDB security document")
    advisories, builds = [], {}
    for line in text.splitlines():
        if not line.startswith("|") or "CVE-" not in line:
            continue
        fields = [col.strip() for col in line.strip().strip("|").split("|")]
        if len(fields) != 4 or len(cves := set(_CVE.findall(fields[0]))) != 1:
            raise ValueError("Unexpected MariaDB advisory row")
        cve = next(iter(cves))
        issued = date.fromisoformat(fields[1]).isoformat()
        score = None
        if re.fullmatch(r"(?:10(?:\.0)?|[0-9](?:\.[0-9])?)", fields[2]):
            score = float(fields[2])
            severity = score_severity(score)
        elif fields[2].startswith("N/A"):
            rating = re.fullmatch(r"N/A(?: \((Critical|High|Medium|Low)\))?", fields[2])
            severity = rating[1].lower() if rating and rating[1] else "unknown"
        else:
            raise ValueError("Unrecognized MariaDB CVSS severity")
        rows = []
        for version, href, released in _FIX.findall(fields[3]):
            if not href.startswith("/docs/release-notes/community-server/"):
                continue
            series = series_for("mariadb", version)
            fixed = version if version.count(".") == 2 else None
            if fixed:
                builds[version] = DatabaseBuild(version, series, issued_at=released or None)
            rows.append(DatabaseAdvisory(cve, severity, "MariaDB Community Server", _DOC, issued, series,
                                         fixed_version=fixed, cvss_score=score))
        if not rows and "/docs/release-notes/community-server/" in fields[3]:
            raise ValueError("Unrecognized MariaDB Server release in advisory")
        advisories.extend(rows)
    if not advisories or not builds:
        raise ValueError("Empty MariaDB security table")
    return DatabaseFeedData(tuple(dict.fromkeys(advisories)), tuple(builds.values()))


async def _releases(client):
    index = json.loads(await fetch_bytes(client, _RELEASES.url, 2_000_000))
    targets = {}
    for row in index["major_releases"]:
        series = row["release_id"]
        if row["release_status"] != "Stable":
            continue
        if not re.fullmatch(r"[0-9]+\.[0-9]+", series):
            raise ValueError("Unrecognized MariaDB release series")
        eol = row.get("release_eol_date")
        targets[series] = date.fromisoformat(eol) >= datetime.now(timezone.utc).date() if eol else None
    builds = []
    for offset in range(0, len(targets), 3):
        batch = tuple(targets)[offset:offset + 3]
        payloads = await asyncio.gather(*(fetch_bytes(client, _RELEASES.url + series + "/", 12_000_000) for series in batch))
        for series, blob in zip(batch, payloads):
            releases = json.loads(blob)["releases"]
            for version, row in releases.items():
                if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+[a-z]?", version) or series_for("mariadb", version) != series or row["release_id"] != version:
                    raise ValueError("Unexpected MariaDB release version")
                builds.append(DatabaseBuild(version, series, issued_at=row.get("date_of_release") or None, supported=targets[series]))
    if not builds:
        raise ValueError("Empty MariaDB release catalog")
    return DatabaseFeedData((), tuple(builds))


async def fetch_mariadb(client, target, feed):
    if target != MARIADB_TARGET or feed not in target.feeds:
        raise ValueError("지원하지 않는 MariaDB 출처입니다.")
    if feed == _RELEASES:
        return await _releases(client)
    return parse_mariadb(await fetch_bytes(client, _DOC + ".md", 3_000_000))
