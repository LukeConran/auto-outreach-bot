import score


def test_score_candidate_parses_result(monkeypatch):
    monkeypatch.setattr(score, "chat_json", lambda *a, **k: {"score": 85, "rationale": "Direct overlap."})
    result = score.score_candidate("positioning", "Title", "Abstract")
    assert result.score == 85
    assert result.rationale == "Direct overlap."


def test_score_prompt_is_industry_networking_not_job():
    prompt = score.score_prompt(
        "positioning", "Occupancy Nets", "abstract",
        affiliation="Waymo", company="Waymo",
    )
    lower = prompt.lower()
    assert "networking" in lower
    assert "referral" in lower
    assert "internship" in lower
    assert "llm" in lower and "rag" in lower
    assert "waymo" in lower


def test_score_candidate_clamps_out_of_range_scores(monkeypatch):
    monkeypatch.setattr(score, "chat_json", lambda *a, **k: {"score": 150, "rationale": "x"})
    assert score.score_candidate("p", "t", "a").score == 100

    monkeypatch.setattr(score, "chat_json", lambda *a, **k: {"score": -10, "rationale": "x"})
    assert score.score_candidate("p", "t", "a").score == 0


def test_is_relevant_uses_default_threshold():
    result = score.ScoreResult(score=61, rationale="")
    assert score.is_relevant(result) is True

    result = score.ScoreResult(score=59, rationale="")
    assert score.is_relevant(result) is False


def test_is_relevant_respects_custom_threshold():
    result = score.ScoreResult(score=50, rationale="")
    assert score.is_relevant(result, threshold=40) is True
    assert score.is_relevant(result, threshold=60) is False
