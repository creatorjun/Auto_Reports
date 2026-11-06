# backend/src/infrastructure/external/el_kernel_cve.py
import asyncio
import bz2
import gzip
import hashlib
import io
import re
from functools import cmp_to_key

import httpx
from defusedxml import ElementTree as XML

from src.domain.entities.kernel_cve import KernelAdvisory, KernelBuild, KernelFeed, KernelFeedData, KernelTarget
from src.infrastructure.external.kernel_feed_http import fetch_bytes
from src.infrastructure.external.kernel_rpm import compare_versions


ROCKY = "https://dl.rockylinux.org/pub/rocky"
VAULT = "https://vault.centos.org/7.9.2009/updates/x86_64/"
RH_OVAL = "https://security.access.redhat.com/data/oval/v2/RHEL7/rhel-7.oval.xml.bz2"
ARCHES = ("x86_64", "aarch64")
CVE_ID = re.compile(r"\bCVE-[0-9]{4}-[0-9]{4,}\b")
SEVERITY = {"critical": "critical", "important": "high", "moderate": "medium", "low": "low"}
OTHER_TARGETS = (
    KernelTarget("centos7", "CentOS Linux 7.9", ("kernel",), ("x86_64",),
                 (KernelFeed("centos79-vault", "CentOS Vault · Red Hat 권고", VAULT),),
                 "2024-06-30 지원 종료. CentOS 7.9 Vault의 커널 빌드와 일치하는 Red Hat 보안 권고와 RPM 변경 기록을 조회합니다. 지원 종료 이후 취약점은 평가할 수 없습니다."),
    *(KernelTarget(f"rocky{major}", f"Rocky Linux {major}", ("kernel",), ARCHES,
                   tuple(KernelFeed(f"rocky{major}-{arch}", f"BaseOS · {arch}", f"{ROCKY}/{major}/BaseOS/{arch}/os/", (arch,)) for arch in ARCHES),
                   "Rocky Linux BaseOS 저장소에 공개된 표준 커널 업데이트 권고 전체를 대상으로 합니다. 위험도는 배포판 권고 등급입니다.")
      for major in (8, 9)),
)


def _unpack(blob: bytes, opener, maximum: int) -> bytes:
    with opener(io.BytesIO(blob), "rb") as reader:
        data = reader.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("Kernel metadata exceeds the uncompressed size limit")
    return data


async def _repository_xml(client: httpx.AsyncClient, base: str, kind: str) -> bytes:
    index = XML.fromstring(await fetch_bytes(client, base + "repodata/repomd.xml", 512_000), forbid_dtd=True)
    record = index.find(f"{{*}}data[@type='{kind}']")
    if record is None:
        raise ValueError(f"Missing repository {kind} metadata")
    checksum = record.find("{*}checksum")
    location = record.find("{*}location")
    href = location.get("href", "") if location is not None else ""
    if checksum is None or checksum.get("type") != "sha256" or not re.fullmatch(rf"repodata/[0-9a-f]{{64}}-{kind}\.xml\.gz", href):
        raise ValueError("Unexpected repository metadata descriptor")
    blob = await fetch_bytes(client, base + href, 32_000_000)
    if hashlib.sha256(blob).hexdigest() != checksum.text:
        raise ValueError("Repository metadata checksum mismatch")
    return await asyncio.to_thread(_unpack, blob, gzip.open, 128_000_000)


def _cve_titles(description: str) -> dict[str, str]:
    titles = {}
    for line in description.splitlines():
        for cve in CVE_ID.findall(line):
            text = line.strip(" \t*-")
            titles[cve] = re.sub(r"\s*\(CVE-[\d-]+\)\s*$", "", text)[:360]
    return titles


def _records(xml: bytes, tag: str):
    parents = []
    for event, node in XML.iterparse(io.BytesIO(xml), events=("start", "end"), forbid_dtd=True):
        if event == "start":
            parents.append(node)
        else:
            if node.tag.rsplit("}", 1)[-1] == tag:
                yield node
                if len(parents) > 1:
                    parents[-2].remove(node)
            parents.pop()


