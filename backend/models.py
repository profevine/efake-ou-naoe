from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    input: str  # URL or raw text


class FactCheckerResult(BaseModel):
    source: str
    result: str  # "FALSO" | "VERDADEIRO" | "ENGANOSO" | "INCONCLUSIVO"
    title: str
    url: str


class Signals(BaseModel):
    fact_checkers: list[FactCheckerResult] = []
    domain_blacklisted: bool = False
    domain_age_days: Optional[int] = None
    sensationalist_words: list[str] = []
    suspicious_url_pattern: bool = False


class AnalyzeResult(BaseModel):
    input: str
    score: int
    verdict: str       # "credible" | "suspicious" | "fake"
    label: str         # human-readable PT-BR
    signals: Signals
    cached: bool = False
    analyzed_at: datetime


class HistoryItem(BaseModel):
    id: int
    input: str
    score: int
    verdict: str
    label: str
    analyzed_at: datetime
