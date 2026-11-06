# backend/src/infrastructure/external/database_mysql.py
import asyncio
import html
import json
import re
from urllib.parse import urlsplit

from defusedxml import ElementTree

from src.domain.entities.database_cve import DatabaseAdvisory, DatabaseBuild, DatabaseFeed, DatabaseFeedData, DatabaseTarget
from src.infrastructure.external.database_version import compare_versions, score_severity, series_for, version_parts
from src.infrastructure.external.kernel_feed_http import fetch_bytes


_BASE = "https://www.oracle.com/security-alerts/"
_DOCS = "https://www.oracle.com/a/tech/docs/security-alerts/"
_CSAF = DatabaseFeed("mysql-csaf", "Oracle CSAF 보안 권고", _DOCS + "oracle-cpu-csaf-rss.xml")
_ARCHIVE = DatabaseFeed("mysql-cpu-archive", "Oracle 이전 분기 보안 권고", _BASE + "cpuarchive.html")
_RELEASES = DatabaseFeed("mysql-tags", "MySQL Server 공식 릴리스 태그", "https://api.github.com/repos/mysql/mysql-server/git/matching-refs/tags/mysql-", releases_only=True)
MYSQL_TARGET = DatabaseTarget("mysql", "MySQL", (_CSAF, _ARCHIVE, _RELEASES),
    "2012년부터 Oracle 권고에서 MySQL Server 제품에 명시된 버전 범위를 조회합니다. MySQL Cluster·Connector 등 별도 제품의 항목은 제외합니다.")
_VER = r"[0-9]+(?:\.[0-9]+){1,3}"
_CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,}")
_HREF = re.compile(r"""\bhref\s*=\s*["']([^"']+)["']""", re.I)


def _ranges(value):
    value = value.strip().replace(" and eariler", " and earlier")
    terms = re.split(r",\s*|(?<=earlier)\s*(?=[0-9])", value)
    for term in terms:
        if ambiguous := re.fullmatch(r"([1-9][0-9]*)\.0[0-9]+ and (?:prior|earlier)", term):
            yield ambiguous[1] + ".*", None, None, None
        elif prior := re.fullmatch(rf"({_VER}) and (?:prior|earlier)", term):
            yield series_for("mysql", prior[1]), None, prior[1], None
        elif bounds := re.fullmatch(rf"({_VER})(?:-| to )({_VER})", term):
            lo, hi = bounds.groups()
            ln, _ = version_parts(lo)
            rn, _ = version_parts(hi)
            if ln[0] != rn[0] or compare_versions(hi, lo) < 0 or rn[1] - ln[1] > 100:
                raise ValueError("Unsupported Oracle MySQL series interval")
            for minor in range(ln[1], rn[1] + 1):
                yield f"{ln[0]}.{minor}", lo, hi, None
        elif re.fullmatch(_VER, term):
            yield series_for("mysql", term), None, None, term
        elif wild := re.fullmatch(r"([0-9]+\.[0-9]+)\.x", term):
            yield wild[1], None, None, None
        else:
            raise ValueError(f"Unrecognized MySQL affected range: {term[:100]}")


def _builds(items):
    versions = {value for item in items for value in (item.affected_from, item.affected_through, item.affected_version) if value and value.count(".") >= 2}
    return tuple(DatabaseBuild(v, series_for("mysql", v)) for v in sorted(versions))


def _products(node, product="", family=""):
    if node.get("category") == "product_family":
        family = node["name"]
    if node.get("category") == "product_name":
        product = node["name"]
    item = node.get("product")
    if item and product == "MySQL Server" and family == "Oracle MySQL":
        match = re.fullmatch(r"MySQL Server(?:\((.*)\))? Version (.+)", item["name"])
        if not match:
            raise ValueError("Unrecognized CSAF MySQL product")
        yield item["product_id"], (match[1] or "", tuple(_ranges(match[2])))
    for child in node.get("branches", ()):
        yield from _products(child, product, family)


def _public_reference(document):
    for ref in document.get("references", ()):
        url = ref.get("url", "")
        if re.fullmatch(r"https://www\.oracle\.com/security-alerts/[A-Za-z0-9_-]+\.html", url):
            return url
    raise ValueError("Missing Oracle advisory URL")


def parse_mysql_csaf(payload: bytes):
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = payload.decode("latin-1")
    doc = json.loads(text)
    products = dict(_products(doc["product_tree"]))
    if not products:
        return ()
    info = doc["document"]
    link = _public_reference(info)
    title = info["title"]
    issued = info["tracking"]["initial_release_date"][:10]
    advisories = []
    for entry in doc["vulnerabilities"]:
        matched = products.keys() & set(entry.get("product_status", {}).get("known_affected", ()))
        if not matched:
            continue
        cve = entry["cve"]
        if not _CVE.fullmatch(cve):
            raise ValueError("Invalid Oracle CVE identifier")
        scores = {pid: float(score["cvss_v3"]["baseScore"]) for score in entry.get("scores", ()) if "cvss_v3" in score for pid in score.get("products", ())}
        note = next((n["text"] for n in entry.get("notes", ()) if n.get("category") == "description" and re.search(r"in the MySQL Server(?:,| product| component)", n.get("text", ""), re.I)), "")
        for pid in sorted(matched):
            part, ranges = products[pid]
            if not part and note:
                detail = re.search(r"\(component: (.+?)\)\.", note)
                part = detail[1] if detail else ""
            score = scores.get(pid)
            if score is not None and not 0 <= score <= 10:
                raise ValueError("Invalid Oracle CVSS score")
            for series, low, high, exact in ranges:
                advisories.append(DatabaseAdvisory(cve, score_severity(score), title, link, issued, series, summary=note[:1500],
                    affected_from=low, affected_through=high, affected_version=exact, component=part, cvss_score=score))
    return tuple(advisories)


