"""Stage 1: DISCOVER.

Default path (industry): pluggable sources (arXiv today; eng blogs later) plus
Semantic Scholar affiliation annotation, filtered to COMPANY_ALLOWLIST / US industry.

Academic path (opt-in): original arXiv-only paper search, no company/US filter.

LinkedIn is never a discovery source.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import config
import industry
from http_cache import cached_get
from xai_client import chat_json

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}
S2_API = "https://api.semanticscholar.org/graph/v1"


@dataclass
class Paper:
    title: str
    abstract: str
    url: str
    authors: list[str] = field(default_factory=list)
    published: str = ""
    author_affiliations: dict[str, str] = field(default_factory=dict)
    source: str = "arxiv"


def expand_queries(interests: list[str]) -> list[str]:
    """Ask Grok to turn broad interests into concrete arXiv search strings."""
    prompt = (
        "You are a research-discovery assistant. Given a list of research interests, "
        "produce concrete arXiv search query strings (using arXiv search syntax, e.g. "
        '`abs:"bird\'s eye view" AND cat:cs.CV`) that will surface recent, relevant papers. '
        "Include synonyms and related subfields. Prefer industry / applied perception, "
        "autonomous driving, and medical-imaging work over LLM-tuning or RAG papers. "
        "Return JSON: "
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
            source="arxiv",
        ))
    return papers


def discover_academic(interests: list[str] | None = None,
                      max_results_per_query: int = 10) -> list[Paper]:
    """Original academic path: expand queries -> search arXiv -> dedup papers by URL.

    Not the default. Call explicitly or set DISCOVER_MODE=academic.
    """
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


class DiscoverySource:
    """Pluggable industry discovery source.

    Add company eng blogs, patents, etc. by subclassing and appending to
    INDUSTRY_SOURCES. Never add LinkedIn scraping.
    """
    name = "base"

    def find_papers(self, interests: list[str], max_results_per_query: int = 10) -> list[Paper]:
        raise NotImplementedError


class ArxivIndustrySource(DiscoverySource):
    """Interest-query arXiv papers, later filtered to industry-affiliated authors."""
    name = "arxiv"

    def find_papers(self, interests: list[str], max_results_per_query: int = 10) -> list[Paper]:
        papers = discover_academic(interests, max_results_per_query=max_results_per_query)
        for p in papers:
            p.source = self.name
        return papers


# Register additional industry sources here (eng blogs, etc.).
INDUSTRY_SOURCES: list[DiscoverySource] = [ArxivIndustrySource()]


def _s2_headers() -> dict:
    headers = {}
    if config.SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = config.SEMANTIC_SCHOLAR_API_KEY
    return headers


def arxiv_id_from_url(url: str) -> str | None:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d+\.\d+)", url or "", re.I)
    return match.group(1) if match else None


def annotate_paper_affiliations(paper: Paper) -> Paper:
    """Attach Semantic Scholar author affiliations when the paper has an arXiv id.

    Fail-open: if S2 is unavailable, leave author_affiliations empty so run.py
    can still filter after enrich/contact.
    """
    arxiv_id = arxiv_id_from_url(paper.url)
    if not arxiv_id:
        return paper
    resp = cached_get(
        f"{S2_API}/paper/ARXIV:{arxiv_id}",
        params={"fields": "authors.name,authors.affiliations"},
        headers=_s2_headers(),
    )
    if resp is None or resp.status_code != 200:
        return paper
    try:
        data = resp.json()
    except Exception:
        return paper
    affiliations: dict[str, str] = {}
    for author in data.get("authors") or []:
        name = (author.get("name") or "").strip()
        affs = author.get("affiliations") or []
        if name and affs:
            affiliations[name] = affs[0] if isinstance(affs[0], str) else str(affs[0])
    paper.author_affiliations = affiliations
    return paper


def paper_has_industry_author(paper: Paper) -> bool:
    """True if at least one annotated author passes the US industry allowlist filter."""
    if not paper.author_affiliations:
        return False
    return any(
        industry.keep_candidate(affiliation=aff)
        for aff in paper.author_affiliations.values()
    )


def keep_industry_paper(paper: Paper) -> bool:
    """Drop papers whose authors are all known academia-only / non-allowlist.

    If affiliations are unknown, keep the paper and let later stages decide.
    """
    if not paper.author_affiliations:
        return True
    return paper_has_industry_author(paper)


def discover_industry(interests: list[str] | None = None,
                      max_results_per_query: int = 10,
                      sources: list[DiscoverySource] | None = None) -> list[Paper]:
    """Default discovery path: run registered industry sources, annotate, filter."""
    interests = interests or config.INTERESTS
    sources = sources if sources is not None else INDUSTRY_SOURCES
    seen_urls: set[str] = set()
    papers: list[Paper] = []
    for source in sources:
        for paper in source.find_papers(interests, max_results_per_query=max_results_per_query):
            if paper.url in seen_urls:
                continue
            seen_urls.add(paper.url)
            papers.append(annotate_paper_affiliations(paper))
    return [p for p in papers if keep_industry_paper(p)]


def discover(interests: list[str] | None = None, max_results_per_query: int = 10,
             mode: str | None = None) -> list[Paper]:
    """Dispatch on DISCOVER_MODE (default industry). Academic path remains callable."""
    mode = (mode or config.DISCOVER_MODE or "industry").lower()
    if mode == "academic":
        return discover_academic(interests, max_results_per_query=max_results_per_query)
    return discover_industry(interests, max_results_per_query=max_results_per_query)
