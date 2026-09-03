#!/usr/bin/env python3
"""Orchestrates the full DISCOVER -> ENRICH -> CONTACT -> SCORE -> DRAFT -> TRACK pipeline.

Usage:
    python run.py --limit 5
    python run.py --limit 5 --dry-run     # skip Grok/network calls, print what would happen
    python run.py --followups             # check history for anyone due a one-time nudge
"""
import argparse
import sys

import config
import contact
import discover
import draft as draft_mod
import enrich
import score as score_mod
import track


def run_pipeline(limit: int, verbose: bool = True) -> list[dict]:
    """Runs one full pass. Returns the list of newly drafted candidates (as dicts)."""
    def log(msg):
        if verbose:
            print(msg)

    log(f"[1/6] DISCOVER: expanding interests and searching arXiv...")
    papers = discover.discover()
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

            log(f"[4/6] SCORE: rating relevance vs. positioning")
            try:
                result = score_mod.score_candidate(
                    config.POSITIONING, paper.title, paper.abstract
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

            log(f"[5/6] DRAFT: writing hook + email")
            try:
                d = draft_mod.build_draft(
                    author_id=profile.author_id,
                    name=profile.name,
                    email=email,
                    paper_title=paper.title,
                    paper_abstract=paper.abstract,
                )
            except Exception as e:
                log(f"      draft failed ({e}), skipping")
                continue
            draft_path = draft_mod.save_draft(d)

            log(f"[6/6] TRACK: logging to sheet")
            track.add_row(
                author_id=profile.author_id,
                name=profile.name,
                affiliation=profile.affiliation,
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
    parser = argparse.ArgumentParser(description="Autonomous research-outreach pipeline")
    parser.add_argument("--limit", type=int, default=5, help="max new candidates to draft")
    parser.add_argument("--followups", action="store_true", help="check for due follow-ups instead")
    args = parser.parse_args()

    if args.followups:
        run_followups()
        return

    limit = min(args.limit, config.DAILY_CAP)
    kept = run_pipeline(limit=limit)

    print("\n=== SUMMARY ===")
    print(f"Drafted {len(kept)} new candidate(s).")
    for c in kept:
        print(f"  - {c['name']} <{c['email']}>  score={c['score']}  {c['draft_path']}")
    print(f"\nReview drafts in ./pending/ and rows in ./history/contacts.csv")
    print("Nothing is sent automatically. Approve + send manually (or via Gmail draft step).")


if __name__ == "__main__":
    sys.exit(main())
