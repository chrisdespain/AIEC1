import pytest
import cache

def setup_function():
    cache._store.clear()
    cache._freq.clear()

def test_miss_returns_none():
    assert cache.get("what does this repo do?") is None

def test_hit_returns_answer():
    cache.put("what does this repo do?", "It deploys things.")
    assert cache.get("what does this repo do?") == "It deploys things."

def test_normalize_strips_punctuation_and_case():
    cache.put("What does this repo do?", "It deploys things.")
    assert cache.get("what does this repo do") == "It deploys things."

def test_normalize_collapses_whitespace():
    cache.put("what  does   this repo   do", "It deploys things.")
    assert cache.get("what does this repo do") == "It deploys things."

def test_frequency_ordering():
    cache.put("query a", "answer a")
    cache.put("query b", "answer b")
    cache.put("query b", "answer b updated")
    tops = cache.top(2)
    assert tops[0]["query"] == "query b"
    assert tops[0]["count"] == 2

def test_top_n_cap():
    for i in range(15):
        cache.put(f"query {i}", f"answer {i}")
    assert len(cache.top(10)) == 10

def test_top_includes_answer():
    cache.put("hello world", "a response")
    tops = cache.top(1)
    assert tops[0]["answer"] == "a response"
    assert tops[0]["query"] == "hello world"
