# backend/tests/test_java_zulu.py
import json
import unittest

from src.infrastructure.external.java_zulu import ZULU_TARGET, _read_catalog, compare_zulu_versions, validate_zulu, zulu_coverage_note, zulu_matcher


def build(version, channel="psu"):
    return {"zulu": version, "jdk": "17.0.21+9", "type": channel}


def record(cve, versions, notes=()):
    return {"cve": cve, "zulu_versions": versions, "baseScore": 8.1, "notes": list(notes)}


def release(cves):
    return {"release": "26_10", "date": "2026-10-20", "description": "October release", "cves": cves,
            "notes": {"1": "Our analysis shows that Azul Zulu and OpenJDK are not affected by CVE-2026-9999."}}


class ZuluCveTest(unittest.TestCase):
    def test_vendor_build_notation_is_distinct_from_java_runtime_version(self):
        self.assertEqual(validate_zulu("Zulu11.58+23-CA"), 11)
        self.assertEqual(compare_zulu_versions("Zulu11.58+23-CA", "11.58.23"), 0)
        self.assertGreater(compare_zulu_versions("11.58.23", "11.58.9"), 0)
        for value in ("17.0.21", "1.8.0_402", "8u402", "11.58.23-FIPS", "17"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_zulu(value)

    def test_same_train_backport_and_cpu_psu_do_not_mask_precise_fix(self):
        cve = "CVE-2026-12345"
        raw = release([record(cve, [build("17.67.304", "cpu"), build("17.69.114", "cpu"), build("17.70.111")])])
        snapshot = _read_catalog(json.dumps([raw]).encode(), vulnerabilities=True)
        for selected, expected in [("17.69.112", ["17.69.114"]), ("17.69.114", []), ("17.67.304", []),
                                   ("17.70.109", ["17.70.111"]), ("17.70.111", [])]:
            with self.subTest(selected=selected):
                matches = zulu_matcher(ZULU_TARGET, selected, (snapshot,))
                self.assertEqual([a.fixed_version for a in snapshot.advisories if matches(a)], expected)
        self.assertIsNone(zulu_matcher(ZULU_TARGET, "17.99.5", (snapshot,)))

    def test_only_documented_applicable_standard_builds_become_matches(self):
        item = release([record("CVE-2026-1111", [build("17.70.111")]), record("CVE-2026-2222", []),
                        record("CVE-2026-9999", [build("17.70.111")], ["1"])])
        fips = {**release([record("CVE-2026-3333", [build("17.70.112")])]),
                "description": "This release applies only to Azul Zulu FIPS bundles."}
        snapshot = _read_catalog(json.dumps([item, fips]).encode(), vulnerabilities=True)
        self.assertEqual([a.cve_id for a in snapshot.advisories], ["CVE-2026-1111"])

    def test_unpublished_channel_fix_is_explicitly_unknown(self):
        older = {**release([record("CVE-2026-1000", [build("17.70.107")])]), "date": "2026-10-20"}
        newer = {**release([record("CVE-2026-2000", [build("17.69.114", "cpu")])]), "date": "2026-10-24"}
        snapshot = _read_catalog(json.dumps([older, newer]).encode(), vulnerabilities=True)
        self.assertIn("CVE-2026-2000", zulu_coverage_note(ZULU_TARGET, "17.70.107", (snapshot,)))
