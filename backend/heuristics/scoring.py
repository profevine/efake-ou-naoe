from __future__ import annotations
import re
from ..models import Signals

# Suspicious path patterns in URLs
_SUSPICIOUS_URL_RE = re.compile(
    r"(noticia[-_]urgente|urgente[-_]|bomba[-_]|exclusivo[-_]|"
    r"chocante|inacreditavel|voce[-_]nao[-_]vai[-_]acreditar|"
    r"\d{8,})",
    re.IGNORECASE,
)


def has_suspicious_url_pattern(url: str) -> bool:
    return bool(_SUSPICIOUS_URL_RE.search(url))


def compute_score(signals: Signals) -> int:
    score = 0

    for fc in signals.fact_checkers:
        if fc.result == "FALSO":
            score += 40
        elif fc.result == "ENGANOSO":
            score += 25
        elif fc.result == "VERDADEIRO":
            score -= 30
        else:
            score += 5  # found but inconclusive: slight nudge

    # not finding results is neutral — don't add points

    if signals.domain_blacklisted:
        score += 35

    if signals.domain_age_days is not None and signals.domain_age_days < 90:
        score += 15

    word_count = len(signals.sensationalist_words)
    if word_count >= 5:
        score += 45
    elif word_count >= 3:
        score += 25
    elif word_count >= 1:
        score += 10

    if signals.suspicious_url_pattern:
        score += 10

    return max(0, min(100, score))


def verdict_from_score(score: int) -> tuple[str, str]:
    if score <= 40:
        return "credible", "Provavelmente verdadeiro"
    if score <= 65:
        return "suspicious", "Suspeito — verifique as fontes"
    return "fake", "Provavelmente falso"
