from __future__ import annotations

import re
import threading
import time
from typing import List

import arxiv
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from app.rag import retrieve_information

# arXiv asks for a 3-second delay and one connection at a time across the process.
_arxiv_lock = threading.Lock()
_last_arxiv_request: float = 0.0


@tool
def arxiv_search(query: str, max_results: int = 3) -> str:
    """Search arxiv.org using a field-qualified query.

    Format every term with all:, ti:, abs:, au:, or cat:. Prefer OR for broad
    discovery and use AND only when every term must match. Use at most five
    focused terms. Example: all:cat OR all:feline OR all:sleep
    """
    global _last_arxiv_request

    query = query.strip()
    if len(query) > 200:
        return "Invalid arXiv query: use at most five focused terms and 200 characters."
    if not re.search(r"(?:^|[ (])(?:all|ti|abs|au|cat):\S+", query):
        return (
            "Invalid arXiv query. Qualify terms with all:, ti:, abs:, au:, or cat: "
            "and join them with uppercase AND, OR, or ANDNOT."
        )
    max_results = min(max(max_results, 1), 5)

    retry_delays = (0.0, 5.0, 10.0)
    with _arxiv_lock:
        for attempt, retry_delay in enumerate(retry_delays):
            if retry_delay:
                time.sleep(retry_delay)
            elapsed = time.monotonic() - _last_arxiv_request
            if elapsed < 3.0:
                time.sleep(3.0 - elapsed)

            try:
                client = arxiv.Client(
                    page_size=max_results,
                    delay_seconds=3.0,
                    num_retries=0,
                )
                search = arxiv.Search(query=query, max_results=max_results)
                _last_arxiv_request = time.monotonic()
                results = list(client.results(search))
                break
            except arxiv.HTTPError as e:
                _last_arxiv_request = time.monotonic()
                if e.status == 503 and attempt < len(retry_delays) - 1:
                    continue
                if e.status == 429:
                    return "arXiv rate limit reached. Use Tavily or try again later."
                if e.status == 503:
                    return "arXiv is temporarily unavailable after three attempts. Use Tavily."
                return f"arXiv returned HTTP {e.status}: {e}"
            except Exception as e:
                _last_arxiv_request = time.monotonic()
                return f"arXiv search failed: {e}"

    if not results:
        return "No arxiv results found."
    docs = []
    for result in results:
        authors = ", ".join(a.name for a in result.authors)
        docs.append(
            f"Published: {result.updated.date()}\n"
            f"Title: {result.title}\n"
            f"Authors: {authors}\n"
            f"Summary: {result.summary}"
        )
    return "\n\n".join(docs)[:4000]


def get_tool_belt() -> List:
    tavily_tool = TavilySearch(max_results=5)
    return [tavily_tool, arxiv_search, retrieve_information]
