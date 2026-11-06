# backend/tests/test_oracle_kernel_cve.py
import bz2
import unittest
from unittest.mock import patch

import httpx
from defusedxml.common import DTDForbidden

from src.domain.entities.kernel_cve import KernelAdvisory, KernelBuild, KernelFeedData, KernelTarget
from src.infrastructure.external.kernel_rpm import compare_versions, coverage_note, matches_build, validate_build
from src.infrastructure.external.oracle_kernel_cve import ORACLE_TARGETS, fetch_oracle, parse_oracle_kernel


OL8 = next(target for target in ORACLE_TARGETS if target.id == "ol8")
FIXED = "0:5.15.0-326.222.4.el8uek"
BUILD = KernelBuild("kernel-uek", "x86_64", "5.15.0-322.203.3.2.el8uek.x86_64")
DOCUMENT = f"""<oval_definitions xmlns="http://oval.mitre.org/XMLSchema/oval-definitions-5"
 xmlns:l="http://oval.mitre.org/XMLSchema/oval-definitions-5#linux">
 <definitions><definition><metadata><title>UEK update</title>
 <reference source="elsa" ref_id="ELSA-2026-1234-0"/>
 <reference source="CVE" ref_id="CVE-2021-1111"/>
 <advisory><issued date="2026-09-28"/><severity>IMPORTANT</severity>
 <affected_cpe_list><cpe>cpe:/a:oracle:linux:8::UEKR7</cpe></affected_cpe_list>
 <cve cvss3="5.5/CVSS:3.1/AV:L">CVE-2025-8888</cve></advisory></metadata>
 <criteria operator="OR">
 <criteria operator="AND"><criterion comment="Oracle Linux 7 is installed"/>
 <criterion comment="Oracle Linux arch is aarch64"/>
 <criterion comment="kernel-uek is earlier than 0:5.4.17-2000.el7uek" test_ref="outside"/></criteria>
 <criteria operator="AND"><criterion comment="Oracle Linux 8 is installed"/>
 <criteria operator="AND"><criterion comment="Oracle Linux arch is x86_64"/>
 <criteria operator="OR"><criteria operator="AND">
 <criterion comment="kernel-uek is earlier than {FIXED}" test_ref="version"/>
 <criterion comment="kernel-uek is signed with the Oracle Linux 8 key"/>
 </criteria></criteria></criteria></criteria></criteria></definition></definitions>
 <tests><l:rpminfo_test id="version"><l:object object_ref="kernel"/><l:state state_ref="threshold"/></l:rpminfo_test></tests>
 <objects><l:rpminfo_object id="kernel"><l:name>kernel-uek</l:name></l:rpminfo_object></objects>
 <states><l:rpminfo_state id="threshold"><l:version operation="pattern match">5.15.0</l:version>
 <l:evr operation="less than">{FIXED}</l:evr></l:rpminfo_state></states></oval_definitions>"""


class OracleKernelCveTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetches_one_complete_vendor_feed_and_applies_os_arch_package_conditions(self):
        requests = []

        def respond(request):
            requests.append(str(request.url))
            return httpx.Response(200, content=bz2.compress(DOCUMENT.encode()))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            data = await fetch_oracle(client, OL8, OL8.feeds[0])
        self.assertEqual([OL8.feeds[0].url], requests)
        self.assertEqual((KernelBuild("kernel-uek", "x86_64", FIXED),), data.builds)
        self.assertEqual({"CVE-2021-1111": "high", "CVE-2025-8888": "medium"}, {a.cve_id: a.severity for a in data.advisories})
        self.assertEqual({"https://linux.oracle.com/errata/ELSA-2026-1234-0.html"}, {a.advisory_url for a in data.advisories})
        self.assertTrue(all(matches_build(OL8, BUILD, a) for a in data.advisories))

    def test_rejects_mismatched_oval_object_range_or_branch_and_truncated_or_hostile_feed(self):
        for old, new in [
            ('<l:name>kernel-uek', '<l:name>kernel-tools'), ('operation="less than"', 'operation="equals"'),
            ('pattern match">5.15.0', 'pattern match">5.4.17'), ('id="version"', 'id="missing"'),
            ('linux:8::UEKR7', 'linux:8::MODRHCK'), ('linux:8::UEKR7', 'linux:8::developer_UEKR7'),
        ]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                parse_oracle_kernel(bz2.compress(DOCUMENT.replace(old, new).encode()), OL8)
        compressed = bz2.compress(DOCUMENT.encode())
        with self.assertRaises((EOFError, OSError)):
            parse_oracle_kernel(compressed[:-2], OL8)
        with patch("src.infrastructure.external.oracle_kernel_cve._MAX_XML", 100), self.assertRaises(ValueError):
            parse_oracle_kernel(compressed, OL8)
        with self.assertRaises(DTDForbidden):
            parse_oracle_kernel(bz2.compress(("<!DOCTYPE oval_definitions>" + DOCUMENT).encode()), OL8)

    def test_canonical_evr_order_and_release_specific_inputs(self):
        for left, right in [
            ("1:1.0-1.el8", "0:99.0-20.el8"),
            ("5.15-12.el8", "5.15-9.el8"),
            ("5.15.0-3.0.el8", "5.15.0-3.a.el8"),
            ("5.15.1-1.el8", "5.15^git-100.el8"),
            ("5.15^git-1.el8", "5.15-100.el8"),
            ("5.15-1.el8", "5.15~rc1-99.el8"),
        ]:
            with self.subTest(left=left):
                self.assertGreater(compare_versions(left, right), 0)
                self.assertLess(compare_versions(right, left), 0)
        self.assertEqual(0, compare_versions("0:5.15.0-1.el8.x86_64", "5.15.0-001.el8"))
        validate_build(OL8, BUILD)
        for bad in ["5.15.0", "5.15.0-90.el7uek", "5.15.0-1.el8", "5.15.0-1.el8uek.aarch64"]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_build(OL8, KernelBuild("kernel-uek", "x86_64", bad))
        centos = KernelTarget("centos7", "CentOS 7.9", ("kernel",), ("x86_64",), (), "")
        validate_build(centos, KernelBuild("kernel", "x86_64", "3.10.0-1160.119.1.el7.x86_64"))
        with self.assertRaises(ValueError):
            validate_build(centos, KernelBuild("kernel", "x86_64", "3.10.0-1127.el7"))

    def test_equal_or_fixed_versions_other_arch_and_parallel_uek_releases_do_not_match(self):
        advisory = KernelAdvisory("CVE-2025-8888", "high", "ELSA-2026-1234", "", None, "kernel-uek", "x86_64", FIXED, "5.15.0")
        for build in [
            KernelBuild("kernel-uek", "x86_64", FIXED), KernelBuild("kernel-uek", "x86_64", "5.15.0-999.el8uek"),
            KernelBuild("kernel-uek", "x86_64", "5.4.17-100.el8uek"), KernelBuild("kernel", "x86_64", "4.18.0-1.el8"),
            KernelBuild("kernel-uek", "aarch64", BUILD.version),
        ]:
            self.assertFalse(matches_build(OL8, build, advisory))
        data = KernelFeedData((advisory,), (KernelBuild("kernel-uek", "x86_64", FIXED),))
        self.assertIsNone(coverage_note(OL8, data.builds[0], (data,)))
        self.assertTrue(coverage_note(OL8, BUILD, (data,)))
