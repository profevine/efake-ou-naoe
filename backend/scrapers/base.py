from __future__ import annotations
import httpx
from abc import ABC, abstractmethod
from ..models import FactCheckerResult

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}
TIMEOUT = 10.0


class BaseScraper(ABC):
    name: str

    async def search(self, query: str) -> list[FactCheckerResult]:
        try:
            async with httpx.AsyncClient(
                headers=HEADERS, timeout=TIMEOUT, follow_redirects=True
            ) as client:
                return await self._search(client, query)
        except Exception:
            return []

    @abstractmethod
    async def _search(
        self, client: httpx.AsyncClient, query: str
    ) -> list[FactCheckerResult]: ...
