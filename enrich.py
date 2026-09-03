"""Stage 2: ENRICH.

Given a candidate author name, pull their author profile from Semantic
Scholar (recent works, citation count, affiliation) and cross-reference
GitHub for repo activity.
"""
from dataclasses import dataclass, field

import config
from http_cache import cached_get

S2_API = "https://api.semanticscholar.org/graph/v1"
GITHUB_API = "https://api.github.com"


@dataclass
class AuthorProfile:
    author_id: str
    name: str
    affiliation: str = ""
    paper_count: int = 0
    citation_count: int = 0
    recent_papers: list[str] = field(default_factory=list)
    github_username: str = ""


def _s2_headers():
    headers = {}
    if config.SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = config.SEMANTIC_SCHOLAR_API_KEY
    return headers


def find_author(name: str) -> AuthorProfile | None:
    """Look up an author by name on Semantic Scholar. Returns the best match, or None."""
    resp = cached_get(
        f"{S2_API}/author/search",
        params={"query": name, "fields": "name,affiliations,paperCount,citationCount"},
        headers=_s2_headers(),
    )
    if resp is None or resp.status_code != 200:
        return None
    data = resp.json()
    matches = data.get("data", [])
    if not matches:
        return None
    top = matches[0]
    affiliations = top.get("affiliations") or []
    return AuthorProfile(
        author_id=top["authorId"],
        name=top.get("name", name),
        affiliation=affiliations[0] if affiliations else "",
        paper_count=top.get("paperCount", 0) or 0,
        citation_count=top.get("citationCount", 0) or 0,
    )


def get_recent_papers(author_id: str, limit: int = 5) -> list[str]:
    """Fetch an author's most recent paper titles from Semantic Scholar."""
    resp = cached_get(
        f"{S2_API}/author/{author_id}/papers",
        params={"fields": "title,year", "limit": limit},
        headers=_s2_headers(),
    )
    if resp is None or resp.status_code != 200:
        return []
    data = resp.json()
    papers = data.get("data", [])
    papers.sort(key=lambda p: p.get("year") or 0, reverse=True)
    return [p["title"] for p in papers if p.get("title")]


def find_github_username(name: str) -> str:
    """Best-effort GitHub username lookup by full-name search. Empty string if not found."""
    if not name.strip():
        return ""
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    resp = cached_get(
        f"{GITHUB_API}/search/users",
        params={"q": f'"{name}" in:fullname', "per_page": 1},
        headers=headers,
    )
    if resp is None or resp.status_code != 200:
        return ""
    items = resp.json().get("items", [])
    return items[0]["login"] if items else ""


def enrich(name: str) -> AuthorProfile | None:
    """Full enrich stage for one author name."""
    profile = find_author(name)
    if profile is None:
        return None
    profile.recent_papers = get_recent_papers(profile.author_id)
    profile.github_username = find_github_username(name)
    return profile
