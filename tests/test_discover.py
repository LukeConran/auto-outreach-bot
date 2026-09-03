import discover

SAMPLE_ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>  Occupancy Networks for Autonomous Driving  </title>
    <summary>We propose a new occupancy network for 3D perception in driving.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Jane Doe</name></author>
    <author><name>John Smith</name></author>
  </entry>
</feed>
"""


def test_parse_arxiv_feed_extracts_papers():
    papers = discover._parse_arxiv_feed(SAMPLE_ARXIV_FEED)
    assert len(papers) == 1
    p = papers[0]
    assert p.title == "Occupancy Networks for Autonomous Driving"
    assert "occupancy network" in p.abstract
    assert p.authors == ["Jane Doe", "John Smith"]
    assert p.url == "http://arxiv.org/abs/2401.00001v1"


def test_parse_arxiv_feed_handles_empty_feed():
    empty = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    assert discover._parse_arxiv_feed(empty) == []


def test_parse_arxiv_feed_handles_malformed_xml():
    assert discover._parse_arxiv_feed("not xml at all") == []


def test_search_arxiv_uses_cache(monkeypatch):
    class FakeResp:
        status_code = 200
        text = SAMPLE_ARXIV_FEED

    monkeypatch.setattr(discover, "cached_get", lambda *a, **k: FakeResp())
    papers = discover.search_arxiv('abs:"occupancy"')
    assert len(papers) == 1


def test_search_arxiv_returns_empty_on_failure(monkeypatch):
    monkeypatch.setattr(discover, "cached_get", lambda *a, **k: None)
    assert discover.search_arxiv("query") == []


def test_expand_queries_falls_back_when_grok_unavailable(monkeypatch):
    def broken_chat_json(*a, **k):
        raise RuntimeError("no api key")

    monkeypatch.setattr(discover, "chat_json", broken_chat_json)
    queries = discover.expand_queries(["3D perception", "SLAM"])
    assert len(queries) == 2
    assert 'abs:"3D perception"' in queries


def test_expand_queries_uses_grok_result(monkeypatch):
    monkeypatch.setattr(discover, "chat_json", lambda *a, **k: {"queries": ["abs:\"BEV\""]})
    assert discover.expand_queries(["3D perception"]) == ['abs:"BEV"']


def test_discover_dedups_by_url(monkeypatch):
    monkeypatch.setattr(discover, "expand_queries", lambda interests: ["q1", "q2"])
    monkeypatch.setattr(discover, "search_arxiv", lambda q, max_results=10: discover._parse_arxiv_feed(SAMPLE_ARXIV_FEED))
    papers = discover.discover(["3D perception"])
    assert len(papers) == 1
