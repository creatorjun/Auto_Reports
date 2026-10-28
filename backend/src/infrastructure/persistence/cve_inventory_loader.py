# backend/src/infrastructure/persistence/cve_inventory_loader.py
import asyncio
import hashlib
import json
import re
from pathlib import Path

from src.application.ports.cve_inventory_port import CveInventoryLoaderPort
from src.domain.entities.cve_inventory import CveInventory, CveInventoryPackage


MAX_INVENTORY_BYTES = 32 * 1024 * 1024
MAX_INVENTORY_TARGETS = 50000
MAVEN_NAME = re.compile(r"[A-Za-z0-9_.-]+:[A-Za-z0-9_.-]+\Z")
NPM_NAME = re.compile(r"(?:@[A-Za-z0-9_.-]+/)?[A-Za-z0-9_][A-Za-z0-9_.-]*\Z")
RPM_NAME = re.compile(r"[A-Za-z0-9_+][A-Za-z0-9_.+-]*\Z")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate inventory property")
        result[key] = value
    return result


def _text(value, *, required=False, maximum=1000):
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError("Invalid inventory text")
    return value.strip()


def _identity(target):
    identifiers = target.get("identifiers")
    if not isinstance(identifiers, dict):
        raise ValueError("Invalid inventory identifiers")
    coordinates = identifiers.get("maven_coordinates")
    group = identifiers.get("maven_group_id")
    artifact = identifiers.get("maven_artifact_id")
    if coordinates and isinstance(coordinates, str) and MAVEN_NAME.fullmatch(coordinates):
        if (group and coordinates.split(":")[0] != group) or (artifact and coordinates.split(":")[1] != artifact):
            return None
        return "Maven", coordinates
    if isinstance(group, str) and isinstance(artifact, str) and MAVEN_NAME.fullmatch(f"{group}:{artifact}"):
        return "Maven", f"{group}:{artifact}"
    npm = identifiers.get("npm_name")
    if isinstance(npm, str) and NPM_NAME.fullmatch(npm):
        return "npm", npm
    return None


def _rpm_identity(target):
    rpm = target.get("rpm")
    if not isinstance(rpm, dict) or rpm.get("distribution_id") != "ol":
        return None
    distribution = rpm.get("distribution_version")
    name = rpm.get("package_name")
    if not isinstance(distribution, str) or distribution.split(".")[0] != "8" or not isinstance(name, str) or not RPM_NAME.fullmatch(name):
        return None
    if name != target.get("name"):
        return None
    return name


