"""Stage 4: SCORE.

Grok relevance agent: given your positioning and a candidate's top paper
abstract, return a 0-100 relevance score plus a one-line rationale.
Candidates below config.RELEVANCE_THRESHOLD, or already in history, are dropped.
"""
from dataclasses import dataclass

import config
from xai_client import chat_json


@dataclass
class ScoreResult:
    score: int
    rationale: str


def score_candidate(positioning: str, paper_title: str, paper_abstract: str) -> ScoreResult:
    """Ask Grok how relevant this candidate's paper is to your positioning/interests."""
    prompt = (
        "You are a relevance-scoring assistant for cold-outreach research. "
        "Given the sender's positioning/interests and a candidate researcher's paper, "
        "score how relevant this candidate is as an outreach target from 0 (irrelevant) "
        "to 100 (perfect match). Return JSON: "
        '{"score": <int 0-100>, "rationale": "<one sentence>"}\n\n'
        f"Sender positioning:\n{positioning}\n\n"
        f"Candidate's paper title: {paper_title}\n"
        f"Candidate's paper abstract: {paper_abstract}"
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
