"""
utils/job_fetcher.py — Multi-source job fetcher
================================================
Supports four sources selectable via --source flag:

  mock        Hardcoded sample jobs (default, no API keys needed)
  jobspy      python-jobspy: scrapes Indeed + LinkedIn + Glassdoor + ZipRecruiter (free, no key)
  jsearch     JSearch via RapidAPI: aggregates LinkedIn, Indeed, Glassdoor (free tier 200 req/mo)
  llm_careers LLM-powered: reads resume, picks target companies, scrapes their careers pages live

Usage from main.py:
  jobs = fetch_jobs(query=query, location=location, source=source, resume_text=resume_text)

Environment variables:
  RAPIDAPI_KEY      — required for --source jsearch
  ANTHROPIC_API_KEY — required for --source llm_careers (or set LLM_PROVIDER=openai + OPENAI_API_KEY)
"""

from __future__ import annotations

import os
import json
import time
import re
import requests
from typing import Optional

# ── Public entry point ────────────────────────────────────────────────────────

def fetch_jobs(
    query: str = "software engineer",
    location: str = "Canada",
    source: str = "mock",
    resume_text: str = "",
    max_results: int = 20,
) -> list[dict]:
    """
    Fetch jobs from the chosen source and normalise them into the shared schema:

      {
        "title":    str,
        "company":  str,
        "location": str,
        "salary":   str | None,
        "salary_cad": int,        # best-effort numeric for filter comparisons
        "description": str,
        "url":      str,
      }
    """
    print(f"  [job_fetcher] source={source!r}  query={query!r}  location={location!r}")

    if source == "mock":
        return _fetch_mock(query, location)
    elif source == "jobspy":
        return _fetch_jobspy(query, location, max_results)
    elif source == "jsearch":
        return _fetch_jsearch(query, location, max_results)
    elif source == "llm_careers":
        return _fetch_llm_careers(resume_text, query, location, max_results)
    else:
        raise ValueError(
            f"Unknown source {source!r}. Choose: mock | jobspy | jsearch | llm_careers"
        )


# ── Source A: Mock (original hardcoded data) ──────────────────────────────────

def _fetch_mock(query: str, location: str) -> list[dict]:
    return [
        {
            "title": "Senior Software Engineer — Backend",
            "company": "Shopify",
            "location": "Ottawa, Canada (Remote)",
            "salary": "CAD 180,000 – 220,000",
            "salary_cad": 200_000,
            "description": (
                "Build and scale Shopify's core commerce platform. "
                "Strong Python or Ruby experience required. "
                "You'll work with Kafka, Redis, and PostgreSQL at massive scale. "
                "CI/CD expertise and a track record of shipping production systems expected."
            ),
            "url": "https://www.shopify.com/careers",
        },
        {
            "title": "Machine Learning Engineer",
            "company": "Cohere",
            "location": "Toronto, Canada",
            "salary": "CAD 160,000 – 200,000",
            "salary_cad": 180_000,
            "description": (
                "Join Cohere's research engineering team. "
                "Design, train, and deploy large language models. "
                "Strong Python, PyTorch, and distributed training experience required. "
                "Prior publications or open-source contributions a plus."
            ),
            "url": "https://cohere.com/careers",
        },
        {
            "title": "Data Engineer",
            "company": "RBC",
            "location": "Toronto, Canada",
            "salary": "CAD 110,000 – 140,000",
            "salary_cad": 125_000,
            "description": (
                "Design and maintain data pipelines for RBC's analytics platform. "
                "Spark, Airflow, and dbt experience preferred. "
                "SQL proficiency essential. Knowledge of financial data a plus."
            ),
            "url": "https://jobs.rbc.com",
        },
        {
            "title": "Frontend Engineer — React",
            "company": "Wealthsimple",
            "location": "Toronto, Canada (Hybrid)",
            "salary": "CAD 130,000 – 160,000",
            "salary_cad": 145_000,
            "description": (
                "Build beautiful, accessible financial interfaces used by millions. "
                "Expert-level React, TypeScript, and CSS. "
                "Experience with design systems and performance optimisation required."
            ),
            "url": "https://www.wealthsimple.com/en-ca/careers",
        },
        {
            "title": "DevOps / Platform Engineer",
            "company": "Lightspeed Commerce",
            "location": "Montreal, Canada",
            "salary": "CAD 120,000 – 150,000",
            "salary_cad": 135_000,
            "description": (
                "Own Lightspeed's cloud infrastructure on AWS and GCP. "
                "Kubernetes, Terraform, and Helm are daily tools. "
                "Strong scripting (Python / Bash) and SRE mindset required."
            ),
            "url": "https://www.lightspeedcommerce.com/careers",
        },
    ]


