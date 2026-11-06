# backend/src/infrastructure/external/oracle_kernel_cve.py
import asyncio
import bz2
import io
import re
from datetime import date

import httpx
from defusedxml import ElementTree

from src.domain.entities.kernel_cve import KernelAdvisory, KernelBuild, KernelFeed, KernelFeedData, KernelTarget
from src.infrastructure.external.kernel_feed_http import fetch_bytes
from src.infrastructure.external.kernel_rpm import rpm_branch, validate_build


_OVAL = "{http://oval.mitre.org/XMLSchema/oval-definitions-5}"
_LINUX = "{http://oval.mitre.org/XMLSchema/oval-definitions-5#linux}"
_FIX = re.compile(r"(kernel(?:-uek)?(?:-core)?) is earlier than ([^\s]+)\Z")
_CVE = re.compile(r"CVE-[0-9]{4}-[0-9]{4,}\Z")
_ADVISORY = re.compile(r"EL[SBE]A-[0-9]{4}-[0-9]+(?:-[0-9]+)?\Z")
_RISK = {"CRITICAL": "critical", "IMPORTANT": "high", "MODERATE": "medium", "LOW": "low"}
_PUBLIC_CHANNEL = re.compile(r"(?:baseos_|optional_)?(?:base|patch|latest|latest_archive|latest_ELS)|UEKR[0-9]+(?:_archive|_ELS)?")
_MAX_ARCHIVE = 24 * 1024**2
_MAX_XML = 240 * 1024**2
ORACLE_TARGETS = tuple(
    KernelTarget(
        id=f"ol{major}", label=f"Oracle Linux {major}",
        packages=("kernel", "kernel-uek") if major == 7 else ("kernel", "kernel-core", "kernel-uek", "kernel-uek-core"),
        architectures=("x86_64", "aarch64"),
        feeds=(KernelFeed(f"oracle-oval-{major}", f"Oracle Linux {major} ELSA OVAL",
                          f"https://linux.oracle.com/security/oval/com.oracle.elsa-ol{major}.xml.bz2"),),
        coverage="Oracle ELSA 전체 기간의 표준 RHCK·UEK 업데이트 계열을 비교합니다. 위험도는 CVSS 3 점수 또는 권고 등급입니다. MODRHCK·개발 전용 채널, Ksplice 상태와 미수정 취약점은 포함하지 않습니다.",
    ) for major in (7, 8, 9)
)


class _LimitedReader:
    def __init__(self, stream):
        self.stream = stream
        self.remaining = _MAX_XML

    def read(self, n):
        data = self.stream.read(min(n, self.remaining + 1))
        self.remaining -= len(data)
        if self.remaining < 0:
            raise ValueError("Oracle OVAL XML exceeds the limit")
        return data


def _kernel_leaves(criteria, target, inherited=()):
    if criteria.get("negate", "false") == "true":
        return
    direct = criteria.findall(_OVAL + "criterion")
    if criteria.get("operator", "AND") == "AND":
        inherited += tuple((n.get("comment", ""), n.get("negate") == "true") for n in direct)
    guards = {text for text, negated in inherited if not negated}
    os_guard = f"{target.label} is installed"
    for item in direct:
        fix = _FIX.fullmatch(item.get("comment", ""))
        if not fix or item.get("negate") == "true" or os_guard not in guards or fix[1] not in target.packages:
            continue
        archs = [a for a in target.architectures if f"Oracle Linux arch is {a}" in guards]
        allowed = {os_guard, item.get("comment"), f"{fix[1]} is signed with the {target.label} key"}
        allowed.update(f"Oracle Linux arch is {a}" for a in archs)
        if len(archs) != 1 or guards - allowed or any(neg for _, neg in inherited):
            raise ValueError("Unrecognized condition on Oracle kernel package")
        yield item.get("test_ref"), KernelBuild(fix[1], archs[0], fix[2])
    for child in criteria.findall(_OVAL + "criteria"):
        yield from _kernel_leaves(child, target, inherited)


def _in_standard_channel(meta, target):
    platform = f":oracle:linux:{target.id[2:]}:"
    channels = [(n.text or "").strip().rsplit(":", 1)[-1] for n in meta.iter(_OVAL + "cpe") if platform in (n.text or "")]
    if not channels:
        raise ValueError("Missing Oracle kernel advisory channel")
    return any(_PUBLIC_CHANNEL.fullmatch(channel) for channel in channels)


