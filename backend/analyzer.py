from __future__ import annotations
import asyncio
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from .models import AnalyzeResult, Signals
from .scrapers.lupa import LupaScraper
from .scrapers.aosfatos import AosFatosScraper
from .scrapers.afp import AFPScraper
from .scrapers.boatos import BoatosScraper
from .heuristics.domain import extract_domain, is_blacklisted, get_domain_age_days, has_suspicious_tld
from .heuristics.language import find_sensationalist_words
from .heuristics.scoring import compute_score, verdict_from_score, has_suspicious_url_pattern
from . import database

_SCRAPERS = [LupaScraper(), AosFatosScraper(), AFPScraper(), BoatosScraper()]


def _input_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


def _is_url(text: str) -> bool:
    try:
        result = urlparse(text.strip())
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


def _extract_query(text: str) -> str:
    """Use domain + path keywords for URL inputs, or first ~120 chars for plain text."""
    if _is_url(text):
        parsed = urlparse(text.strip())
        path_words = parsed.path.replace("/", " ").replace("-", " ").replace("_", " ")
        return (parsed.netloc + " " + path_words).strip()[:120]
    return text.strip()[:120]


async def analyze(input_text: str) -> AnalyzeResult:
    input_clean = input_text.strip()
    h = _input_hash(input_clean)

    cached_row = await database.get_cached(h)
    if cached_row:
        import json
        signals_data = json.loads(cached_row["signals"])
        signals = Signals(**signals_data)
        verdict, label = verdict_from_score(cached_row["score"])
        return AnalyzeResult(
            input=cached_row["input"],
            score=cached_row["score"],
            verdict=verdict,
            label=label,
            signals=signals,
            cached=True,
            analyzed_at=datetime.fromisoformat(cached_row["analyzed_at"]).replace(
                tzinfo=timezone.utc
            ),
        )

    query = _extract_query(input_clean)

    # Run all scrapers in parallel
    fc_results_list = await asyncio.gather(
        *[s.search(query) for s in _SCRAPERS], return_exceptions=True
    )
    fact_checkers = []
    for res in fc_results_list:
        if isinstance(res, list):
            fact_checkers.extend(res)

    # Domain heuristics (only for URLs)
    domain_blacklisted = False
    domain_age_days = None
    suspicious_url = False
    if _is_url(input_clean):
        domain = extract_domain(input_clean)
        if domain:
            domain_blacklisted = is_blacklisted(domain) or has_suspicious_tld(domain)
            domain_age_days = await asyncio.get_event_loop().run_in_executor(
                None, get_domain_age_days, domain
            )
        suspicious_url = has_suspicious_url_pattern(input_clean)

    sensationalist = find_sensationalist_words(input_clean)

    signals = Signals(
        fact_checkers=fact_checkers,
        domain_blacklisted=domain_blacklisted,
        domain_age_days=domain_age_days,
        sensationalist_words=sensationalist,
        suspicious_url_pattern=suspicious_url,
    )

    score = compute_score(signals)
    verdict, label = verdict_from_score(score)
    now = datetime.now(tz=timezone.utc)

    await database.save_analysis(
        input_text=input_clean,
        input_hash=h,
        score=score,
        verdict=verdict,
        label=label,
        signals=signals.model_dump(),
    )

    return AnalyzeResult(
        input=input_clean,
        score=score,
        verdict=verdict,
        label=label,
        signals=signals,
        cached=False,
        analyzed_at=now,
    )
