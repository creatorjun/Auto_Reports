# backend/src/infrastructure/external/security_news_source.py
import asyncio
import hashlib
import json
import math
import re
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx
from defusedxml import ElementTree

from src.application.ports.security_news_port import SecurityNewsPort
from src.domain.entities.security_news import (
    SecurityNewsItem,
    SecurityNewsSource,
    SecurityNewsSourceResult,
)
from src.infrastructure.external.security_cve_remediation import cve_remediations
from src.infrastructure.external.security_cve_provenance import manufacturer_remediations


SOURCES = (
    SecurityNewsSource("cisa-kev", "CISA KEV", "https://www.cisa.gov/known-exploited-vulnerabilities-catalog", "cve", minimum_refresh_seconds=7200, collection_version=3),
    SecurityNewsSource("nvd", "NVD", "https://nvd.nist.gov/", "cve", minimum_refresh_seconds=7200, collection_version=2),
    SecurityNewsSource("kisa", "KISA 보호나라", "https://www.boho.or.kr/", "advisory"),
    SecurityNewsSource("cisco", "Cisco 보안 권고", "https://sec.cloudapps.cisco.com/security/center/publicationListing.x", "advisory"),
)
ENDPOINTS = {
    "cisa-kev": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
    "nvd": "https://services.nvd.nist.gov/rest/json/cves/2.0",
    "kisa": "https://www.boho.or.kr/kr/rss.do?bbsId=B0000133",
    "cisco": "https://sec.cloudapps.cisco.com/security/center/psirtrss20/CiscoSecurityAdvisory.xml",
}
CVE_PATTERN = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_ITEMS = 300
SOURCE_TIMEOUT_SECONDS = 65
NVD_SOURCE_TIMEOUT_SECONDS = 180
NVD_REQUEST_INTERVAL_SECONDS = 6
NVD_BATCH_SIZE = 100
VALID_SEVERITIES = {"critical", "high", "medium", "low"}


class PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._hidden += 1
        elif tag in {"p", "br", "div", "li"} and not self._hidden:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._hidden:
            self._hidden -= 1
        elif tag in {"p", "div", "li"} and not self._hidden:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._hidden:
            self.parts.append(data)


def plain_text(value: object, limit: int = 1200) -> str:
    parser = PlainTextParser()
    parser.feed(str(value or "")[:100_000])
    parser.close()
    return " ".join(unescape("".join(parser.parts)).split())[:limit]


