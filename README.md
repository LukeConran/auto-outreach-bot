# US Industry Networking Outreach

One command finds people on **US industry teams** at tech / tech-related
companies whose work overlaps Luke's interests, then writes a personalized
hook + a 15–20 minute **networking** email. You review `pending/*.json` and
send yourself — **nothing is auto-sent**. Scripts and agents never send email.

```
interests -> [1 DISCOVER] -> [2 ENRICH] -> [3 CONTACT] -> [4 SCORE] -> [5 DRAFT] -> [6 TRACK] -> human review/send
             industry-filtered   S2 + GitHub    emails      Grok rank     Grok hook+email   CSV/Sheet
             arXiv (+ plugins)
```

Default discovery is **industry** (`DISCOVER_MODE = "industry"`): arXiv / Semantic
Scholar results are kept only when an author matches `COMPANY_ALLOWLIST` (name or
email domain) and looks like **United States industry** employment. Pure
university / `*.edu` corresponding authors with no company affiliation are
dropped. The old academic-only path is still callable (`--mode academic` or
`DISCOVER_MODE=academic`).

**Ask (every draft):** 15–20 minutes to discuss their career path (especially
research-without-PhD paths), recent work aligned with Luke's interests, or
shared background (Texas A&M, raised in St. Louis).

**Hard bans:** never ask for a referral; never mention internships, new-grad
search, or that Luke is job hunting.

PR #1 filled an internship-shaped `POSITIONING` ("Summer 2027 ML eng internship
… pointer to open roles"). That framing is superseded here — do not treat #1's
pitch as current.

## What this is not

- Not a job / internship / new-grad pipeline
- Not a referral machine
- **LinkedIn is out of scope** — never automate LinkedIn, never scrape it
  (ToS). Do not add LinkedIn as a discovery source.
- Not an auto-sender — human gate on every `pending/*.json`

## Agent vs Python path

Cursor **Grok Bot** can reason over this repo and draft emails from `POSITIONING`
without an `XAI_API_KEY`. The **Python** path (`python run.py`) still calls
`xai_client.py` (xAI Grok) for query expansion, scoring, and drafting, so that
CLI still needs `XAI_API_KEY` in `.env`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Optional: XAI_API_KEY for the Python Grok path
# Optional but recommended: GITHUB_TOKEN, SEMANTIC_SCHOLAR_API_KEY (rate limits)
```

Edit `config.py`:

- `INTERESTS` — search domains (3D perception, AV, medical 3D MRI, …)
- `POSITIONING` — networking intro + 15–20 minute ask (used verbatim in drafts)
- `COMPANY_ALLOWLIST` — append a `{name, needles, domains}` dict to add a company
- `US_ONLY` — default `True`
- `DISCOVER_MODE` — default `"industry"`; `"academic"` restores the old path
- `DAILY_CAP`, `RELEVANCE_THRESHOLD`, `FOLLOWUP_BUSINESS_DAYS` — unchanged guardrails

## Run

```bash
python run.py --limit 5
python run.py --limit 5 --mode academic   # old arXiv/academia path
```

`--limit` is clamped to `DAILY_CAP`. Progress prints through all six stages,
personalized drafts land in `pending/<author_id>.json`, and rows append to
`history/contacts.csv` (status `DRAFT`). Re-running never re-contacts anyone
already in that CSV — dedup key is the Semantic Scholar `author_id`
(`track.already_contacted`).

Check for people due a one-time follow-up nudge (6 business days after
`SENT`, no reply):

```bash
python run.py --followups
```

## Review and send (the human gate)

Nothing sends automatically. Agent/scripts only write local JSON.

1. Open `pending/<author_id>.json` — read the hook + email body.
2. Confirm it is a 15–20 minute career/work/background chat, with no referral
   or internship/new-grad language.
3. If it's good, send it yourself (or wire up the Gmail-draft step below)
   and flip the row's status via `track.update_status(author_id, "APPROVED")`
   / `"SENT"`.

## Tests

```bash
pytest -q
```

Tests cover every stage with mocked APIs (arXiv XML, Semantic Scholar JSON,
GitHub JSON, xAI chat completions) — no network calls, no API key required.
They include allowlist / academia-drop / US filters, draft-prompt bans, and an
end-to-end pipeline proving:

- a US industry candidate flows through all 6 stages into `pending/` + the CSV
- academia-only authors are dropped in industry mode
- `--limit` is respected and clamped to `DAILY_CAP`
- re-running is idempotent (no duplicate contacts)
- low relevance scores and missing emails correctly drop a candidate

## What you need to provide to make this fully live

| Needed | Why | Where |
|---|---|---|
| **xAI API key** (`XAI_API_KEY`) | Python path: query expansion, scoring, hook + email writing. Without it, `discover.py` still falls back to naive queries, but `score.py`/`draft.py` will raise. Grok Bot can draft without this key. | `.env`, get one at console.x.ai |
| **Interests, positioning, company list** | `config.INTERESTS` / `POSITIONING` / `COMPANY_ALLOWLIST` | `config.py` |
| GitHub token (optional, recommended) | Raises GitHub API rate limit from 60/hr to 5000/hr for author lookups + email fallback. | `.env` → `GITHUB_TOKEN` |
| Semantic Scholar API key (optional, recommended) | Raises S2 rate limits for author + paper affiliation lookups. | `.env` → `SEMANTIC_SCHOLAR_API_KEY` |
| Google service account + Sheet ID (optional) | Only needed if you want the live Google Sheet instead of the CSV. Swap `track.py`'s read/write functions for `gspread` calls — same column schema (`COLUMNS` in `track.py`), same dedup contract (`already_contacted`). | `.env` → `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEET_ID` |
| Gmail API credentials (optional) | Only needed for the "create Gmail draft" convenience step (still requires you to click send). Not implemented yet — currently you send manually from `pending/*.json`. | not yet wired |

### Not yet built

- Additional industry sources (company eng blogs, etc.) — `DiscoverySource` in
  `discover.py` is the plug-in point; arXiv + S2 affiliation filter ships now
- Google Sheets backend (CSV works today, same schema, swap is mechanical)
- Gmail-draft creation step (`create_draft` via Gmail API) — currently a manual copy/paste from `pending/*.json`
- PatentsView / OpenAlex as extra sources

## Guardrails baked in

- Never auto-sends — writes local draft files + a DRAFT row only
- Hard daily cap (`DAILY_CAP` in `config.py`; `--limit` is clamped to it)
- Dedup against `history/contacts.csv` on every run (`track.already_contacted`)
- Company allowlist + US-only + academia-only drop on the industry path
- Draft prompts + a regex post-check ban referral / internship / new-grad language
- Relevance threshold (`RELEVANCE_THRESHOLD`) drops low-fit candidates before a draft is written
- On-disk GET cache (`.cache/`, 1-day TTL) to stay under arXiv/Semantic Scholar rate limits
- Secrets only ever read from `.env` (gitignored), never written to the sheet or repo
- No LinkedIn automation
