"""
main.py — Job Search & Resume Optimisation Agent
================================================
Orchestrates the full pipeline:
  1. Load resume
  2. Fetch jobs
  3. Match & score jobs   (Agent 1)
  4. Filter jobs
  5. Generate tailored resumes  (Agent 2)
  6. Evaluate & improve resumes (Agent 3)
  7. Save outputs

Run:
  python main.py
  python main.py --query "machine learning engineer" --location "Toronto"
  python main.py --dry-run   # score jobs only, skip LLM resume writing
"""

# Load environment variables from .env file automatically (if present)
from dotenv import load_dotenv
load_dotenv()

import os
import json
import argparse
from datetime import datetime
from pathlib import Path

# ── Agent & utility imports ───────────────────────────────────────────────────
from utils.resume_loader import load_resume
from utils.job_fetcher    import fetch_jobs
from agents.matcher       import match_all_jobs
from agents.generator     import generate_tailored_resume
from agents.evaluator     import evaluate_and_improve


# ── Config ────────────────────────────────────────────────────────────────────
SCORE_THRESHOLD  = 70         # minimum match score to keep a job
SALARY_THRESHOLD = 200_000    # CAD: keep job even if score is low
OUTPUTS_DIR      = Path("outputs")


# ── Pipeline ──────────────────────────────────────────────────────────────────
def run(query: str, location: str, resume_path: str, dry_run: bool = False):
    start = datetime.now()
    print(f"\n{'='*60}")
    print(f"  JOB SEARCH AGENT  —  started {start.strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    # ── 1. Load resume ─────────────────────────────────────────────────────────
    print("STEP 1 — Loading resume...")
    resume_text = load_resume(resume_path)
    print(f"         ✓ Resume loaded ({len(resume_text)} chars)\n")

    # ── 2. Fetch jobs ──────────────────────────────────────────────────────────
    print("STEP 2 — Fetching jobs...")
    jobs = fetch_jobs(query=query, location=location)
    print(f"         ✓ {len(jobs)} jobs fetched\n")

    # ── 3. Match jobs (Agent 1) ────────────────────────────────────────────────
    print("STEP 3 — Matching jobs (Agent 1)...")
    scored_jobs = match_all_jobs(resume_text, jobs)
    print(f"         ✓ All jobs scored\n")

    _print_scores(scored_jobs)

    # ── 4. Filter jobs ─────────────────────────────────────────────────────────
    print("STEP 4 — Filtering jobs...")
    selected_jobs = [
        job for job in scored_jobs
        if job["match_score"] >= SCORE_THRESHOLD
        or job.get("salary_cad", 0) >= SALARY_THRESHOLD
    ]
    print(f"         ✓ {len(selected_jobs)} / {len(scored_jobs)} jobs selected "
          f"(score ≥ {SCORE_THRESHOLD} OR salary ≥ CAD {SALARY_THRESHOLD:,})\n")

    if not selected_jobs:
        print("  ⚠  No jobs passed the filter. "
              "Try lowering SCORE_THRESHOLD in main.py or improving the resume.")
        return

    # ── 5–6. Generate & Evaluate resumes ──────────────────────────────────────
    if dry_run:
        print("  [dry-run] Skipping resume generation. Remove --dry-run to write resumes.\n")
        return

    for i, job in enumerate(selected_jobs, 1):
        print(f"\n{'─'*60}")
        print(f"  JOB {i}/{len(selected_jobs)}: {job['title']} @ {job['company']}")
        print(f"  Score: {job['match_score']}/100  |  Salary: {job['salary'] or 'N/A'}")
        print(f"{'─'*60}")

        # ── Checkpoint: skip already-processed jobs ────────────────────────────
        folder_name = _safe_name(f"{job['company']}_{job['title']}")
        folder = OUTPUTS_DIR / folder_name
        if (folder / "improved_resume.txt").exists():
            print(f"  ⏭  Already processed — skipping. Delete the folder to rerun.")
            continue

        # Agent 2 — tailored resume
        print("STEP 5 — Generating tailored resume (Agent 2)...")
        tailored = generate_tailored_resume(resume_text, job)
        print("         ✓ Tailored resume generated")

        # Agent 3 — evaluate and improve
        print("STEP 6 — Evaluating & improving resume (Agent 3)...")
        critique, improved = evaluate_and_improve(tailored, job)
        print("         ✓ Resume improved")

        # Save outputs
        print("STEP 7 — Saving outputs...")
        _save_outputs(job, tailored, critique, improved)
        print("         ✓ Files saved")

    # ── Summary ────────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).seconds
    print(f"\n{'='*60}")
    print(f"  DONE  —  processed {len(selected_jobs)} jobs in {elapsed}s")
    print(f"  Results saved to: {OUTPUTS_DIR.resolve()}")
    print(f"{'='*60}\n")


# ── Output writer ─────────────────────────────────────────────────────────────
def _save_outputs(job: dict, tailored: str, critique: str, improved: str):
    """Create a folder per job and write three output files."""
    # Build a safe folder name from company + title
    folder_name = _safe_name(f"{job['company']}_{job['title']}")
    folder = OUTPUTS_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    # ── job_info.json ──────────────────────────────────────────────────────────
    job_info = {
        "title":         job["title"],
        "company":       job["company"],
        "location":      job["location"],
        "salary":        job["salary"],
        "url":           job["url"],
        "match_score":   job["match_score"],
        "missing_skills":job["missing_skills"],
        "reasoning":     job["reasoning"],
    }
    (folder / "job_info.json").write_text(
        json.dumps(job_info, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ── tailored_resume.txt ────────────────────────────────────────────────────
    (folder / "tailored_resume.txt").write_text(tailored, encoding="utf-8")

    # ── improved_resume.txt ────────────────────────────────────────────────────
    improved_with_critique = (
        "=" * 60 + "\n"
        "CRITIQUE\n"
        "=" * 60 + "\n"
        + critique + "\n\n"
        "=" * 60 + "\n"
        "IMPROVED RESUME\n"
        "=" * 60 + "\n"
        + improved
    )
    (folder / "improved_resume.txt").write_text(
        improved_with_critique, encoding="utf-8"
    )

    print(f"         → {folder}/")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _safe_name(text: str, max_len: int = 60) -> str:
    """Convert an arbitrary string to a safe filesystem folder name."""
    import re
    text = re.sub(r"[^\w\s-]", "", text)   # remove special chars
    text = re.sub(r"[\s]+", "_", text)     # spaces → underscores
    return text[:max_len].strip("_")


def _print_scores(scored_jobs: list):
    """Pretty-print the scoring table."""
    print(f"  {'TITLE':<40} {'COMPANY':<20} {'SCORE':>6}  {'SALARY'}")
    print(f"  {'─'*40} {'─'*20} {'─'*6}  {'─'*25}")
    for job in scored_jobs:
        flag = " ✓" if (
            job["match_score"] >= SCORE_THRESHOLD
            or job.get("salary_cad", 0) >= SALARY_THRESHOLD
        ) else ""
        print(
            f"  {job['title'][:40]:<40} "
            f"{job['company'][:20]:<20} "
            f"{job['match_score']:>5}%"
            f"  {job['salary'] or 'N/A'}"
            f"{flag}"
        )
    print()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Job Search Agent")
    parser.add_argument("--query",   default="software engineer",
                        help="Job search keyword (default: 'software engineer')")
    parser.add_argument("--location",default="Canada",
                        help="Job location (default: 'Canada')")
    parser.add_argument("--resume",  default="resume.docx",
                        help="Path to your resume .docx file (default: resume.docx)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Score jobs but skip resume generation (no LLM writing calls)")
    args = parser.parse_args()

    run(query=args.query, location=args.location, resume_path=args.resume, dry_run=args.dry_run)