def parse_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value.strip())
        except (ValueError, TypeError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def safe_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if any(ord(char) < 32 for char in value) or "\\" in value or len(value) > 4096:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        parsed.port
    except ValueError:
        return None
    return value


def cve_ids(value: str) -> tuple[str, ...]:
    return tuple(sorted({match.upper() for match in CVE_PATTERN.findall(value)}))


def recent_items(items: list[SecurityNewsItem], limit: int = MAX_ITEMS) -> tuple[SecurityNewsItem, ...]:
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    unique = {item.id: item for item in items}
    return tuple(sorted(
        unique.values(),
        key=lambda item: (item.published_at or item.updated_at or oldest, item.id),
        reverse=True,
    )[:limit])


def parse_kev(payload: bytes) -> SecurityNewsSourceResult:
    data = json.loads(payload)
    rows = data.get("vulnerabilities")
    if not isinstance(rows, list):
        raise ValueError("Invalid KEV response")
    items: list[SecurityNewsItem] = []
    exploited: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        cve = str(row.get("cveID", "")).upper()
        if not CVE_PATTERN.fullmatch(cve):
            continue
        exploited.add(cve)
        due = parse_date(row.get("dueDate"))
        description = plain_text(row.get("shortDescription"), 100_000)
        product = plain_text(row.get("product"), 200) or None
        vendor = plain_text(row.get("vendorProject"), 200) or None
        url = f"https://nvd.nist.gov/vuln/detail/{cve}"
        items.append(SecurityNewsItem(
            id=f"cisa-kev:{cve}", source_id="cisa-kev", kind="cve",
            title=plain_text(f"{cve} · {row.get('vulnerabilityName', '')}", 240),
            summary=description[:1200], url=url,
            published_at=parse_date(row.get("dateAdded")), cve_ids=(cve,),
            known_exploited=True,
            vendor=vendor, product=product,
            due_date=due.date().isoformat() if due is not None else None,
            remediations=cve_remediations(None, description, url, product=product, vendor=vendor),
            original_description=description or None,
        ))
    return SecurityNewsSourceResult(
        recent_items(items), frozenset(exploited),
        "최근 KEV 등재 최대 300건입니다. 표시 날짜는 CVE 공개일이 아닌 KEV 등재일이며, 조치 기한은 미국 연방기관 기준입니다.",
    )


def cvss_details(metrics: object) -> tuple[str, float | None, str | None]:
    if not isinstance(metrics, dict):
        return "unknown", None, None
    for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        candidates = metrics.get(key)
        if not isinstance(candidates, list):
            continue
        candidates = sorted(
            (candidate for candidate in candidates if isinstance(candidate, dict)),
            key=lambda candidate: candidate.get("type") != "Primary",
        )
        for candidate in candidates:
            cvss = candidate.get("cvssData")
            if not isinstance(cvss, dict):
                continue
            value = cvss.get("baseScore")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 10:
                continue
            severity = str(cvss.get("baseSeverity") or candidate.get("baseSeverity") or "").lower()
            return (
                severity if severity in VALID_SEVERITIES else "unknown",
                float(value),
                str(cvss.get("version")) if cvss.get("version") is not None else None,
            )
    return "unknown", None, None


def parse_nvd(payload: bytes) -> SecurityNewsSourceResult:
    data = json.loads(payload)
    rows = data.get("vulnerabilities")
    if not isinstance(rows, list):
        raise ValueError("Invalid NVD response")
    items: list[SecurityNewsItem] = []
    for entry in rows:
        if not isinstance(entry, dict) or not isinstance(entry.get("cve"), dict):
            continue
        row = entry["cve"]
        cve = str(row.get("id", "")).upper()
        if not CVE_PATTERN.fullmatch(cve) or row.get("vulnStatus") == "Rejected":
            continue
        descriptions = row.get("descriptions")
        descriptions = descriptions if isinstance(descriptions, list) else []
        summaries = [value for value in descriptions if isinstance(value, dict)]
        description = next(
            (value.get("value") for value in summaries if value.get("lang") == "en"),
            next((value.get("value") for value in summaries), ""),
        )
        description = plain_text(description, 100_000)
        summary = description[:1200]
        severity, score, version = cvss_details(row.get("metrics"))
        url = f"https://nvd.nist.gov/vuln/detail/{cve}"
        items.append(SecurityNewsItem(
            id=f"nvd:{cve}", source_id="nvd", kind="cve",
            title=plain_text(f"{cve} · {summary}", 240), summary=summary,
            url=url,
            published_at=parse_date(row.get("published")),
            updated_at=parse_date(row.get("lastModified")),
            cve_ids=(cve,), severity=severity, cvss_score=score, cvss_version=version,
            remediations=manufacturer_remediations(
                cve_remediations(row.get("configurations"), description, url), row.get("sourceIdentifier"), row.get("references"),
            ),
            original_description=description or None,
        ))
    warning = "최근 7일에 공개된 CVE 중 최신 최대 200건이며, 수동 새로고침을 포함해 2시간 간격으로 조회합니다. CVSS 미평가 항목은 심각도 미정입니다."
    return SecurityNewsSourceResult(recent_items(items, 200), warning=warning)


def element_text(element, names: tuple[str, ...]) -> str:
    for name in names:
        for namespace in (
            "", "http://www.w3.org/2005/Atom", "http://purl.org/rss/1.0/",
            "http://purl.org/dc/elements/1.1/", "http://purl.org/rss/1.0/modules/content/",
        ):
            tag = f"{{{namespace}}}{name}" if namespace else name
            for child in element:
                if child.tag == tag:
                    return "".join(child.itertext()).strip()
    return ""


def parse_feed(payload: bytes, source: SecurityNewsSource) -> SecurityNewsSourceResult:
    root = ElementTree.fromstring(payload, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    if root.tag.rsplit("}", 1)[-1] not in {"rss", "RDF", "feed"}:
        raise ValueError("Invalid feed response")
    items: list[SecurityNewsItem] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
            continue
        title = plain_text(element_text(element, ("title",)), 240)
        link = element_text(element, ("link",))
        if not link:
            link = next(
                (
                    child.attrib.get("href", "")
                    for child in element
                    if child.tag.rsplit("}", 1)[-1] == "link"
                    and child.attrib.get("rel", "alternate") == "alternate"
                ),
                "",
            )
        url = safe_url(link)
        if not title or url is None:
            continue
        description = plain_text(element_text(element, ("description", "summary", "encoded", "content")), 100_000)
        identifier = element_text(element, ("guid", "id")) or url
        digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:24]
        items.append(SecurityNewsItem(
            id=f"{source.id}:{digest}", source_id=source.id, kind=source.kind,
            title=title, summary=description[:600], url=url,
            published_at=parse_date(element_text(element, ("pubDate", "published", "date"))),
            updated_at=parse_date(element_text(element, ("updated",))),
            cve_ids=cve_ids(f"{title} {description}"),
        ))
    return SecurityNewsSourceResult(recent_items(items, 100))


class PublicSecurityNewsSource(SecurityNewsPort):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(25.0, connect=8.0),
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=5),
            follow_redirects=False,
            headers={"User-Agent": "TAC-Auto-Reports-Security-News/1.0", "Accept": "application/json, application/rss+xml, application/xml, text/xml"},
        )
        self._owns_client = client is None
        self._nvd_lock = asyncio.Lock()
        self._nvd_next_request = 0.0

    @property
    def sources(self) -> tuple[SecurityNewsSource, ...]:
        return SOURCES

    async def fetch(self, source_id: str) -> SecurityNewsSourceResult:
        if source_id not in ENDPOINTS:
            raise ValueError("Unknown security news source")
        timeout = NVD_SOURCE_TIMEOUT_SECONDS if source_id in {"nvd", "cisa-kev"} else SOURCE_TIMEOUT_SECONDS
        return await asyncio.wait_for(self._fetch(source_id), timeout=timeout)

    async def _fetch(self, source_id: str) -> SecurityNewsSourceResult:
        if source_id == "nvd":
            now = datetime.now(timezone.utc)
            params = {
                "pubStartDate": (now - timedelta(days=7)).isoformat(timespec="milliseconds"),
                "pubEndDate": now.isoformat(timespec="milliseconds"),
                "resultsPerPage": 1,
            }
            first_payload = await self._read_nvd(params)
            first_page = json.loads(first_payload)
            total = first_page.get("totalResults")
            if isinstance(total, bool) or not isinstance(total, int) or total < 0:
                raise ValueError("Invalid NVD total")
            if total <= 1:
                return parse_nvd(first_payload)
            params.update({"resultsPerPage": 200, "startIndex": max(0, total - 200)})
            return parse_nvd(await self._read_nvd(params))
        payload = await self._read_response(ENDPOINTS[source_id])
        if source_id == "cisa-kev":
            return await self._enrich_kev(parse_kev(payload))
        source = next(source for source in SOURCES if source.id == source_id)
        return parse_feed(payload, source)

    async def _read_nvd(self, params: dict) -> bytes:
        async with self._nvd_lock:
            delay = self._nvd_next_request - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            try:
                return await self._read_response(ENDPOINTS["nvd"], params=params)
            finally:
                self._nvd_next_request = time.monotonic() + NVD_REQUEST_INTERVAL_SECONDS

    async def _enrich_kev(self, result: SecurityNewsSourceResult) -> SecurityNewsSourceResult:
        identifiers = tuple(dict.fromkeys(cve for item in result.items for cve in item.cve_ids))
        details: dict[str, SecurityNewsItem] = {}
        for start in range(0, len(identifiers), NVD_BATCH_SIZE):
            batch = identifiers[start:start + NVD_BATCH_SIZE]
            payload = await self._read_nvd({"cveIds": ",".join(batch), "resultsPerPage": NVD_BATCH_SIZE})
            document = json.loads(payload)
            if not isinstance(document, dict):
                raise ValueError("Invalid NVD detail response")
            rows, total = document.get("vulnerabilities"), document.get("totalResults")
            if (
                not isinstance(rows, list) or isinstance(total, bool) or not isinstance(total, int)
                or not 0 <= total <= len(batch) or total != len(rows) or document.get("startIndex", 0) != 0
            ):
                raise ValueError("Incomplete NVD detail response")
            returned = [row.get("cve", {}).get("id") for row in rows if isinstance(row, dict) and isinstance(row.get("cve"), dict)]
            if (
                len(returned) != total or any(not isinstance(value, str) or not CVE_PATTERN.fullmatch(value) for value in returned)
                or len(set(returned)) != total or not set(returned).issubset(batch)
            ):
                raise ValueError("Mismatched NVD detail response")
            details.update((item.cve_ids[0], item) for item in parse_nvd(payload).items)
        items = []
        missing = 0
        for item in result.items:
            detail = details.get(item.cve_ids[0])
            if detail is None:
                missing += 1
                items.append(item)
                continue
            normalize = lambda value: re.sub(r"[\W_]", "", value or "").casefold()
            names = {normalize(item.product), normalize(f"{item.vendor or ''} {item.product or ''}")}
            matching = tuple(entry for entry in detail.remediations if normalize(entry.product) in names or normalize(f"{entry.vendor or ''} {entry.product}") in names)
            items.append(replace(
                item, severity=detail.severity, cvss_score=detail.cvss_score, cvss_version=detail.cvss_version,
                updated_at=detail.updated_at, remediations=matching or detail.remediations or item.remediations,
                original_description="\n\n".join(dict.fromkeys(
                    value for value in (item.original_description, detail.original_description) if value
                )) or None,
            ))
        warning = (result.warning or "") + " CVE 번호로 NVD 상세 정보를 조회해 버전과 CVSS를 보완하며 최소 2시간 간격으로 갱신합니다."
        if missing:
            warning += f" NVD 상세 정보가 없는 {missing}건은 KEV 원문을 표시합니다."
        return replace(result, items=tuple(items), warning=warning)

    async def _read_response(self, url: str, *, params: dict | None = None) -> bytes:
        payload = bytearray()
        async with self._client.stream("GET", url, params=params) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                if len(payload) + len(chunk) > MAX_RESPONSE_BYTES:
                    raise ValueError("Security news response is too large")
                payload.extend(chunk)
        return bytes(payload)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
