import pytest

import config
import xai_client
from xai_client import XAIError, chat, chat_json


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_chat_returns_content(monkeypatch):
    def fake_post(url, headers, json, timeout):
        assert "Authorization" in headers
        assert json["model"] == config.XAI_REASONING_MODEL
        return FakeResponse(200, {"choices": [{"message": {"content": "hello"}}]})

    monkeypatch.setattr(xai_client.requests, "post", fake_post)
    assert chat([{"role": "user", "content": "hi"}]) == "hello"


def test_chat_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(config, "XAI_API_KEY", "")
    with pytest.raises(XAIError):
        chat([{"role": "user", "content": "hi"}])


def test_chat_raises_on_non_200(monkeypatch):
    def fake_post(*a, **k):
        return FakeResponse(500, "server error")

    monkeypatch.setattr(xai_client.requests, "post", fake_post)
    with pytest.raises(XAIError):
        chat([{"role": "user", "content": "hi"}])


def test_chat_json_parses_content(monkeypatch):
    def fake_post(*a, **k):
        return FakeResponse(200, {"choices": [{"message": {"content": '{"score": 80}'}}]})

    monkeypatch.setattr(xai_client.requests, "post", fake_post)
    result = chat_json([{"role": "user", "content": "hi"}])
    assert result == {"score": 80}


def test_chat_json_raises_on_bad_json(monkeypatch):
    def fake_post(*a, **k):
        return FakeResponse(200, {"choices": [{"message": {"content": "not json"}}]})

    monkeypatch.setattr(xai_client.requests, "post", fake_post)
    with pytest.raises(XAIError):
        chat_json([{"role": "user", "content": "hi"}])
