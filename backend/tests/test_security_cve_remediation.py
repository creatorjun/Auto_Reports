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
TOMCAT_DESCRIPTION = (
    "Missing Encryption of Sensitive Data vulnerability in Apache Tomcat. "
    "This issue affects Apache Tomcat: 11.0.20, 10.1.53, 9.0.116.\n\n"
    "Users are recommended to upgrade to version 11.0.21, 10.1.54 or 9.0.117, which fix the issue."
)


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

    def test_cve_2026_34486_pairs_explicit_tomcat_versions_by_branch(self):
        payload = json.dumps({"vulnerabilities": [{"cve": {
            "id": "CVE-2026-34486", "descriptions": [{"lang": "en", "value": TOMCAT_DESCRIPTION}],
        }}]}).encode()
        item = parse_nvd(payload).items[0]
        self.assertEqual([
            ("Apache Tomcat", "11.0.20", "11.0.21"),
            ("Apache Tomcat", "10.1.53", "10.1.54"),
            ("Apache Tomcat", "9.0.116", "9.0.117"),
        ], [(row.product, row.affected_versions, row.fixed_version) for row in item.remediations])
        self.assertTrue(all(row.reference_url == "https://nvd.nist.gov/vuln/detail/CVE-2026-34486" for row in item.remediations))

    def test_fix_list_order_does_not_determine_branch_pairing(self):
        description = TOMCAT_DESCRIPTION.replace("11.0.21, 10.1.54 or 9.0.117", "9.0.117, 11.0.21 or 10.1.54")
        rows = cve_remediations(None, description, URL, product="Tomcat", vendor="Apache")
        self.assertEqual(["11.0.21", "10.1.54", "9.0.117"], [row.fixed_version for row in rows])
        self.assertTrue(all(row.product == "Tomcat" and row.vendor == "Apache" for row in rows))

    def test_explicit_same_product_ranges_support_multiple_branches(self):
        rows = cve_remediations(None,
            "This vulnerability affects Example Library: from 3.2.0-beta1 through 3.2.5, from 2.4.0 before 2.4.7. "
            "This vulnerability was fixed in versions 2.4.7 and 3.2.6.", URL)
        self.assertEqual([
            (">= 3.2.0-beta1, <= 3.2.5", "3.2.6"),
            (">= 2.4.0, < 2.4.7", "2.4.7"),
        ], [(row.affected_versions, row.fixed_version) for row in rows])

    def test_cpe_product_identity_prevents_distribution_fix_assignment(self):
        rows = cve_remediations(configurations(
            cpe(criteria="cpe:2.3:a:apache:tomcat:11.0.20:*:*:*:*:*:*:*"),
            cpe(criteria="cpe:2.3:a:apache:tomcat:10.1.53:*:*:*:*:*:*:*"),
            cpe(criteria="cpe:2.3:a:apache:tomcat:9.0.116:*:*:*:*:*:*:*"),
            cpe(criteria="cpe:2.3:o:redhat:enterprise_linux:9.0.116:*:*:*:*:*:*:*"),
            cpe(criteria="cpe:2.3:a:other:tomcat_manager:11.0.20:*:*:*:*:*:*:*"),
        ), TOMCAT_DESCRIPTION, URL)
        self.assertEqual(5, len(rows))
        self.assertEqual(["11.0.21", "10.1.54", "9.0.117", None, None], [row.fixed_version for row in rows])

    def test_inconsistent_fix_lists_and_additional_product_statements_stay_unknown(self):
        for description in (
            TOMCAT_DESCRIPTION.replace("9.0.117", "8.0.117"),
            TOMCAT_DESCRIPTION.replace("9.0.117", "11.0.22"),
            TOMCAT_DESCRIPTION.replace("11.0.21", "11.0.20"),
            TOMCAT_DESCRIPTION.replace("11.0.21", "11.0.19"),
            TOMCAT_DESCRIPTION + " This issue is fixed in version 11.0.22.",
            TOMCAT_DESCRIPTION + " Version 11.0.21 is still affected.",
            TOMCAT_DESCRIPTION + " Another Product 11.0.21 is affected.",
            TOMCAT_DESCRIPTION.replace("which fix the issue", "which do not fix the issue"),
        ):
            with self.subTest(description=description):
                rows = cve_remediations(None, description, URL)
                self.assertEqual(3, len(rows))
                self.assertTrue(all(row.fixed_version is None for row in rows))

    def test_ambiguous_affected_products_and_branches_do_not_invent_fixes(self):
        for description in (
            TOMCAT_DESCRIPTION.replace("Apache Tomcat:", "Apache Tomcat and Another Product:"),
            TOMCAT_DESCRIPTION.replace("11.0.20, 10.1.53, 9.0.116", "11.0.19, 11.0.20, 9.0.116"),
            TOMCAT_DESCRIPTION.replace("11.0.20, 10.1.53, 9.0.116", "from 10.1.53 through 11.0.20, 9.0.116"),
            TOMCAT_DESCRIPTION.replace("11.0.20, 10.1.53, 9.0.116", "from 11.0.22 through 11.0.20, 10.1.53, 9.0.116"),
        ):
            with self.subTest(description=description):
                self.assertTrue(all(row.fixed_version is None for row in cve_remediations(None, description, URL)))

    def test_conflicting_cpe_affected_version_blocks_that_branch_fix(self):
        rows = cve_remediations(configurations(
            cpe(criteria="cpe:2.3:a:apache:tomcat:11.0.22:*:*:*:*:*:*:*"),
        ), TOMCAT_DESCRIPTION, URL)
        self.assertEqual([("11.0.22", None), ("10.1.53", "10.1.54"), ("9.0.116", "9.0.117")],
                         [(row.affected_versions, row.fixed_version) for row in rows])

    def test_explicit_description_fixes_can_enrich_matching_cpe_branch_ranges(self):
        rows = cve_remediations(configurations(
            cpe(criteria="cpe:2.3:a:apache:tomcat:*:*:*:*:*:*:*:*", versionStartIncluding="11.0.0", versionEndExcluding="11.0.21"),
        ), TOMCAT_DESCRIPTION, URL)
        self.assertEqual(">= 11.0.0, < 11.0.21", rows[0].affected_versions)
        self.assertEqual("11.0.21", rows[0].fixed_version)
        self.assertEqual(3, len(rows))

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