# ── Source B: python-jobspy ───────────────────────────────────────────────────

def _fetch_jobspy(query: str, location: str, max_results: int) -> list[dict]:
    """
    Uses the open-source python-jobspy library to scrape Indeed, LinkedIn,
    Glassdoor, and ZipRecruiter simultaneously.

    Install: pip install python-jobspy
    No API key required. May occasionally break if sites change their HTML.
    """
    try:
        from jobspy import scrape_jobs  # type: ignore
    except ImportError:
        raise ImportError(
            "python-jobspy is not installed.\n"
            "Run: pip install python-jobspy\n"
            "Then retry with --source jobspy"
        )

    print("  [jobspy] Scraping Indeed + LinkedIn + Glassdoor + ZipRecruiter …")

    df = scrape_jobs(
        site_name=["indeed", "linkedin", "glassdoor", "zip_recruiter"],
        search_term=query,
        location=location,
        results_wanted=max_results,
        hours_old=72,           # only jobs posted in last 3 days
        country_indeed="USA",   # change to "Canada" / "UK" etc. as needed
    )

    jobs = []
    for _, row in df.iterrows():
        salary_str = _jobspy_salary(row)
        jobs.append({
            "title":       str(row.get("title", "Unknown")),
            "company":     str(row.get("company", "Unknown")),
            "location":    str(row.get("location", location)),
            "salary":      salary_str,
            "salary_cad":  _parse_salary_to_cad(salary_str),
            "description": str(row.get("description", ""))[:4000],
            "url":         str(row.get("job_url", "")),
        })

    print(f"  [jobspy] ✓ {len(jobs)} jobs scraped")
    return jobs


def _jobspy_salary(row) -> Optional[str]:
    """Best-effort salary string from jobspy row."""
    min_s = row.get("min_amount")
    max_s = row.get("max_amount")
    interval = str(row.get("interval", "yearly")).lower()
    currency = str(row.get("currency", "USD")).upper()
    if min_s and max_s:
        return f"{currency} {int(min_s):,} – {int(max_s):,} / {interval}"
    if min_s:
        return f"{currency} {int(min_s):,}+ / {interval}"
    return None


# ── Source C: JSearch via RapidAPI ────────────────────────────────────────────

