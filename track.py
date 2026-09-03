"""Stage 6: TRACK.

CSV-backed tracking sheet (history/contacts.csv) so the pipeline runs
instantly with zero Google setup. Swap in Google Sheets later by
replacing the read/write functions below with `gspread` calls while
keeping the same column schema and dedup-by-author_id contract.
"""
import csv
import datetime as dt

import config

COLUMNS = [
    "author_id", "date_found", "name", "affiliation", "email",
    "hook", "draft_link", "status", "sent_date", "followup_date", "notes",
]


def _ensure_csv():
    if not config.HISTORY_CSV.exists():
        with config.HISTORY_CSV.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()


def load_history() -> list[dict]:
    """Return all rows in the tracking sheet."""
    _ensure_csv()
    with config.HISTORY_CSV.open(newline="") as f:
        return list(csv.DictReader(f))


def already_contacted(author_id: str) -> bool:
    """Dedup check: has this author_id ever been logged before?"""
    return any(row["author_id"] == author_id for row in load_history())


def add_row(author_id: str, name: str, affiliation: str, email: str,
            hook: str, draft_link: str, status: str = "DRAFT",
            sent_date: str = "", followup_date: str = "", notes: str = "") -> None:
    """Append one candidate to the tracking sheet."""
    _ensure_csv()
    with config.HISTORY_CSV.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writerow({
            "author_id": author_id,
            "date_found": dt.date.today().isoformat(),
            "name": name,
            "affiliation": affiliation,
            "email": email,
            "hook": hook,
            "draft_link": draft_link,
            "status": status,
            "sent_date": sent_date,
            "followup_date": followup_date,
            "notes": notes,
        })


def update_status(author_id: str, status: str, sent_date: str = "",
                   followup_date: str = "") -> bool:
    """Update a row's status (e.g. DRAFT -> APPROVED -> SENT). Returns True if found."""
    rows = load_history()
    found = False
    for row in rows:
        if row["author_id"] == author_id:
            row["status"] = status
            if sent_date:
                row["sent_date"] = sent_date
            if followup_date:
                row["followup_date"] = followup_date
            found = True
    if found:
        with config.HISTORY_CSV.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    return found


def business_days_from_today(n: int) -> str:
    """Return an ISO date n business days from today (skips Sat/Sun)."""
    d = dt.date.today()
    added = 0
    while added < n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d.isoformat()


def due_for_followup() -> list[dict]:
    """Rows with status SENT whose followup_date has passed."""
    today = dt.date.today().isoformat()
    return [
        row for row in load_history()
        if row["status"] == "SENT" and row["followup_date"] and row["followup_date"] <= today
    ]
