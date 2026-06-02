from __future__ import annotations

import re
from collections import Counter
from typing import Any


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
    "their", "this", "to", "was", "were", "with", "without", "about", "after",
    "before", "between", "can", "could", "may", "might", "must", "not", "will",
    "would", "you", "your", "i", "we", "they", "he", "she", "them", "his",
    "her", "our", "us", "do", "does", "did", "doing", "done", "new", "latest",
    "tom", "tat", "giup", "minh", "bai", "bao", "nay", "ve", "va", "cho",
    "toi", "hay", "tren", "duoi", "cac", "mot", "nhung", "la", "co", "cua",
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w][\w.+#-]{1,}", text, flags=re.UNICODE)


def _keyword_score(token: str) -> tuple[int, int, str]:
    has_digit = int(any(ch.isdigit() for ch in token))
    has_upper = int(any(ch.isupper() for ch in token[1:]))
    return (has_digit + has_upper, len(token), token.lower())


def _entities(text: str, limit: int) -> list[str]:
    # Capitalized spans and acronyms are a cheap local signal for named entities.
    pattern = r"\b(?:[A-Z][\w.+#-]*|[A-Z]{2,})(?:\s+(?:[A-Z][\w.+#-]*|[A-Z]{2,}))*"
    seen: set[str] = set()
    entities: list[str] = []
    for match in re.finditer(pattern, text):
        value = re.sub(r"\s+", " ", match.group(0)).strip()
        key = value.lower()
        if len(value) < 2 or key in seen:
            continue
        seen.add(key)
        entities.append(value)
        if len(entities) >= limit:
            break
    return entities


def extract_keywords(text: str, max_keywords: int = 8, include_entities: bool = True) -> dict[str, Any]:
    clean_text = (text or "").strip()
    limit = max(1, min(int(max_keywords or 8), 25))
    words = _tokens(clean_text)
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}

    for word in words:
        normalized = word.strip("._-").lower()
        if len(normalized) < 3 or normalized in STOPWORDS:
            continue
        counts[normalized] += 1
        display.setdefault(normalized, word.strip("._-"))

    ranked = sorted(
        counts,
        key=lambda item: (counts[item], *_keyword_score(display[item])),
        reverse=True,
    )
    keywords = [display[item] for item in ranked[:limit]]
    entities = _entities(clean_text, limit) if include_entities else []

    return {
        "tool": "extract_keywords",
        "keywords": keywords,
        "entities": entities,
        "count": len(keywords),
        "source_chars": len(clean_text),
    }