def _metadata(meta):
    advisory = meta.find(_OVAL + "advisory")
    if advisory is None:
        raise ValueError("Missing Oracle erratum metadata")
    refs = meta.findall(_OVAL + "reference")
    identifier = next((r.get("ref_id", "") for r in refs if r.get("source", "").lower() in {"elsa", "elba", "elea"}), "")
    if not _ADVISORY.fullmatch(identifier):
        raise ValueError("Invalid Oracle erratum identifier")
    issued = advisory.find(_OVAL + "issued")
    issued_at = date.fromisoformat(issued.get("date")).isoformat() if issued is not None else None
    title = " ".join((meta.findtext(_OVAL + "title") or "").split())
    risk = _RISK.get((advisory.findtext(_OVAL + "severity") or "").strip().upper(), "unknown")
    cves = {r.get("ref_id"): risk for r in refs if r.get("source", "").upper() == "CVE"}
    for cve in advisory.findall(_OVAL + "cve"):
        severity = risk
        score = (cve.get("cvss3") or "").partition("/")[0]
        if re.fullmatch(r"(?:[0-9](?:\.[0-9])?|10(?:\.0)?)", score):
            value = float(score)
            severity = "critical" if value >= 9 else "high" if value >= 7 else "medium" if value >= 4 else "low" if value > 0 else "unknown"
        cves[(cve.text or "").strip()] = severity
    if any(not _CVE.fullmatch(c or "") for c in cves):
        raise ValueError("Invalid CVE in Oracle kernel erratum")
    return identifier, issued_at, title, cves


def parse_oracle_kernel(payload: bytes, target: KernelTarget) -> KernelFeedData:
    if len(payload) > _MAX_ARCHIVE or not payload.startswith(b"BZh"):
        raise ValueError("Invalid Oracle OVAL archive")
    expected, tests, objects, states = {}, {}, {}, {}
    pending_objects, pending_states = set(), set()
    advisories, builds = [], set()
    with bz2.BZ2File(io.BytesIO(payload)) as source:
        events = ElementTree.iterparse(_LimitedReader(source), events=("start", "end"), forbid_dtd=True)
        if next(events)[1].tag != _OVAL + "oval_definitions":
            raise ValueError("Invalid Oracle OVAL root")
        for event, node in events:
            if event != "end":
                continue
            if node.tag == _OVAL + "definition":
                criteria = node.find(_OVAL + "criteria")
                entries = tuple(_kernel_leaves(criteria, target)) if criteria is not None else ()
                meta = node.find(_OVAL + "metadata")
                if entries and _in_standard_channel(meta, target):
                    identifier, issued_at, title, cves = _metadata(meta)
                    for ref, build in entries:
                        validate_build(target, build)
                        if not ref or expected.setdefault(ref, (build.package, build.version)) != (build.package, build.version):
                            raise ValueError("Conflicting Oracle package test")
                        builds.add(build)
                        advisories.extend(KernelAdvisory(
                            cve_id=cve, severity=risk, advisory_id=identifier,
                            advisory_url=f"https://linux.oracle.com/errata/{identifier}.html",
                            issued_at=issued_at, package=build.package, architecture=build.architecture,
                            fixed_version=build.version, branch=rpm_branch(build.version), title=title,
                        ) for cve, risk in cves.items())
                node.clear()
            elif node.tag.endswith("_test"):
                key = node.get("id")
                if key in expected:
                    obj, state = node.findall(_LINUX + "object"), node.findall(_LINUX + "state")
                    if node.tag != _LINUX + "rpminfo_test" or len(obj) != 1 or len(state) != 1:
                        raise ValueError("Incomplete Oracle kernel package test")
                    a, b = obj[0].get("object_ref"), state[0].get("state_ref")
                    tests[key] = a, b
                    pending_objects.add(a)
                    pending_states.add(b)
                node.clear()
            elif node.tag.endswith("_object"):
                if node.get("id") in pending_objects:
                    name = node.find(_LINUX + "name")
                    if node.tag == _LINUX + "rpminfo_object" and name is not None and name.get("operation", "equals") == "equals":
                        objects[node.get("id")] = (name.text or "").strip()
                node.clear()
            elif node.tag.endswith("_state"):
                if node.get("id") in pending_states:
                    evr = node.find(_LINUX + "evr")
                    if node.tag == _LINUX + "rpminfo_state" and evr is not None and evr.get("operation") == "less than":
                        value = (evr.text or "").strip()
                        version = node.find(_LINUX + "version")
                        if len(node) == 1 or (len(node) == 2 and version is not None and version.get("operation") in {"pattern match", "equals"} and (version.text or "").strip() == rpm_branch(value)):
                            states[node.get("id")] = value
                node.clear()
    if not builds or not advisories or set(tests) != set(expected):
        raise ValueError("Incomplete Oracle kernel OVAL feed")
    for ref, (o, s) in tests.items():
        if expected[ref] != (objects.get(o), states.get(s)):
            raise ValueError("Oracle package condition differs from formal RPM criteria")
    return KernelFeedData(tuple(dict.fromkeys(advisories)), tuple(sorted(builds, key=lambda b: (b.package, b.architecture, b.version))))


async def fetch_oracle(client: httpx.AsyncClient, target: KernelTarget, feed: KernelFeed) -> KernelFeedData:
    if target not in ORACLE_TARGETS or feed not in target.feeds:
        raise ValueError("Unknown Oracle kernel feed")
    payload = await fetch_bytes(client, feed.url, _MAX_ARCHIVE)
    return await asyncio.to_thread(parse_oracle_kernel, payload, target)
