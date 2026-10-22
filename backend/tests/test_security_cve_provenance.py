# backend/tests/test_security_cve_provenance.py
import json
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

from src.domain.entities.security_news import SecurityCveRemediation, SecurityNewsItem, SecurityNewsSourceResult, SecurityNewsStoredSnapshot
from src.infrastructure.external.security_cve_provenance import manufacturer_remediations
from src.infrastructure.external.security_news_source import PublicSecurityNewsSource, parse_kev, parse_nvd
from src.infrastructure.persistence.security_news_snapshot_store import SqliteSecurityNewsSnapshotStore, _decode
from src.presentation.schemas.security_news import SecurityNewsItemResponse
from tests.test_security_cve_remediation import TOMCAT_DESCRIPTION, configurations, cpe


NVD_URL = "https://nvd.nist.gov/vuln/detail/CVE-2026-34486"
VENDOR_URL = "https://lists.apache.org/thread/official-advisory"
SOURCE = "security@apache.org"
REFERENCES = [{"url": VENDOR_URL, "source": SOURCE, "tags": ["Vendor Advisory"]}]
ROW = SecurityCveRemediation("tomcat", "11.0.20", "apache", "11.0.21", NVD_URL, "description", "11.0")


class CveRemediationProvenanceTest(unittest.TestCase):
    def test_manufacturer_publisher_product_and_official_reference_are_required(self):
        row, = manufacturer_remediations((ROW,), SOURCE, REFERENCES)
        self.assertEqual("vendor", row.fixed_version_basis)
        self.assertEqual(VENDOR_URL, row.reference_url)
        self.assertEqual("11.0", row.fixed_version_branch)
        prefixed = replace(ROW, vendor=None, product="Apache Tomcat")
        self.assertEqual("vendor", manufacturer_remediations((prefixed,), SOURCE, REFERENCES)[0].fixed_version_basis)

    def test_advisory_tag_or_email_alone_cannot_confirm_manufacturer(self):
        for source, refs, row in (
            ("nvd@nist.gov", REFERENCES, ROW),
            (SOURCE, [], ROW),
            (SOURCE, [{**REFERENCES[0], "tags": ["Third Party Advisory"]}], ROW),
            (SOURCE, [{**REFERENCES[0], "source": "other@apache.org"}], ROW),
            (SOURCE, REFERENCES, replace(ROW, vendor="another vendor")),
            (SOURCE, REFERENCES, replace(ROW, vendor=None, product="unrelated library")),
            ("reporter@example.org", [{"url": "https://example.org/fix", "source": "reporter@example.org", "tags": ["Vendor Advisory"]}], ROW),
        ):
            with self.subTest(source=source, refs=refs, row=row):
                self.assertEqual((row,), manufacturer_remediations((row,), source, refs))

    def test_untrusted_or_invalid_reference_urls_do_not_get_vendor_label(self):
        for url in (
            "https://apache.org.evil.example/advisory", "https://evilapache.org/advisory", "javascript:alert(1)",
            "http://lists.apache.org/advisory", "https://user@lists.apache.org/advisory", "https://lists.apache.org:444/advisory",
            "https://lists.apache.org:invalid/advisory", "https://lists.apache.org/with space", "https://[broken/advisory",
        ):
            with self.subTest(url=url):
                self.assertEqual((ROW,), manufacturer_remediations((ROW,), SOURCE, [{**REFERENCES[0], "url": url}]))

    def test_nvd_inference_and_legacy_fixes_are_never_promoted(self):
        for basis in (None, "nvd_range"):
            row = replace(ROW, fixed_version_basis=basis)
            self.assertEqual((row,), manufacturer_remediations((row,), SOURCE, REFERENCES))
        row = replace(ROW, fixed_version=None)
        self.assertEqual((row,), manufacturer_remediations((row,), SOURCE, REFERENCES))

    def test_nvd_parsing_marks_explicit_vendor_fixes_and_retains_other_products(self):
        data = {"vulnerabilities": [{"cve": {
            "id": "CVE-2026-34486", "sourceIdentifier": SOURCE, "references": REFERENCES,
            "descriptions": [{"lang": "en", "value": TOMCAT_DESCRIPTION}],
            "configurations": configurations(cpe(criteria="cpe:2.3:a:apache:tomcat:11.0.20:*:*:*:*:*:*:*")),
        }}]}
        item, = parse_nvd(json.dumps(data).encode()).items
        self.assertEqual(3, len(item.remediations))
        self.assertEqual({"vendor"}, {row.fixed_version_basis for row in item.remediations})
        self.assertEqual({VENDOR_URL}, {row.reference_url for row in item.remediations})


class CveRemediationProvenancePersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_new_basis_roundtrips_and_legacy_fix_remains_unverified(self):
        item = SecurityNewsItem("nvd:id", "nvd", "cve", "CVE", "", NVD_URL, remediations=(ROW, replace(ROW, fixed_version_basis="nvd_range")))
        snapshot = SecurityNewsStoredSnapshot((("nvd", SecurityNewsSourceResult((item,))),), (), (), None, None, True)
        with tempfile.TemporaryDirectory() as directory:
            store = SqliteSecurityNewsSnapshotStore(str(Path(directory) / "snapshot.sqlite3"))
            try:
                await store.save(snapshot)
                self.assertEqual(snapshot, await store.load())
            finally:
                await store.aclose()
        payload = SecurityNewsItemResponse.model_validate(item).model_dump(mode="json")
        self.assertEqual("nvd_range", payload["remediations"][1]["fixed_version_basis"])
        value = asdict(snapshot)
        value["results"][0][1]["known_exploited_cve_ids"] = []
        for remediation in value["results"][0][1]["items"][0]["remediations"]:
            remediation.pop("fixed_version_basis")
            remediation.pop("fixed_version_branch")
        restored = _decode(json.dumps({"version": 1, "snapshot": value}))
        self.assertTrue(all(row.fixed_version_basis is None and row.fixed_version_branch is None for row in restored.results[0][1].items[0].remediations))

    async def test_kev_enrichment_preserves_nvd_basis_and_branch(self):
        payload = {"vulnerabilities": [{"cve": {"id": "CVE-2026-34486", "sourceIdentifier": SOURCE,
            "references": REFERENCES, "descriptions": [{"lang": "en", "value": TOMCAT_DESCRIPTION}]}}], "totalResults": 1, "startIndex": 0}
        kev = parse_kev(json.dumps({"vulnerabilities": [{"cveID": "CVE-2026-34486", "vendorProject": "Apache", "product": "Tomcat", "vulnerabilityName": "Tomcat issue", "shortDescription": "An issue", "dateAdded": "2026-08-04"}]}).encode())
        port = PublicSecurityNewsSource()
        async def read(params):
            return json.dumps(payload).encode()
        port._read_nvd = read
        try:
            enriched = await port._enrich_kev(kev)
        finally:
            await port.aclose()
        self.assertEqual({"vendor"}, {row.fixed_version_basis for row in enriched.items[0].remediations})
        self.assertEqual({"11.0", "10.1", "9.0"}, {row.fixed_version_branch for row in enriched.items[0].remediations})
