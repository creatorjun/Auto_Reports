# backend/tests/test_java_openjdk.py
import unittest

import httpx
from defusedxml.common import EntitiesForbidden

from src.infrastructure.external.java_openjdk import OPENJDK_TARGET, fetch_openjdk, openjdk_coverage_note, openjdk_matcher, parse_openjdk_advisory
from src.infrastructure.external.java_version import compare_java_versions, java_version


DAY = "2024-04-16"
INDEX = b'<html><div id="main"><h2 id="advisories">Advisories</h2><ul><li><a href="2024-04-16">April</a></li></ul></div></html>'
NOTICE = b"""<html><div id="main"><h1>OpenJDK Vulnerability Advisory: 2024/4/16</h1>
<p>The affected versions are 17.0.10, 8u402, and earlier.</p>
<h2 id="risk-matrix">OpenJDK Risk matrix</h2><table>
<tr><th>Affected</th></tr><tr><th>CVE ID</th><th>Component</th><th>CVSSv3.1</th><th>8</th><th>17</th></tr>
<tr><td>CVE-2024-1234</td><td>core-libs/<br/>java.net</td><td>8.1<br/>vector</td><td></td><td>&#8226;</td></tr>
<tr><td>CVE-2024-1235</td><td>hotspot</td><td>3.7<br/>vector</td><td>&#8226;</td><td></td></tr></table>
<h2 id="jfx-risk-matrix">OpenJFX Risk matrix</h2><table><tr><td>CVE-2024-2222</td></tr></table></div></html>"""


class OpenJdkAdvisoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_vendor_matrix_is_inclusive_on_marked_majors_and_keeps_fixes_unknown(self):
        requests = []

        def respond(request):
            requests.append(request.url.path)
            return httpx.Response(200, content=NOTICE if request.url.path.endswith(DAY) else INDEX)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            feed = await fetch_openjdk(client, OPENJDK_TARGET, OPENJDK_TARGET.feeds[0])
        self.assertEqual(2, len(requests))
        self.assertEqual({"17.0.10", "8u402"}, {b.version for b in feed.builds})
        modern, legacy = feed.advisories
        self.assertEqual(("CVE-2024-1234", 17, "17.0.10", None, "core-libs/java.net", 8.1, "high"),
                         (modern.cve_id, modern.major, modern.affected_through, modern.fixed_version, modern.component, modern.cvss_score, modern.severity))
        for version, expected in [("17.0.9", [modern]), ("17.0.10+7", [modern]), ("17.0.11", []),
                                  ("1.8.0_402-b06", [legacy]), ("8u403", [])]:
            with self.subTest(version=version):
                self.assertEqual(expected, list(filter(openjdk_matcher(version, (feed,)), feed.advisories)))
        self.assertIsNone(openjdk_matcher("11.0.1", (feed,)))

    def test_unaligned_header_and_prose_never_invent_a_version_bound(self):
        feed = parse_openjdk_advisory(NOTICE.replace(b"<th>17</th>", b"<th>21</th>"), DAY)
        self.assertIsNone(feed.advisories[0].affected_through)
        self.assertIsNone(openjdk_matcher("21", (feed,)))
        self.assertTrue(openjdk_coverage_note("21", (feed,)))
        self.assertIsNone(openjdk_coverage_note("8u402-b07", (feed,)))
        self.assertTrue(openjdk_coverage_note("8u499", (feed,)))

    def test_malformed_ranges_dates_marks_and_unsafe_xml_are_rejected(self):
        for old, new in [
            (b"and earlier", b"only"), (b"2024/4/16", b"2024/4/17"), (b"&#8226;", b"?"),
            (b"8.1<br", b"high<br"), (b"17.0.10,", b"17.0.10, 17.0.9,"),
        ]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                parse_openjdk_advisory(NOTICE.replace(old, new), DAY)
        with self.assertRaises(EntitiesForbidden):
            parse_openjdk_advisory(b'<!DOCTYPE html [<!ENTITY huge "text">]>' + NOTICE, DAY)

    async def test_catalog_uses_only_released_builds_and_is_independent_of_risk_collection(self):
        pages = {
            "/archive/": '<th>17.0.2 (build 17.0.2+8)</th><th>26 GA (build 26+35)</th>',
            "/": '<h1>Ready for use: <a href="/27/">JDK 27</a></h1><h1>Early access: <a href="/28/">JDK 28</a></h1>',
            "/27/": '<h1>OpenJDK JDK 27.0.1.0.3 GA Release Builds</h1>',
        }
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=f'<html><div id="main">{pages[r.url.path]}</div></html>'))) as client:
            data = await fetch_openjdk(client, OPENJDK_TARGET, OPENJDK_TARGET.feeds[1])
        self.assertEqual({"17.0.2", "26", "27.0.1.0.3"}, {b.version for b in data.builds})
        self.assertFalse(data.advisories)
        self.assertIsNone(openjdk_matcher("26", (data,)))

    def test_java_formal_versions_and_build_order(self):
        self.assertEqual(java_version("8u402-b06"), java_version("1.8.0_402-b06"))
        self.assertEqual(java_version("8u402-b06"), java_version("8.0.402+6"))
        self.assertGreater(compare_java_versions("17.0.11", "17.0.9"), 0)
        self.assertGreater(compare_java_versions("17.0.21.0.3+1", "17.0.21.0.2+9"), 0)
        self.assertGreater(compare_java_versions("17.0.21+10-LTS", "17.0.21+9"), 0)
        for unsupported in ("21-ea+28", "17.0.11~ea", "17.0.11+8-custom", "latest", "8u", "1.8.0_402text", "11..7"):
            with self.subTest(unsupported=unsupported), self.assertRaises(ValueError):
                java_version(unsupported)
