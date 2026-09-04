#!/usr/bin/env python3
"""Orchestrates the full DISCOVER -> ENRICH -> CONTACT -> SCORE -> DRAFT -> TRACK pipeline.

Default path finds people on US industry teams (COMPANY_ALLOWLIST) and drafts a
15–20 minute networking email. Nothing is sent automatically.

Usage:
    python run.py --limit 5
    python run.py --limit 5 --mode academic   # old arXiv/academia path
    python run.py --followups                 # check history for a one-time nudge
"""
import argparse
import sys

import config
import contact
import discover
import draft as draft_mod
import enrich
import industry
import score as score_mod
import track


def run_pipeline(limit: int, verbose: bool = True, mode: str | None = None) -> list[dict]:
    """Runs one full pass. Returns the list of newly drafted candidates (as dicts).

    `mode` is "industry" (default) or "academic". Industry applies company allowlist
    + US_ONLY + academia-drop filters. Never sends email.
    """
    mode = (mode or config.DISCOVER_MODE or "industry").lower()
    industry_mode = mode != "academic"

    def log(msg):
        if verbose:
            print(msg)

    log(f"[1/6] DISCOVER: {mode} path (interests + "
        f"{'company/US filters' if industry_mode else 'academic arXiv'})...")
    papers = discover.discover(mode=mode)
    log(f"      found {len(papers)} candidate papers")

    kept: list[dict] = []
    seen_authors = set()

    for paper in papers:
        if len(kept) >= limit:
            break
        for author_name in paper.authors:
            if len(kept) >= limit:
                break
            if author_name in seen_authors:
                continue
            seen_authors.add(author_name)

            log(f"[2/6] ENRICH: {author_name}")
            profile = enrich.enrich(author_name)
            if profile is None:
                continue

            if track.already_contacted(profile.author_id):
                log(f"      skip (already in history)")
                continue

            paper_aff = (paper.author_affiliations or {}).get(author_name, "")
            affiliation = profile.affiliation or paper_aff

            if industry_mode and not industry.keep_candidate(affiliation=affiliation):
                log(f"      skip (not US industry allowlist / academia-only)")
                continue

            company = industry.match_company(affiliation)
            company_name = company.name if company else ""

            log(f"[4/6] SCORE: rating industry + interest fit for a networking chat")
            try:
                result = score_mod.score_candidate(
                    config.POSITIONING, paper.title, paper.abstract,
                    affiliation=affiliation, company=company_name,
                )
            except Exception as e:
                log(f"      score failed ({e}), skipping")
                continue
            if not score_mod.is_relevant(result):
                log(f"      score {result.score} below threshold, skip")
                continue

            log(f"[3/6] CONTACT: extracting email")
            email = contact.find_contact_email(paper.url, profile.github_username)
            if not email:
                log(f"      no email found, skip")
                continue

            if industry_mode and not industry.keep_candidate(
                affiliation=affiliation, email=email
            ):
                log(f"      skip (email/affiliation failed industry+US filter)")
                continue

            # Recompute company in case the email domain is the allowlist hit.
            company = industry.match_company(affiliation, email)
            company_name = company.name if company else company_name

            log(f"[5/6] DRAFT: writing hook + email (human review; never sent)")
            try:
                d = draft_mod.build_draft(
                    author_id=profile.author_id,
                    name=profile.name,
                    email=email,
                    paper_title=paper.title,
                    paper_abstract=paper.abstract,
                    affiliation=affiliation,
                    company=company_name,
                )
            except Exception as e:
                log(f"      draft failed ({e}), skipping")
                continue
            draft_path = draft_mod.save_draft(d)

            log(f"[6/6] TRACK: logging to sheet")
            track.add_row(
                author_id=profile.author_id,
                name=profile.name,
                affiliation=affiliation,
                email=email,
                hook=d.hook,
                draft_link=draft_path,
                status="DRAFT",
            )

            kept.append({
                "author_id": profile.author_id,
                "name": profile.name,
                "email": email,
                "paper_title": paper.title,
                "score": result.score,
                "draft_path": draft_path,
            })
            log(f"      kept: {profile.name} (score {result.score})\n")

    return kept


def run_followups(verbose: bool = True):
    """One-time nudge for anyone SENT and past their follow-up date, with no reply."""
    due = track.due_for_followup()
    if verbose:
        print(f"{len(due)} contact(s) due for a follow-up nudge.")
    return due


def main():
    parser = argparse.ArgumentParser(
        description="US industry networking outreach pipeline (drafts only; never sends)"
    )
    parser.add_argument("--limit", type=int, default=5, help="max new candidates to draft")
    parser.add_argument(
        "--mode",
        choices=["industry", "academic"],
        default=None,
        help="discovery path (default: config.DISCOVER_MODE, currently industry)",
    )
    parser.add_argument("--followups", action="store_true", help="check for due follow-ups instead")
    args = parser.parse_args()

    if args.followups:
        run_followups()
        return

    limit = min(args.limit, config.DAILY_CAP)
    kept = run_pipeline(limit=limit, mode=args.mode)

    print("\n=== SUMMARY ===")
    print(f"Drafted {len(kept)} new candidate(s).")
    for c in kept:
        print(f"  - {c['name']} <{c['email']}>  score={c['score']}  {c['draft_path']}")
    print(f"\nReview drafts in ./pending/ and rows in ./history/contacts.csv")
    print("Nothing is sent automatically. Approve + send manually (or via Gmail draft step).")


if __name__ == "__main__":
    sys.exit(main())
