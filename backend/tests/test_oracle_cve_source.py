# backend/tests/test_oracle_cve_source.py
import bz2
import unittest
from unittest.mock import patch

import httpx
from defusedxml.common import DTDForbidden

from src.domain.entities.cve_inventory import CveInventoryPackage
from src.infrastructure.external.oracle_cve_source import OracleCveSource, parse_oracle_oval


FIXTURE = b'''<oval_definitions xmlns="http://oval.mitre.org/XMLSchema/oval-definitions-5" xmlns:linux="http://oval.mitre.org/XMLSchema/oval-definitions-5#linux">
<definitions><definition id="d1" class="patch"><metadata>
<title>ELSA-2026-1000: example security update (IMPORTANT)</title>
<affected family="unix"><platform>Oracle Linux 8</platform></affected>
<reference source="elsa" ref_id="ELSA-2026-1000" ref_url="https://linux.oracle.com/errata/ELSA-2026-1000.html"/>
<reference source="CVE" ref_id="CVE-2026-1234" ref_url="https://linux.oracle.com/cve/CVE-2026-1234.html"/>
<advisory><severity>IMPORTANT</severity><issued date="2026-10-01"/><updated date="2026-10-02"/>
<cve cvss3="9.8/CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H" public="20260929">CVE-2026-1234</cve>
<cve public="20260930">CVE-2026-1235</cve></advisory></metadata>
<criteria operator="AND"><criterion test_ref="t_os" comment="Oracle Linux 8 is installed"/>
<criteria operator="OR"><criteria operator="AND"><criterion test_ref="t_arch" comment="Oracle Linux arch is x86_64"/>
<criterion test_ref="t_module" comment="Module example:2 stream is enabled"/>
<criteria operator="AND"><criterion test_ref="t_version" comment="example is earlier than 1:2.0-4.el8"/>
<criterion test_ref="t_signature" comment="example is signed with the Oracle Linux 8 key"/></criteria></criteria></criteria></criteria>
</definition></definitions>
<tests>
<linux:rpminfo_test id="t_os"><linux:object object_ref="o_os"/><linux:state state_ref="s_os"/></linux:rpminfo_test>
<linux:rpminfo_test id="t_arch"><linux:object object_ref="o_os"/><linux:state state_ref="s_arch"/></linux:rpminfo_test>
<linux:rpminfo_test id="t_version"><linux:object object_ref="o_package"/><linux:state state_ref="s_version"/></linux:rpminfo_test>
<linux:rpminfo_test id="t_signature"><linux:object object_ref="o_package"/><linux:state state_ref="s_signature"/></linux:rpminfo_test>
<textfilecontent54_test id="t_module"/>
</tests><objects><linux:rpminfo_object id="o_os"><linux:name>oraclelinux-release</linux:name></linux:rpminfo_object>
<linux:rpminfo_object id="o_package"><linux:name>example</linux:name></linux:rpminfo_object></objects>
<states><linux:rpminfo_state id="s_os"><linux:version operation="pattern match">^8</linux:version></linux:rpminfo_state>
<linux:rpminfo_state id="s_arch"><linux:arch>x86_64</linux:arch></linux:rpminfo_state>
<linux:rpminfo_state id="s_signature"><linux:signature_keyid>oracle-key</linux:signature_keyid></linux:rpminfo_state>
<linux:rpminfo_state id="s_version"><linux:evr datatype="evr_string" operation="less than">1:2.0-4.el8</linux:evr></linux:rpminfo_state></states>
</oval_definitions>'''


def package(name="example"):
    return CveInventoryPackage(id="p1", name=name, ecosystem="RPM", versions=("1:1.0-1.el8",), source="oracle", query_name=name, distribution_id="ol", distribution_version="8")


