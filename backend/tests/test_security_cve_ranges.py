# backend/tests/test_security_cve_ranges.py
import unittest

from src.infrastructure.external.security_cve_remediation import cve_remediations


URL = "https://nvd.nist.gov/vuln/detail/CVE-2026-1234"


def cpe(product="library", vendor="vendor", version="*", part="a", **bounds):
    return {"vulnerable": True, "criteria": f"cpe:2.3:{part}:{vendor}:{product}:{version}:*:*:*:*:*:*:*", **bounds}


def configuration(*matches):
    return [{"nodes": [{"operator": "OR", "cpeMatch": list(matches)}]}]


class CveRangeResolutionTest(unittest.TestCase):
    def rows(self, *matches, description=""):
        return cve_remediations(configuration(*matches), description, URL)

    def test_excluded_boundary_is_labeled_as_nvd_evidence_and_branch(self):
        row, = self.rows(cpe(versionEndExcluding="1.6.20"))
        self.assertEqual("< 1.6.20", row.affected_versions)
        self.assertEqual(("1.6.20", "nvd_range", "1.6"), (row.fixed_version, row.fixed_version_basis, row.fixed_version_branch))
        self.assertEqual(URL, row.reference_url)

    def test_overlapping_and_disjoint_ranges_use_latest_safe_branch_boundary(self):
        rows = self.rows(
            cpe(versionStartIncluding="1.6.0", versionEndExcluding="1.6.20"),
            cpe(versionStartIncluding="1.6.15", versionEndExcluding="1.6.21"),
            cpe(versionStartIncluding="1.6.30", versionEndExcluding="1.6.40"),
        )
        self.assertEqual(["1.6.40"] * 3, [row.fixed_version for row in rows])

    def test_boundary_order_is_numeric_and_zero_padded(self):
        rows = self.rows(cpe(versionEndExcluding="1.6.9"), cpe(versionEndExcluding="1.6.20.0"))
        self.assertEqual(["1.6.20.0"] * 2, [row.fixed_version for row in rows])

    def test_independent_branches_keep_their_own_safe_targets(self):
        rows = self.rows(
            cpe(versionStartIncluding="1.6.0", versionEndExcluding="1.6.20"),
            cpe(versionStartIncluding="2.1.0", versionEndExcluding="2.1.8"),
        )
        self.assertEqual([("1.6.20", "1.6"), ("2.1.8", "2.1")], [(row.fixed_version, row.fixed_version_branch) for row in rows])

    def test_open_later_branch_does_not_block_an_earlier_closed_branch(self):
        rows = self.rows(cpe(versionEndExcluding="1.6.20"), cpe(versionStartIncluding="2.0.0"))
        self.assertEqual(["1.6.20", None], [row.fixed_version for row in rows])

    def test_later_unbounded_same_branch_blocks_unsafe_inference(self):
        rows = self.rows(cpe(versionEndExcluding="1.6.20"), cpe(versionStartIncluding="1.6.30"))
        self.assertTrue(all(row.fixed_version is None for row in rows))

    def test_inclusive_upper_bound_does_not_invent_the_next_patch(self):
        row, = self.rows(cpe(versionEndIncluding="1.6.20"))
        self.assertIsNone(row.fixed_version)
        self.assertIsNone(row.fixed_version_basis)

    def test_exact_or_inclusive_boundary_conflict_blocks_exclusion_candidate(self):
        for conflicting in (cpe(version="1.6.20"), cpe(versionEndIncluding="1.6.20"), cpe(version="1.6.21")):
            with self.subTest(conflicting=conflicting):
                rows = self.rows(cpe(versionEndExcluding="1.6.20"), conflicting)
                self.assertTrue(all(row.fixed_version is None for row in rows))

    def test_a_later_exclusive_bound_can_cover_an_earlier_inclusive_or_exact_range(self):
        rows = self.rows(cpe(version="1.6.20"), cpe(versionEndIncluding="1.6.21"), cpe(versionEndExcluding="1.6.22"))
        self.assertEqual(["1.6.22"] * 3, [row.fixed_version for row in rows])

    def test_unversioned_and_non_numeric_ranges_block_inference(self):
        for conflicting in (
            cpe(), cpe(version="-"), cpe(version="1.6.20-rc1"),
            cpe(versionStartIncluding="1.6.0-beta1", versionEndExcluding="1.6.25"),
            cpe(versionStartIncluding="unknown", versionEndExcluding="1.6.25"),
            cpe(versionEndExcluding="1.6"), cpe(versionEndExcluding=None),
        ):
            with self.subTest(conflicting=conflicting):
                self.assertTrue(all(row.fixed_version is None for row in self.rows(cpe(versionEndExcluding="1.6.20"), conflicting)))

    def test_invalid_or_contradictory_bounds_block_inference(self):
        for conflicting in (
            cpe(versionStartIncluding="1.6.30", versionEndExcluding="1.6.20"),
            cpe(versionStartIncluding="1.6.20", versionEndExcluding="1.6.20"),
            cpe(versionEndIncluding="1.6.19", versionEndExcluding="1.6.20"),
            cpe(versionStartIncluding="1.6.1", versionStartExcluding="1.6.2", versionEndExcluding="1.6.20"),
            cpe(version="1.6.19", versionEndExcluding="1.6.20"),
        ):
            with self.subTest(conflicting=conflicting):
                self.assertTrue(all(row.fixed_version is None for row in self.rows(cpe(versionEndExcluding="1.6.20"), conflicting)))

    def test_other_vendor_product_and_cpe_part_are_never_merged(self):
        rows = self.rows(
            cpe(versionEndExcluding="1.6.20"),
            cpe(vendor="other", versionEndExcluding="1.6.50"),
            cpe(product="other", versionEndExcluding="1.6.60"),
            cpe(part="o", versionEndExcluding="1.6.70"),
        )
        self.assertEqual(["1.6.20", "1.6.50", "1.6.60", "1.6.70"], [row.fixed_version for row in rows])

    def test_identical_display_rows_with_different_part_identity_are_not_merged_for_inference(self):
        rows = self.rows(cpe(versionEndExcluding="1.6.20"), cpe(part="o", versionEndExcluding="1.6.20"))
        self.assertEqual(1, len(rows))
        self.assertIsNone(rows[0].fixed_version)

    def test_different_cpe_platform_qualifiers_still_contribute_conflicts(self):
        first = cpe(versionEndExcluding="1.6.20")
        second = cpe(versionStartIncluding="1.6.30")
        first["criteria"] = "cpe:2.3:a:vendor:library:*:*:*:*:*:windows:*:*"
        second["criteria"] = "cpe:2.3:a:vendor:library:*:*:*:*:*:linux:*:*"
        self.assertTrue(all(row.fixed_version is None for row in self.rows(first, second)))

    def test_cross_branch_range_blocks_earlier_candidate_and_does_not_force_branch_upgrade(self):
        rows = self.rows(cpe(versionEndExcluding="1.6.20"), cpe(versionStartIncluding="1.6.15", versionEndExcluding="2.0.5"))
        self.assertTrue(all(row.fixed_version is None for row in rows))

    def test_excluded_start_of_new_branch_is_not_a_fix_for_previous_branch(self):
        rows = self.rows(cpe(versionEndExcluding="1.6.20"), cpe(versionStartIncluding="1.5.0", versionEndExcluding="1.6.0"))
        self.assertEqual(["1.6.20", None], [row.fixed_version for row in rows])

    def test_ambiguous_negated_and_unknown_logical_nodes_disable_inference(self):
        for extra in (
            {"negate": True, "nodes": [{"cpeMatch": [cpe(version="1.6.20")]}]},
            {"operator": "XOR", "cpeMatch": [cpe(version="1.6.20")]},
            {"cpeMatch": "malformed"}, {"children": {}}, None,
        ):
            with self.subTest(extra=extra):
                rows = cve_remediations(configuration(cpe(versionEndExcluding="1.6.20")) + [extra], "", URL)
                self.assertTrue(all(row.fixed_version is None for row in rows))

    def test_and_environment_constraints_do_not_add_non_vulnerable_ranges(self):
        rows = cve_remediations([{"operator": "AND", "nodes": [
            {"cpeMatch": [cpe(versionEndExcluding="1.6.20")]},
            {"cpeMatch": [{**cpe(versionStartIncluding="1.6.30"), "vulnerable": False}]},
        ]}], "", URL)
        self.assertEqual(["1.6.20"], [row.fixed_version for row in rows])

    def test_malformed_cpe_identity_or_unrecognized_vulnerability_flag_disables_inference(self):
        for extra in ({"vulnerable": True, "criteria": "broken"}, {"criteria": cpe()["criteria"]}, cpe(vendor="*")):
            with self.subTest(extra=extra):
                self.assertTrue(all(row.fixed_version is None for row in self.rows(cpe(versionEndExcluding="1.6.20"), extra)))

    def test_truncated_configuration_tree_cannot_supply_a_safe_boundary(self):
        config = [{"cpeMatch": [cpe(versionEndExcluding="1.6.20")]}] + [{} for _ in range(10000)]
        config.append({"cpeMatch": [cpe(version="1.6.20")]})
        rows = cve_remediations(config, "", URL)
        self.assertIsNone(rows[0].fixed_version)

    def test_truncated_match_list_cannot_supply_a_safe_boundary(self):
        matches = [cpe(versionEndExcluding="1.6.20")] * 20000 + [cpe(version="1.6.20")]
        rows = cve_remediations(configuration(*matches), "", URL)
        self.assertIsNone(rows[0].fixed_version)

    def test_explicit_fix_is_description_evidence_until_caller_verifies_publisher(self):
        row, = self.rows(cpe(versionEndExcluding="1.6.20"), description="Library before 1.6.20 is affected. This issue is fixed in 1.6.20.")
        self.assertEqual(("1.6.20", "description", "1.6"), (row.fixed_version, row.fixed_version_basis, row.fixed_version_branch))

    def test_known_cpe_conflict_overrides_single_explicit_fix(self):
        row, = self.rows(cpe(version="1.6.20"), description="Library before 1.6.20 is affected. This issue is fixed in 1.6.20.")
        self.assertIsNone(row.fixed_version)
        self.assertIsNone(row.fixed_version_basis)

    def test_known_later_range_uses_nvd_boundary_instead_of_conflicting_explicit_fix(self):
        row, = self.rows(cpe(versionEndExcluding="1.6.30"), description="Library before 1.6.20 is affected. This issue is fixed in 1.6.20.")
        self.assertEqual(("1.6.30", "nvd_range", "1.6"), (row.fixed_version, row.fixed_version_basis, row.fixed_version_branch))

    def test_prose_only_affected_upper_bound_is_not_nvd_range_evidence(self):
        row, = cve_remediations(None, "Library before 1.6.20 is affected.", URL)
        self.assertIsNone(row.fixed_version)
        self.assertIsNone(row.fixed_version_basis)

    def test_case_variants_of_cpe_identity_contribute_conflicts(self):
        rows = self.rows(cpe(versionEndExcluding="1.6.20"), cpe(product="Library", vendor="Vendor", version="1.6.20"))
        self.assertTrue(all(row.fixed_version is None for row in rows))

    def test_product_identity_patterns_disable_inference(self):
        for extra in (cpe(product="lib*"), cpe(vendor="vend?r")):
            with self.subTest(extra=extra):
                self.assertTrue(all(row.fixed_version is None for row in self.rows(cpe(versionEndExcluding="1.6.20"), extra)))

    def test_ambiguous_vendor_identity_cannot_share_a_description_fix(self):
        rows = self.rows(
            cpe(vendor="first", version="1.6.19"), cpe(vendor="second", version="1.6.19"),
            description="This issue affects Library: 1.6.19. This issue is fixed in version 1.6.20.",
        )
        self.assertEqual(2, len(rows))
        self.assertTrue(all(row.fixed_version is None for row in rows))

    def test_ambiguous_cpe_part_identity_cannot_share_a_description_fix(self):
        rows = self.rows(
            cpe(version="1.6.19"), cpe(part="o", version="1.6.19"),
            description="This issue affects Library: 1.6.19. This issue is fixed in version 1.6.20.",
        )
        self.assertEqual(1, len(rows))
        self.assertIsNone(rows[0].fixed_version)
