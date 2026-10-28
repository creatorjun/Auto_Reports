# backend/tests/test_cve_inventory_loader.py
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.persistence.cve_inventory_loader import JsonCveInventoryLoader, parse_cve_inventory


def target(identifier="t1", *, version="1.0", coordinates="org.example:library", status="confirmed"):
    return dict(id=identifier, product_id="p1", name="library", ecosystem="Java", current_version=version,
                display_version=version or "미확인", version_status=status,
                identifiers=dict(maven_coordinates=coordinates, maven_group_id=None, maven_artifact_id=None, npm_name=None),
                matching=dict(route="identity_mapping_required", query_ready=False, review_reasons=["version_unknown"]), rpm=None)


def payload(*targets):
    return dict(schema_version="1.0.0", dataset_id="test-source", snapshot_at="2026-10-22T15:04:43+09:00",
                environment=dict(runtime_loading_verified=False, host="private-host", application_root="/private"),
                products={"p1": dict(id="p1", name="Example", category="Java 라이브러리", target_ids=[row["id"] for row in targets])},
                targets={row["id"]: row for row in targets})


def parse(data):
    return parse_cve_inventory(json.dumps(data).encode())


class InventoryLoaderTest(unittest.TestCase):
    def test_all_versions_maps_verified_identity_even_without_known_version(self):
        inventory = parse(payload(target(version=None, status="unknown")))
        package, = inventory.packages
        self.assertEqual(("osv", "Maven", "org.example:library", "ready"), (package.source, package.query_ecosystem, package.query_name, package.mapping_status))
        self.assertEqual("unknown", package.version_confidence)
        self.assertEqual(("미확인",), package.versions)

    def test_deduplication_preserves_every_target_and_conflicting_version_evidence(self):
        inventory = parse(payload(target(), target("t2", version="1.0 / 2.0", status="conflicting")))
        package, = inventory.packages
        self.assertEqual(2, inventory.target_count)
        self.assertEqual(("t1", "t2"), package.target_ids)
        self.assertEqual("mixed", package.version_confidence)
        self.assertEqual(("1.0", "1.0 / 2.0"), package.versions)

    def test_unmapped_package_is_retained_and_untrusted_query_is_not_forwarded(self):
        row = target(coordinates=None)
        row["matching"].update(query_ready=True, osv_query={"package": {"ecosystem": "Maven", "name": "unverified:guess"}, "url": "https://attacker.invalid"})
        package, = parse(payload(row)).packages
        self.assertEqual(("unmapped", "mapping_required", None), (package.source, package.mapping_status, package.query_name))
        self.assertEqual(("t1",), package.target_ids)

    def test_conflicting_coordinates_do_not_create_a_false_identity(self):
        row = target()
        row["identifiers"]["maven_group_id"] = "different"
        self.assertEqual("unmapped", parse(payload(row)).packages[0].source)

    def test_notice_is_not_promoted_to_an_independent_package(self):
        row = target()
        row["matching"]["route"] = "parent_product_advisory"
        self.assertEqual("unmapped", parse(payload(row)).packages[0].source)

    def test_exact_same_product_artifact_identity_can_be_shared_without_version_certainty(self):
        known, missing = target(), target("t2", coordinates=None, version="0.9")
        known["identifiers"]["maven_artifact_id"] = "library"
        missing["identifiers"]["maven_artifact_id"] = "library"
        package, = parse(payload(known, missing)).packages
        self.assertEqual(("t1", "t2"), package.target_ids)
        self.assertEqual("same_product_exact_artifact_identity", package.mapping_reason)
        self.assertEqual("mixed", package.version_confidence)

    def test_ambiguous_sibling_coordinate_does_not_map_a_missing_identity(self):
        first = target()
        second = target("t2", coordinates="other.group:library")
        missing = target("t3", coordinates=None)
        for row in (first, second, missing):
            row["identifiers"]["maven_artifact_id"] = "library"
        result = parse(payload(first, second, missing))
        self.assertEqual(1, sum(p.source == "unmapped" for p in result.packages))

    def test_rpm_keeps_epoch_release_distribution_and_missing_vendor(self):
        row = target(coordinates=None)
        row.update(name="openssl-libs", ecosystem="RPM", rpm=dict(package_name="openssl-libs", epoch="1", version="1.1.1k", release="14.el8", evr="1:1.1.1k-14.el8", architecture="x86_64", distribution_id="ol", distribution_version="8.10", package_vendor=None))
        row["matching"]["route"] = "distribution_vendor_advisory"
        package, = parse(payload(row)).packages
        self.assertEqual(("oracle", "openssl-libs", "ol", "8"), (package.source, package.query_name, package.distribution_id, package.distribution_version))
        self.assertEqual(("1:1.1.1k-14.el8",), package.versions)
        self.assertIsNone(package.rpm_vendor)

    def test_only_exact_installed_uek_identity_links_the_running_kernel(self):
        rpm = target(coordinates=None)
        rpm.update(name="kernel-uek", ecosystem="RPM", rpm=dict(package_name="kernel-uek", version="5.15.0", release="206.el8uek", evr="0:5.15.0-206.el8uek", architecture="x86_64", distribution_id="ol", distribution_version="8.10", package_vendor=None))
        rpm["matching"]["route"] = "distribution_vendor_advisory"
        kernel = target("t2", coordinates=None, version="5.15.0-206.el8uek.x86_64")
        kernel["identifiers"]["source_identifier"] = "kernel:uname-r"
        kernel["matching"]["route"] = "vendor_advisory"
        inventory = parse(payload(rpm, kernel))
        self.assertEqual(1, len(inventory.packages))
        self.assertEqual(("t1", "t2"), inventory.packages[0].target_ids)
        kernel["current_version"] = "5.15.0-999.el8uek.x86_64"
        self.assertEqual(2, len(parse(payload(rpm, kernel)).packages))

    def test_inventory_identity_changes_when_mapping_changes_even_with_same_source_id(self):
        data = payload(target())
        first = parse(data).dataset_id
        data["targets"]["t1"]["identifiers"]["maven_coordinates"] = "org.example:other"
        self.assertNotEqual(first, parse(data).dataset_id)

    def test_private_locations_and_host_are_not_present_in_normalized_packages(self):
        row = target()
        row["locations"] = ["/private/path"]
        row["observations"] = [{"notes": "private-secret"}]
        result = repr(parse(payload(row)))
        for secret in ("private-host", "/private", "private-secret"):
            self.assertNotIn(secret, result)

    def test_rejects_duplicate_keys_wrong_schema_and_broken_links(self):
        with self.assertRaises(ValueError):
            parse_cve_inventory(b'{"schema_version":"1.0.0","schema_version":"2.0.0"}')
        data = payload(target())
        data["schema_version"] = "2.0.0"
        with self.assertRaises(ValueError):
            parse(data)
        data["schema_version"] = "1.0.0"
        data["products"]["p1"]["target_ids"] = []
        with self.assertRaises(ValueError):
            parse(data)

    def test_bounded_async_file_loader(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "inventory.json"
            path.write_text(json.dumps(payload(target())), encoding="utf-8")
            self.assertEqual(1, asyncio.run(JsonCveInventoryLoader(path).load()).target_count)
            with patch("src.infrastructure.persistence.cve_inventory_loader.MAX_INVENTORY_BYTES", 16):
                with self.assertRaises(ValueError):
                    asyncio.run(JsonCveInventoryLoader(path).load())
