import datetime as dt

import track


def test_add_row_and_load_history():
    track.add_row("a1", "Jane Doe", "MIT", "jane@mit.edu", "hook", "pending/a1.json")
    rows = track.load_history()
    assert len(rows) == 1
    assert rows[0]["name"] == "Jane Doe"
    assert rows[0]["status"] == "DRAFT"


def test_already_contacted_dedup():
    assert track.already_contacted("a1") is False
    track.add_row("a1", "Jane Doe", "MIT", "jane@mit.edu", "hook", "pending/a1.json")
    assert track.already_contacted("a1") is True


def test_update_status_transitions_and_persists():
    track.add_row("a1", "Jane Doe", "MIT", "jane@mit.edu", "hook", "pending/a1.json")
    ok = track.update_status("a1", "APPROVED")
    assert ok is True
    rows = track.load_history()
    assert rows[0]["status"] == "APPROVED"


def test_update_status_returns_false_for_unknown_id():
    assert track.update_status("nonexistent", "APPROVED") is False


def test_business_days_from_today_skips_weekends(monkeypatch):
    class FixedDate(dt.date):
        @classmethod
        def today(cls):
            return dt.date(2024, 1, 5)  # Friday

    monkeypatch.setattr(track.dt, "date", FixedDate)
    result = track.business_days_from_today(1)
    assert result == "2024-01-08"  # Monday, skipping the weekend


def test_due_for_followup_filters_by_status_and_date():
    today = dt.date.today().isoformat()
    yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()

    track.add_row("a1", "Due Now", "MIT", "a@mit.edu", "h", "d", status="SENT", followup_date=yesterday)
    track.add_row("a2", "Not Due Yet", "MIT", "b@mit.edu", "h", "d", status="SENT", followup_date=tomorrow)
    track.add_row("a3", "Still Draft", "MIT", "c@mit.edu", "h", "d", status="DRAFT", followup_date=today)

    due = track.due_for_followup()
    assert len(due) == 1
    assert due[0]["author_id"] == "a1"
