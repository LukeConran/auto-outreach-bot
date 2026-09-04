"""US industry-team filters: company allowlist, academia drop, US-only.

Used by the default (industry) discovery path and by run.py after enrich/contact.
Matching is normalized against affiliation strings and email domains.

This module never talks to LinkedIn.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import config

# Word-ish needle match: needles must sit on non-alnum boundaries after normalize().
_NEEDLE_RE_CACHE: dict[str, re.Pattern] = {}

# Signals that an affiliation/email is university / academia-only.
ACADEMIA_NEEDLES = [
    "university",
    "univ ",
    "université",
    "universidad",
    "universität",
    "universitat",
    "college",
    "institute of technology",
    "polytechnic",
    "max planck",
    "inria",
    "cnrs",
    "riken",
    "school of computer",
    "dept of computer",
    "department of computer",
    "department of electrical",
]

ACADEMIA_EMAIL_SUFFIXES = (
    ".edu",
    ".ac.uk",
    ".ac.jp",
    ".ac.kr",
    ".ac.cn",
    ".edu.au",
    ".edu.cn",
    ".edu.sg",
    ".edu.tw",
    ".edu.hk",
)

# Positive US industry geography (affiliation text).
US_POSITIVE_NEEDLES = [
    "united states",
    "usa",
    "u.s.a",
    "u.s.",
    "mountain view",
    "palo alto",
    "sunnyvale",
    "cupertino",
    "menlo park",
    "san francisco",
    "san jose",
    "los angeles",
    "seattle",
    "redmond",
    "bellevue",
    "austin",
    "detroit",
    "warren",
    "ann arbor",
    "pittsburgh",
    "boston",
    "cambridge ma",
    "new york",
    "nyc",
    "foster city",
    "irvine",
    "santa clara",
    "sausalito",
    "hawthorne",
    "fremont",
    "dearborn",
    "california",
    "texas",
    "washington",
    "massachusetts",
    "michigan",
    "pennsylvania",
    "colorado",
    "illinois",
    "georgia",
    "florida",
    "arizona",
    "nevada",
    "oregon",
    "virginia",
    "maryland",
    "missouri",
    "st louis",
    "st. louis",
    "saint louis",
]

# Explicit non-US geography — drop when this is the only location signal.
NON_US_NEEDLES = [
    "united kingdom",
    "great britain",
    "england",
    "scotland",
    "london",
    "oxford",
    "cambridge uk",
    "canada",
    "toronto",
    "montreal",
    "vancouver",
    "waterloo",
    "germany",
    "munich",
    "berlin",
    "france",
    "paris",
    "switzerland",
    "zurich",
    "israel",
    "tel aviv",
    "haifa",
    "china",
    "beijing",
    "shanghai",
    "shenzhen",
    "hangzhou",
    "tsinghua",
    "japan",
    "tokyo",
    "osaka",
    "korea",
    "seoul",
    "india",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "singapore",
    "australia",
    "sydney",
    "melbourne",
    "netherlands",
    "amsterdam",
    "sweden",
    "stockholm",
    "ireland",
    "dublin",
]

SHARED_BACKGROUND_NEEDLES = [
    "texas a&m",
    "texas a and m",
    "tamu",
    "college station",
    "st louis",
    "st. louis",
    "saint louis",
    "missouri",
]


@dataclass(frozen=True)
class CompanyMatch:
    name: str
    via: str  # "affiliation" | "email"


def normalize(text: str) -> str:
    """Lowercase, map punctuation to spaces, collapse whitespace."""
    lowered = (text or "").lower()
    cleaned = re.sub(r"[^a-z0-9.@]+", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def _needle_pattern(needle: str) -> re.Pattern:
    key = normalize(needle)
    if key not in _NEEDLE_RE_CACHE:
        _NEEDLE_RE_CACHE[key] = re.compile(rf"(?:^| ){re.escape(key)}(?:$| )")
    return _NEEDLE_RE_CACHE[key]


def contains_needle(text: str, needle: str) -> bool:
    if not text or not needle:
        return False
    return _needle_pattern(needle).search(f" {normalize(text)} ") is not None


def contains_any(text: str, needles: list[str]) -> bool:
    return any(contains_needle(text, n) for n in needles)


def email_domain(email: str | None) -> str:
    if not email or "@" not in email:
        return ""
    return email.split("@", 1)[1].lower().rstrip(".")


def domain_matches(domain: str, company_domain: str) -> bool:
    domain = (domain or "").lower().rstrip(".")
    company_domain = (company_domain or "").lower().rstrip(".")
    if not domain or not company_domain:
        return False
    return domain == company_domain or domain.endswith("." + company_domain)


def match_company(affiliation: str = "", email: str | None = None,
                  allowlist: list[dict] | None = None) -> CompanyMatch | None:
    """Return the first allowlist company matching affiliation text or email domain."""
    allowlist = allowlist if allowlist is not None else config.COMPANY_ALLOWLIST
    domain = email_domain(email)
    aff = affiliation or ""

    for company in allowlist:
        for d in company.get("domains") or []:
            if domain_matches(domain, d):
                return CompanyMatch(name=company["name"], via="email")
        # Longer needles first so "uber atg" wins over a later generic clash.
        needles = sorted(company.get("needles") or [], key=len, reverse=True)
        for needle in needles:
            if contains_needle(aff, needle):
                return CompanyMatch(name=company["name"], via="affiliation")
    return None


def is_academia(affiliation: str = "", email: str | None = None) -> bool:
    """True if affiliation/email looks like a university with no other context required."""
    aff = affiliation or ""
    if contains_any(aff, ACADEMIA_NEEDLES):
        return True
    domain = email_domain(email)
    if domain.endswith(".edu") or any(domain.endswith(s) for s in ACADEMIA_EMAIL_SUFFIXES):
        return True
    if ".edu." in domain:  # e.g. student.mit.edu already caught; foo.edu.au via suffixes
        return True
    return False


def looks_us(affiliation: str = "", email: str | None = None,
             company: CompanyMatch | None = None) -> bool:
    """Whether affiliation/email/company presence indicates US industry employment."""
    aff = affiliation or ""
    has_us = contains_any(aff, US_POSITIVE_NEEDLES)
    has_non_us = contains_any(aff, NON_US_NEEDLES)

    if has_us and not has_non_us:
        return True
    if has_non_us and not has_us:
        return False
    if has_us and has_non_us:
        # Mixed (e.g. "Google, Mountain View and London") — treat as US-present.
        return True

    domain = email_domain(email)
    if domain.endswith(".edu"):
        # .edu is a US-academia signal, not US-industry by itself.
        return company is not None

    # Allowlisted companies in this repo are US industry teams. Absent an explicit
    # foreign office, a company match (name or corporate email) counts as US.
    if company is not None:
        return True
    return False


def has_shared_background(affiliation: str = "", email: str | None = None) -> bool:
    blob = f"{affiliation or ''} {email or ''}"
    return contains_any(blob, SHARED_BACKGROUND_NEEDLES)


def keep_candidate(affiliation: str = "", email: str | None = None,
                   us_only: bool | None = None,
                   allowlist: list[dict] | None = None) -> bool:
    """Keep US industry-allowlist people; drop academia-only and non-US-only roles.

    Rules:
    - Company allowlist hit (affiliation string OR email domain) is required.
    - Pure university / *.edu corresponding authors with no company affiliation are dropped.
    - When us_only (default config.US_ONLY), also require a US industry signal.
    """
    if us_only is None:
        us_only = config.US_ONLY

    company = match_company(affiliation, email, allowlist=allowlist)
    if company is None:
        return False

    if us_only and not looks_us(affiliation, email, company=company):
        return False

    return True
