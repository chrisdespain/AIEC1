import re
from collections import defaultdict

_store: dict[str, str] = {}
_freq: dict[str, int] = defaultdict(int)

def normalize(query: str) -> str:
    cleaned = re.sub(r'[^\w\s]', '', query.lower())
    return re.sub(r'\s+', ' ', cleaned).strip()

def get(query: str) -> str | None:
    return _store.get(normalize(query))

def put(query: str, answer: str) -> None:
    key = normalize(query)
    _store[key] = answer
    _freq[key] += 1

def top(n: int = 10) -> list[dict]:
    ranked = sorted(_freq.keys(), key=lambda k: _freq[k], reverse=True)
    return [
        {"query": k, "answer": _store[k], "count": _freq[k]}
        for k in ranked[:n]
        if k in _store
    ]
