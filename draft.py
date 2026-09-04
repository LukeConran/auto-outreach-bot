"""Stage 5: DRAFT.

Two Grok agents:
- hook writer: one specific sentence tying the recipient's actual industry work
  (or career-path / shared-background cue) to your interest.
- draft writer: short cold email using your positioning + the hook.

Hard bans in every prompt and in a post-check on the generated body:
- NEVER ask for a referral
- NEVER mention internships, new-grad search, or that Luke is job hunting

Ask is only 15–20 minutes to discuss career path, recent work, or shared
background (Texas A&M, St. Louis). Agent/scripts never send email; output is
written to pending/<author_id>.json for human review.
"""
import json
import re
from dataclasses import asdict, dataclass

import config
import industry
from xai_client import chat

# Phrases that must never appear in a draft. Keep in sync with DRAFT_RULES.
BANNED_DRAFT_PATTERNS = [
    r"\breferrals?\b",
    r"\binternships?\b",
    r"\binterns?\b",
    r"\bnew[-\s]?grads?\b",
    r"\bjob hunt(?:ing)?\b",
    r"\bjob search(?:ing)?\b",
    r"\blooking for (?:a )?jobs?\b",
    r"\bseeking (?:a )?(?:role|position|job)\b",
    r"\bopen roles?\b",
    r"\bpointer to (?:open )?roles?\b",
]


DRAFT_RULES = """
HARD BANS (must follow):
- NEVER ask for a referral, intro to recruiting, or hiring manager.
- NEVER mention internships, intern, new-grad, new grad, job hunting, job search, or open roles.
- NEVER pitch Luke as a job candidate. This is not a job ask.
- NEVER imply the sender is applying or asking to be considered.

THE ASK (must include):
- Request only 15–20 minutes to hear about their career path and/or recent work
  and/or shared background (Texas A&M / TAMU, raised in St. Louis).
- Prefer hooks in this order: (1) their recent industry work, (2) a research-without-PhD
  career path if that is visible, (3) shared TAMU or St. Louis background when applicable.
""".strip()


@dataclass
class Draft:
    author_id: str
    name: str
    email: str
    hook: str
    subject: str
    body: str


def banned_language_hits(text: str) -> list[str]:
    """Return the banned regexes that match `text` (case-insensitive)."""
    hits = []
    blob = text or ""
    for pattern in BANNED_DRAFT_PATTERNS:
        if re.search(pattern, blob, flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def is_draft_compliant(subject: str, body: str) -> bool:
    return not banned_language_hits(f"{subject}\n{body}")


def write_hook(name: str, paper_title: str, paper_abstract: str,
               affiliation: str = "", company: str = "") -> str:
    """One sentence tying the recipient's specific industry work to the sender's interest."""
    shared = (
        " Shared TAMU or St. Louis background is a valid secondary hook if visible."
        if industry.has_shared_background(affiliation)
        else ""
    )
    prompt = (
        "Write exactly one sentence (no more than 30 words) that shows genuine, specific "
        "familiarity with this person's recent industry work. Reference the paper title or "
        "a concrete detail from the abstract, or their team/company work. "
        "No generic flattery, no 'I came across your work'. "
        "Do not mention referrals, internships, new-grad search, or job hunting. "
        "A research-without-PhD career path is a good angle when relevant."
        f"{shared} "
        "Return only the sentence, no quotes.\n\n"
        f"Name: {name}\n"
        f"Affiliation: {affiliation or '(unknown)'}\n"
        f"Company: {company or '(unknown)'}\n"
        f"Paper title: {paper_title}\n"
        f"Abstract: {paper_abstract}"
    )
    return chat([{"role": "user", "content": prompt}], model=config.XAI_REASONING_MODEL).strip()


def email_prompt(name: str, hook: str, positioning: str,
                 affiliation: str = "", company: str = "") -> str:
    shared_note = (
        "The recipient appears to share TAMU and/or St. Louis background — you may "
        "mention that briefly as a reason you'd enjoy the chat."
        if industry.has_shared_background(affiliation)
        else "Only mention TAMU / St. Louis if it is a natural shared-background point."
    )
    return (
        "Write a short, specific cold email (under 150 words) from the sender to the "
        "person below. Open with the hook sentence (you may lightly edit it to flow "
        "naturally). Include the sender's positioning near the end. Sign off simply.\n"
        f"{DRAFT_RULES}\n"
        f"{shared_note}\n"
        "Return JSON: {\"subject\": \"...\", \"body\": \"...\"}\n\n"
        f"Recipient name: {name}\n"
        f"Affiliation: {affiliation or '(unknown)'}\n"
        f"Company: {company or '(unknown)'}\n"
        f"Hook sentence: {hook}\n"
        f"Sender positioning:\n{positioning}"
    )


def write_email(name: str, hook: str, positioning: str,
                affiliation: str = "", company: str = "") -> tuple[str, str]:
    """Returns (subject, body) for a short networking email."""
    prompt = email_prompt(name, hook, positioning, affiliation=affiliation, company=company)
    from xai_client import chat_json
    result = chat_json([{"role": "user", "content": prompt}], model=config.XAI_REASONING_MODEL)
    subject = result.get("subject", "Quick question about your work")
    body = result.get("body", "")
    return subject, body


def build_draft(author_id: str, name: str, email: str, paper_title: str,
                paper_abstract: str, positioning: str | None = None,
                affiliation: str = "", company: str = "") -> Draft:
    positioning = positioning or config.POSITIONING
    hook = write_hook(name, paper_title, paper_abstract,
                      affiliation=affiliation, company=company)
    subject, body = write_email(name, hook, positioning,
                                affiliation=affiliation, company=company)
    if not is_draft_compliant(subject, body):
        raise ValueError(
            "Draft contained banned language (referral / internship / new-grad / job hunt)"
        )
    return Draft(author_id=author_id, name=name, email=email, hook=hook,
                 subject=subject, body=body)


def save_draft(draft: Draft) -> str:
    """Write the draft to pending/<author_id>.json. Returns the file path."""
    path = config.PENDING_DIR / f"{draft.author_id}.json"
    path.write_text(json.dumps(asdict(draft), indent=2))
    return str(path)
