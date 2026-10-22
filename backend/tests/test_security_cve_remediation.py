# backend/tests/test_security_cve_remediation.py
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from src.domain.entities.security_news import SecurityCveRemediation, SecurityNewsItem, SecurityNewsSourceResult, SecurityNewsStoredSnapshot
from src.infrastructure.external.security_cve_remediation import cve_remediations
from src.infrastructure.external.security_news_source import parse_kev, parse_nvd
from src.infrastructure.persistence.security_news_snapshot_store import SqliteSecurityNewsSnapshotStore, _decode
from src.presentation.schemas.security_news import SecurityNewsItemResponse


URL = "https://nvd.nist.gov/vuln/detail/CVE-2026-1234"


def configurations(*matches):
    return [{"nodes": [{"operator": "OR", "cpeMatch": list(matches)}]}]


def cpe(product="library", **values):
    return {"vulnerable": True, "criteria": f"cpe:2.3:a:vendor:{product}:*:*:*:*:*:*:*:*", **values}


class CveRemediationParsingTest(unittest.TestCase):
    def test_inclusive_exclusive_ranges_do_not_claim_fixed_version(self):
        rows = cve_remediations(configurations(
            cpe(versionStartIncluding="1.0", versionEndExcluding="1.5"),
            cpe(versionStartExcluding="2.0", versionEndIncluding="2.5"),
        ), "An issue was reported.", URL)
        self.assertEqual([">= 1.0, < 1.5", "> 2.0, <= 2.5"], [row.affected_versions for row in rows])
        self.assertTrue(all(row.fixed_version is None for row in rows))

    def test_environment_and_negated_nodes_are_excluded(self):
        rows = cve_remediations([{"nodes": [
            {"cpeMatch": [cpe(vulnerable=False), cpe()]},
            {"negate": True, "children": [{"cpeMatch": [cpe("excluded")]}]},
        ]}], "", URL)
        self.assertEqual(["library"], [row.product for row in rows])

    def test_escaped_cpe_and_exact_update_are_preserved_and_deduplicated(self):
        match = cpe(criteria=r"cpe:2.3:a:acme:library\:core:1.2.3:sp1:*:*:*:*:*:*")
        rows = cve_remediations(configurations(match, match), "", URL)
        self.assertEqual(1, len(rows))
        self.assertEqual("library:core", rows[0].product)
        self.assertEqual("1.2.3 (sp1)", rows[0].affected_versions)

    def test_explicit_single_product_fix_uses_full_description(self):
        description = "Library versions before 1.2.3 allow a crash. " + "Details. " * 200 + "This vulnerability is fixed in version 1.2.3."
        payload = json.dumps({"vulnerabilities": [{"cve": {
            "id": "CVE-2026-1234", "descriptions": [{"lang": "en", "value": description}],
            "configurations": configurations(cpe(versionEndExcluding="1.2.3")),
        }}]}).encode()
        item = parse_nvd(payload).items[0]
        self.assertEqual(1200, len(item.summary))
        self.assertEqual("1.2.3", item.remediations[0].fixed_version)
        self.assertEqual(URL, item.remediations[0].reference_url)

    def test_unanalyzed_description_can_supply_product_range_and_fix(self):
        rows = cve_remediations(None, "Example Library prior to 3.2.1 allows a crash. This issue was patched in 3.2.1.", URL)
        self.assertEqual("Example Library", rows[0].product)
        self.assertEqual("< 3.2.1", rows[0].affected_versions)
        self.assertEqual("3.2.1", rows[0].fixed_version)

    def test_multiple_products_branches_and_other_product_fixes_stay_unknown(self):
        for config, description in (
            (configurations(cpe(), cpe("other")), "Library before 1.2.3 is affected. This issue is fixed in 1.2.3."),
            (configurations(cpe(versionEndExcluding="1.2"), cpe(versionStartIncluding="2.0", versionEndExcluding="2.1")), "Library before 1.2 is affected. This issue is fixed in 1.2."),
            (configurations(cpe()), "Other before 1.2.3 is affected. This issue is fixed in 1.2.3."),
            (configurations(cpe()), "Library before 1.2.3 is affected. This issue is fixed in 1.2.3 and 2.3.4."),
            (configurations(cpe()), "Library before 1.2.3 is affected. This issue is not fixed in 1.2.3."),
            (configurations(cpe()), "Library before 1.2.3 is affected. Other versions before 4.0 have a separate flaw. This issue is fixed in 4.0."),
            (configurations(cpe()), "Library before 2.0 contains a flaw. Addon 3.0 has another issue. This issue is fixed in version 3.1."),
            (configurations(cpe()), "Library through 1.2.3 is affected. This issue is fixed in 1.2.3."),
        ):
            with self.subTest(description=description):
                self.assertTrue(all(row.fixed_version is None for row in cve_remediations(config, description, URL)))

    def test_kev_has_product_fallback_and_keeps_exploitation_flag(self):
        payload = json.dumps({"vulnerabilities": [{
            "cveID": "CVE-2026-1234", "product": "Library", "vendorProject": "Acme",
            "shortDescription": "A vulnerability is being exploited.",
        }]}).encode()
        item = parse_kev(payload).items[0]
        self.assertTrue(item.known_exploited)
        self.assertEqual("Library", item.remediations[0].product)
        self.assertEqual("Acme", item.remediations[0].vendor)
        self.assertEqual("버전 확인 필요", item.remediations[0].affected_versions)
        self.assertIsNone(item.remediations[0].fixed_version)

    def test_malformed_and_unidentified_sources_do_not_invent_a_product(self):
        for config in (None, {}, [None], configurations(cpe(criteria="broken")), configurations(cpe(criteria="cpe:2.3:a:*:*:*:*:*:*:*:*:*:*"))):
            self.assertEqual((), cve_remediations(config, "A vulnerability affects software.", URL))


class CveRemediationPersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_roundtrip_schema_and_legacy_snapshot(self):
        remediation = SecurityCveRemediation("Library", "< 1.2.3", "Acme", "1.2.3", URL)
        item = SecurityNewsItem("id", "nvd", "cve", "Title", "Summary", URL, remediations=(remediation,))
        snapshot = SecurityNewsStoredSnapshot((("nvd", SecurityNewsSourceResult((item,))),), (), (), None, None, True)
        with tempfile.TemporaryDirectory() as directory:
            store = SqliteSecurityNewsSnapshotStore(str(Path(directory) / "snapshot.sqlite3"))
            try:
                await store.save(snapshot)
                self.assertEqual(snapshot, await store.load())
            finally:
                await store.aclose()
        self.assertEqual([asdict(remediation)], SecurityNewsItemResponse.model_validate(item).model_dump(mode="json")["remediations"])
        value = asdict(snapshot)
        value["results"][0][1]["items"][0].pop("remediations")
        value["results"][0][1]["known_exploited_cve_ids"] = []
        legacy = _decode(json.dumps({"version": 1, "snapshot": value}))
        self.assertEqual((), legacy.results[0][1].items[0].remediations)
