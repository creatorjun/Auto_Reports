# backend/tests/test_security_kev_enrichment.py
import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx

from src.application.use_cases.security_news import SecurityNewsUseCase
from src.infrastructure.external.security_news_source import PublicSecurityNewsSource, parse_date


def kev_entry(identifier: str, *, product: str = "Tomcat", vendor: str = "Apache") -> dict:
    return {
        "cveID": identifier,
        "vulnerabilityName": f"{vendor} {product} vulnerability",
        "shortDescription": "The vendor reported exploitation of this vulnerability.",
        "dateAdded": "2026-08-04",
        "dueDate": "2026-08-25",
        "vendorProject": vendor,
        "product": product,
    }


def nvd_entry(identifier: str, *, description: str = "", configurations: list | None = None) -> dict:
    return {"cve": {
        "id": identifier,
        "published": "2026-04-07T08:00:00.000",
        "lastModified": "2026-08-05T10:00:00.000",
        "descriptions": [{"lang": "en", "value": description}],
        "configurations": configurations or [],
        "metrics": {"cvssMetricV31": [{"type": "Primary", "cvssData": {
            "version": "3.1", "baseScore": 8.1, "baseSeverity": "HIGH",
        }}]},
    }}


def nvd_document(entries: list) -> dict:
    return {"startIndex": 0, "totalResults": len(entries), "vulnerabilities": entries}


class SecurityKevEnrichmentTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        interval = patch("src.infrastructure.external.security_news_source.NVD_REQUEST_INTERVAL_SECONDS", 0)
        interval.start()
        self.addCleanup(interval.stop)

    async def test_only_visible_300_details_are_requested_and_all_305_exploited_ids_survive(self) -> None:
        catalog = [kev_entry(f"CVE-2026-{10000 + index}") for index in range(305)]
        requested: list[tuple[str, ...]] = []

        def handle(request):
            if request.url.host == "www.cisa.gov":
                return httpx.Response(200, json={"vulnerabilities": catalog})
            identifiers = tuple(request.url.params["cveIds"].split(","))
            requested.append(identifiers)
            self.assertNotIn("pubStartDate", request.url.params)
            self.assertNotIn("pubEndDate", request.url.params)
            return httpx.Response(200, json=nvd_document([nvd_entry(value) for value in identifiers]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await PublicSecurityNewsSource(client).fetch("cisa-kev")
        visible = {identifier for item in result.items for identifier in item.cve_ids}
        self.assertEqual(300, len(result.items))
        self.assertEqual([100, 100, 100], [len(batch) for batch in requested])
        self.assertEqual(visible, {identifier for batch in requested for identifier in batch})
        self.assertEqual(300, sum(len(batch) for batch in requested))
        self.assertEqual({row["cveID"] for row in catalog}, result.known_exploited_cve_ids)
        self.assertTrue(all(item.known_exploited and item.severity == "high" for item in result.items))

    async def test_details_attach_to_matching_cve_even_when_response_order_is_reversed(self) -> None:
        identifiers = ("CVE-2026-12340", "CVE-2026-12341")
        catalog = [kev_entry(identifiers[0]), kev_entry(identifiers[1], product="Other", vendor="Example")]

        def handle(request):
            if request.url.host == "www.cisa.gov":
                return httpx.Response(200, json={"vulnerabilities": catalog})
            return httpx.Response(200, json=nvd_document([
                nvd_entry(identifiers[0], description="Tomcat before 11.0.21 is affected. This issue is fixed in 11.0.21."),
                nvd_entry(identifiers[1], description="Other before 2.5.3 is affected. This issue is fixed in 2.5.3."),
            ]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await PublicSecurityNewsSource(client).fetch("cisa-kev")
        items = {item.cve_ids[0]: item for item in result.items}
        self.assertEqual("11.0.21", items[identifiers[0]].remediations[0].fixed_version)
        self.assertEqual("2.5.3", items[identifiers[1]].remediations[0].fixed_version)
        for identifier, item in items.items():
            self.assertEqual(f"cisa-kev:{identifier}", item.id)
            self.assertEqual("cisa-kev", item.source_id)
            self.assertEqual("The vendor reported exploitation of this vulnerability.", item.summary)
            self.assertEqual(parse_date("2026-08-04"), item.published_at)
            self.assertEqual(parse_date("2026-08-05T10:00:00.000"), item.updated_at)
            self.assertEqual("2026-08-25", item.due_date)
            self.assertTrue(item.known_exploited)
            self.assertEqual(("high", 8.1, "3.1"), (item.severity, item.cvss_score, item.cvss_version))
            self.assertTrue(all(row.reference_url.endswith(identifier) for row in item.remediations))

    async def test_cve_2026_34486_kev_detail_displays_three_tomcat_version_branches(self) -> None:
        identifier = "CVE-2026-34486"
        description = (
            "Missing Encryption of Sensitive Data vulnerability in Apache Tomcat. "
            "This issue affects Apache Tomcat: 11.0.20, 10.1.53, 9.0.116.\n\n"
            "Users are recommended to upgrade to version 11.0.21, 10.1.54 or 9.0.117, which fix the issue."
        )
        requested = []

        def handle(request):
            if request.url.host == "www.cisa.gov":
                return httpx.Response(200, json={"vulnerabilities": [kev_entry(identifier)]})
            requested.append(request.url.params["cveIds"])
            return httpx.Response(200, json=nvd_document([nvd_entry(identifier, description=description)]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            item = (await PublicSecurityNewsSource(client).fetch("cisa-kev")).items[0]
        self.assertEqual([identifier], requested)
        self.assertEqual("cisa-kev", item.source_id)
        self.assertEqual("Apache", item.vendor)
        self.assertEqual("Tomcat", item.product)
        self.assertEqual([
            ("Apache Tomcat", "11.0.20", "11.0.21"),
            ("Apache Tomcat", "10.1.53", "10.1.54"),
            ("Apache Tomcat", "9.0.116", "9.0.117"),
        ], [(row.product, row.affected_versions, row.fixed_version) for row in item.remediations])
        self.assertTrue(all(row.reference_url == f"https://nvd.nist.gov/vuln/detail/{identifier}" for row in item.remediations))
        self.assertEqual(parse_date("2026-08-04"), item.published_at)
        self.assertTrue(item.known_exploited)
        self.assertIsNone(item.title_ko)
        self.assertIsNone(item.summary_ko)

    async def test_matching_kev_product_excludes_unrelated_distribution_rows(self) -> None:
        identifier = "CVE-2026-12340"
        configurations = [{"nodes": [{"cpeMatch": [
            {"vulnerable": True, "criteria": "cpe:2.3:a:apache:tomcat:11.0.20:*:*:*:*:*:*:*"},
            {"vulnerable": True, "criteria": "cpe:2.3:o:debian:debian_linux:13.0:*:*:*:*:*:*:*"},
        ]}]}]

        def handle(request):
            if request.url.host == "www.cisa.gov":
                return httpx.Response(200, json={"vulnerabilities": [kev_entry(identifier)]})
            return httpx.Response(200, json=nvd_document([nvd_entry(identifier, configurations=configurations)]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            item = (await PublicSecurityNewsSource(client).fetch("cisa-kev")).items[0]
        self.assertEqual(1, len(item.remediations))
        self.assertEqual("tomcat", item.remediations[0].product)
        self.assertEqual("11.0.20", item.remediations[0].affected_versions)
        self.assertIsNone(item.remediations[0].fixed_version)

    async def test_missing_nvd_detail_keeps_kev_product_and_unknown_versions(self) -> None:
        identifier = "CVE-2026-12340"

        def handle(request):
            if request.url.host == "www.cisa.gov":
                return httpx.Response(200, json={"vulnerabilities": [kev_entry(identifier)]})
            return httpx.Response(200, json=nvd_document([]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await PublicSecurityNewsSource(client).fetch("cisa-kev")
        item = result.items[0]
        self.assertEqual(("CVE-2026-12340",), item.cve_ids)
        self.assertEqual("unknown", item.severity)
        self.assertIsNone(item.cvss_score)
        self.assertEqual("Tomcat", item.remediations[0].product)
        self.assertEqual("Apache", item.remediations[0].vendor)
        self.assertEqual("버전 확인 필요", item.remediations[0].affected_versions)
        self.assertIsNone(item.remediations[0].fixed_version)
        self.assertIn("1건", result.warning)
        self.assertEqual(frozenset({identifier}), result.known_exploited_cve_ids)

    async def test_incomplete_or_unrelated_nvd_responses_fail_instead_of_merging(self) -> None:
        identifier = "CVE-2026-12340"
        malformed = (
            None,
            [],
            {"totalResults": 1, "vulnerabilities": []},
            {"totalResults": True, "vulnerabilities": [nvd_entry(identifier)]},
            {"totalResults": -1, "vulnerabilities": []},
            {"totalResults": 1, "vulnerabilities": {}},
            {"totalResults": 1, "vulnerabilities": [{"cve": "bad"}]},
            {"totalResults": 1, "vulnerabilities": [{"cve": {"id": [identifier]}}]},
            {"startIndex": 1, "totalResults": 1, "vulnerabilities": [nvd_entry(identifier)]},
            nvd_document([nvd_entry("CVE-2026-99999")]),
            nvd_document([nvd_entry(identifier), nvd_entry(identifier)]),
        )
        for document in malformed:
            with self.subTest(document=document):
                def handle(request):
                    if request.url.host == "www.cisa.gov":
                        return httpx.Response(200, json={"vulnerabilities": [kev_entry(identifier)]})
                    return httpx.Response(200, content=json.dumps(document).encode())

                async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
                    with self.assertRaises(ValueError):
                        await PublicSecurityNewsSource(client).fetch("cisa-kev")

    async def test_nvd_rate_limit_fails_whole_enrichment_without_partial_result(self) -> None:
        requests = []

        def handle(request):
            if request.url.host == "www.cisa.gov":
                return httpx.Response(200, json={"vulnerabilities": [kev_entry(f"CVE-2026-{10000 + index}") for index in range(101)]})
            requests.append(request)
            if len(requests) == 2:
                return httpx.Response(429, headers={"Retry-After": "30"})
            return httpx.Response(200, json=nvd_document([nvd_entry(value) for value in request.url.params["cveIds"].split(",")]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with self.assertRaises(httpx.HTTPStatusError) as caught:
                await PublicSecurityNewsSource(client).fetch("cisa-kev")
        self.assertEqual(429, caught.exception.response.status_code)
        self.assertEqual(2, len(requests))

    async def test_kev_details_and_recent_nvd_fetch_do_not_overlap_requests(self) -> None:
        entered, release = asyncio.Event(), asyncio.Event()
        active = 0
        maximum = 0
        nvd_calls = []

        async def handle(request):
            nonlocal active, maximum
            if request.url.host == "www.cisa.gov":
                return httpx.Response(200, json={"vulnerabilities": [kev_entry("CVE-2026-12340")]})
            active += 1
            maximum = max(maximum, active)
            nvd_calls.append(request)
            try:
                if "cveIds" in request.url.params:
                    entered.set()
                    await release.wait()
                    return httpx.Response(200, json=nvd_document([nvd_entry("CVE-2026-12340")]))
                return httpx.Response(200, json=nvd_document([]))
            finally:
                active -= 1

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            source = PublicSecurityNewsSource(client)
            kev = asyncio.create_task(source.fetch("cisa-kev"))
            recent = None
            try:
                await asyncio.wait_for(entered.wait(), timeout=1)
                recent = asyncio.create_task(source.fetch("nvd"))
                await asyncio.sleep(0.02)
                self.assertEqual(1, len(nvd_calls))
            finally:
                release.set()
                await asyncio.wait_for(asyncio.gather(*(task for task in (kev, recent) if task is not None)), timeout=1)
        self.assertEqual(1, maximum)
        self.assertEqual(2, len(nvd_calls))

    async def test_cancellation_during_detail_request_allows_following_nvd_fetch(self) -> None:
        entered = asyncio.Event()
        never_release = asyncio.Event()

        async def handle(request):
            if request.url.host == "www.cisa.gov":
                return httpx.Response(200, json={"vulnerabilities": [kev_entry("CVE-2026-12340")]})
            if "cveIds" in request.url.params:
                entered.set()
                await never_release.wait()
            return httpx.Response(200, json=nvd_document([]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            source = PublicSecurityNewsSource(client)
            task = asyncio.create_task(source.fetch("cisa-kev"))
            try:
                await asyncio.wait_for(entered.wait(), timeout=1)
            finally:
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            result = await asyncio.wait_for(source.fetch("nvd"), timeout=1)
        self.assertEqual((), result.items)

    async def test_failed_detail_refresh_keeps_last_successful_remediations_and_timestamp(self) -> None:
        now = datetime(2026, 10, 22, tzinfo=timezone.utc)
        fail_details = False

        def handle(request):
            if request.url.host == "www.cisa.gov":
                return httpx.Response(200, json={"vulnerabilities": [kev_entry("CVE-2026-12340")]})
            if fail_details:
                return httpx.Response(503)
            return httpx.Response(200, json=nvd_document([nvd_entry(
                "CVE-2026-12340", description="Tomcat before 11.0.21 is affected. This issue is fixed in 11.0.21.",
            )]))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            source = PublicSecurityNewsSource(client)
            port = AsyncMock()
            port.sources = tuple(value for value in source.sources if value.id == "cisa-kev")
            port.fetch.side_effect = source.fetch
            use_case = SecurityNewsUseCase(port, clock=lambda: now)
            try:
                await use_case.get_snapshot(refresh=True)
                await use_case._task
                successful = await use_case.get_snapshot()
                self.assertEqual("11.0.21", successful.items[0].remediations[0].fixed_version)
                fail_details = True
                now += timedelta(hours=2)
                with self.assertLogs("src.application.use_cases.security_news", level="WARNING"):
                    await use_case.get_snapshot(refresh=True)
                    await use_case._task
                failed = await use_case.get_snapshot()
                self.assertEqual(successful.items, failed.items)
                self.assertEqual("stale", failed.sources[0].status)
                self.assertEqual(successful.sources[0].last_success_at, failed.sources[0].last_success_at)
                self.assertEqual(2, port.fetch.await_count)
                now += timedelta(seconds=60)
                await use_case.get_snapshot(refresh=True)
                await use_case._task
                self.assertEqual(2, port.fetch.await_count)
            finally:
                await use_case.aclose()


if __name__ == "__main__":
    unittest.main()
