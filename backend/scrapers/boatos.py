from __future__ import annotations
import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper
from ..models import FactCheckerResult

# Boatos.org focuses on debunking; presence = boato (fake/suspicious)
_TRUE_KEYWORDS = ["verdade", "verdadeiro", "confirmado", "real"]


def _classify(title: str, excerpt: str) -> str:
    text = (title + " " + excerpt).lower()
    for kw in _TRUE_KEYWORDS:
        if kw in text:
            return "VERDADEIRO"
    # Default for boatos.org: if found, the content is likely being debunked
    return "FALSO"


class BoatosScraper(BaseScraper):
    name = "Boatos.org"

    async def _search(
        self, client: httpx.AsyncClient, query: str
    ) -> list[FactCheckerResult]:
        url = f"https://www.boatos.org/?s={httpx.QueryParams({'s': query})['s']}"
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        results: list[FactCheckerResult] = []
        for article in soup.select("article")[:5]:
            title_tag = article.select_one("h2.entry-title a, h1.entry-title a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            excerpt_tag = article.select_one(".entry-summary, .entry-content p")
            excerpt = excerpt_tag.get_text(strip=True) if excerpt_tag else ""
            verdict = _classify(title, excerpt)
            results.append(
                FactCheckerResult(
                    source=self.name,
                    result=verdict,
                    title=title,
                    url=link,
                )
            )
        return results
