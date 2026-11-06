# backend/src/infrastructure/external/java_openjdk.py
import asyncio
import re
from datetime import date, datetime

import httpx
from defusedxml import ElementTree

from src.domain.entities.java_cve import JavaAdvisory, JavaBuild, JavaFeed, JavaFeedData, JavaTarget
from src.infrastructure.external.java_version import java_version
from src.infrastructure.external.kernel_feed_http import fetch_bytes


_SITE = "https://jdk.java.net"
_BULLETINS = JavaFeed("openjdk-advisories", "OpenJDK 취약점 권고", "https://openjdk.org/groups/vulnerability/advisories/")
_RELEASES = JavaFeed("openjdk-ga", "OpenJDK 정식 릴리스", _SITE + "/archive/", releases_only=True)
OPENJDK_TARGET = JavaTarget(
    "openjdk", "OpenJDK", (_BULLETINS, _RELEASES),
    "OpenJDK 권고의 CVE별 적용 계열과 마지막 영향 버전을 비교합니다. 빌드 번호별 공급자 백포트와 별도 OpenJFX 권고는 제외합니다.",
)
_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,}")


async def _page(client, url):
    return await fetch_bytes(client, url, 2_000_000)


def _main(page):
    main = ElementTree.fromstring(page).find(".//{*}div[@id='main']")
    if main is None:
        raise ValueError("Missing OpenJDK content")
    return main


def _text(node):
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def _after_heading(main, heading_id, tag):
    children = list(main)
    for heading, section in zip(children, children[1:]):
        if heading.get("id") == heading_id and section.tag.rsplit("}", 1)[-1] == tag:
            return section
    raise ValueError(f"Missing OpenJDK section: {heading_id}")


def _index(page):
    section = _after_heading(_main(page), "advisories", "ul")
    dates = set()
    for row in section.findall("{*}li"):
        link = row.find("{*}a")
        day = link.get("href", "") if link is not None else ""
        if not _DAY.fullmatch(day):
            raise ValueError("Unexpected OpenJDK advisory link")
        dates.add(date.fromisoformat(day).isoformat())
    if not dates:
        raise ValueError("Empty OpenJDK advisory index")
    return sorted(dates, reverse=True)


def _affected_releases(main):
    prose = " ".join(_text(p) for p in main.findall("{*}p"))
    declared = re.search(r"\bThe affected versions are (.+?),? and earlier\.", prose)
    if not declared:
        raise ValueError("Missing OpenJDK affected version range")
    releases = {}
    for value in declared[1].strip(",").split(", "):
        major = java_version(value)[0][0]
        if major in releases:
            raise ValueError("Ambiguous OpenJDK affected version range")
        releases[major] = value
    return releases


def _severity(value):
    if not re.fullmatch(r"(?:10(?:\.0)?|[0-9](?:\.[0-9])?)", value):
        raise ValueError("Invalid OpenJDK CVSS score")
    score = float(value)
    for threshold, label in ((9, "critical"), (7, "high"), (4, "medium")):
        if score >= threshold:
            return label, score
    return ("low" if score else "unknown"), score


def parse_openjdk_advisory(page: bytes, day: str) -> JavaFeedData:
    main = _main(page)
    heading = _text(main.find("{*}h1")).removeprefix("OpenJDK Vulnerability Advisory: ")
    if datetime.strptime(heading, "%Y/%m/%d").date().isoformat() != day:
        raise ValueError("OpenJDK advisory identity mismatch")
    releases = _affected_releases(main)
    table = _after_heading(main, "risk-matrix", "table")
    rows = table.findall(".//{*}tr")
    if len(rows) < 3:
        raise ValueError("Incomplete OpenJDK risk matrix")
    headings = [_text(cell) for cell in rows[1].findall("{*}th")]
    if headings[:2] != ["CVE ID", "Component"] or len(headings) < 4 or "CVSS" not in headings[2]:
        raise ValueError("Unexpected OpenJDK risk matrix columns")
    majors = [int(h) for h in headings[3:]]
    if len(set(majors)) != len(majors):
        raise ValueError("Duplicate OpenJDK risk matrix column")
    advisories = []
    for row in rows[2:]:
        cells = row.findall("{*}td")
        values = [_text(cell) for cell in cells]
        if len(values) != len(headings) or any(mark not in {"", "•"} for mark in values[3:]):
            raise ValueError("Unexpected OpenJDK risk matrix cells")
        cve = values[0]
        if cve == "None" and not any(values[1:]):
            continue
        if not _CVE.fullmatch(cve) or not values[1]:
            raise ValueError("Incomplete OpenJDK vulnerability row")
        severity, score = _severity((cells[2].text or "").strip())
        for major, mark in zip(majors, values[3:]):
            if mark:
                advisories.append(JavaAdvisory(
                    cve, severity, f"OpenJDK {day}", _BULLETINS.url + day, day, major,
                    affected_through=releases.get(major), component=values[1], cvss_score=score,
                ))
    return JavaFeedData(tuple(advisories), tuple(JavaBuild(v, m) for m, v in releases.items()))


