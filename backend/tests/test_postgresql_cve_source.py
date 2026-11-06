# backend/tests/test_postgresql_cve_source.py
import unittest

import httpx

from src.infrastructure.external.database_postgresql import _PgPage, _advisories, _series, _versions


def table(fixed):
    return f"""<table><tr><th>Reference</th><th>Affected</th><th>Fixed</th><th>Component &amp; CVSS v3 Base Score</th>
    <th>Description</th></tr><tr><td><a href="/support/security/CVE-2026-18024/">CVE-2026-18024</a></td>
    <td>17, 9.6</td><td>{fixed}</td><td>core server<br/><a href="/score">4.3</a><br/>AV:N/AC:L</td>
    <td>PostgreSQL function reads past end of buffer<br/><a href="/support/security/CVE-2026-18024/">more details</a></td>
    </tr></table>""".encode()


class PostgreSqlFeedTest(unittest.IsolatedAsyncioTestCase):
    async def test_release_notes_for_predecessor_products_do_not_discard_known_releases(self):
        def response(req):
            if req.url.path == "/versions.json":
                return httpx.Response(200, json=[{"major": "17", "supported": True}, {"major": "9.6", "supported": False}])
            return httpx.Response(200, content=b'<a href="/docs/release/0.01/">old</a><a href="/docs/release/9.6/">9.6</a><a href="/docs/release/17.10/">17.10</a>')
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
            data = await _versions(client)
        self.assertEqual({b.version: b.supported for b in data.builds}, {"17.10": True, "9.6.0": False})

    def test_fixes_are_associated_by_branch_and_keep_component_and_score(self):
        for series, fixed in [("17", "17.11"), ("9.6", "9.6.24")]:
            rows = list(_advisories(_PgPage(table("9.6.24, 17.11")), series))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual((row.fixed_version, row.severity, row.cvss_score, row.component), (fixed, "medium", 4.3, "core server"))
            self.assertNotIn("more details", row.title)
        self.assertEqual(list(_advisories(_PgPage(table("9.6.24, 17.11")), "15")), [])

    def test_truncated_tables_missing_series_and_invalid_version_are_rejected(self):
        with self.assertRaises(ValueError):
            _PgPage(table("17.11, 9.6.24")[:-9])
        with self.assertRaises(ValueError):
            list(_advisories(_PgPage(table("17.11")), "9.6"))
        with self.assertRaises(ValueError):
            _series("9.6")
