# backend/tests/test_security_news_source.py
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from defusedxml.common import DTDForbidden

from src.infrastructure.external.security_news_source import (
    ENDPOINTS,
    SOURCES,
    PublicSecurityNewsSource,
    cvss_details,
    parse_date,
    parse_feed,
    parse_kev,
    parse_nvd,
    plain_text,
    safe_url,
)


class SecurityNewsParsingTest(unittest.TestCase):
    def test_kev_retains_exploited_ids_beyond_visible_limit_without_fabricating_cvss(self) -> None:
        payload = json.dumps({"vulnerabilities": [
            {
                "cveID": f"CVE-2026-{index + 1000}",
                "vulnerabilityName": "Product vulnerability",
                "shortDescription": "<b>Description</b>",
                "dateAdded": "2026-10-20", "dueDate": "2026-11-03",
                "vendorProject": "Vendor", "product": "Product",
            }
            for index in range(305)
        ]}).encode()
        result = parse_kev(payload)
        self.assertEqual(300, len(result.items))
        self.assertEqual(305, len(result.known_exploited_cve_ids))
        self.assertEqual("unknown", result.items[0].severity)
        self.assertIsNone(result.items[0].cvss_score)
        self.assertEqual("2026-11-03", result.items[0].due_date)
        self.assertEqual("Description", result.items[0].summary)

    def test_nvd_uses_real_cvss_and_excludes_rejected_cves(self) -> None:
        payload = json.dumps({"vulnerabilities": [
            {"cve": {
                "id": "CVE-2026-1234", "published": "2026-10-20T08:30:00.000",
                "lastModified": "2026-10-20T10:30:00.000",
                "descriptions": [{"lang": "en", "value": "A vulnerability"}],
                "metrics": {"cvssMetricV31": [{"type": "Primary", "cvssData": {
                    "version": "3.1", "baseScore": 9.8, "baseSeverity": "CRITICAL",
                }}]},
            }},
            {"cve": {"id": "CVE-2026-1235", "vulnStatus": "Rejected"}},
            {"cve": {"id": "CVE-2026-1236"}},
        ]}).encode()
        result = parse_nvd(payload)
        self.assertEqual(2, len(result.items))
        item = result.items[0]
        self.assertEqual("critical", item.severity)
        self.assertEqual(9.8, item.cvss_score)
        self.assertEqual("3.1", item.cvss_version)
        self.assertEqual("unknown", result.items[1].severity)
        self.assertIsNotNone(item.published_at.tzinfo)

    def test_cvss_prefers_primary_and_newest_valid_version(self) -> None:
        self.assertEqual(("high", 8.1, "4.0"), cvss_details({
            "cvssMetricV40": [
                {"type": "Secondary", "cvssData": {"baseScore": 9.9, "baseSeverity": "CRITICAL", "version": "4.0"}},
                {"type": "Primary", "cvssData": {"baseScore": 8.1, "baseSeverity": "HIGH", "version": "4.0"}},
            ],
            "cvssMetricV31": [{"cvssData": {"baseScore": 5.0, "version": "3.1"}}],
        }))
        for score in (True, float("nan"), float("inf"), -1, 11, "9.8"):
            self.assertEqual(("unknown", None, None), cvss_details({"cvssMetricV31": [{"cvssData": {"baseScore": score}}]}))
        self.assertEqual(("unknown", 5.0, "3.1"), cvss_details({"cvssMetricV31": [{"cvssData": {"baseScore": 5.0, "version": "3.1"}}]}))

    def test_rss_handles_korean_empty_summary_invalid_links_and_duplicates(self) -> None:
        payload = """<rss><channel>
          <item><title> 취약점 CVE-2026-1234 </title><link> https://www.boho.or.kr/detail?x=1&amp;y=2 </link><pubDate>2026-10-20</pubDate></item>
          <item><title> 취약점 CVE-2026-1234 </title><link> https://www.boho.or.kr/detail?x=1&amp;y=2 </link><pubDate>2026-10-20</pubDate></item>
          <item><title>Bad link</title><link>javascript:alert(1)</link></item>
        </channel></rss>""".encode()
        result = parse_feed(payload, SOURCES[2])
        self.assertEqual(1, len(result.items))
        self.assertEqual("", result.items[0].summary)
        self.assertEqual(("CVE-2026-1234",), result.items[0].cve_ids)
        self.assertEqual("https://www.boho.or.kr/detail?x=1&y=2", result.items[0].url)

    def test_rss_html_is_plain_text_without_script_or_style_content(self) -> None:
        payload = b"""<rss><channel><item><title>News</title><link>https://example.com/</link>
        <description><![CDATA[<p>Safe <b>news</b></p><script>alert('bad')</script><img src="track"><style>evil</style>]]></description>
        <pubDate>Tue, 20 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>"""
        item = parse_feed(payload, SOURCES[4]).items[0]
        self.assertEqual("Safe news", item.summary)
        self.assertEqual(2026, item.published_at.year)
        self.assertEqual("one two", plain_text("<p>one</p><p>two</p>"))

    def test_article_description_wins_over_media_alternative_text(self) -> None:
        payload = b"""<rss xmlns:media="http://search.yahoo.com/mrss/"><channel><item>
        <title>Article</title><link>https://blog.google/security/test/</link>
        <media:description>Image alternative text</media:description>
        <description><![CDATA[<p>Actual article summary</p>]]></description>
        </item></channel></rss>"""
        self.assertEqual("Actual article summary", parse_feed(payload, SOURCES[4]).items[0].summary)

    def test_cve_references_remain_searchable_after_summary_shortening(self) -> None:
        payload = (
            '<rss><channel><item><title>Advisory</title><link>https://example.com/</link>'
            '<description>' + "Details " * 120 + 'CVE-2026-9876</description></item></channel></rss>'
        ).encode()
        item = parse_feed(payload, SOURCES[3]).items[0]
        self.assertEqual(600, len(item.summary))
        self.assertEqual(("CVE-2026-9876",), item.cve_ids)

    def test_xml_entities_and_html_error_documents_are_rejected(self) -> None:
        with self.assertRaises(DTDForbidden):
            parse_feed(b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss><channel>&x;</channel></rss>', SOURCES[2])
        with self.assertRaises(ValueError):
            parse_feed(b"<html><body>Access denied</body></html>", SOURCES[2])

    def test_atom_links_and_updated_dates_are_supported(self) -> None:
        payload = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Advisory</title>
        <id>one</id><link href="https://example.com/a"/><updated>2026-10-20T09:00:00Z</updated></entry></feed>"""
        item = parse_feed(payload, SOURCES[3]).items[0]
        self.assertEqual("https://example.com/a", item.url)
        self.assertIsNone(item.published_at)
        self.assertEqual(9, item.updated_at.hour)

    def test_invalid_dates_and_unsafe_urls_are_not_invented(self) -> None:
        for value in ("", "not a date", None):
            self.assertIsNone(parse_date(value))
        for value in ("javascript:alert(1)", "//example.com", "https://user:pass@example.com", "https://example.com:bad", "https://example.com\\evil", "https://example.com\nx"):
            self.assertIsNone(safe_url(value))
        self.assertEqual("https://example.com/", safe_url(" https://example.com/ "))


class SecurityNewsHttpTest(unittest.IsolatedAsyncioTestCase):
    async def test_nvd_fetches_latest_tail_with_fixed_window_and_request_gap(self) -> None:
        requests: list[httpx.Request] = []

        def handle(request):
            requests.append(request)
            if request.url.params.get("resultsPerPage") == "1":
                return httpx.Response(200, json={"totalResults": 5356, "vulnerabilities": []})
            return httpx.Response(200, json={"totalResults": 5356, "vulnerabilities": [{"cve": {"id": "CVE-2026-9999"}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            source = PublicSecurityNewsSource(client)
            with patch("src.infrastructure.external.security_news_source.asyncio.sleep", new_callable=AsyncMock) as sleep:
                result = await source.fetch("nvd")
            self.assertEqual(2, len(requests))
            self.assertEqual("5156", requests[1].url.params["startIndex"])
            self.assertEqual("200", requests[1].url.params["resultsPerPage"])
            self.assertEqual(requests[0].url.params["pubEndDate"], requests[1].url.params["pubEndDate"])
            sleep.assert_awaited_once_with(6)
            self.assertEqual(("CVE-2026-9999",), result.items[0].cve_ids)
            await source.aclose()
            self.assertFalse(client.is_closed)

    async def test_unknown_source_and_oversized_body_are_rejected(self) -> None:
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(200, content=b"x" * 32)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            source = PublicSecurityNewsSource(client)
            with self.assertRaises(ValueError):
                await source.fetch("https://localhost/private")
            self.assertEqual([], requests)
            with patch("src.infrastructure.external.security_news_source.MAX_RESPONSE_BYTES", 16):
                with self.assertRaisesRegex(ValueError, "too large"):
                    await source.fetch("kisa")
            self.assertEqual(ENDPOINTS["kisa"], str(requests[0].url))

    async def test_redirects_and_provider_failures_do_not_become_empty_successes(self) -> None:
        for status in (302, 403, 429, 503):
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(status, headers={"Location": "http://localhost/private"})
            )) as client:
                with self.assertRaises(httpx.HTTPStatusError):
                    await PublicSecurityNewsSource(client).fetch("kisa")

    async def test_overall_deadline_cancels_a_slow_source(self) -> None:
        cancelled = asyncio.Event()

        async def read(url, *, params=None):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        async with httpx.AsyncClient() as client:
            source = PublicSecurityNewsSource(client)
            with (
                patch.object(source, "_read_response", side_effect=read),
                patch("src.infrastructure.external.security_news_source.SOURCE_TIMEOUT_SECONDS", 0.01),
            ):
                with self.assertRaises(TimeoutError):
                    await source.fetch("kisa")
            self.assertTrue(cancelled.is_set())