def _fetch_jsearch(query: str, location: str, max_results: int) -> list[dict]:
    """
    JSearch aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter via RapidAPI.
    Free tier: 200 requests / month.

    Set environment variable:  RAPIDAPI_KEY=your_key_here
    Sign up at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    """
    api_key = os.environ.get("RAPIDAPI_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "RAPIDAPI_KEY is not set.\n"
            "1. Sign up at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch\n"
            "2. export RAPIDAPI_KEY=your_key_here\n"
            "3. Retry with --source jsearch"
        )

    print("  [jsearch] Querying JSearch / RapidAPI …")

    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    jobs = []
    page = 1
    per_page = min(10, max_results)  # JSearch max per page is 10

    while len(jobs) < max_results:
        params = {
            "query": f"{query} in {location}",
            "page": str(page),
            "num_pages": "1",
            "date_posted": "week",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("data", [])
        if not results:
            break

        for item in results:
            salary_str = _jsearch_salary(item)
            jobs.append({
                "title":       item.get("job_title", "Unknown"),
                "company":     item.get("employer_name", "Unknown"),
                "location":    _jsearch_location(item),
                "salary":      salary_str,
                "salary_cad":  _parse_salary_to_cad(salary_str),
                "description": (item.get("job_description") or "")[:4000],
                "url":         item.get("job_apply_link") or item.get("job_google_link", ""),
            })
            if len(jobs) >= max_results:
                break

        page += 1
        time.sleep(0.5)   # be polite to the API

    print(f"  [jsearch] ✓ {len(jobs)} jobs fetched")
    return jobs


def _jsearch_location(item: dict) -> str:
    parts = [
        item.get("job_city", ""),
        item.get("job_state", ""),
        item.get("job_country", ""),
    ]
    return ", ".join(p for p in parts if p)


def _jsearch_salary(item: dict) -> Optional[str]:
    min_s = item.get("job_min_salary")
    max_s = item.get("job_max_salary")
    currency = item.get("job_salary_currency", "USD").upper()
    period = item.get("job_salary_period", "YEAR")
    if min_s and max_s:
        return f"{currency} {int(min_s):,} – {int(max_s):,} / {period.lower()}"
    if min_s:
        return f"{currency} {int(min_s):,}+ / {period.lower()}"
    return None


# ── Source D: LLM-powered career-page scraper ─────────────────────────────────

def _fetch_llm_careers(
    resume_text: str,
    query: str,
    location: str,
    max_results: int,
) -> list[dict]:
    """
    Three-step AI pipeline:
      1. Ask the LLM which companies match this resume + query.
      2. Find each company's careers page URL (via requests + heuristics).
      3. Fetch the careers page, ask the LLM to extract job listings as JSON.

    Requires: ANTHROPIC_API_KEY or (LLM_PROVIDER=openai + OPENAI_API_KEY)
    Uses your existing utils/llm.py wrapper.
    """
    try:
        from utils.llm import call_llm  # reuse the project's own LLM wrapper
    except ImportError:
        raise ImportError("Could not import utils.llm — run from the project root.")

    if not resume_text:
        raise ValueError(
            "--source llm_careers requires the resume to be loaded first. "
            "Make sure --resume points to a valid file."
        )

    # ── Step 1: Identify target companies ─────────────────────────────────────
    print("  [llm_careers] Step 1 — Asking LLM to identify target companies …")

    company_prompt = f"""You are a career advisor helping a job seeker find the best companies to apply to.

RESUME (excerpt — first 3000 chars):
{resume_text[:3000]}

JOB TARGET: {query} in {location}

Task: Return a JSON array of exactly 8 companies that would be an excellent fit for this candidate.
For each company include:
  - "name": official company name
  - "careers_url": the direct URL to their careers/jobs page (e.g. https://stripe.com/jobs)
  - "why": one sentence explaining the fit

Consider companies across different sizes (startups, mid-size, large tech).
Include companies hiring for {query} roles.
For location={location!r}, include both local companies and remote-friendly global ones.

IMPORTANT: Return ONLY a valid JSON array. No markdown, no explanation.
Example format:
[{{"name": "Stripe", "careers_url": "https://stripe.com/jobs", "why": "Strong Python/payments fit"}}]
"""

    companies_raw = call_llm(company_prompt)
    companies = _safe_parse_json(companies_raw)

    if not companies or not isinstance(companies, list):
        print("  [llm_careers] ⚠ Could not parse company list from LLM, using fallbacks.")
        companies = _fallback_companies(query, location)

    print(f"  [llm_careers] ✓ {len(companies)} target companies identified")
    for c in companies:
        print(f"    • {c.get('name')} — {c.get('careers_url')}")

    # ── Step 2 & 3: Fetch each careers page and extract jobs ──────────────────
    print("\n  [llm_careers] Step 2 — Scraping careers pages and extracting jobs …")

    all_jobs: list[dict] = []
    jobs_per_company = max(2, max_results // len(companies))

    for company in companies:
        name = company.get("name", "Unknown")
        careers_url = company.get("careers_url", "")

        if not careers_url:
            print(f"    ⚠ {name}: no URL, skipping")
            continue

        print(f"    Fetching {name} ({careers_url}) …", end=" ", flush=True)

        page_text = _fetch_page_text(careers_url)
        if not page_text:
            print("failed (could not fetch page)")
            continue

        print(f"{len(page_text)} chars")

        # Ask LLM to extract job listings from the page HTML/text
        extract_prompt = f"""You are a web scraping assistant. Below is text scraped from {name}'s careers page.

Extract up to {jobs_per_company} job listings for roles related to: "{query}"
Focus on jobs in or remote-friendly for: "{location}"

For each job return a JSON object with these exact keys:
  - "title": job title
  - "company": "{name}"
  - "location": job location or "Remote"
  - "salary": salary range as string, or null if not listed
  - "description": job description or responsibilities (up to 500 chars)
  - "url": direct application URL or the careers page URL if not found

Return ONLY a valid JSON array of job objects. If no relevant jobs found, return [].
No markdown, no explanation.

CAREERS PAGE TEXT (first 8000 chars):
{page_text[:8000]}
"""

        jobs_raw = call_llm(extract_prompt)
        jobs = _safe_parse_json(jobs_raw)

        if not isinstance(jobs, list):
            print(f"    ⚠ {name}: LLM did not return a list, skipping")
            continue

        for job in jobs:
            if not isinstance(job, dict):
                continue
            # Normalise and add salary_cad
            salary_str = job.get("salary")
            job["salary_cad"] = _parse_salary_to_cad(salary_str)
            job.setdefault("company", name)
            job.setdefault("url", careers_url)
            job.setdefault("description", "")
            all_jobs.append(job)

        print(f"    ✓ {name}: {len(jobs)} jobs extracted")
        time.sleep(1)  # polite delay between requests

    print(f"\n  [llm_careers] ✓ Total: {len(all_jobs)} jobs extracted across all companies")
    return all_jobs[:max_results]


def _fetch_page_text(url: str, timeout: int = 15) -> str:
    """Fetch a URL and return cleaned text (strips most HTML tags)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        text = resp.text

        # Light HTML stripping — remove script/style blocks, then tags
        text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    except Exception as exc:
        print(f"(error: {exc})", end=" ")
        return ""


def _fallback_companies(query: str, location: str) -> list[dict]:
    """Used if the LLM company-selection step fails."""
    return [
        {"name": "Shopify", "careers_url": "https://www.shopify.com/careers"},
        {"name": "Stripe",  "careers_url": "https://stripe.com/jobs"},
        {"name": "Notion",  "careers_url": "https://www.notion.so/careers"},
        {"name": "Figma",   "careers_url": "https://www.figma.com/careers"},
    ]


# ── Shared helpers ────────────────────────────────────────────────────────────

def _safe_parse_json(text: str):
    """Parse JSON from LLM output, tolerating markdown fences."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find first [...] or {...} block
        m = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    return None


def _parse_salary_to_cad(salary_str: Optional[str]) -> int:
    """
    Best-effort: extract the higher number from a salary string and convert to CAD.
    Very rough — USD→CAD ×1.35, GBP→CAD ×1.70, EUR→CAD ×1.45.
    Returns 0 if unparseable.
    """
    if not salary_str:
        return 0
    salary_str = salary_str.upper()

    # Find all numbers (strip commas/dots used as thousand separators)
    numbers = [int(n.replace(",", "")) for n in re.findall(r"[\d,]+", salary_str)]
    if not numbers:
        return 0

    amount = max(numbers)

    # If listed as hourly/monthly, annualise roughly
    if "HOUR" in salary_str:
        amount = amount * 40 * 52
    elif "MONTH" in salary_str:
        amount = amount * 12

    # Currency conversion
    if "GBP" in salary_str or "£" in salary_str:
        amount = int(amount * 1.70)
    elif "EUR" in salary_str or "€" in salary_str:
        amount = int(amount * 1.45)
    elif "USD" in salary_str or "$" in salary_str:
        amount = int(amount * 1.35)
    # Already CAD or unknown → keep as-is

    return amount