class OracleParsingTest(unittest.TestCase):
    def test_structural_rpm_mapping_keeps_fixed_evr_branch_guards_and_individual_scores(self):
        rows = parse_oracle_oval(bz2.compress(FIXTURE))
        self.assertEqual({"example"}, set(rows))
        first, second = rows["example"]
        self.assertEqual(("CVE-2026-1234", "critical", 9.8, "3.1"), (first.cve_id, first.severity, first.cvss_score, first.cvss_version))
        self.assertEqual(("1:2.0-4.el8",), first.fixed_versions)
        self.assertEqual("RPM_EVR", first.ranges[0].type)
        for guard in ("x86_64", "example:2 stream", "Oracle Linux 8 key", "ELSA-2026-1000"):
            self.assertIn(guard, first.ranges[0].affected)
        self.assertEqual(("2026-09-29", "2026-10-02"), (first.published_at, first.modified_at))
        self.assertEqual(("high", None, "oracle_advisory"), (second.severity, second.cvss_score, second.severity_source))
        self.assertEqual("unknown", first.inventory_impact)

    def test_inclusive_boundary_never_invents_fixed_version(self):
        first = parse_oracle_oval(FIXTURE.replace(b'operation="less than"', b'operation="less than or equal"'))["example"][0]
        self.assertEqual((), first.fixed_versions)
        self.assertIsNone(first.ranges[0].fixed)
        self.assertTrue(first.ranges[0].affected.startswith("<= 1:2.0-4.el8"))

    def test_inventory_filter_excludes_unrequested_packages(self):
        self.assertEqual({}, parse_oracle_oval(FIXTURE, frozenset({"unrelated"})))
        self.assertEqual({"example"}, set(parse_oracle_oval(FIXTURE, frozenset({"example"}))))

    def test_negated_package_branch_does_not_generate_vulnerabilities(self):
        data = FIXTURE.replace(b'<criterion test_ref="t_version"', b'<criterion negate="true" test_ref="t_version"')
        self.assertEqual({}, parse_oracle_oval(data))

    def test_unresolved_reference_fails_instead_of_silently_losing_coverage(self):
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            parse_oracle_oval(FIXTURE.replace(b'object_ref="o_package"', b'object_ref="missing"'))

    def test_forbids_dtd_entities_and_wrong_document(self):
        with self.assertRaises(DTDForbidden):
            parse_oracle_oval(b'<!DOCTYPE oval_definitions [<!ENTITY x SYSTEM "file:///etc/passwd">]>' + FIXTURE)
        with self.assertRaises(ValueError):
            parse_oracle_oval(b'<html>not a feed</html>')

    def test_expansion_limit_and_truncated_bzip_fail(self):
        with patch("src.infrastructure.external.oracle_cve_source.MAX_XML_BYTES", 100):
            with self.assertRaises(ValueError):
                parse_oracle_oval(bz2.compress(FIXTURE))
        with self.assertRaises((EOFError, OSError)):
            parse_oracle_oval(bz2.compress(FIXTURE)[:-20])

    def test_unsafe_reference_is_not_preserved(self):
        result = parse_oracle_oval(FIXTURE.replace(b'https://linux.oracle.com/errata/ELSA-2026-1000.html', b'javascript:alert(1)'))
        self.assertTrue(all(url.startswith("https://") for row in result["example"] for url in row.references))


class OracleSourceTest(unittest.IsolatedAsyncioTestCase):
    async def test_shared_feed_download_is_once_per_refresh_and_contains_no_private_inventory(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, content=bz2.compress(FIXTURE))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = OracleCveSource(client)
            await source.configure((package(), package("other")))
            self.assertEqual([], requests)
            self.assertEqual(2, len(await source.fetch(package())))
            self.assertEqual((), await source.fetch(package("other")))
            self.assertEqual(1, len(requests))
            self.assertEqual(b"", requests[0].content)
            self.assertEqual("", requests[0].url.query.decode())
            await source.begin_refresh()
            await source.fetch(package())
            self.assertEqual(2, len(requests))
            await source.aclose()
            self.assertFalse(client.is_closed)

    async def test_failed_feed_is_not_downloaded_for_every_package(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(503)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source = OracleCveSource(client)
            with self.assertRaises(httpx.HTTPStatusError):
                await source.fetch(package())
            with self.assertRaises(RuntimeError):
                await source.fetch(package("other"))
            self.assertEqual(1, len(requests))
