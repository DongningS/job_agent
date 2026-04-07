"""
evaluator.py — Agent 3: Resume Evaluator & Improver

Two-step process:
  Step 1 — Critique: identify weaknesses in the tailored resume
  Step 2 — Improve:  produce an improved version based on the critique

Focuses on clarity, impact, and keyword alignment.
"""

from typing import Dict, Tuple
from utils.llm import call_llm


# ── System prompts ────────────────────────────────────────────────────────────
_CRITIQUE_SYSTEM = """
You are a senior hiring manager and resume expert.
Critique the resume critically and honestly.
Focus on: clarity, impact, ATS keyword alignment, and weak phrasing.
Be specific — point to actual lines or sections that need work.
""".strip()

_IMPROVE_SYSTEM = """
You are a professional resume editor.
Apply the critique to produce an improved version of the resume.
Keep the same structure and truthful content — just make it stronger.
Output ONLY the improved resume text — no commentary.
""".strip()


def evaluate_and_improve(tailored_resume: str, job: Dict) -> Tuple[str, str]:
    """
    Critique and then improve a tailored resume.

    Args:
        tailored_resume: Resume text from the generator agent.
        job:             The target job dict.

    Returns:
        Tuple of (critique_text, improved_resume_text)
    """
    print(f"[evaluator] Critiquing resume for: {job['title']} @ {job['company']}")

    critique = _critique(tailored_resume, job)
    print(f"[evaluator] Improving resume based on critique...")
    improved = _improve(tailored_resume, critique, job)

    return critique, improved


# ── Step 1: Critique ──────────────────────────────────────────────────────────
def _critique(resume: str, job: Dict) -> str:
    prompt = f"""
Review this resume for the job below and provide a structured critique.

TARGET ROLE: {job['title']} at {job['company']}

RESUME:
{resume}

Provide your critique in this format:

STRENGTHS:
• [what is working well]

WEAKNESSES:
• [specific issues with clarity, impact, or ATS alignment]

KEYWORD GAPS:
• [important keywords from the job that are missing or underused]

IMPROVEMENT PRIORITIES:
• [top 3-5 specific changes to make, most impactful first]
""".strip()

    return call_llm(prompt, system=_CRITIQUE_SYSTEM)


# ── Step 2: Improve ───────────────────────────────────────────────────────────
def _improve(resume: str, critique: str, job: Dict) -> str:
    prompt = f"""
You have critiqued a resume targeting this role: {job['title']} at {job['company']}.

Apply the critique below to produce a stronger version of the resume.

══════════════════════════════════════════════════════════════════
CRITIQUE
{critique}
══════════════════════════════════════════════════════════════════

ORIGINAL TAILORED RESUME
{resume}
══════════════════════════════════════════════════════════════════

RULES:
1. Apply every improvement priority from the critique.
2. Fix weak or passive phrasing — use strong action verbs.
3. Add missing keywords naturally (only if underlying experience exists).
4. Keep bullet format: "• " prefix on every bullet point.
5. Keep section headers in ALL CAPS.
6. Do NOT fabricate any experience, skills, numbers, or credentials.
7. Output ONLY the improved resume — no commentary or labels.
""".strip()

    return call_llm(prompt, system=_IMPROVE_SYSTEM)
