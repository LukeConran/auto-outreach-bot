"""Stage 1: DISCOVER.

Grok expands your interests into search queries, then we query arXiv
(public, no key required) for matching recent papers. Each paper's
authors become candidate researchers for the next stage.
"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import config
from http_cache import cached_get
from xai_client import chat_json

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass
class Paper:
    title: str
    abstract: str
    url: str
    authors: list[str] = field(default_factory=list)
    published: str = ""


def expand_queries(interests: list[str]) -> list[str]:
    """Ask Grok to turn broad interests into concrete arXiv search strings."""
    prompt = (
        "You are a research-discovery assistant. Given a list of research interests, "
        "produce concrete arXiv search query strings (using arXiv search syntax, e.g. "
        '`abs:"bird\'s eye view" AND cat:cs.CV`) that will surface recent, relevant papers. '
        "Include synonyms and related subfields. Return JSON: "
        '{"queries": ["...", "..."]}\n\n'
        f"Interests: {', '.join(interests)}"
    )
    try:
        result = chat_json(
            [{"role": "user", "content": prompt}],
            model=config.XAI_FAST_MODEL,
        )
        queries = result.get("queries", [])
        if queries:
            return queries
    except Exception:
        pass
    # Fallback: use interests verbatim as queries if Grok is unavailable.
    return [f'abs:"{interest}"' for interest in interests]


def search_arxiv(query: str, max_results: int = 10) -> list[Paper]:
    """Query the arXiv API for a single search string. Returns parsed Paper objects."""
    resp = cached_get(
        ARXIV_API,
        params={
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        },
    )
    if resp is None or resp.status_code != 200:
        return []
    return _parse_arxiv_feed(resp.text)


def _parse_arxiv_feed(xml_text: str) -> list[Paper]:
    papers = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    for entry in root.findall("atom:entry", ARXIV_NS):
        title_el = entry.find("atom:title", ARXIV_NS)
        summary_el = entry.find("atom:summary", ARXIV_NS)
        id_el = entry.find("atom:id", ARXIV_NS)
        published_el = entry.find("atom:published", ARXIV_NS)
        authors = [
            a.find("atom:name", ARXIV_NS).text.strip()
            for a in entry.findall("atom:author", ARXIV_NS)
            if a.find("atom:name", ARXIV_NS) is not None
        ]
        if title_el is None or id_el is None:
            continue
        papers.append(Paper(
            title=" ".join(title_el.text.split()),
            abstract=" ".join((summary_el.text or "").split()) if summary_el is not None else "",
            url=id_el.text.strip(),
            authors=authors,
            published=(published_el.text.strip() if published_el is not None else ""),
        ))
    return papers


def discover(interests: list[str] | None = None, max_results_per_query: int = 10) -> list[Paper]:
    """Full discover stage: expand queries -> search arXiv -> dedup papers by URL."""
    interests = interests or config.INTERESTS
    queries = expand_queries(interests)
    seen_urls = set()
    papers: list[Paper] = []
    for q in queries:
        for p in search_arxiv(q, max_results=max_results_per_query):
            if p.url not in seen_urls:
                seen_urls.add(p.url)
                papers.append(p)
    return papers
