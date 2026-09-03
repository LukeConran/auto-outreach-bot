"""Stage 3: CONTACT.

Extract a contact email two ways, in order of preference:
1. Corresponding-author email printed in the paper's PDF (arXiv abs page -> PDF text).
2. GitHub public profile email (GitHub API), if the user has one set.
"""
import re

import config
from http_cache import cached_get

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
GITHUB_API = "https://api.github.com"

# Domains that show up in PDFs but are never a personal contact address.
EMAIL_DOMAIN_BLOCKLIST = {"example.com", "sentry.io", "wandb.ai"}


def extract_email_from_text(text: str) -> str | None:
    """Return the first plausible email address found in raw text, or None."""
    for match in EMAIL_RE.findall(text):
        domain = match.split("@")[-1].lower()
        if domain not in EMAIL_DOMAIN_BLOCKLIST:
            return match
    return None


def extract_email_from_pdf_bytes(pdf_bytes: bytes) -> str | None:
    """Extract the first page's text via pdfplumber and scan for an email."""
    import io

    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:2]:  # emails are almost always on p1-2
                text = page.extract_text() or ""
                email = extract_email_from_text(text)
                if email:
                    return email
    except Exception:
        return None
    return None


def email_from_arxiv_pdf(arxiv_abs_url: str) -> str | None:
    """Download an arXiv paper's PDF and try to find a contact email in it."""
    pdf_url = arxiv_abs_url.replace("/abs/", "/pdf/")
    resp = cached_get(pdf_url)
    if resp is None or resp.status_code != 200:
        return None
    return extract_email_from_pdf_bytes(resp.text.encode("latin-1", errors="ignore"))


def email_from_github(username: str) -> str | None:
    """Fetch a GitHub user's public profile email, if set."""
    if not username:
        return None
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    resp = cached_get(f"{GITHUB_API}/users/{username}", headers=headers)
    if resp is None or resp.status_code != 200:
        return None
    return resp.json().get("email") or None


def find_contact_email(paper_url: str, github_username: str = "") -> str | None:
    """Full contact stage: try the paper PDF first, then GitHub as fallback."""
    email = email_from_arxiv_pdf(paper_url)
    if email:
        return email
    return email_from_github(github_username)
