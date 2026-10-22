# backend/src/infrastructure/external/security_cve_provenance.py
import re
from dataclasses import replace
from urllib.parse import urlsplit

from src.domain.entities.security_news import SecurityCveRemediation


MANUFACTURERS = {
    "apache.org": ("apache", "apache software foundation"),
    "cisco.com": ("cisco", "cisco systems"),
    "microsoft.com": ("microsoft",),
    "mozilla.org": ("mozilla", "mozilla foundation"),
    "oracle.com": ("oracle",),
    "php.net": ("php", "php group", "php foundation"),
    "redhat.com": ("redhat", "red hat"),
}


def manufacturer_remediations(entries: tuple[SecurityCveRemediation, ...], source: object, references: object) -> tuple[SecurityCveRemediation, ...]:
    if not isinstance(source, str) or not re.fullmatch(r"[^\s@]+@[^\s@]+", source):
        return entries
    publisher = source.casefold()
    domain = publisher.rsplit("@", 1)[1]
    aliases = MANUFACTURERS.get(domain)
    if not aliases or not isinstance(references, list):
        return entries
    urls = []
    for reference in references:
        if not isinstance(reference, dict) or str(reference.get("source", "")).casefold() != publisher:
            continue
        tags, url = reference.get("tags"), reference.get("url")
        if not isinstance(tags, list) or "Vendor Advisory" not in tags or not isinstance(url, str):
            continue
        if len(url) > 4096 or any(ord(char) < 33 for char in url):
            continue
        try:
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            if parsed.scheme != "https" or parsed.username is not None or parsed.password is not None or parsed.port not in {None, 443}:
                continue
            if host != domain and not host.endswith("." + domain):
                continue
        except ValueError:
            continue
        urls.append(url)
    if not urls:
        return entries
    normalize = lambda value: re.sub(r"[\W_]", "", value).casefold()
    names = {normalize(alias) for alias in aliases}
    result = []
    for entry in entries:
        matches = normalize(entry.vendor or "") in names if entry.vendor else any(
            entry.product.casefold().startswith(alias + " ") for alias in aliases
        )
        if entry.fixed_version and entry.fixed_version_basis == "description" and matches:
            result.append(replace(entry, fixed_version_basis="vendor", reference_url=urls[0]))
        else:
            result.append(entry)
    return tuple(result)
