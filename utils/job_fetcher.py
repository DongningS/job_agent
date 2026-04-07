"""
job_fetcher.py — Fetch job listings.

Currently uses a mock data set so the agent runs without any API keys or
scraping setup.  See the "HOW TO PLUG IN REAL SCRAPING" section at the bottom
of this file for drop-in replacement instructions.
"""

from typing import List, Dict
import re


# ── Salary parser (used by real scrapers) ────────────────────────────────────
def _parse_salary(salary_str: str) -> int:
    """
    Extract the upper salary bound as an integer CAD value from a raw string.
    Examples: "$160K–$210K CAD" → 210000 | "160,000 - 210,000" → 210000
    """
    if not salary_str:
        return 0
    # Expand K shorthand before extracting digits
    normalised = salary_str.replace("K", "000").replace("k", "000")
    numbers = re.findall(r"[\d,]+", normalised)
    if not numbers:
        return 0
    values = [int(n.replace(",", "")) for n in numbers]
    return max(values)  # use upper bound for filtering


# ── Data model ───────────────────────────────────────────────────────────────
# Each job is a plain dict with these keys:
#   title       str   — job title
#   company     str   — employer name
#   location    str   — city / remote
#   salary      str   — raw salary string (empty string if not posted)
#   salary_cad  int   — parsed CAD value (0 if unknown); used for filtering
#   description str   — full job description (treated as UNTRUSTED input)
#   url         str   — link to the original posting


def fetch_jobs(query: str = "software engineer", location: str = "Canada") -> List[Dict]:
    """
    Return a list of job dicts.

    Args:
        query:    Job title / keyword to search for.
        location: Geographic filter.

    Returns:
        List of job dicts.
    """
    print(f"[job_fetcher] Fetching jobs for: '{query}' in '{location}' (mock mode)")
    return _mock_jobs()