def _rocky_data(xml: bytes, target: KernelTarget, arch: str) -> KernelFeedData:
    advisories = []
    builds = set()
    for update in _records(xml, "update"):
        if update.get("status") != "final" or update.findtext("release") != target.label:
            continue
        versions = set()
        for pkg in update.findall("./pkglist/collection/package[@name='kernel']"):
            if pkg.get("arch") == arch:
                epoch = pkg.get("epoch", "0")
                version = (epoch + ":" if epoch != "0" else "") + pkg.attrib["version"] + "-" + pkg.attrib["release"]
                versions.add(version)
                builds.add(KernelBuild("kernel", arch, version))
        if not versions:
            continue
        name = update.findtext("id", "")
        if not re.fullmatch(r"RL[SEB]A-\d{4}:\d+", name):
            raise ValueError("Unexpected Rocky errata identifier")
        issued = update.find("issued")
        titles = _cve_titles(update.findtext("description", ""))
        cves = {r.get("id", "") for r in update.findall("./references/reference[@type='cve']")}
        for cve in sorted(cves):
            if not CVE_ID.fullmatch(cve):
                raise ValueError("Invalid Rocky CVE reference")
            for version in sorted(versions):
                advisories.append(KernelAdvisory(
                    cve, SEVERITY.get(update.findtext("severity", "").lower(), "unknown"), name,
                    f"https://errata.rockylinux.org/{name}", issued.get("date", "")[:10] if issued is not None else None,
                    "kernel", arch, version, title=titles.get(cve) or update.findtext("title", ""),
                ))
    if not advisories:
        raise ValueError("Missing Rocky kernel advisories")
    return KernelFeedData(tuple(advisories), tuple(sorted(builds, key=lambda b: b.version)))


def _vault_builds(xml: bytes) -> tuple[set[str], dict[tuple[str, str], str]]:
    versions = set()
    changes = {}
    for pkg in _records(xml, "package"):
        if (pkg.get("name"), pkg.get("arch")) != ("kernel", "x86_64"):
            continue
        v = pkg.find("{*}version")
        if v is None or v.get("epoch") != "0":
            raise ValueError("Invalid CentOS kernel build")
        versions.add(f"{v.attrib['ver']}-{v.attrib['rel']}")
        for entry in pkg.findall("{*}changelog"):
            build = re.search(r"\[(3\.10\.0-1160(?:\.\d+)*\.el7)\]\s*$", entry.get("author", ""))
            if build:
                for line in (entry.text or "").splitlines():
                    for cve in CVE_ID.findall(line):
                        changes[cve, build[1]] = line.strip(" -")[:360]
    if not versions:
        raise ValueError("Missing CentOS Vault kernel builds")
    return versions, changes


def _centos_data(vault_xml: bytes, oval_blob: bytes) -> KernelFeedData:
    versions, changes = _vault_builds(vault_xml)
    ordered = sorted(versions, key=cmp_to_key(compare_versions))
    xml = _unpack(oval_blob, bz2.open, 96_000_000)
    advisories = {}
    for definition in _records(xml, "definition"):
        meta = definition.find("{*}metadata")
        if meta is None:
            continue
        title = meta.findtext("{*}title", "")
        if not re.match(r"RHSA-\d{4}:\d+: kernel ", title):
            continue
        issued = meta.find("{*}advisory/{*}issued")
        if issued is None or issued.get("date", "9999") > "2024-06-30":
            continue
        name = title.split(": ", 1)[0]
        fixed = set()
        for criterion in definition.iterfind(".//{*}criterion"):
            match = re.fullmatch(r"kernel is earlier than 0:(\S+)", criterion.get("comment", ""))
            if match and match[1] in versions:
                fixed.add(match[1])
        if not fixed:
            continue
        titles = _cve_titles(meta.findtext("{*}description", ""))
        rating = SEVERITY.get(meta.findtext("{*}advisory/{*}severity", "").lower(), "unknown")
        for cve in meta.findall("{*}reference[@source='CVE']"):
            key = cve.get("ref_id", "")
            if not CVE_ID.fullmatch(key):
                raise ValueError("Invalid RHSA CVE reference")
            for version in fixed:
                advisories[key, version] = KernelAdvisory(key, rating, name, f"https://access.redhat.com/errata/{name}",
                    issued.get("date"), "kernel", "x86_64", version, title=titles.get(key, title))
    if not advisories:
        raise ValueError("RHSA records could not be matched to archived CentOS builds")
    for (cve, change_version), title in changes.items():
        fixed = next((v for v in ordered if compare_versions(v, change_version) >= 0), None)
        if fixed and (cve, fixed) not in advisories:
            advisories[cve, fixed] = KernelAdvisory(cve, "unknown", f"CentOS kernel {fixed}", VAULT + "repodata/",
                None, "kernel", "x86_64", fixed, title=title)
    return KernelFeedData(tuple(advisories.values()), tuple(KernelBuild("kernel", "x86_64", v) for v in ordered),
                          complete=False, note="CentOS 7.9의 보안 업데이트는 2024-06-30에 종료되었습니다. 이후 공개된 CVE의 영향 여부는 미확인입니다.")


async def fetch_other(client: httpx.AsyncClient, target: KernelTarget, feed: KernelFeed) -> KernelFeedData:
    if target.id == "centos7":
        vault, oval = await asyncio.gather(_repository_xml(client, VAULT, "other"), fetch_bytes(client, RH_OVAL, 16_000_000))
        return await asyncio.to_thread(_centos_data, vault, oval)
    arch = feed.id.split("-", 1)[1]
    xml = await _repository_xml(client, feed.url, "updateinfo")
    return await asyncio.to_thread(_rocky_data, xml, target, arch)
