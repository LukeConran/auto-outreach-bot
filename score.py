"""Stage 4: SCORE.

Grok relevance agent: given your positioning and a candidate's paper +
industry affiliation, return a 0-100 score plus a one-line rationale.

Score for US-industry + interest fit and suitability for a 15–20 minute
networking chat (career path / recent work / shared background) — not a
job or referral ask. Candidates below config.RELEVANCE_THRESHOLD, or
already in history, are dropped.
"""
from dataclasses import dataclass

import config
from xai_client import chat_json


@dataclass
class ScoreResult:
    score: int
    rationale: str


def score_prompt(positioning: str, paper_title: str, paper_abstract: str,
                 affiliation: str = "", company: str = "") -> str:
    soft_exclude = "; ".join(config.SOFT_EXCLUDE_TOPICS)
    return (
        "You are scoring cold-outreach targets for a US industry networking chat "
        "(not a job application, internship hunt, or referral request).\n"
        "Given the sender's positioning/interests and a candidate's recent work plus "
        "industry affiliation, score 0 (irrelevant) to 100 (excellent networking fit).\n"
        "High scores: US industry team (allowlisted tech/AV/applied-ML companies), "
        "work aligned with 3D perception / computer vision / autonomous driving / "
        "occupancy / BEV / depth / SLAM / on-device perception / medical 3D MRI / "
        "imbalanced classification / robot learning, and a natural 15–20 minute "
        "conversation about their career path, recent work, or shared TAMU / St. Louis "
        "background. Prefer people whose path may include research without a PhD when "
        "that is visible.\n"
        f"Soft-exclude (lower the score unless the work is clearly grounded in the "
        f"sender's perception/AV/medical-imaging interests): {soft_exclude}.\n"
        "Do not reward internship/new-grad/hiring/referral suitability.\n"
        'Return JSON: {"score": <int 0-100>, "rationale": "<one sentence>"}\n\n'
        f"Sender positioning:\n{positioning}\n\n"
        f"Candidate affiliation: {affiliation or '(unknown)'}\n"
        f"Matched company: {company or '(unknown)'}\n"
        f"Candidate's paper title: {paper_title}\n"
        f"Candidate's paper abstract: {paper_abstract}"
    )


def score_candidate(positioning: str, paper_title: str, paper_abstract: str,
                    affiliation: str = "", company: str = "") -> ScoreResult:
    """Ask Grok how relevant this industry candidate is for a networking chat."""
    prompt = score_prompt(
        positioning, paper_title, paper_abstract,
        affiliation=affiliation, company=company,
    )
    result = chat_json(
        [{"role": "user", "content": prompt}],
        model=config.XAI_REASONING_MODEL,
    )
    score = int(result.get("score", 0))
    score = max(0, min(100, score))
    rationale = str(result.get("rationale", "")).strip()
    return ScoreResult(score=score, rationale=rationale)


def is_relevant(result: ScoreResult, threshold: int | None = None) -> bool:
    return result.score >= (threshold if threshold is not None else config.RELEVANCE_THRESHOLD)