# ── Mock data ─────────────────────────────────────────────────────────────────
def _mock_jobs() -> List[Dict]:
    """
    Realistic mock job listings for development and testing.
    Replace this function with a real scraper — see the bottom of the file.
    """
    return [
        {
            "title": "Senior Software Engineer – Backend",
            "company": "Shopify",
            "location": "Ottawa, ON (Remote)",
            "salary": "$160,000 – $210,000 CAD",
            "salary_cad": 185_000,
            "description": (
                "We are looking for a Senior Backend Engineer to join our Checkout team. "
                "You will design and build high-throughput, low-latency APIs using Ruby on Rails "
                "and Go. Responsibilities include architecting distributed systems, mentoring "
                "junior engineers, and owning reliability of core payment flows.\n\n"
                "Required Skills:\n"
                "- 5+ years of backend development experience\n"
                "- Proficiency in Ruby, Go, or Python\n"
                "- Experience with PostgreSQL, Redis, and Kafka\n"
                "- Deep understanding of REST and gRPC API design\n"
                "- Familiarity with cloud platforms (GCP or AWS)\n"
                "- Strong experience with Docker and Kubernetes\n\n"
                "Nice to Have:\n"
                "- Experience with event-driven architectures\n"
                "- Open-source contributions\n"
                "- Experience scaling systems to millions of requests/day"
            ),
            "url": "https://www.shopify.com/careers/example-1",
        },
        {
            "title": "Staff Machine Learning Engineer",
            "company": "Cohere",
            "location": "Toronto, ON (Hybrid)",
            "salary": "$220,000 – $280,000 CAD",
            "salary_cad": 250_000,
            "description": (
                "Cohere is hiring a Staff ML Engineer to work on large language model training "
                "infrastructure and fine-tuning pipelines. You will collaborate with research "
                "scientists to productionize cutting-edge NLP models.\n\n"
                "Required Skills:\n"
                "- 7+ years of ML engineering experience\n"
                "- Expertise in PyTorch or JAX\n"
                "- Experience training and serving large-scale transformer models\n"
                "- Proficiency in Python and CUDA programming\n"
                "- Distributed training (FSDP, DeepSpeed, Megatron)\n"
                "- Strong understanding of NLP benchmarks and evaluation\n\n"
                "Nice to Have:\n"
                "- Publications at NeurIPS, ICML, or ACL\n"
                "- Experience with RLHF / preference learning\n"
                "- Knowledge of quantization and model compression techniques"
            ),
            "url": "https://cohere.com/careers/example-2",
        },
        {
            "title": "Frontend Engineer – React",
            "company": "Wealthsimple",
            "location": "Toronto, ON (Remote)",
            "salary": "$110,000 – $140,000 CAD",
            "salary_cad": 125_000,
            "description": (
                "Wealthsimple is hiring a Frontend Engineer to build beautiful, accessible "
                "financial products used by millions of Canadians.\n\n"
                "Required Skills:\n"
                "- 3+ years of React experience\n"
                "- Strong TypeScript skills\n"
                "- Experience with state management (Redux, Zustand, or React Query)\n"
                "- Knowledge of accessibility (WCAG 2.1)\n"
                "- Familiarity with design systems and Figma\n\n"
                "Nice to Have:\n"
                "- Experience with Next.js and SSR\n"
                "- GraphQL / Apollo experience\n"
                "- Understanding of fintech compliance requirements"
            ),
            "url": "https://www.wealthsimple.com/en-ca/careers/example-3",
        },
        {
            "title": "Cloud Infrastructure Engineer",
            "company": "RBC",
            "location": "Toronto, ON",
            "salary": "$130,000 – $160,000 CAD",
            "salary_cad": 145_000,
            "description": (
                "RBC is seeking a Cloud Infrastructure Engineer to modernize our banking platform "
                "on AWS and Azure.\n\n"
                "Required Skills:\n"
                "- 4+ years with cloud platforms (AWS preferred)\n"
                "- Terraform and Infrastructure-as-Code expertise\n"
                "- Kubernetes and container orchestration\n"
                "- CI/CD pipeline design (GitHub Actions, Jenkins)\n"
                "- Security and compliance in financial services\n"
                "- Python or Bash scripting\n\n"
                "Nice to Have:\n"
                "- AWS Solutions Architect certification\n"
                "- Experience with financial regulatory frameworks\n"
                "- FinOps / cloud cost optimization experience"
            ),
            "url": "https://jobs.rbc.com/example-4",
        },
        {
            "title": "Product Manager – AI Products",
            "company": "OpenText",
            "location": "Waterloo, ON (Hybrid)",
            "salary": "$140,000 – $170,000 CAD",
            "salary_cad": 155_000,
            "description": (
                "OpenText is hiring a Product Manager to lead AI-powered document and workflow "
                "automation products.\n\n"
                "Required Skills:\n"
                "- 5+ years of product management experience\n"
                "- Experience shipping B2B SaaS products\n"
                "- Strong technical communication skills\n"
                "- Ability to translate complex AI capabilities to business value\n"
                "- Experience with agile development and sprint planning\n\n"
                "Nice to Have:\n"
                "- Background in enterprise software or ECM\n"
                "- Exposure to LLM products or AI workflows\n"
                "- MBA or technical degree preferred"
            ),
            "url": "https://www.opentext.com/careers/example-5",
        },
        {
            "title": "Data Engineer – Analytics Platform",
            "company": "Loblaw Digital",
            "location": "Toronto, ON",
            "salary": "$120,000 – $150,000 CAD",
            "salary_cad": 135_000,
            "description": (
                "Loblaw Digital is looking for a Data Engineer to build and maintain our "
                "real-time analytics platform powering personalization for PC Optimum.\n\n"
                "Required Skills:\n"
                "- 3+ years of data engineering experience\n"
                "- Apache Spark and Kafka expertise\n"
                "- SQL and Python proficiency\n"
                "- Experience with Snowflake or BigQuery\n"
                "- dbt for data transformation\n"
                "- Strong data modelling fundamentals\n\n"
                "Nice to Have:\n"
                "- Experience with Airflow or Prefect\n"
                "- Knowledge of streaming architectures\n"
                "- Retail or e-commerce domain experience"
            ),
            "url": "https://loblaw.digital/careers/example-6",
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# HOW TO PLUG IN REAL JOB SCRAPING
# ─────────────────────────────────────────────────────────────────────────────
#
# Option A — Indeed / LinkedIn via SerpAPI (paid, easiest):
#
#   pip install google-search-results
#
#   from serpapi import GoogleSearch
#
#   def fetch_jobs(query="software engineer", location="Canada"):
#       params = {
#           "engine": "google_jobs",
#           "q": query,
#           "location": location,
#           "api_key": os.getenv("SERPAPI_KEY"),
#       }
#       search = GoogleSearch(params)
#       results = search.get_dict().get("jobs_results", [])
#       return [
#           {
#               "title":       r.get("title", ""),
#               "company":     r.get("company_name", ""),
#               "location":    r.get("location", ""),
#               "salary":      r.get("detected_extensions", {}).get("salary", ""),
#               "salary_cad":  _parse_salary(r.get("detected_extensions", {}).get("salary", "")),
#               "description": r.get("description", ""),
#               "url":         r.get("share_link", ""),
#           }
#           for r in results
#       ]
#
# Option B — Jsearch (RapidAPI, free tier):
#
#   pip install requests
#
#   import requests
#
#   def fetch_jobs(query="software engineer", location="Canada"):
#       url = "https://jsearch.p.rapidapi.com/search"
#       headers = {
#           "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
#           "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
#       }
#       params = {"query": f"{query} in {location}", "num_pages": "2"}
#       response = requests.get(url, headers=headers, params=params)
#       results = response.json().get("data", [])
#       return [
#           {
#               "title":       r.get("job_title", ""),
#               "company":     r.get("employer_name", ""),
#               "location":    r.get("job_city", "") + ", " + r.get("job_country", ""),
#               "salary":      f"{r.get('job_min_salary','')} – {r.get('job_max_salary','')}",
#               "salary_cad":  int(r.get("job_max_salary") or 0),
#               "description": r.get("job_description", ""),
#               "url":         r.get("job_apply_link", ""),
#           }
#           for r in results
#       ]
#
# Option C — Direct Indeed scraping (free, fragile):
#   Use the `jobspy` library: pip install python-jobspy
#
#   from jobspy import scrape_jobs
#
#   def fetch_jobs(query="software engineer", location="Canada"):
#       jobs = scrape_jobs(site_name=["indeed","linkedin"], search_term=query,
#                          location=location, results_wanted=20)
#       return jobs.to_dict("records")   # adjust field names as needed
# ─────────────────────────────────────────────────────────────────────────────
