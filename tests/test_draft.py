import json

import config
import draft as draft_mod


def test_write_hook_returns_stripped_sentence(monkeypatch):
    monkeypatch.setattr(draft_mod, "chat", lambda *a, **k: "  Your occupancy network paper is great.  \n")
    hook = draft_mod.write_hook("Jane Doe", "Occupancy Nets", "abstract text")
    assert hook == "Your occupancy network paper is great."


def test_write_email_parses_subject_and_body(monkeypatch):
    import xai_client
    monkeypatch.setattr(
        xai_client, "chat_json",
        lambda *a, **k: {"subject": "Quick question", "body": "Hi Jane, ..."}
    )
    subject, body = draft_mod.write_email("Jane Doe", "hook sentence", "positioning")
    assert subject == "Quick question"
    assert body == "Hi Jane, ..."


def test_email_prompt_enforces_networking_ask_and_bans():
    prompt = draft_mod.email_prompt(
        "Jane Doe", "Your Waymo occupancy work is sharp.", config.POSITIONING,
        affiliation="Waymo", company="Waymo",
    )
    lower = prompt.lower()
    assert "never ask for a referral" in lower
    assert "internship" in lower  # listed as banned
    assert "new-grad" in lower or "new grad" in lower
    assert "15–20 minutes" in prompt or "15-20 minutes" in prompt
    assert "job hunting" in lower
    assert "not a job" in lower or "not a job ask" in lower


def test_banned_language_hits_referral_and_internship():
    assert draft_mod.banned_language_hits("Could you give me a referral?")
    assert draft_mod.banned_language_hits("I'm seeking a summer internship.")
    assert draft_mod.banned_language_hits("As a new-grad applicant...")
    assert draft_mod.banned_language_hits("I'm job hunting in AV.")
    assert not draft_mod.banned_language_hits(
        "Would you have 15–20 minutes to talk about your career path at Waymo?"
    )


def test_is_draft_compliant_happy_path():
    assert draft_mod.is_draft_compliant(
        "Career chat",
        "Hi Jane, I'd love 15–20 minutes to hear about your path at NVIDIA.",
    )


def test_build_draft_composes_hook_and_email(monkeypatch):
    monkeypatch.setattr(draft_mod, "write_hook", lambda *a, **k: "Specific hook.")
    monkeypatch.setattr(draft_mod, "write_email", lambda *a, **k: ("Subject line", "Body text"))
    d = draft_mod.build_draft(
        author_id="123", name="Jane Doe", email="jane@waymo.com",
        paper_title="Title", paper_abstract="Abstract",
        affiliation="Waymo", company="Waymo",
    )
    assert d.hook == "Specific hook."
    assert d.subject == "Subject line"
    assert d.body == "Body text"
    assert d.email == "jane@waymo.com"


def test_build_draft_rejects_banned_language(monkeypatch):
    monkeypatch.setattr(draft_mod, "write_hook", lambda *a, **k: "Hook.")
    monkeypatch.setattr(
        draft_mod, "write_email",
        lambda *a, **k: ("Internships?", "Could you refer me for a new-grad role?"),
    )
    import pytest
    with pytest.raises(ValueError, match="banned language"):
        draft_mod.build_draft(
            author_id="123", name="Jane Doe", email="jane@waymo.com",
            paper_title="Title", paper_abstract="Abstract",
        )


def test_save_draft_writes_json_file():
    d = draft_mod.Draft(
        author_id="123", name="Jane Doe", email="jane@waymo.com",
        hook="hook", subject="subject", body="body",
    )
    path = draft_mod.save_draft(d)
    assert path.endswith("123.json")
    saved = json.loads(open(path).read())
    assert saved["name"] == "Jane Doe"
    assert saved["email"] == "jane@waymo.com"
