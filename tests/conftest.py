import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import config


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    """Redirect config's file paths into a per-test tmp dir so tests never
    touch real ./pending, ./history, or ./.cache."""
    pending = tmp_path / "pending"
    history = tmp_path / "history"
    cache = tmp_path / ".cache"
    pending.mkdir()
    history.mkdir()
    cache.mkdir()
    monkeypatch.setattr(config, "PENDING_DIR", pending)
    monkeypatch.setattr(config, "HISTORY_DIR", history)
    monkeypatch.setattr(config, "HISTORY_CSV", history / "contacts.csv")
    monkeypatch.setattr(config, "CACHE_DIR", cache)
    monkeypatch.setattr(config, "XAI_API_KEY", "test-key")
    yield
