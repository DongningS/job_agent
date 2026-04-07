# Autonomous Job Search & Resume Optimisation Agent

A fully autonomous Python agent that:
1. Reads your resume
2. Fetches job listings
3. Scores each job for fit (Agent 1 — Matcher)
4. Generates a tailored resume per job (Agent 2 — Generator)
5. Critiques and improves each resume (Agent 3 — Evaluator)
6. Saves polished results to `/outputs/`

---

## Project Structure

```
job_agent/
├── main.py                  ← Entry point / orchestrator
├── agents/
│   ├── matcher.py           ← Agent 1: scores jobs vs. resume
│   ├── generator.py         ← Agent 2: writes tailored resume
│   └── evaluator.py         ← Agent 3: critiques and improves
├── utils/
│   ├── llm.py               ← Unified OpenAI / Anthropic wrapper
│   ├── resume_loader.py     ← Extracts text from resume.docx
│   └── job_fetcher.py       ← Mock jobs (+ real scraper plug-in guide)
├── outputs/                 ← Generated results go here
├── requirements.txt
└── .env.example
```

---

## Step-by-Step Setup

### 1 — Clone / download the project

```bash
git clone <repo-url>
cd job_agent
```

### 2 — Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate        # Mac / Linux
venv\Scripts\activate.bat       # Windows
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** You only need `openai` OR `anthropic` depending on which provider you use.
> Both are listed in requirements.txt for convenience.

### 4 — Set your API key

**Option A — environment variables (recommended):**

```bash
# Mac / Linux
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# OR use Anthropic
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

```powershell
# Windows PowerShell
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="sk-..."
```

**Option B — .env file:**

```bash
cp .env.example .env
# Edit .env with your keys
```

Then add this line at the top of `main.py`:
```python
from dotenv import load_dotenv; load_dotenv()
```
And install: `pip install python-dotenv`

### 5 — Add your resume

Place your resume in the project root:
```
job_agent/
└── resume.docx    ← your resume here
```

### 6 — Run the agent

```bash
# Default (uses mock jobs, searches "software engineer" in Canada)
python main.py

# Custom query
python main.py --query "machine learning engineer" --location "Toronto"

# Custom resume path
python main.py --resume /path/to/my_resume.docx
```

---

## Output

For each selected job, you'll find a folder in `outputs/`:

```
outputs/
└── Shopify_Senior_Software_Engineer_Backend/
    ├── job_info.json          ← match score, missing skills, reasoning
    ├── tailored_resume.txt    ← resume rewritten for this job
    └── improved_resume.txt    ← critique + final improved version
```

---

## Switching Between OpenAI and Anthropic

Just change one environment variable:

```bash
# Use OpenAI GPT-4o
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Use Anthropic Claude
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

You can also override the specific model:
```bash
export OPENAI_MODEL=gpt-4-turbo
export ANTHROPIC_MODEL=claude-opus-4-5
```

No code changes needed — `utils/llm.py` handles everything.

---

## Plugging In Real Job Scraping

Open `utils/job_fetcher.py`. At the bottom you'll find three ready-to-use
scraper implementations:

| Option | Service | Cost | Reliability |
|--------|---------|------|-------------|
| A | SerpAPI (`google-search-results`) | ~$50/mo | High |
| B | Jsearch via RapidAPI | Free tier | Medium |
| C | `python-jobspy` (Indeed + LinkedIn) | Free | Fragile |

Uncomment the one you want and replace the `fetch_jobs()` function body.
The rest of the pipeline works unchanged.

---

## Tuning the Filter

Edit these two constants in `main.py`:

```python
SCORE_THRESHOLD  = 70       # Keep jobs with score ≥ this value
SALARY_THRESHOLD = 200_000  # OR keep if salary ≥ this (CAD)
```

---

## Security Notes

- Job descriptions are explicitly marked as **untrusted input** in every agent prompt
- System prompts instruct the LLM to **ignore any instructions embedded in job descriptions** (prompt injection defence)
- API keys are never hardcoded — environment variables only

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `FileNotFoundError: resume.docx` | Place `resume.docx` in the project root |
| `OPENAI_API_KEY not set` | Export the env variable (Step 4) |
| `LLM did not return valid JSON` | Try a smarter model (`gpt-4o` or `claude-opus-4-5`) |
| `ImportError: python-docx` | Run `pip install python-docx` |
| No jobs selected | Lower `SCORE_THRESHOLD` in `main.py` |
