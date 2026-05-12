from __future__ import annotations
import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper
from ..models import FactCheckerResult

_VERDICT_MAP = {
    "falso": "FALSO",
    "verdadeiro": "VERDADEIRO",
    "enganoso": "ENGANOSO",
    "distorcido": "ENGANOSO",
    "impreciso": "ENGANOSO",
    "exagerado": "ENGANOSO",
    "inconclusivo": "INCONCLUSIVO",
}


def _classify(text: str) -> str:
    low = text.lower()
    for key, val in _VERDICT_MAP.items():
        if key in low:
            return val
    return "INCONCLUSIVO"


class AosFatosScraper(BaseScraper):
    name = "Aos Fatos"

    async def _search(
        self, client: httpx.AsyncClient, query: str
    ) -> list[FactCheckerResult]:
        url = f"https://www.aosfatos.org/?s={httpx.QueryParams({'s': query})['s']}"
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        results: list[FactCheckerResult] = []
        for card in soup.select("article, .card, .search-result")[:5]:
            title_tag = card.select_one("h2 a, h3 a, .entry-title a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            label_tag = card.select_one(".veredicto, .verdict, .label, .tag")
            raw_label = label_tag.get_text(strip=True) if label_tag else ""
            verdict = _classify(raw_label or title)
            results.append(
                FactCheckerResult(
                    source=self.name,
                    result=verdict,
                    title=title,
                    url=link,
                )
            )
        return results
