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


def test_build_draft_composes_hook_and_email(monkeypatch):
    monkeypatch.setattr(draft_mod, "write_hook", lambda *a, **k: "Specific hook.")
    monkeypatch.setattr(draft_mod, "write_email", lambda *a, **k: ("Subject line", "Body text"))
    d = draft_mod.build_draft(
        author_id="123", name="Jane Doe", email="jane@mit.edu",
        paper_title="Title", paper_abstract="Abstract",
    )
    assert d.hook == "Specific hook."
    assert d.subject == "Subject line"
    assert d.body == "Body text"
    assert d.email == "jane@mit.edu"


def test_save_draft_writes_json_file():
    d = draft_mod.Draft(
        author_id="123", name="Jane Doe", email="jane@mit.edu",
        hook="hook", subject="subject", body="body",
    )
    path = draft_mod.save_draft(d)
    assert path.endswith("123.json")
    saved = json.loads(open(path).read())
    assert saved["name"] == "Jane Doe"
    assert saved["email"] == "jane@mit.edu"
