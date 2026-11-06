# backend/src/infrastructure/external/java_zulu.py
import asyncio
import json
import re
from collections import defaultdict
from datetime import date
from functools import lru_cache

import httpx

from src.domain.entities.java_cve import JavaAdvisory, JavaBuild, JavaFeed, JavaFeedData, JavaTarget
from src.infrastructure.external.kernel_feed_http import fetch_bytes


_DOCS = "https://docs.azul.com/core"
_CVES = JavaFeed("zulu-cves", "Azul 보안 권고", _DOCS + "/cves/all_cves.json")
_VERSIONS = JavaFeed("zulu-versions", "Azul 릴리스 이력", _DOCS + "/cves/release_versions.json", releases_only=True)
_COMMUNITY = JavaFeed("zulu-ca-builds", "Azul 공개 JDK 빌드", "https://api.azul.com/metadata/v1/zulu/packages/", releases_only=True)
ZULU_TARGET = JavaTarget("zulu", "Azul Zulu JDK", (_CVES, _VERSIONS, _COMMUNITY),
                        "Azul의 표준 Zulu JDK 보안 권고와 CPU·PSU별 수정 빌드를 비교합니다. FIPS 전용 권고는 제외합니다. "
                        "개별 CVE의 적용 여부는 구성요소와 실행 조건에 따라 달라질 수 있습니다.")
_BUILD = re.compile(r"(?:Zulu)?(\d{1,2})\.(\d{1,4})(?:[.+](\d{1,5}))?(?:\.(\d{1,5}))?(?:-(?:CA|SA))?", re.I | re.ASCII)
_CVE = re.compile(r"CVE-\d{4}-\d{4,}", re.ASCII)
_PACKAGE = re.compile(r"zulu([\d.]+)-ca-jdk[^/]+-linux_x64\.tar\.gz")


@lru_cache(maxsize=4096)
def _number(value: str) -> tuple[int, ...]:
    match = _BUILD.fullmatch(value)
    if not match or int(match[1]) < 6 or (int(match[2]) == 0 and int(match[1]) != 9):
        raise ValueError("Zulu 빌드 번호를 입력하세요. 예: 11.58.23 또는 Zulu11.58+23-CA")
    return tuple(int(part) for part in match.groups() if part is not None)


def validate_zulu(version: str) -> int:
    return _number(version)[0]


def compare_zulu_versions(left: str, right: str) -> int:
    a, b = _number(left), _number(right)
    return (a > b) - (a < b)


def _severity(score: float) -> str:
    if score >= 9:
        return "critical"
    if score >= 7:
        return "high"
    if score >= 4:
        return "medium"
    return "low" if score > 0 else "unknown"


def _build(record: dict, published: str) -> JavaBuild:
    value, jdk, channel = record["zulu"], record["jdk"], record["type"]
    major = validate_zulu(value)
    if channel not in {"cpu", "psu"} or not re.match(rf"{major}(?!\d)", jdk):
        raise ValueError("Invalid Azul release mapping")
    return JavaBuild(value, major, f"Zulu {value} · Java {jdk} · {channel.upper()}", channel, published)


def _read_catalog(payload: bytes, *, vulnerabilities: bool) -> JavaFeedData:
    releases = json.loads(payload)
    builds, advisories = {}, []
    if not isinstance(releases, list):
        raise ValueError("Invalid Azul release feed")
    for release in releases:
        published = date.fromisoformat(release["date"]).isoformat()
        release_id = release["release"]
        if not re.fullmatch(r"[a-z0-9_]+", release_id):
            raise ValueError("Invalid Azul release identifier")
        if "applies only to azul zulu fips" in release["description"].lower():
            continue
        if not vulnerabilities:
            for row in release["versions"]:
                build = _build(row, published)
                builds[build.version] = build
            continue
        for item in release["cves"]:
            cve, score = item["cve"], item["baseScore"]
            if not _CVE.fullmatch(cve) or not isinstance(score, (float, int)) or not 0 <= score <= 10:
                raise ValueError("Invalid Azul CVE metadata")
            note_text = release.get("notes", {})
            notes = " ".join(note_text.get(str(key), f"적용 조건은 Azul 권고의 주석 {key}을 확인하세요.") for key in item.get("notes", []))
            if "are not affected by " + cve.lower() in notes.lower() or "non-fips bundles are not affected" in notes.lower():
                continue
            for row in item["zulu_versions"]:
                build = _build(row, published)
                builds[build.version] = build
                advisories.append(JavaAdvisory(
                    cve_id=cve, severity=_severity(score), advisory_id=f"Azul {published} {build.channel.upper()}",
                    advisory_url=f"{_DOCS}/cve#cve-release-{release_id}", issued_at=published,
                    major=build.major, fixed_version=build.version, channel=build.channel, cvss_score=score,
                    title=release["description"], summary=notes,
                ))
    if not builds or (vulnerabilities and not advisories):
        raise ValueError("Azul feed does not contain usable release evidence")
    return JavaFeedData(tuple(advisories), tuple(builds.values()))


