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


def test_discover_academic_dedups_by_url(monkeypatch):
    monkeypatch.setattr(discover, "expand_queries", lambda interests: ["q1", "q2"])
    monkeypatch.setattr(discover, "search_arxiv", lambda q, max_results=10: discover._parse_arxiv_feed(SAMPLE_ARXIV_FEED))
    papers = discover.discover_academic(["3D perception"])
    assert len(papers) == 1


def test_arxiv_id_from_url():
    assert discover.arxiv_id_from_url("http://arxiv.org/abs/2401.00001v1") == "2401.00001"
    assert discover.arxiv_id_from_url("https://arxiv.org/pdf/2401.00001") == "2401.00001"
    assert discover.arxiv_id_from_url("https://example.com") is None


def test_annotate_paper_affiliations_from_s2(monkeypatch):
    paper = discover._parse_arxiv_feed(SAMPLE_ARXIV_FEED)[0]

    class FakeResp:
        status_code = 200

        def json(self):
            return {"authors": [
                {"name": "Jane Doe", "affiliations": ["Waymo"]},
                {"name": "John Smith", "affiliations": ["MIT"]},
            ]}

    monkeypatch.setattr(discover, "cached_get", lambda *a, **k: FakeResp())
    annotated = discover.annotate_paper_affiliations(paper)
    assert annotated.author_affiliations["Jane Doe"] == "Waymo"
    assert annotated.author_affiliations["John Smith"] == "MIT"


def test_keep_industry_paper_drops_academia_only():
    paper = discover.Paper(
        title="t", abstract="a", url="u", authors=["A"],
        author_affiliations={"A": "MIT CSAIL"},
    )
    assert discover.keep_industry_paper(paper) is False


def test_keep_industry_paper_keeps_allowlist_author():
    paper = discover.Paper(
        title="t", abstract="a", url="u", authors=["A", "B"],
        author_affiliations={"A": "MIT", "B": "NVIDIA, Santa Clara"},
    )
    assert discover.keep_industry_paper(paper) is True


def test_keep_industry_paper_defers_when_affiliations_unknown():
    paper = discover.Paper(title="t", abstract="a", url="u", authors=["A"])
    assert discover.keep_industry_paper(paper) is True


def test_discover_industry_filters_academia_and_keeps_allowlist(monkeypatch):
    academic = [
        discover.Paper(title="uni", abstract="a", url="http://arxiv.org/abs/1",
                       authors=["Prof"], author_affiliations={"Prof": "Berkeley"}),
        discover.Paper(title="av", abstract="a", url="http://arxiv.org/abs/2",
                       authors=["Eng"], author_affiliations={"Eng": "Waymo"}),
    ]
    monkeypatch.setattr(discover, "discover_academic", lambda *a, **k: academic)
    monkeypatch.setattr(discover, "annotate_paper_affiliations", lambda p: p)

    papers = discover.discover_industry(["3D perception"])
    assert len(papers) == 1
    assert papers[0].authors == ["Eng"]


def test_discover_dispatches_to_industry_by_default(monkeypatch):
    monkeypatch.setattr(discover, "discover_industry", lambda *a, **k: ["industry"])
    monkeypatch.setattr(discover, "discover_academic", lambda *a, **k: ["academic"])
    assert discover.discover(mode="industry") == ["industry"]
    assert discover.discover(mode="academic") == ["academic"]


def test_industry_source_plugin_is_used(monkeypatch):
    class FakeSource(discover.DiscoverySource):
        name = "eng-blog"

        def find_papers(self, interests, max_results_per_query=10):
            return [discover.Paper(
                title="blog", abstract="bev", url="https://eng.example/1",
                authors=["Pat"], author_affiliations={"Pat": "Lyft, San Francisco"},
                source="eng-blog",
            )]

    monkeypatch.setattr(discover, "annotate_paper_affiliations", lambda p: p)
    papers = discover.discover_industry(["BEV"], sources=[FakeSource()])
    assert len(papers) == 1
    assert papers[0].source == "eng-blog"
