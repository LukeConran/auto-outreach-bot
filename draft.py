"""Stage 5: DRAFT.

Two Grok agents:
- hook writer: one specific sentence tying the recipient's actual work to your interest.
- draft writer: short cold email using your positioning + the hook.

Output is written to pending/<author_id>.json for human review.
"""
import json
from dataclasses import asdict, dataclass

import config
from xai_client import chat


@dataclass
class Draft:
    author_id: str
    name: str
    email: str
    hook: str
    subject: str
    body: str


def write_hook(name: str, paper_title: str, paper_abstract: str) -> str:
    """One sentence tying the recipient's specific paper to the sender's interest."""
    prompt = (
        "Write exactly one sentence (no more than 30 words) that shows genuine, specific "
        "familiarity with this researcher's work. Reference the paper title or a concrete "
        "detail from the abstract. No generic flattery, no 'I came across your work'. "
        "Return only the sentence, no quotes.\n\n"
        f"Researcher: {name}\n"
        f"Paper title: {paper_title}\n"
        f"Abstract: {paper_abstract}"
    )
    return chat([{"role": "user", "content": prompt}], model=config.XAI_REASONING_MODEL).strip()


def write_email(name: str, hook: str, positioning: str) -> tuple[str, str]:
    """Returns (subject, body) for a short cold email. Body includes the hook verbatim context."""
    prompt = (
        "Write a short, specific cold email (under 150 words) from the sender to the "
        "researcher below. Open with the hook sentence (you may lightly edit it to flow "
        "naturally). Include the sender's positioning/ask near the end. Sign off simply. "
        "Return JSON: {\"subject\": \"...\", \"body\": \"...\"}\n\n"
        f"Researcher name: {name}\n"
        f"Hook sentence: {hook}\n"
        f"Sender positioning:\n{positioning}"
    )
    from xai_client import chat_json
    result = chat_json([{"role": "user", "content": prompt}], model=config.XAI_REASONING_MODEL)
    return result.get("subject", f"Quick question about your work"), result.get("body", "")


def build_draft(author_id: str, name: str, email: str, paper_title: str,
                 paper_abstract: str, positioning: str | None = None) -> Draft:
    positioning = positioning or config.POSITIONING
    hook = write_hook(name, paper_title, paper_abstract)
    subject, body = write_email(name, hook, positioning)
    return Draft(author_id=author_id, name=name, email=email, hook=hook,
                 subject=subject, body=body)


def save_draft(draft: Draft) -> str:
    """Write the draft to pending/<author_id>.json. Returns the file path."""
    path = config.PENDING_DIR / f"{draft.author_id}.json"
    path.write_text(json.dumps(asdict(draft), indent=2))
    return str(path)
