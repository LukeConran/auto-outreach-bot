# Research Outreach Pipeline

One command discovers relevant ML researchers in your domains, pulls their
work, writes a personalized hook + draft email, and logs everything to a
tracking sheet. You review and send — nothing is auto-sent.

```
interests -> [1 DISCOVER] -> [2 ENRICH] -> [3 CONTACT] -> [4 SCORE] -> [5 DRAFT] -> [6 TRACK] -> review/send
             arXiv            S2 + GitHub    emails         Grok rank    Grok hook+email  CSV/Sheet
```

Grok (via the xAI API) powers query expansion, relevance scoring, and
writing. Every other stage hits a free, legitimate public API — arXiv,
Semantic Scholar, GitHub. LinkedIn is intentionally out of scope (automating
it violates ToS).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in XAI_API_KEY at minimum
```

Edit `config.py`:
- `INTERESTS` — your search domains
- `POSITIONING` — your pitch/GitHub/resume/ask, used verbatim in drafts

## Run

```bash
python run.py --limit 5
```

This prints progress through all six stages, writes personalized drafts to
`pending/<author_id>.json`, and appends rows to `history/contacts.csv`
(status `DRAFT`). Re-running never re-contacts anyone already in that CSV —
dedup key is the Semantic Scholar `author_id`.

Check for people due a one-time follow-up nudge (6 business days after
`SENT`, no reply):

```bash
python run.py --followups
```

## Review and send (the human gate)

Nothing sends automatically.
1. Open `pending/<author_id>.json` — read the hook + email body.
2. If it's good, send it yourself (or wire up the Gmail-draft step below)
   and manually flip the row's status via `track.update_status(author_id,
   "APPROVED")` / `"SENT"`.

## Tests

```bash
pytest -q
```

51 tests cover every stage with mocked APIs (arXiv XML, Semantic Scholar
JSON, GitHub JSON, xAI chat completions) — no network calls, no API key
required to run the suite. There's also an end-to-end pipeline test proving:
- a candidate flows through all 6 stages and lands in `pending/` + the CSV
- `--limit` is respected
- re-running is idempotent (no duplicate contacts)
- low relevance scores and missing emails correctly drop a candidate

## What you need to provide to make this fully live

| Needed | Why | Where |
|---|---|---|
| **xAI API key** (`XAI_API_KEY`) | Powers query expansion, relevance scoring, hook + email writing — the whole "agent" layer. Without it, `discover.py` still falls back to naive queries, but `score.py`/`draft.py` will raise. | `.env`, get one at console.x.ai |
| **Your interests + positioning** | `config.INTERESTS` / `config.POSITIONING` are placeholders — fill in your real pitch, GitHub link, resume link, and ask. | `config.py` |
| GitHub token (optional) | Raises GitHub API rate limit from 60/hr to 5000/hr for author lookups + email fallback. | `.env` → `GITHUB_TOKEN` |
| Semantic Scholar API key (optional) | Raises S2 rate limits if you're running large batches. | `.env` → `SEMANTIC_SCHOLAR_API_KEY` |
| Google service account + Sheet ID (optional) | Only needed if you want the live Google Sheet instead of the CSV. Swap `track.py`'s read/write functions for `gspread` calls — same column schema (`COLUMNS` in `track.py`), same dedup contract (`already_contacted`). | `.env` → `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEET_ID` |
| Gmail API credentials (optional) | Only needed for the "create Gmail draft" convenience step (still requires you to click send). Not implemented yet — currently you send manually from `pending/*.json`. | not yet wired |

### Not yet built (call out for the demo)
- Google Sheets backend (CSV works today, same schema, swap is mechanical)
- Gmail-draft creation step (`create_draft` via Gmail API) — currently a manual copy/paste from `pending/*.json`
- PatentsView integration (optional per the spec, not required for the demo)
- OpenAlex as a second discovery source (arXiv alone is sufficient for the demo path)

## Guardrails baked in
- Never auto-sends — writes local draft files + a DRAFT row only
- Hard daily cap (`DAILY_CAP` in `config.py`, also `--limit` is clamped to it)
- Dedup against `history/contacts.csv` on every run
- Relevance threshold (`RELEVANCE_THRESHOLD`) drops low-fit candidates before a draft is ever written
- On-disk GET cache (`.cache/`, 1-day TTL) to stay under arXiv/Semantic Scholar rate limits
- Secrets only ever read from `.env` (gitignored), never written to the sheet or repo
