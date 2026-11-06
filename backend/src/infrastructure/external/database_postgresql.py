# backend/src/infrastructure/external/database_postgresql.py
import asyncio
import json
import re
from html.parser import HTMLParser

import httpx

from src.domain.entities.database_cve import DatabaseAdvisory, DatabaseBuild, DatabaseFeed, DatabaseFeedData, DatabaseTarget
from src.infrastructure.external.database_version import score_severity, series_for, validate_version
from src.infrastructure.external.kernel_feed_http import fetch_bytes


_PG = "https://www.postgresql.org"
_SECURITY = DatabaseFeed("postgresql-security", "PostgreSQL 보안 권고", _PG + "/support/security/")
_RELEASES = DatabaseFeed("postgresql-releases", "PostgreSQL 공식 릴리스", _PG + "/docs/release/", releases_only=True)
POSTGRESQL_TARGET = DatabaseTarget("postgresql", "PostgreSQL", (_SECURITY, _RELEASES),
    "PostgreSQL이 공개한 해당 계열의 수정 버전을 기준으로 비교합니다. 서버, 클라이언트, 확장 모듈, 패키징을 구분해 표시합니다.")
_SERIES_HREF = re.compile(r"/support/security/(\d+(?:\.\d+)?)/")
_RELEASE_HREF = re.compile(r"/docs/release/(\d+\.\d+(?:\.\d+)?)/")
_CVE = re.compile(r"\bCVE-[0-9]{4}-[0-9]{4,}\b")


def _series(version: str) -> str:
    validate_version("postgresql", version)
    return series_for("postgresql", version)


class _PgPage(HTMLParser):
    def __init__(self, body: bytes):
        super().__init__(convert_charrefs=True)
        self.links = set()
        self.rows = []
        self.table_found = False
        self._in_table = False
        self._security = False
        self._row = None
        self._cell = None
        self.feed(body.decode("utf-8"))
        self.close()
        if self._in_table:
            raise ValueError("Truncated PostgreSQL table")

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.add(dict(attrs).get("href", ""))
        elif tag == "table":
            self._in_table = True
            self._security = False
        elif tag == "tr" and self._in_table:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append("\n")

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data.replace("\n", " "))

    def handle_endtag(self, tag):
        if tag in {"th", "td"} and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row[:3] == ["Reference", "Affected", "Fixed"]:
                if len(self._row) != 5 or not self._row[3].startswith("Component") or self._row[4] != "Description":
                    raise ValueError("Unexpected PostgreSQL security columns")
                self._security = self.table_found = True
            elif self._security:
                if len(self._row) != 5:
                    raise ValueError("Incomplete PostgreSQL security record")
                self.rows.append(self._row)
            self._row = None
        elif tag == "table":
            self._security = self._in_table = False


def _advisories(page: _PgPage, series: str):
    if not page.table_found:
        raise ValueError("PostgreSQL security table missing")
    for reference, affected, fixed, risk, description in page.rows:
        cve = _CVE.search(reference)
        if cve is None:
            continue
        if f"/support/security/{cve[0]}/" not in page.links:
            raise ValueError("Unexpected PostgreSQL advisory link")
        affected_series = {s.strip() for s in affected.split(",")}
        versions = [v.strip() for v in fixed.split(",")]
        by_series = {_series(v): v for v in versions}
        if len(by_series) != len(versions) or by_series.keys() != affected_series:
            raise ValueError("Ambiguous PostgreSQL fixed version mapping")
        if series not in by_series:
            continue
        lines = [s.strip() for s in risk.splitlines() if s.strip()]
        score = next((float(s) for s in lines[1:] if re.fullmatch(r"\d{1,2}\.\d", s)), None)
        if score is not None and not 0 <= score <= 10:
            raise ValueError("Invalid PostgreSQL CVSS score")
        title = " ".join(description.split()).removesuffix(" more details")
        yield DatabaseAdvisory(cve_id=cve[0], severity=score_severity(score), advisory_id=cve[0],
                               advisory_url=f"{_SECURITY.url}{cve[0]}/", issued_at=None,
                               series=series, fixed_version=by_series[series], component=lines[0],
                               cvss_score=score, title=title, summary=title)


async def _all_advisories(client: httpx.AsyncClient) -> DatabaseFeedData:
    index = _PgPage(await fetch_bytes(client, _SECURITY.url, 4_000_000))
    series = sorted(m[1] for href in index.links if (m := _SERIES_HREF.fullmatch(href)))
    if not index.table_found or not series:
        raise ValueError("PostgreSQL security index missing")
    advisories = []
    for offset in range(0, len(series), 3):
        batch = series[offset:offset + 3]
        pages = await asyncio.gather(*(fetch_bytes(client, f"{_SECURITY.url}{name}/", 4_000_000) for name in batch))
        for name, body in zip(batch, pages):
            advisories.extend(_advisories(_PgPage(body), name))
    if not advisories:
        raise ValueError("No PostgreSQL security evidence")
    builds = {DatabaseBuild(a.fixed_version, a.series) for a in advisories}
    return DatabaseFeedData(tuple(advisories), tuple(sorted(builds, key=lambda b: b.version)))


async def _versions(client: httpx.AsyncClient) -> DatabaseFeedData:
    index, metadata = await asyncio.gather(fetch_bytes(client, _RELEASES.url, 4_000_000), fetch_bytes(client, _PG + "/versions.json", 512_000))
    lifecycle = {row["major"]: row["supported"] for row in json.loads(metadata)}
    builds = []
    for href in sorted(_PgPage(index).links):
        match = _RELEASE_HREF.fullmatch(href)
        if not match:
            continue
        version = match[1]
        major, minor, *rest = version.split(".")
        series = major if int(major) >= 10 else f"{major}.{minor}"
        if series not in lifecycle:
            continue
        if int(major) < 10 and not rest:
            version += ".0"
        validate_version("postgresql", version)
        builds.append(DatabaseBuild(version=version, series=series, label=version, supported=lifecycle[series]))
    if not builds:
        raise ValueError("No published PostgreSQL releases")
    return DatabaseFeedData((), tuple(builds))


async def fetch_postgresql(client: httpx.AsyncClient, target: DatabaseTarget, feed: DatabaseFeed) -> DatabaseFeedData:
    if target != POSTGRESQL_TARGET or feed not in target.feeds:
        raise ValueError("Unknown PostgreSQL source")
    return await (_all_advisories(client) if feed == _SECURITY else _versions(client))
