# backend/tests/test_cve_inventory_source.py
import json
import unittest
from dataclasses import replace

import httpx

from src.domain.entities.cve_inventory import CveInventoryPackage
from src.infrastructure.external.osv_inventory_source import OsvInventorySource, cvss_details, parse_osv_records


def package():
    return CveInventoryPackage("package-one", "example", "npm", ("1.0.0",), query_name="example", query_ecosystem="npm")


def advisory(identifier="GHSA-aaaa-bbbb-cccc", cve="CVE-2026-12345", fixed="2.0.0"):
    return {
        "id": identifier, "aliases": [cve] if cve else [], "summary": "Package vulnerability",
        "published": "2026-01-01T00:00:00Z", "modified": "2026-02-01T00:00:00Z",
        "database_specific": {"severity": "HIGH"},
        "affected": [{"package": {"name": "example", "ecosystem": "npm"}, "ranges": [
            {"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": fixed}]},
        ]}],
        "references": [{"type": "ADVISORY", "url": "https://example.com/advisory"}],
    }


class OsvInventorySourceTest(unittest.IsolatedAsyncioTestCase):
    async def test_queries_all_versions_follows_every_page_and_checks_inventory_separately(self):
        requests = []

        def handler(request):
            value = json.loads(request.content)
            requests.append(value)
            if "version" in value:
                return httpx.Response(200, json={})
            if "page_token" not in value:
                return httpx.Response(200, json={"next_page_token": "next"})
            return httpx.Response(200, json={"vulns": [advisory(), advisory("GHSA-no-cve", None)]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = OsvInventorySource(client)
            findings = await source.fetch(package())
        self.assertEqual(3, len(requests))
        self.assertNotIn("version", requests[0])
        self.assertEqual("next", requests[1]["page_token"])
        self.assertEqual("1.0.0", requests[2]["version"])
        self.assertEqual(1, len(findings))
        self.assertEqual("not_affected", findings[0].inventory_impact)
        self.assertEqual("CVE-2026-12345", findings[0].cve_id)
        self.assertEqual(("2.0.0",), findings[0].fixed_versions)

    async def test_repeated_pagination_token_fails_instead_of_returning_partial_data(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, json={"vulns": [advisory()], "next_page_token": "same"},
        ))) as client:
            with self.assertRaisesRegex(ValueError, "pagination"):
                await OsvInventorySource(client).fetch(package())

    async def test_uncertain_inventory_versions_are_never_queried_as_confirmed(self):
        requests = []

        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"vulns": [advisory()]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            findings = await OsvInventorySource(client).fetch(replace(package(), version_confidence="mixed"))
        self.assertEqual(1, len(requests))
        self.assertEqual("unknown", findings[0].inventory_impact)

    async def test_inventory_lookup_failure_preserves_package_cves_as_unknown(self):
        def handler(request):
            value = json.loads(request.content)
            return httpx.Response(400, json={"error": "Invalid version"}) if "version" in value else httpx.Response(200, json={"vulns": [advisory()]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            findings = await OsvInventorySource(client).fetch(package())
        self.assertEqual(1, len(findings))
        self.assertEqual("unknown", findings[0].inventory_impact)

    async def test_all_cves_are_retained_without_recent_window_or_record_limit(self):
        records = [advisory(f"TEST-{number}", f"CVE-2020-{10000 + number}") for number in range(1200)]
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"vulns": records}))) as client:
            findings = await OsvInventorySource(client).fetch(replace(package(), versions=()))
        self.assertEqual(1200, len(findings))

    async def test_incomplete_records_and_invalid_tokens_do_not_become_empty_success(self):
        for document in (
            {"vulns": [{"id": "GHSA-aaaa-bbbb-cccc", "aliases": ["CVE-2026-12345"]}]},
            {"vulns": [], "next_page_token": 0},
            {"vulns": [], "next_page_token": False},
            {"vulns": [], "next_page_token": []},
        ):
            with self.subTest(document=document):
                async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=document))) as client:
                    with self.assertRaises(ValueError):
                        await OsvInventorySource(client).fetch(package())

    async def test_partial_kev_response_is_unknown_instead_of_clearing_exploitation(self):
        for document in (
            {"count": 2, "vulnerabilities": [{"cveID": "CVE-2026-12345"}]},
            {"count": 2, "vulnerabilities": [{"cveID": "CVE-2026-12345"}, {"cveID": "invalid"}]},
        ):
            with self.subTest(document=document):
                async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=document))) as client:
                    self.assertIsNone(await OsvInventorySource(client).begin_refresh())

    def test_duplicate_alias_records_preserve_fix_branches(self):
        first = advisory(fixed="1.2.3")
        second = advisory("PYSEC-2026-123", fixed="2.3.4")
        second["affected"][0]["ranges"][0]["events"][0] = {"introduced": "2.0.0"}
        rows = parse_osv_records((first, second), package())
        self.assertEqual(1, len(rows))
        self.assertEqual(("1.2.3", "2.3.4"), rows[0].fixed_versions)
        self.assertEqual(("< 1.2.3", ">= 2.0.0, < 2.3.4"), rows[0].affected_versions)

    def test_unrelated_packages_withdrawn_records_and_non_cve_advisories_are_excluded(self):
        wrong = advisory()
        wrong["affected"][0]["package"]["name"] = "another-package"
        withdrawn = advisory()
        withdrawn["withdrawn"] = "2026-02-01T00:00:00Z"
        self.assertEqual((), parse_osv_records((wrong, withdrawn, advisory(cve=None)), package()))

    def test_range_limit_and_git_hash_are_not_claimed_as_fixed_package_versions(self):
        record = advisory()
        record["affected"][0]["ranges"] = [
            {"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"limit": "2.0.0"}]},
            {"type": "GIT", "events": [{"introduced": "abc123"}, {"fixed": "def456"}]},
        ]
        result = parse_osv_records((record,), package())[0]
        self.assertEqual((), result.fixed_versions)
        self.assertEqual(2, len(result.ranges))
        self.assertIsNone(result.ranges[0].fixed)

    def test_cvss_scores_use_standard_vector_calculation(self):
        value = {"severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}]}
        self.assertEqual(("critical", 9.8, "3.1", "OSV CVSS"), cvss_details(value))
        self.assertEqual("unknown", cvss_details({})[0])
