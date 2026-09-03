import contact


def test_extract_email_from_text_finds_email():
    text = "For correspondence, contact jane.doe@mit.edu regarding this work."
    assert contact.extract_email_from_text(text) == "jane.doe@mit.edu"


def test_extract_email_from_text_returns_none_when_absent():
    assert contact.extract_email_from_text("no email here") is None


def test_extract_email_from_text_skips_blocklisted_domains():
    text = "noreply@example.com is not real, but jane@stanford.edu is."
    assert contact.extract_email_from_text(text) == "jane@stanford.edu"


def test_email_from_github_returns_email(monkeypatch):
    class FakeResp:
        status_code = 200

        def json(self):
            return {"email": "jane@github-user.com"}

    monkeypatch.setattr(contact, "cached_get", lambda *a, **k: FakeResp())
    assert contact.email_from_github("janedoe") == "jane@github-user.com"


def test_email_from_github_returns_none_when_blank_username():
    assert contact.email_from_github("") is None


def test_email_from_github_returns_none_when_no_email_set(monkeypatch):
    class FakeResp:
        status_code = 200

        def json(self):
            return {"email": None}

    monkeypatch.setattr(contact, "cached_get", lambda *a, **k: FakeResp())
    assert contact.email_from_github("janedoe") is None


def test_find_contact_email_prefers_pdf(monkeypatch):
    monkeypatch.setattr(contact, "email_from_arxiv_pdf", lambda url: "pdf@example-author.com")
    monkeypatch.setattr(contact, "email_from_github", lambda username: "github@example-author.com")
    assert contact.find_contact_email("http://arxiv.org/abs/1234", "janedoe") == "pdf@example-author.com"


def test_find_contact_email_falls_back_to_github(monkeypatch):
    monkeypatch.setattr(contact, "email_from_arxiv_pdf", lambda url: None)
    monkeypatch.setattr(contact, "email_from_github", lambda username: "github@example-author.com")
    assert contact.find_contact_email("http://arxiv.org/abs/1234", "janedoe") == "github@example-author.com"


def test_find_contact_email_returns_none_when_both_fail(monkeypatch):
    monkeypatch.setattr(contact, "email_from_arxiv_pdf", lambda url: None)
    monkeypatch.setattr(contact, "email_from_github", lambda username: None)
    assert contact.find_contact_email("http://arxiv.org/abs/1234", "janedoe") is None
