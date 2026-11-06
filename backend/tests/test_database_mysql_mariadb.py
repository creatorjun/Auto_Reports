# backend/tests/test_database_mysql_mariadb.py
import json
import unittest

import httpx

from src.domain.entities.database_cve import DatabaseFeedData
from src.infrastructure.external.database_mariadb import parse_mariadb
from src.infrastructure.external.database_mysql import MYSQL_TARGET, fetch_mysql, parse_mysql_csaf, parse_mysql_legacy
from src.infrastructure.external.database_version import compare_versions, coverage_note, matcher, validate_version


MARIA = """# Security Vulnerabilities (CVE) Fixed in MariaDB Community Server
| [CVE-2026-1000](https://www.cve.org) | 2026-01-01 | 8.1 | [10.11.5](/docs/release-notes/community-server/10.11/10.11.5.md) (2026-01-01), [Connector/C 3.4.1](/docs/release-notes/connectors/c/3.4.1.md) |
| [CVE-2026-1000](https://www.cve.org) | 2026-01-01 | 8.1 | [10.11.8](/docs/release-notes/community-server/10.11/10.11.8.md) (2026-03-01) |
| [CVE-2026-1001](https://www.cve.org) | 2026-01-01 | N/A (Medium) | [5.5](/docs/release-notes/community-server/old-releases/5.5/notes.md) |
| [CVE-2026-1002](https://www.cve.org) | 2026-01-01 | N/A | [5.5.28a](/docs/release-notes/community-server/old-releases/5.5/5.5.28a.md) |
"""


def product(name, version, pid):
    return {"category": "product_name", "name": name, "branches": [{"category": "product_version_range", "name": version,
            "product": {"product_id": pid, "name": f"{name} Version {version}"}}]}


def mysql_document(products, vulnerabilities):
    return json.dumps({
        "document": {"title": "Oracle security update", "tracking": {"initial_release_date": "2026-01-20T13:00:00-08:00"},
                     "references": [{"url": "https://www.oracle.com/security-alerts/cpujan2026.html"}]},
        "product_tree": {"branches": [{"category": "product_family", "name": "Oracle MySQL", "branches": products}]},
        "vulnerabilities": vulnerabilities,
    }).encode()


class DatabaseVendorTest(unittest.IsolatedAsyncioTestCase):
    def test_mariadb_community_fixes_distinguish_connectors_repeated_fixes_and_series_without_patch(self):
        data = parse_mariadb(MARIA.encode())
        self.assertEqual({"10.11.5", "10.11.8", "5.5.28a"}, {b.version for b in data.builds})
        self.assertEqual(["high", "high", "medium", "unknown"], [r.severity for r in data.advisories])
        self.assertTrue(any(filter(matcher("mariadb", "10.11.4", (data,)), data.advisories)))
        self.assertFalse(any(filter(matcher("mariadb", "10.11.5", (data,)), data.advisories)))
        self.assertTrue(coverage_note("mariadb", "5.5.28a", (data,)))
        self.assertGreater(compare_versions("5.5.28a", "5.5.28"), 0)
        self.assertIsNone(matcher("mariadb", "10.10.5", (data,)))

    def test_mysql_csaf_only_uses_known_affected_server_and_per_product_scores(self):
        products = [product("MySQL Server", "9.0.0-9.4.0", "s"), product("MySQL Server", "8.4.2", "p"),
                    product("MySQL Cluster", "8.0.0-8.0.41", "c"), product("MySQL Connector/J", "9.0.0", "j")]
        vulnerabilities = [{"cve": "CVE-2026-1000", "product_status": {"known_affected": ["s", "c"], "known_not_affected": ["p"]},
                            "scores": [{"products": ["s"], "cvss_v3": {"baseScore": 5.2}}, {"products": ["c"], "cvss_v3": {"baseScore": 9.8}}]},
                           {"cve": "CVE-2026-1001", "product_status": {"known_affected": ["p"]}},
                           {"cve": "CVE-2026-1002", "product_status": {"known_affected": ["j"]}}]
        rows = parse_mysql_csaf(mysql_document(products, vulnerabilities))
        data = (DatabaseFeedData(rows, ()),)
        for version in ("9.0.0", "9.2.1", "9.4.0"):
            matched = [r for r in rows if matcher("mysql", version, data)(r)]
            self.assertEqual([("CVE-2026-1000", 5.2, "9.0.0", "9.4.0", None)], [(r.cve_id, r.cvss_score, r.affected_from, r.affected_through, r.fixed_version) for r in matched])
        self.assertFalse(any(filter(matcher("mysql", "9.4.0.1", data), rows)))
        self.assertFalse(any(filter(matcher("mysql", "8.4.1", data), rows)))
        self.assertEqual(["CVE-2026-1001"], [r.cve_id for r in rows if matcher("mysql", "8.4.2", data)(r)])
        self.assertIsNone(matcher("mysql", "8.0.38", data))

    def test_legacy_table_with_colspans_preserves_earlier_bounds_and_rejects_ambiguous_versions(self):
        page = """<title>CPU July 2018</title><table><tr><th>CVE#</th><th>Product</th><th>Component</th>
        <th colspan="2">CVSS VERSION 2.0 RISK</th><th>Supported Versions Affected</th></tr>
        <tr><th>Base Score</th><th>Access Vector</th></tr>
        <tr><td>CVE-2018-1000</td><td>MySQL Server</td><td>Optimizer</td><td>9.8</td><td>Network</td><td>5.6.28 and earlier 5.7.10 and earlier</td></tr>
        <tr><td>CVE-2018-1001</td><td>MySQL Server</td><td>Parser</td><td>4.4</td><td>Network</td><td>8.017 and prior</td></tr>
        <tr><td>CVE-2018-1002</td><td>MySQL Workbench</td><td>Parser</td><td>4.4</td><td>Network</td><td>8.0.17 and prior</td></tr></table>"""
        rows = parse_mysql_legacy(page.encode(), "https://www.oracle.com/security-alerts/cpujul2018.html")
        self.assertEqual({"5.6", "5.7", "8.*"}, {r.series for r in rows})
        self.assertEqual({"high"}, {r.severity for r in rows if r.cve_id == "CVE-2018-1000"})
        self.assertIsNone(matcher("mysql", "8.0.17", (DatabaseFeedData(rows, ()),)))
        self.assertTrue(coverage_note("mysql", "5.6.28", (DatabaseFeedData(rows, ()),)))
        with self.assertRaises(ValueError):
            validate_version("mysql", "8.0-MariaDB")

    async def test_foreign_rss_references_cannot_request_arbitrary_urls(self):
        requested = []
        def respond(request):
            requested.append(request.url.host)
            return httpx.Response(200, text="<rss><channel><item><link>https://example.net/fakecsaf.json</link></item></channel></rss>")
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with self.assertRaises(ValueError):
                await fetch_mysql(client, MYSQL_TARGET, MYSQL_TARGET.feeds[0])
        self.assertEqual(["www.oracle.com"], requested)
