"""
llm.py — Unified LLM wrapper for OpenAI and Anthropic.

Set environment variables:
  LLM_PROVIDER=openai   (default) or anthropic
  OPENAI_API_KEY=sk-...
  ANTHROPIC_API_KEY=sk-ant-...
"""

import os
import json
import time

# ── Provider config ──────────────────────────────────────────────────────────
PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

OPENAI_MODEL    = os.getenv("OPENAI_MODEL",    "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

# ── Lazy-import so the unused SDK is never required ──────────────────────────
def _openai_client():
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Run: pip install openai")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")
    return OpenAI(api_key=api_key)


def _anthropic_client():
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run: pip install anthropic")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
    return anthropic.Anthropic(api_key=api_key)


# ── Public interface ─────────────────────────────────────────────────────────
def call_llm(prompt: str, system: str = "", model: str = "") -> str:
    """
    Send a prompt to the configured LLM and return the text response.

    Args:
        prompt:  The user-turn message.
        system:  Optional system-level instruction.
        model:   Override the default model (optional).

    Returns:
        The model's response as a plain string.
    """
    if PROVIDER == "anthropic":
        return _call_anthropic(prompt, system, model or ANTHROPIC_MODEL)
    else:
        return _call_openai(prompt, system, model or OPENAI_MODEL)


def _call_openai(prompt: str, system: str, model: str) -> str:
    client = _openai_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(3):  # retry up to 3 times on rate limit
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,   # low temp = consistent, structured output
                max_tokens=4096,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"[llm] Rate limited. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("OpenAI call failed after 3 retries.")


def _call_anthropic(prompt: str, system: str, model: str) -> str:
    client = _anthropic_client()

    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    for attempt in range(3):  # retry up to 3 times on rate limit
        try:
            response = client.messages.create(**kwargs)
            return response.content[0].text.strip()
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"[llm] Rate limited. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Anthropic call failed after 3 retries.")


# ── JSON helper ──────────────────────────────────────────────────────────────
def call_llm_json(prompt: str, system: str = "") -> dict:
    """
    Like call_llm but parses the response as JSON.
    The caller is responsible for including JSON instructions in the prompt.
    """
    raw = call_llm(prompt, system=system)
    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON.\nRaw response:\n{raw}\nError: {e}")
