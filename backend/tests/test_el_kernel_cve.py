# backend/tests/test_el_kernel_cve.py
import bz2
import gzip
import hashlib
import io
import json
import unittest
import zipfile

import httpx

from src.infrastructure.external.el_kernel_cve import OTHER_TARGETS, _centos_data, _repository_xml, _rocky_data
from src.infrastructure.external.kernel_upstream import _parse


class KernelVendorFeedsTest(unittest.IsolatedAsyncioTestCase):
    def test_rocky_selects_published_standard_kernel_for_target_architecture(self):
        xml = b"""<updates><update status="final"><id>RLSA-2024:1234</id><release>Rocky Linux 8</release>
        <severity>Important</severity><issued date="2024-06-01"/><references>
        <reference type="cve" id="CVE-2024-12345"/></references>
        <pkglist><collection><package name="kernel" arch="x86_64" version="4.18.0" release="513.el8"/>
        <package name="kernel" arch="aarch64" version="4.18.0" release="520.el8"/>
        <package name="kernel-rt" arch="x86_64" version="4.18.0" release="999.el8"/>
        </collection></pkglist></update></updates>"""
        result = _rocky_data(xml, next(t for t in OTHER_TARGETS if t.id == "rocky8"), "x86_64")
        self.assertEqual([(a.cve_id, a.fixed_version, a.severity) for a in result.advisories],
                         [("CVE-2024-12345", "4.18.0-513.el8", "high")])

    async def test_repository_rejects_truncated_or_substituted_metadata(self):
        payload = gzip.compress(b"<updates/>")
        checksum = hashlib.sha256(payload).hexdigest()
        descriptor = f'<repomd><data type="updateinfo"><checksum type="sha256">{checksum}</checksum><location href="repodata/{checksum}-updateinfo.xml.gz"/></data></repomd>'
        def serve(req):
            return httpx.Response(200, content=descriptor.encode() if req.url.path.endswith("repomd.xml") else payload[:-2])
        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as client:
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                await _repository_xml(client, "https://example.test/", "updateinfo")

    def test_centos_only_accepts_rhsa_for_builds_published_in_vault_before_eol(self):
        vault = b'<otherdata><package name="kernel" arch="x86_64"><version epoch="0" ver="3.10.0" rel="1160.118.1.el7"/></package></otherdata>'
        template = """<definition><metadata><title>RHSA-2024:2004: kernel security update</title>
        <reference source="CVE" ref_id="{cve}"/><advisory><issued date="{date}"/><severity>Important</severity></advisory>
        </metadata><criteria><criterion comment="kernel is earlier than 0:3.10.0-{release}.el7"/></criteria></definition>"""
        updates = [("CVE-2023-4622", "2024-04-23", "1160.118.1"), ("CVE-2024-9999", "2024-07-01", "1160.118.1"),
                   ("CVE-2024-8888", "2024-04-23", "1160.888.1")]
        oval = "<definitions>" + "".join(template.format(cve=c, date=d, release=r) for c, d, r in updates) + "</definitions>"
        result = _centos_data(vault, bz2.compress(oval.encode()))
        self.assertEqual([a.cve_id for a in result.advisories], ["CVE-2023-4622"])
        self.assertFalse(result.complete)

    def test_upstream_deduplicates_aliases_and_suppresses_withdrawn_cves(self):
        primary_id = "CVE-2026-12345"
        removed_id = "CVE-2026-54321"
        default = {"published": "2026-11-05T08:48:01Z", "affected": [{"package": {"ecosystem": "Linux", "name": "Kernel"}}]}
        records = [{"id": primary_id, "summary": "Kernel issue"}, {"id": "GSD-1", "aliases": [primary_id, removed_id]},
                   {"id": removed_id, "withdrawn": "2026-11-06"}, {"id": "CVE-2026-88888", "affected": []}]
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as z:
            for item in records:
                z.writestr(item["id"] + ".json", json.dumps({**default, **item}))
        result = _parse(archive.getvalue())
        self.assertEqual([(a.cve_id, a.title, a.issued_at) for a in result.advisories], [(primary_id, "Kernel issue", "2026-11-05")])
