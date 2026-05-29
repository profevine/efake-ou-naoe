from __future__ import annotations

from backend.analyzer import _extract_query, _input_hash, _is_url


def test_is_url():
    assert _is_url("https://example.com/a")
    assert _is_url("http://example.com")
    assert not _is_url("apenas um texto solto")
    assert not _is_url("ftp://example.com")


def test_input_hash_is_normalized():
    # hashing ignores surrounding whitespace and case
    assert _input_hash("  Texto  ") == _input_hash("texto")


def test_extract_query_for_url_uses_domain_and_path():
    q = _extract_query("https://site.com/uma-noticia-importante")
    assert "site.com" in q
    assert "uma noticia importante" in q


def test_extract_query_for_text_truncates():
    long_text = "palavra " * 50
    assert len(_extract_query(long_text)) <= 120