def _legacy_rows(page: str):
    for table in re.findall(r"<table\b[^>]*>(.*?)</table>", page, re.I | re.S):
        if "mysql server" not in table.lower():
            continue
        rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", table, re.I | re.S)
        if not rows:
            continue
        cells = re.compile(r"<t[dh]\b([^>]*)>(.*?)</t[dh]>", re.I | re.S)
        def plain(raw):
            return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).replace("\u00ad", "").split())
        headers = []
        for attr, raw in cells.findall(rows[0]):
            colspan = re.search(r"""colspan\s*=\s*["']?([0-9]+)""", attr, re.I)
            headers.extend([plain(raw).lower().replace("- ", "-")] * (int(colspan[1]) if colspan else 1))
        if not headers or not headers[0].startswith("cve") or "supported versions affected" not in headers:
            continue
        pi = headers.index("product") if "product" in headers else headers.index("component")
        ci = next((i for i, h in enumerate(headers) if i != pi and h.replace("-", "") in {"subcomponent", "component"}), None)
        vi = headers.index("supported versions affected")
        si = next(i for i, h in enumerate(headers) if h.startswith("cvss version"))
        for row in rows[1:]:
            values = [plain(raw) for _, raw in cells.findall(row)]
            if len(values) > pi and values[pi] == "MySQL Server":
                if len(values) <= vi or not _CVE.fullmatch(values[0]):
                    raise ValueError("Malformed Oracle CPU matrix row")
                score = float(values[si])
                if not 0 <= score <= 10:
                    raise ValueError("Invalid Oracle CPU score")
                severity = "high" if score >= 9 and "version 2" in headers[si] else score_severity(score)
                yield values[0], severity, score, values[ci] if ci is not None else "", values[vi]


def parse_mysql_legacy(payload: bytes, url: str):
    page = payload.decode("utf-8", errors="replace")
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    if not title or not ("Critical Patch Update" in title[1] or re.fullmatch(r"CPU [A-Za-z]+ [0-9]{4}", title[1])):
        raise ValueError("Invalid legacy Oracle CPU document")
    advisories = []
    for cve, severity, score, component, value in _legacy_rows(page):
        for series, low, high, exact in _ranges(value):
            advisories.append(DatabaseAdvisory(cve, severity, html.unescape(title[1]).strip(), url, None, series,
                affected_from=low, affected_through=high, affected_version=exact, component=component, cvss_score=score))
    if not advisories:
        raise ValueError("Oracle archive contains no recognized MySQL Server risk matrix")
    return tuple(advisories)


async def _collect(client, urls, parser):
    items = []
    for offset in range(0, len(urls), 3):
        batch = urls[offset:offset + 3]
        pages = await asyncio.gather(*(fetch_bytes(client, u, 16_000_000) for u in batch))
        for page, url in zip(pages, batch):
            items.extend(await asyncio.to_thread(parser, page, url))
    if not items:
        raise ValueError("No Oracle MySQL advisories collected")
    return DatabaseFeedData(tuple(dict.fromkeys(items)), _builds(items))


async def _legacy(client):
    pages = await asyncio.gather(*(fetch_bytes(client, u, 2_000_000) for u in (_BASE, _ARCHIVE.url)))
    urls = set()
    for page in pages:
        for href in _HREF.findall(page.decode("utf-8", errors="replace")):
            slug = re.fullmatch(r"(?:https://www\.oracle\.com)?/security-alerts/(cpu(jan|apr|july?|oct)([0-9]{4})(?:v[0-9]+)?\.html)", href)
            if slug and (2012 <= int(slug[3]) <= 2021 or (slug[2], slug[3]) == ("jan", "2022")):
                urls.add(_BASE + slug[1])
    return await _collect(client, sorted(urls), parse_mysql_legacy)


async def _csaf(client):
    rss = ElementTree.fromstring(await fetch_bytes(client, _CSAF.url, 2_000_000), forbid_dtd=True)
    urls = set()
    for item in rss.findall("./channel/item"):
        parsed = urlsplit((item.findtext("link") or "").strip())
        name = re.fullmatch(r"/(?:a/tech/docs|docs/tech)/security-alerts/([a-zA-Z0-9-]+csaf\.json)", parsed.path)
        if parsed.scheme != "https" or parsed.netloc != "www.oracle.com" or not name or parsed.query or parsed.fragment:
            raise ValueError("Unexpected Oracle CSAF feed URL")
        urls.add(_DOCS + name[1])
    return await _collect(client, sorted(urls), lambda page, url: parse_mysql_csaf(page))


async def fetch_mysql(client, target, feed):
    if target != MYSQL_TARGET or feed not in target.feeds:
        raise ValueError("지원하지 않는 MySQL 출처입니다.")
    if feed == _ARCHIVE:
        return await _legacy(client)
    if feed == _CSAF:
        return await _csaf(client)
    tags = json.loads(await fetch_bytes(client, _RELEASES.url, 8_000_000))
    versions = set()
    for tag in tags:
        match = re.fullmatch(r"refs/tags/mysql-([0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?)", tag["ref"])
        if match:
            versions.add(match[1])
    if not versions:
        raise ValueError("Empty MySQL release tag catalog")
    return DatabaseFeedData((), tuple(DatabaseBuild(v, series_for("mysql", v)) for v in sorted(versions)))
