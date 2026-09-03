"""End-to-end pipeline test: every external call (arXiv, Semantic Scholar,
GitHub, xAI) is mocked, proving the six stages wire together correctly and
that dedup/limit/gating behave as specified.
"""
import contact
import discover
import draft as draft_mod
import enrich
import run
import score as score_mod
import track


def _fake_paper():
    return discover.Paper(
        title="Occupancy Networks for 3D Perception",
        abstract="We present a new method for occupancy-based 3D perception.",
        url="http://arxiv.org/abs/2401.00001",
        authors=["Jane Doe"],
    )


def _wire_happy_path(monkeypatch):
    monkeypatch.setattr(discover, "discover", lambda: [_fake_paper()])
    monkeypatch.setattr(enrich, "enrich", lambda name: enrich.AuthorProfile(
        author_id="auth-1", name=name, affiliation="MIT",
        recent_papers=["Occupancy Networks for 3D Perception"], github_username="janedoe",
    ))
    monkeypatch.setattr(score_mod, "score_candidate", lambda pos, title, abstract: score_mod.ScoreResult(
        score=90, rationale="Strong overlap with 3D perception interest.",
    ))
    monkeypatch.setattr(contact, "find_contact_email", lambda url, gh: "jane.doe@mit.edu")
    monkeypatch.setattr(draft_mod, "build_draft", lambda **kw: draft_mod.Draft(
        author_id=kw["author_id"], name=kw["name"], email=kw["email"],
        hook=f"Your paper '{kw['paper_title']}' on occupancy networks caught my eye.",
        subject="Quick question about your occupancy network work",
        body="Hi Jane, ...",
    ))


def test_pipeline_produces_vetted_candidate_with_paper_reference(monkeypatch):
    _wire_happy_path(monkeypatch)
    kept = run.run_pipeline(limit=5, verbose=False)

    assert len(kept) == 1
    candidate = kept[0]
    assert candidate["name"] == "Jane Doe"
    assert candidate["email"] == "jane.doe@mit.edu"
    assert candidate["score"] == 90

    rows = track.load_history()
    assert len(rows) == 1
    assert rows[0]["status"] == "DRAFT"

    import json
    saved = json.loads(open(candidate["draft_path"]).read())
    assert "Occupancy Networks for 3D Perception" in saved["hook"]


def test_pipeline_respects_limit(monkeypatch):
    papers = [
        discover.Paper(title=f"Paper {i}", abstract="abstract", url=f"http://arxiv.org/abs/{i}",
                        authors=[f"Author {i}"])
        for i in range(5)
    ]
    monkeypatch.setattr(discover, "discover", lambda: papers)
    monkeypatch.setattr(enrich, "enrich", lambda name: enrich.AuthorProfile(
        author_id=name, name=name, affiliation="MIT",
    ))
    monkeypatch.setattr(score_mod, "score_candidate", lambda pos, title, abstract: score_mod.ScoreResult(
        score=90, rationale="ok",
    ))
    monkeypatch.setattr(contact, "find_contact_email", lambda url, gh: "x@example.com")
    monkeypatch.setattr(draft_mod, "build_draft", lambda **kw: draft_mod.Draft(
        author_id=kw["author_id"], name=kw["name"], email=kw["email"],
        hook="hook", subject="subject", body="body",
    ))

    kept = run.run_pipeline(limit=2, verbose=False)
    assert len(kept) == 2


def test_pipeline_is_idempotent_never_recontacts(monkeypatch):
    """Re-running after a candidate is already tracked must produce zero new drafts."""
    _wire_happy_path(monkeypatch)
    first = run.run_pipeline(limit=5, verbose=False)
    assert len(first) == 1

    second = run.run_pipeline(limit=5, verbose=False)
    assert len(second) == 0
    assert len(track.load_history()) == 1  # no duplicate row


def test_pipeline_drops_candidates_below_relevance_threshold(monkeypatch):
    _wire_happy_path(monkeypatch)
    monkeypatch.setattr(score_mod, "score_candidate", lambda pos, title, abstract: score_mod.ScoreResult(
        score=10, rationale="not relevant",
    ))
    kept = run.run_pipeline(limit=5, verbose=False)
    assert kept == []
    assert track.load_history() == []


def test_pipeline_skips_candidates_with_no_email(monkeypatch):
    _wire_happy_path(monkeypatch)
    monkeypatch.setattr(contact, "find_contact_email", lambda url, gh: None)
    kept = run.run_pipeline(limit=5, verbose=False)
    assert kept == []


def test_pipeline_skips_candidates_enrich_cannot_resolve(monkeypatch):
    _wire_happy_path(monkeypatch)
    monkeypatch.setattr(enrich, "enrich", lambda name: None)
    kept = run.run_pipeline(limit=5, verbose=False)
    assert kept == []
