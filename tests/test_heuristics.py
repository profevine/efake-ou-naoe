from __future__ import annotations

import pytest

from backend.heuristics.domain import (
    extract_domain,
    has_suspicious_tld,
    is_blacklisted,
)
from backend.heuristics.language import find_sensationalist_words
from backend.heuristics.scoring import (
    compute_score,
    has_suspicious_url_pattern,
    verdict_from_score,
)
from backend.models import FactCheckerResult, Signals


# --- extract_domain (regression test for the lstrip("www.") bug) ---

@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.wired.com/article", "wired.com"),
        ("https://wired.com", "wired.com"),
        ("http://www.example.com.br/noticia/123", "example.com.br"),
        ("https://www.example.com:8443/x", "example.com"),
        ("https://user:pass@www.example.com/x", "example.com"),
        ("https://WWW.Example.COM/x", "example.com"),
        # leading 'w' must not be stripped from non-www hosts
        ("https://wikipedia.org", "wikipedia.org"),
    ],
)
def test_extract_domain(url, expected):
    assert extract_domain(url) == expected


def test_extract_domain_invalid():
    assert extract_domain("not a url") in (None, "")


# --- blacklist / TLD ---

def test_is_blacklisted_known_domain():
    assert is_blacklisted("verdade-agora.com") is True
    assert is_blacklisted("g1.globo.com") is False


def test_has_suspicious_tld():
    assert has_suspicious_tld("foo.xyz") is True
    assert has_suspicious_tld("noticias24horas.click") is True
    assert has_suspicious_tld("g1.globo.com") is False


# --- sensationalist words ---

def test_find_sensationalist_words_basic():
    found = find_sensationalist_words("URGENTE: bomba na política, é um escândalo!")
    assert "URGENTE" in found
    assert "BOMBA" in found
    assert "ESCÂNDALO" in found


def test_find_sensationalist_words_dedup_and_empty():
    assert find_sensationalist_words("uma notícia comum e tranquila") == []
    found = find_sensationalist_words("urgente urgente urgente")
    assert found == ["URGENTE"]


def test_find_sensationalist_words_multiword_phrase():
    found = find_sensationalist_words("você não vai acreditar no que aconteceu")
    assert "VOCÊ NÃO VAI ACREDITAR" in found


# --- URL pattern ---

def test_has_suspicious_url_pattern():
    assert has_suspicious_url_pattern("https://x.com/noticia-urgente-aqui")
    assert has_suspicious_url_pattern("https://x.com/post/123456789")
    assert not has_suspicious_url_pattern("https://g1.globo.com/economia")


# --- scoring ---

def _signals(**kw) -> Signals:
    return Signals(**kw)


def test_compute_score_clean_is_zero():
    assert compute_score(_signals()) == 0


def test_compute_score_false_factcheck_pushes_up():
    sig = _signals(
        fact_checkers=[
            FactCheckerResult(source="Lupa", result="FALSO", title="t", url="u")
        ]
    )
    assert compute_score(sig) == 40


def test_compute_score_true_factcheck_pushes_down():
    sig = _signals(
        fact_checkers=[
            FactCheckerResult(source="Lupa", result="VERDADEIRO", title="t", url="u")
        ]
    )
    assert compute_score(sig) == 0  # clamped at 0, not negative


def test_compute_score_clamped_at_100():
    sig = _signals(
        fact_checkers=[
            FactCheckerResult(source="a", result="FALSO", title="t", url="u"),
            FactCheckerResult(source="b", result="FALSO", title="t", url="u"),
        ],
        domain_blacklisted=True,
        domain_age_days=10,
        sensationalist_words=["A", "B", "C", "D", "E"],
        suspicious_url_pattern=True,
    )
    assert compute_score(sig) == 100


@pytest.mark.parametrize(
    "score, verdict",
    [
        (0, "credible"),
        (40, "credible"),
        (41, "suspicious"),
        (65, "suspicious"),
        (66, "fake"),
        (100, "fake"),
    ],
)
def test_verdict_from_score(score, verdict):
    assert verdict_from_score(score)[0] == verdict
