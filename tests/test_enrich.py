import enrich


class FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_find_author_returns_profile(monkeypatch):
    payload = {"data": [{
        "authorId": "123",
        "name": "Jane Doe",
        "affiliations": ["MIT"],
        "paperCount": 42,
        "citationCount": 1000,
    }]}
    monkeypatch.setattr(enrich, "cached_get", lambda *a, **k: FakeResp(200, payload))
    profile = enrich.find_author("Jane Doe")
    assert profile.author_id == "123"
    assert profile.affiliation == "MIT"
    assert profile.citation_count == 1000


def test_find_author_returns_none_when_no_matches(monkeypatch):
    monkeypatch.setattr(enrich, "cached_get", lambda *a, **k: FakeResp(200, {"data": []}))
    assert enrich.find_author("Nobody") is None


def test_find_author_returns_none_on_network_failure(monkeypatch):
    monkeypatch.setattr(enrich, "cached_get", lambda *a, **k: None)
    assert enrich.find_author("Jane Doe") is None


def test_get_recent_papers_sorted_by_year(monkeypatch):
    payload = {"data": [
        {"title": "Old Paper", "year": 2018},
        {"title": "New Paper", "year": 2024},
    ]}
    monkeypatch.setattr(enrich, "cached_get", lambda *a, **k: FakeResp(200, payload))
    titles = enrich.get_recent_papers("123")
    assert titles == ["New Paper", "Old Paper"]


def test_find_github_username_returns_login(monkeypatch):
    monkeypatch.setattr(enrich, "cached_get", lambda *a, **k: FakeResp(200, {"items": [{"login": "janedoe"}]}))
    assert enrich.find_github_username("Jane Doe") == "janedoe"


def test_find_github_username_empty_when_no_match(monkeypatch):
    monkeypatch.setattr(enrich, "cached_get", lambda *a, **k: FakeResp(200, {"items": []}))
    assert enrich.find_github_username("Jane Doe") == ""


def test_find_github_username_empty_for_blank_name():
    assert enrich.find_github_username("") == ""


def test_enrich_full_flow(monkeypatch):
    profile = enrich.AuthorProfile(author_id="123", name="Jane Doe", affiliation="MIT")
    monkeypatch.setattr(enrich, "find_author", lambda name: profile)
    monkeypatch.setattr(enrich, "get_recent_papers", lambda author_id, limit=5: ["Paper A"])
    monkeypatch.setattr(enrich, "find_github_username", lambda name: "janedoe")
    result = enrich.enrich("Jane Doe")
    assert result.recent_papers == ["Paper A"]
    assert result.github_username == "janedoe"


def test_enrich_returns_none_when_author_not_found(monkeypatch):
    monkeypatch.setattr(enrich, "find_author", lambda name: None)
    assert enrich.enrich("Nobody") is None
