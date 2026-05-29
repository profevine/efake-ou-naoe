from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import whois  # python-whois

_BLACKLIST: set[str] = set()
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _load_blacklist() -> None:
    path = os.path.join(_DATA_DIR, "fake_domains.txt")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    _BLACKLIST.add(line.lower())
    except FileNotFoundError:
        pass


_load_blacklist()

# TLDs commonly associated with low-quality news sites
_SUSPICIOUS_TLDS = {".click", ".xyz", ".top", ".info", ".biz", ".site", ".online", ".tk"}


def extract_domain(url: str) -> Optional[str]:
    try:
        netloc = urlparse(url).netloc.lower()
        # strip credentials and port, then the leading "www." label
        netloc = netloc.rsplit("@", 1)[-1].split(":", 1)[0]
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc or None
    except Exception:
        return None


def is_blacklisted(domain: str) -> bool:
    return domain in _BLACKLIST


def has_suspicious_tld(domain: str) -> bool:
    for tld in _SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            return True
    return False


def get_domain_age_days(domain: str) -> Optional[int]:
    try:
        w = whois.whois(domain)
        created = w.creation_date
        if isinstance(created, list):
            created = created[0]
        if created is None:
            return None
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = (datetime.now(tz=timezone.utc) - created).days
        return max(age, 0)
    except Exception:
        return None
