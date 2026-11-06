# backend/src/infrastructure/external/kernel_upstream.py
import asyncio
import io
import json
import re
import zipfile

import httpx

from src.domain.entities.kernel_cve import KernelAdvisory, KernelFeed, KernelFeedData, KernelTarget
from src.infrastructure.external.kernel_feed_http import fetch_bytes


UPSTREAM_FEED = KernelFeed("osv-linux", "OSV · Linux Kernel", "https://storage.googleapis.com/osv-vulnerabilities/Linux/all.zip")
UPSTREAM_TARGET = KernelTarget("linux-upstream", "Linux Kernel", (), (), (UPSTREAM_FEED,), "Linux 생태계에 공개된 CVE")
_CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,}")


def _parse(blob: bytes) -> KernelFeedData:
    records = {}
    withdrawn = set()
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        if sum(entry.file_size for entry in archive.infolist()) > 1_000_000_000:
            raise ValueError("OSV Linux export exceeds its size limit")
        for entry in archive.infolist():
            if not entry.filename.endswith(".json"):
                continue
            if entry.file_size > 8_000_000:
                raise ValueError("Oversized OSV record")
            item = json.loads(archive.read(entry))
            record_id = item["id"]
            if item.get("withdrawn"):
                if _CVE.fullmatch(record_id):
                    withdrawn.add(record_id)
                continue
            cves = {key for key in [record_id, *item.get("aliases", [])] if _CVE.fullmatch(key)}
            if not cves or not any(a.get("package", {}).get("ecosystem") == "Linux" for a in item.get("affected", [])):
                continue
            title = item.get("summary") or next((line for line in item.get("details", "").splitlines() if line.strip()), record_id)
            for cve in cves:
                if cve == record_id or cve not in records:
                    records[cve] = KernelAdvisory(cve, "unknown", record_id, f"https://www.cve.org/CVERecord?id={cve}",
                                                  item["published"][:10], "", "", "", title=title[:400])
    for cve in withdrawn:
        records.pop(cve, None)
    if not records:
        raise ValueError("No active Linux kernel CVE records in the OSV export")
    return KernelFeedData(tuple(records.values()), ())


async def fetch_upstream(client: httpx.AsyncClient) -> KernelFeedData:
    archive = await fetch_bytes(client, UPSTREAM_FEED.url, 192_000_000)
    return await asyncio.to_thread(_parse, archive)
