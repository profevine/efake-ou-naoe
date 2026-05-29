from __future__ import annotations
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite

DB_PATH = os.environ.get("EFAKE_DB", "efake.db")
# How long a cached analysis stays fresh, in seconds (default 24h).
# Fact-checker results and domain age change over time, so cached
# verdicts must eventually be recomputed. Set to 0 to disable caching.
CACHE_TTL_SECONDS = int(os.environ.get("EFAKE_CACHE_TTL", str(24 * 60 * 60)))

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS analyses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    input       TEXT    NOT NULL,
    input_hash  TEXT    NOT NULL,
    score       INTEGER NOT NULL,
    verdict     TEXT    NOT NULL,
    label       TEXT    NOT NULL,
    signals     TEXT    NOT NULL,
    analyzed_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_input_hash ON analyses (input_hash);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLE)
        await db.commit()


async def get_cached(input_hash: str) -> Optional[dict]:
    if CACHE_TTL_SECONDS <= 0:
        return None
    # stored as naive UTC (see save_analysis), so compare in the same format
    cutoff = (
        datetime.now(tz=timezone.utc) - timedelta(seconds=CACHE_TTL_SECONDS)
    ).replace(tzinfo=None).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM analyses WHERE input_hash = ? AND analyzed_at >= ? "
            "ORDER BY id DESC LIMIT 1",
            (input_hash, cutoff),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None


async def save_analysis(
    input_text: str,
    input_hash: str,
    score: int,
    verdict: str,
    label: str,
    signals: dict,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO analyses (input, input_hash, score, verdict, label, signals, analyzed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                input_text,
                input_hash,
                score,
                verdict,
                label,
                json.dumps(signals, ensure_ascii=False),
                datetime.now(tz=timezone.utc).replace(tzinfo=None).isoformat(),
            ),
        )
        await db.commit()


async def get_history(limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, input, score, verdict, label, analyzed_at FROM analyses ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