async def _all_advisories(client):
    days = _index(await _page(client, _BULLETINS.url))
    advisories, builds = [], {}
    for offset in range(0, len(days), 4):
        batch = days[offset:offset + 4]
        pages = await asyncio.gather(*(_page(client, _BULLETINS.url + day) for day in batch))
        for day, page in zip(batch, pages):
            result = parse_openjdk_advisory(page, day)
            advisories.extend(result.advisories)
            builds.update((b.version, b) for b in result.builds)
    if not advisories:
        raise ValueError("OpenJDK archive contains no vulnerabilities")
    return JavaFeedData(tuple(advisories), tuple(builds.values()))


async def _ga_releases(client):
    archive, home = await asyncio.gather(_page(client, _RELEASES.url), _page(client, _SITE + "/"))
    versions = set()
    for heading in _main(archive).findall(".//{*}th"):
        text = _text(heading)
        if "(build " in text:
            match = re.fullmatch(r"(?:JDK )?([0-9.]+)(?: GA)? \(build [^)]+\)", text)
            if not match:
                raise ValueError("Unrecognized OpenJDK archived release")
            versions.add(match[1])
    if not versions:
        raise ValueError("Empty OpenJDK release archive")
    current = set()
    for heading in _main(home).findall(".//{*}h1"):
        if _text(heading).startswith("Ready for use:"):
            current.update(link.get("href") for link in heading.findall("{*}a") if re.fullmatch(r"/[0-9]+/", link.get("href", "")))
    if not current:
        raise ValueError("Missing OpenJDK production release link")
    for path in sorted(current):
        heading = _text(_main(await _page(client, _SITE + path)).find("{*}h1"))
        match = re.fullmatch(r"(?:OpenJDK )?JDK ([0-9.]+) GA Release Builds", heading)
        if not match or str(java_version(match[1])[0][0]) != path.strip("/"):
            raise ValueError("OpenJDK production release identity mismatch")
        versions.add(match[1])
    return JavaFeedData((), tuple(JavaBuild(v, java_version(v)[0][0]) for v in sorted(versions)))


async def fetch_openjdk(client: httpx.AsyncClient, target: JavaTarget, feed: JavaFeed) -> JavaFeedData:
    if target != OPENJDK_TARGET or feed not in target.feeds:
        raise ValueError("지원하지 않는 OpenJDK 출처입니다.")
    return await (_all_advisories(client) if feed == _BULLETINS else _ga_releases(client))


def openjdk_matcher(version: str, data: tuple[JavaFeedData, ...]):
    selected, _ = java_version(version)
    if not any(row.major == selected[0] and row.affected_through for feed in data for row in feed.advisories):
        return None

    def matches(row: JavaAdvisory) -> bool:
        return row.major == selected[0] and row.affected_through is not None and selected <= java_version(row.affected_through)[0]

    return matches


def openjdk_coverage_note(version: str, data: tuple[JavaFeedData, ...]) -> str | None:
    selected, _ = java_version(version)
    rows = [row for feed in data for row in feed.advisories if row.major == selected[0]]
    if not rows:
        return "이 Java 계열에 대한 OpenJDK 권고의 적용 범위를 확인할 수 없습니다."
    for day in {r.issued_at for r in rows if not r.affected_through}:
        subsequent = [java_version(r.affected_through)[0] for r in rows if r.issued_at > day and r.affected_through]
        if not subsequent or selected <= min(subsequent):
            return "일부 OpenJDK 권고에서 이 계열의 마지막 영향 버전을 명시하지 않아 해당 CVE의 적용 여부를 확인할 수 없습니다."
    if not any(java_version(b.version)[0] == selected for feed in data for b in feed.builds if b.major == selected[0]):
        return "입력한 릴리스는 수집된 버전 목록에 없습니다. OpenJDK 권고의 같은 계열 영향 범위와 비교한 결과입니다."
    return None
