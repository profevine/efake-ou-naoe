from __future__ import annotations
import httpx
from bs4 import BeautifulSoup
from .base import BaseScraper
from ..models import FactCheckerResult

# Label keywords that Lupa uses in its verdicts
_VERDICT_MAP = {
    "falso": "FALSO",
    "verdadeiro": "VERDADEIRO",
    "exagerado": "ENGANOSO",
    "distorcido": "ENGANOSO",
    "insustentável": "ENGANOSO",
    "contraditório": "ENGANOSO",
    "inconclusivo": "INCONCLUSIVO",
    "de olho": "INCONCLUSIVO",
}


def _classify(text: str) -> str:
    low = text.lower()
    for key, val in _VERDICT_MAP.items():
        if key in low:
            return val
    return "INCONCLUSIVO"


class LupaScraper(BaseScraper):
    name = "Agência Lupa"

    async def _search(
        self, client: httpx.AsyncClient, query: str
    ) -> list[FactCheckerResult]:
        url = f"https://lupa.uol.com.br/?s={httpx.QueryParams({'s': query})['s']}"
        resp = await client.get(url)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        results: list[FactCheckerResult] = []
        for article in soup.select("article.post")[:5]:
            title_tag = article.select_one("h2.entry-title a, h3.entry-title a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get("href", "")
            label_tag = article.select_one(".lupa-label, .post-categoria, .category")
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
