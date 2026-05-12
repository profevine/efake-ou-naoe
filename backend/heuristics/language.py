from __future__ import annotations
import os
import re

_WORDS: list[str] = []
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def _load_words() -> None:
    path = os.path.join(_DATA_DIR, "sensationalist_words.txt")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    _WORDS.append(line.lower())
    except FileNotFoundError:
        pass


_load_words()


def find_sensationalist_words(text: str) -> list[str]:
    low = text.lower()
    found = []
    for word in _WORDS:
        # word boundary match — handle accents via simple contains
        pattern = re.escape(word)
        if re.search(r'\b' + pattern + r'\b', low):
            found.append(word.upper())
        elif len(word) > 8 and word in low:
            found.append(word.upper())
    return list(dict.fromkeys(found))  # deduplicate, preserve order
