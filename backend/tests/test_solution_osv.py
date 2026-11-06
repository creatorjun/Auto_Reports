# backend/tests/test_solution_osv.py
import io
import json
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import httpx

from src.domain.entities.solution_package import SolutionPackage
from src.infrastructure.external.solution_osv import match_solution_packages
from src.infrastructure.external.solution_osv_versions import affected_version


def entry(ecosystem="Maven", name="fixture:library", **fields):
    return {"package": {"name": name, "ecosystem": ecosystem}, **fields}


def record(identifier, *affected, **fields):
    return {"id": identifier, "affected": affected, **fields}


def archive_bytes(records):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for item in records:
            archive.writestr(item["id"] + ".json", json.dumps(item))
    return buffer.getvalue()


class OsvVersionTests(unittest.TestCase):
    def test_semver_uses_numeric_and_prerelease_precedence_and_disjoint_ranges(self):
        events = [{"fixed": "2.9.0"}, {"introduced": "0"}, {"introduced": "2.10.0-alpha.2"}, {"fixed": "2.10.1"}]
        entry = {"ranges": [{"type": "SEMVER", "events": events}]}
        for version, expected in [
            ("2.8.99", True), ("2.9.0", False), ("2.10.0-alpha.1", False),
            ("2.10.0-alpha.11", True), ("2.10.0", True), ("2.10.1+build.5", False), ("v2.10", None),
        ]:
            with self.subTest(version=version):
                self.assertIs(affected_version(version, "npm", entry), expected)

    def test_numeric_maven_last_affected_and_limits(self):
        affected = {"ranges": [{"type": "ECOSYSTEM", "events": [
            {"introduced": "0"}, {"last_affected": "1.10.0"}, {"limit": "1.10.1"}, {"limit": "1.9"},
        ]}]}
        for version, expected in [("1.10", True), ("1.10.1", False), ("1.10.0.Final", None)]:
            self.assertIs(affected_version(version, "Maven", affected), expected)

    def test_explicit_versions_take_precedence_over_unsupported_ranges(self):
        affected = {"versions": ["1.2.Final"], "ranges": [{"type": "GIT", "events": [{"introduced": "0"}]}]}
        self.assertIs(affected_version("1.2.Final", "Maven", affected), True)
        self.assertIsNone(affected_version("2.0", "Maven", affected))
        self.assertIsNone(affected_version("2.0", "Maven", {}))
        self.assertIsNone(affected_version("2.0", "Maven", {"ranges": [{"type": "ECOSYSTEM", "events": [{"fixed": "3.0"}]}]}))


class OsvDumpTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self, packages, ecosystem, records):
        observed = []
        def serve(request):
            observed.append((request.method, str(request.url), request.content))
            return httpx.Response(200, content=archive_bytes(records))
        with httpx.Client(transport=httpx.MockTransport(serve)) as client:
            with patch("src.infrastructure.external.solution_osv.httpx.stream", side_effect=client.stream):
                result = await match_solution_packages(packages, ecosystem)
        self.assertEqual(observed, [("GET", f"https://storage.googleapis.com/osv-vulnerabilities/{ecosystem}/all.zip", b"")])
        return result

    async def test_matches_rows_exactly_and_only_uses_active_cve_ids_or_aliases(self):
        cve, withdrawn = "CVE-2099-1111", "CVE-2099-2222"
        affected = entry(versions=["1.0"])
        items = [
            SolutionPackage("a", "fixture:library", "1.0", "Java 라이브러리와 JDBC 드라이버", "check"),
            SolutionPackage("b", "fixture:library", "2.0", "Java 라이브러리와 JDBC 드라이버", "check"),
            SolutionPackage("c", "not:listed", "1.0", "Java 라이브러리와 JDBC 드라이버", "check"),
            SolutionPackage("d", "fixture:library", "1.0", "서버 런타임과 WAS", "check"),
        ]
        records = [
            record("GHSA-fixture", affected, aliases=[cve, withdrawn], related=["CVE-2099-3333"]),
            record(cve, affected), record(withdrawn, withdrawn="2099-01-01T00:00:00Z"),
            record("GHSA-withdrawn", affected, aliases=["CVE-2099-4444"], withdrawn="2099-01-01T00:00:00Z"),
            record("GHSA-no-cve", entry(versions=["2.0"])),
            record("CVE-2099-5555", entry("npm", "fixture:library", versions=["2.0"])),
        ]
        self.assertEqual(await self.collect(items, "Maven", records), {"a": (cve,), "b": (), "c": None})

    async def test_partial_and_unsupported_web_identity_preserve_limited_coverage(self):
        first = SolutionPackage("a", "fixture", "1.0.0", "웹 라이브러리", "version metadata", ())
        limited = SolutionPackage("b", "fixture", "1.0.0", first.category, "signature", None)
        css = SolutionPackage("c", "fixture", "1.0.0", "CSS에서만 확인한 라이브러리", "check")
        records = [
            record("CVE-2099-1111", entry("npm", "fixture", versions=["1.0.0"])),
            record("CVE-2099-2222", entry("npm", "fixture", ranges=[{"type": "GIT", "events": [{"introduced": "0"}]}])),
        ]
        self.assertEqual(await self.collect([first, limited, css], "npm", records), {"a": None, "b": None})

    async def test_empty_or_wrong_ecosystem_archive_is_a_failure(self):
        target = SolutionPackage("a", "fixture:library", "1", "Java 라이브러리와 JDBC 드라이버", "check")
        with self.assertRaises(ValueError):
            await self.collect([target], "Maven", [record("CVE-2099-1111", entry("npm", versions=["1"]))])

    async def test_invalid_ecosystem_and_inapplicable_rows_make_no_requests(self):
        with patch("src.infrastructure.external.solution_osv.httpx.stream") as fetch:
            with self.assertRaises(ValueError):
                await match_solution_packages([], "unsupported")
            self.assertEqual(await match_solution_packages([], "npm"), {})
            fetch.assert_not_called()