def parse_cve_inventory(raw: bytes) -> CveInventory:
    if len(raw) > MAX_INVENTORY_BYTES:
        raise ValueError("Inventory exceeds size limit")
    data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_object)
    if not isinstance(data, dict) or data.get("schema_version") != "1.0.0":
        raise ValueError("Unsupported inventory schema")
    declared_id = _text(data.get("dataset_id"), required=True)
    products, targets = data.get("products"), data.get("targets")
    if not isinstance(products, dict) or not isinstance(targets, dict) or not targets or len(targets) > MAX_INVENTORY_TARGETS:
        raise ValueError("Invalid inventory products or targets")
    environment = data.get("environment", {})
    if not isinstance(environment, dict):
        raise ValueError("Invalid inventory environment")
    for product_id, product in products.items():
        if not isinstance(product, dict) or product.get("id") != product_id:
            raise ValueError("Invalid inventory product identity")
        _text(product.get("name"), required=True)
        _text(product.get("category"), required=True)
        links = product.get("target_ids")
        if not isinstance(links, list) or any(not isinstance(link, str) for link in links) or len(set(links)) != len(links):
            raise ValueError("Invalid inventory product target links")
        if any(not isinstance(link, str) or link not in targets or not isinstance(targets[link], dict) or targets[link].get("product_id") != product_id for link in links):
            raise ValueError("Unresolved inventory product target link")
    kernel_rpms, sibling_identities = {}, {}
    for target in targets.values():
        if not isinstance(target, dict):
            raise ValueError("Invalid inventory target")
        matching = target.get("matching")
        if not isinstance(matching, dict):
            raise ValueError("Invalid inventory matching metadata")
        if matching.get("route") not in {"parent_product_advisory", "distribution_vendor_advisory", "vendor_advisory"}:
            identity = _identity(target)
            artifact = target["identifiers"].get("maven_artifact_id")
            if identity and isinstance(artifact, str):
                sibling_identities.setdefault((target.get("product_id"), target.get("ecosystem"), artifact), set()).add(identity)
        if isinstance(target, dict) and _rpm_identity(target) == "kernel-uek":
            rpm = target["rpm"]
            release = f"{rpm.get('version')}-{rpm.get('release')}.{rpm.get('architecture')}"
            kernel_rpms[release] = target
    grouped = {}
    for target_id, target in targets.items():
        if not isinstance(target, dict) or target.get("id") != target_id or target.get("product_id") not in products:
            raise ValueError("Invalid inventory target identity")
        product = products[target["product_id"]]
        if target_id not in product["target_ids"]:
            raise ValueError("Unlinked inventory target")
        name = _text(target.get("name"), required=True)
        ecosystem = _text(target.get("ecosystem"), required=True)
        confidence = _text(target.get("version_status"), required=True)
        version = _text(target.get("current_version")) or _text(target.get("display_version"), required=True)
        matching = target.get("matching")
        if not isinstance(matching, dict):
            raise ValueError("Invalid inventory matching metadata")
        route = matching.get("route")
        identity = _identity(target) if route not in {"parent_product_advisory", "distribution_vendor_advisory", "vendor_advisory"} else None
        inherited_identity = False
        if identity is None and route == "identity_mapping_required":
            identifiers = target["identifiers"]
            artifact = identifiers.get("maven_artifact_id")
            if isinstance(artifact, str) and not identifiers.get("maven_coordinates") and not identifiers.get("maven_group_id"):
                candidates = sibling_identities.get((target["product_id"], target["ecosystem"], artifact), set())
                if len(candidates) == 1:
                    identity = next(iter(candidates))
                    inherited_identity = True
        rpm_target = target
        rpm_name = _rpm_identity(target)
        if target.get("identifiers", {}).get("source_identifier") == "kernel:uname-r" and version in kernel_rpms:
            rpm_target = kernel_rpms[version]
            rpm_name = "kernel-uek"
        source, query_name, query_ecosystem = "unmapped", None, None
        mapping_reason = ", ".join(str(x) for x in matching.get("review_reasons", []) if isinstance(x, str)) or "package_identity_mapping_required"
        distribution_id, distribution_version, rpm_vendor = None, None, None
        if identity:
            ecosystem, query_name = identity
            query_ecosystem, source = ecosystem, "osv"
            key = (source, ecosystem, query_name)
            name, mapping_reason = query_name, "same_product_exact_artifact_identity" if inherited_identity else None
        elif rpm_name:
            rpm = rpm_target["rpm"]
            source, ecosystem, query_name, query_ecosystem = "oracle", "RPM", rpm_name, "OracleLinux:8"
            distribution_id, distribution_version = "ol", "8"
            rpm_vendor = _text(rpm.get("package_vendor"))
            version = _text(rpm.get("evr"), required=True)
            key = (source, "OracleLinux:8", rpm_name)
            name, mapping_reason = rpm_name, None
        else:
            key = (source, target_id)
        row = grouped.setdefault(key, dict(name=name, ecosystem=ecosystem, versions=set(), product_ids=set(), product_names=set(), categories=set(), target_ids=set(), confidences=set(), query_name=query_name, query_ecosystem=query_ecosystem, source=source, mapping_reason=mapping_reason, distribution_id=distribution_id, distribution_version=distribution_version, rpm_vendors=set()))
        row["versions"].add(version)
        row["product_ids"].add(target["product_id"])
        row["product_names"].add(product["name"])
        row["categories"].add(product["category"])
        row["target_ids"].add(target_id)
        row["confidences"].add(confidence)
        if inherited_identity:
            row["confidences"].add("identity_inferred")
            row["mapping_reason"] = "same_product_exact_artifact_identity"
        row["rpm_vendors"].add(rpm_vendor)
    packages = []
    for key, row in grouped.items():
        confidences = row.pop("confidences")
        vendors = row.pop("rpm_vendors")
        for field in ("versions", "product_ids", "product_names", "categories", "target_ids"):
            row[field] = tuple(sorted(row[field]))
        packages.append(CveInventoryPackage(
            id="pkg_" + hashlib.sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest()[:24],
            mapping_status="ready" if row["source"] != "unmapped" else "mapping_required",
            version_confidence=next(iter(confidences)) if len(confidences) == 1 else "mixed",
            rpm_vendor=next(iter(vendors)) if len(vendors) == 1 else None,
            **row,
        ))
    return CveInventory(
        dataset_id=f"{declared_id}:inventory:{hashlib.sha256(raw).hexdigest()}",
        snapshot_at=_text(data.get("snapshot_at")),
        packages=tuple(sorted(packages, key=lambda row: (row.name.casefold(), row.id))),
        product_count=len(products), target_count=len(targets),
        runtime_verified=environment.get("runtime_loading_verified") is True,
    )


class JsonCveInventoryLoader(CveInventoryLoaderPort):
    def __init__(self, path: str | Path):
        self._path = Path(path)

    def _load(self) -> CveInventory:
        with self._path.open("rb") as stream:
            raw = stream.read(MAX_INVENTORY_BYTES + 1)
        return parse_cve_inventory(raw)

    async def load(self) -> CveInventory:
        return await asyncio.to_thread(self._load)