async def _public_builds(client: httpx.AsyncClient) -> JavaFeedData:
    params = {"os": "linux", "arch": "x86_64", "archive_type": "tar.gz", "javafx_bundled": "false",
              "availability_types": "CA", "java_package_type": "jdk", "release_status": "ga", "page_size": 1000}
    builds = {}
    seen = set()
    page = 1
    while True:
        response = await client.get(_COMMUNITY.url, params={**params, "page": page})
        response.raise_for_status()
        paging, batch = json.loads(response.headers["x-pagination"]), response.json()
        if not isinstance(batch, list) or paging["page"] != page or not batch:
            raise ValueError("Invalid Azul package page")
        for item in batch:
            uid = item["package_uuid"]
            if uid in seen:
                raise ValueError("Repeated Azul package page")
            seen.add(uid)
            match = _PACKAGE.fullmatch(item["name"])
            if match and item["product"] == "zulu" and item["availability_type"] == "CA":
                value = match[1]
                major = validate_zulu(value)
                jdk = ".".join(str(n) for n in item["java_version"]) + f"+{item['openjdk_build_number']}"
                builds[value] = JavaBuild(value, major, f"Zulu {value} · Java {jdk} · CA")
        if page == paging["last_page"]:
            if len(seen) != paging["total"] or not builds:
                raise ValueError("Incomplete Azul package catalog")
            return JavaFeedData((), tuple(builds.values()))
        if paging.get("next_page") != page + 1:
            raise ValueError("Invalid Azul package pagination")
        page += 1


async def fetch_zulu(client: httpx.AsyncClient, target: JavaTarget, feed: JavaFeed) -> JavaFeedData:
    if target != ZULU_TARGET or feed not in target.feeds:
        raise ValueError("Unsupported Azul source")
    if feed == _COMMUNITY:
        return await _public_builds(client)
    payload = await fetch_bytes(client, feed.url, 12_000_000)
    return await asyncio.to_thread(_read_catalog, payload, vulnerabilities=feed == _CVES)


def _selection(version: str, data: tuple[JavaFeedData, ...]):
    selected = _number(version)
    train = selected[:2]
    channels = set()
    exact_advisory_build = False
    for part in data:
        for build in part.builds:
            n = _number(build.version)
            if n[:2] == train and build.channel:
                channels.add(build.channel)
                if n == selected:
                    exact_advisory_build = True
    return selected, channels.pop() if len(channels) == 1 else None, exact_advisory_build


def zulu_coverage_note(target: JavaTarget, version: str, data: tuple[JavaFeedData, ...]) -> str | None:
    selected, channel, exact = _selection(version, data)
    if channel is None:
        return "이 빌드의 CPU·PSU 업데이트 계열을 Azul 자료에서 확인할 수 없습니다."
    notes = []
    if not exact:
        notes.append("같은 업데이트 계열의 수정 빌드를 기준으로 비교했습니다. 공개판(CA)과 구독판(SA)의 세부 빌드 번호가 다를 수 있습니다.")
    builds = [b for part in data for b in part.builds if b.issued_at and b.channel and _number(b.version)[:2] == selected[:2]]
    known_dates = [b.issued_at for b in builds if _number(b.version) <= selected]
    as_of = max(known_dates, default="")
    evidence = [a for part in data for a in part.advisories if a.major == selected[0]]
    missing = {a.cve_id for a in evidence if a.issued_at and a.issued_at > as_of} - {a.cve_id for a in evidence if a.channel == channel}
    if missing:
        examples = ", ".join(sorted(missing)[-3:])
        notes.append(f"같은 Java 계열의 권고 중 {channel.upper()} 수정 빌드가 명시되지 않은 CVE {len(missing)}건은 영향 미확인입니다({examples}).")
    return " ".join(notes) or None


def zulu_matcher(target: JavaTarget, version: str, data: tuple[JavaFeedData, ...]):
    selected, channel, _ = _selection(version, data)
    if channel is None:
        return None
    train = selected[:2]
    thresholds = defaultdict(set)
    for part in data:
        for advisory in part.advisories:
            if advisory.major == selected[0] and advisory.channel == channel and advisory.fixed_version:
                thresholds[advisory.cve_id].add(_number(advisory.fixed_version))
    relevant = {}
    for cve, versions in thresholds.items():
        same_train = [v for v in versions if v[:2] == train]
        if same_train:
            limit = min(same_train)
        else:
            limit = min(versions)
        if selected < limit:
            relevant[cve] = limit
    return lambda row: (row.channel == channel and row.fixed_version is not None
                        and relevant.get(row.cve_id) == _number(row.fixed_version))
