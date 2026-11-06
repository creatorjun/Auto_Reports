# backend/src/infrastructure/external/kernel_rpm.py
import re
from functools import lru_cache

from src.domain.entities.kernel_cve import KernelAdvisory, KernelBuild, KernelFeedData, KernelTarget


_EVR = re.compile(r"(?:(?P<epoch>[0-9]+):)?(?P<version>[0-9][A-Za-z0-9._+~^]*)-(?P<release>[A-Za-z0-9._+~^]+)\Z", re.ASCII)
_SEGMENT = re.compile(r"[0-9]+|[A-Za-z]+|[~^]")
_DISTRO = re.compile(r"(?:^|\.)el(?P<major>[0-9]+)(?P<uek>uek)?(?=[._+~^]|$)")
_ARCH = re.compile(r"\.(x86_64|aarch64|ppc64le|s390x|i[3-6]86)\Z")


@lru_cache(maxsize=4096)
def _parts(value: str) -> tuple[int, str, str]:
    parsed = _EVR.fullmatch(_ARCH.sub("", value)) if len(value) <= 160 else None
    if parsed is None:
        raise ValueError("Epoch(선택), 버전, 릴리스를 포함한 RPM 커널 빌드를 입력하세요.")
    return int(parsed["epoch"] or 0), parsed["version"], parsed["release"]


@lru_cache(maxsize=4096)
def _segments(value: str) -> tuple:
    result = []
    for token in _SEGMENT.findall(value):
        if token == "~":
            result.append((0,))
        elif token == "^":
            result.append((2,))
        elif token.isdigit():
            number = token.lstrip("0")
            result.append((4, len(number), number))
        else:
            result.append((3, token))
    result.append((1,))
    return tuple(result)


def compare_versions(left: str, right: str) -> int:
    le, lv, lr = _parts(left)
    re_, rv, rr = _parts(right)
    left_key = le, _segments(lv), _segments(lr)
    right_key = re_, _segments(rv), _segments(rr)
    return (left_key > right_key) - (left_key < right_key)


def rpm_branch(version: str) -> str:
    return _parts(version)[1]


def validate_build(target: KernelTarget, build: KernelBuild) -> None:
    if build.package not in target.packages or build.architecture not in target.architectures:
        raise ValueError("선택한 OS에서 지원하는 커널 패키지와 아키텍처를 선택하세요.")
    arch = _ARCH.search(build.version)
    if arch and arch[1] != build.architecture:
        raise ValueError("커널 빌드의 아키텍처와 선택한 아키텍처가 다릅니다.")
    _, version, release = _parts(build.version)
    distro = _DISTRO.search(release)
    major = re.search(r"\d+", target.id)
    if not distro or not major or distro["major"] != major[0]:
        raise ValueError("선택한 OS 버전과 일치하는 배포판 커널 RPM 빌드를 입력하세요.")
    if bool(distro["uek"]) != build.package.startswith("kernel-uek"):
        raise ValueError("커널 패키지와 빌드의 UEK 구분이 다릅니다.")
    if target.id == "centos7" and (version != "3.10.0" or not re.fullmatch(r"1160(?:\.[0-9]+)*\.el7", release)):
        raise ValueError("CentOS Linux 7.9.2009에서 제공한 3.10.0-1160 계열 빌드를 입력하세요.")


def same_branch(build: KernelBuild, advisory: KernelAdvisory) -> bool:
    if build.package != advisory.package or build.architecture != advisory.architecture:
        return False
    return rpm_branch(build.version) == (advisory.branch or rpm_branch(advisory.fixed_version))


def matches_build(target: KernelTarget, build: KernelBuild, advisory: KernelAdvisory) -> bool:
    return same_branch(build, advisory) and compare_versions(build.version, advisory.fixed_version) < 0


def coverage_note(target: KernelTarget, build: KernelBuild, data: tuple[KernelFeedData, ...]) -> str | None:
    same_series = False
    for feed in data:
        for known in feed.builds:
            if known.package == build.package and known.architecture == build.architecture:
                if compare_versions(known.version, build.version) == 0:
                    return None
                if rpm_branch(known.version) == rpm_branch(build.version):
                    same_series = True
    if same_series:
        return "공급자 자료에서 입력한 빌드를 확인하지 못했습니다. 같은 커널 계열의 수정 버전과 비교한 결과입니다."
    return "이 패키지·아키텍처·커널 계열의 수정 이력을 수집한 권고에서 확인할 수 없습니다."
