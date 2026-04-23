"""
stage1_list_updater.py — Stage 1
================================
Goal:
  - Read all .docx in input/
  - Extract a privacy-minimized text (remove numbers + "insight-y" keywords)
  - Send that text + current whitelist/blacklist to AI
  - AI suggests updates to whitelist/blacklist
  - Save back to GitHub private repo (or local cache)
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

from groq import Groq

from .key_pool import get_key_pool
from .list_store import load_lists, save_lists
from .docx_parser import docx_to_input_json


BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR.parent / "input"
CONFIG_FILE = BASE_DIR / "config.json"


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


INSIGHT_KEYWORDS = {
    # VI
    "tăng", "giảm", "nhanh", "chậm", "đột biến", "bứt phá", "suy giảm", "phục hồi",
    "cao nhất", "thấp nhất", "dẫn đầu", "tụt", "tụt hậu", "vượt", "kém", "mạnh", "yếu",
    # EN
    "increase", "decrease", "grow", "growth", "decline", "drop", "rise", "fall",
    "faster", "slower", "rapid", "slow", "spike", "surge", "plunge", "rebound",
}


_re_numbers = re.compile(r"[\d]+([.,][\d]+)*%?")


def _minimize_text(s: str) -> str:
    if not s:
        return ""
    s = _re_numbers.sub(" ", s)
    # remove insight keywords (whole-word where possible)
    for kw in sorted(INSIGHT_KEYWORDS, key=len, reverse=True):
        s = re.sub(rf"(?i)\b{re.escape(kw)}\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _collect_input_text() -> str:
    INPUT_DIR.mkdir(exist_ok=True)
    parts: List[str] = []
    for docx in sorted(INPUT_DIR.glob("*.docx")):
        try:
            data = docx_to_input_json(str(docx))
        except Exception:
            continue
        parts.append(f"[FILE] {docx.name}")
        parts.append(_minimize_text(str(data.get("presentation_title", ""))))
        for slide in data.get("slides", []):
            parts.append(_minimize_text(str(slide.get("title", ""))))
            c = slide.get("content")
            if isinstance(c, str):
                parts.append(_minimize_text(c))
            elif isinstance(c, list):
                for it in c:
                    parts.append(_minimize_text(str(it)))
            elif isinstance(c, dict):
                # tables: keep only column names + string-ish cells (numbers already stripped)
                cols = c.get("columns", [])
                parts.append(_minimize_text(" ".join(str(x) for x in cols)))
                for row in c.get("rows", [])[:10]:
                    if not isinstance(row, list):
                        continue
                    for cell in row:
                        if isinstance(cell, (int, float)):
                            continue
                        parts.append(_minimize_text(str(cell)))
    text = "\n".join(p for p in parts if p)
    # hard cap to avoid giant prompts
    return text[:18_000]


SYSTEM_PROMPT = """
You are a data-privacy keyword classifier.

You receive:
  - A sanitized/minimized text corpus extracted from documents (numbers removed, insight words removed).
  - An existing WHITELIST (safe words that should NOT be masked).
  - An existing BLACKLIST (sensitive tokens that MUST be masked).

Task:
1) Identify candidate sensitive tokens in the text that belong in BLACKLIST:
   - company names, person names, locations, brands, product/client names, organizations
2) Identify tokens that are clearly generic/safe and belong in WHITELIST:
   - months, weekdays, fruit/common nouns, generic metrics words, etc.
3) Do NOT add pure numbers (they were removed) and do NOT add single-character noise.

Output JSON only with:
{
  "add_whitelist": ["..."],
  "add_blacklist": ["..."]
}

Rules:
- Prefer precision: only add when confident.
- Keep original casing from the text when possible.
- If already present in lists, don't repeat.
""".strip()


def _call_groq_json(user_prompt: str, *, model: str, max_retries: int = 3) -> Dict:
    pool = get_key_pool()
    last_err: Exception | None = None
    for attempt in range(max_retries):
        key = pool.next_key() if len(pool) else None
        client = Groq(api_key=key) if key else Groq()
        try:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=1200,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = resp.choices[0].message.content or ""
            text = re.sub(r"```(?:json)?|```", "", text).strip()
            return json.loads(text)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "429" in msg or "rate limit" in msg:
                time.sleep(1.5 + 0.75 * attempt)
                continue
            raise
    assert last_err is not None
    raise last_err


def run_stage1_update(*, dry_run: bool = False) -> Tuple[int, int]:
    """
    Returns (n_added_whitelist, n_added_blacklist)
    """
    text = _collect_input_text()
    if not text.strip():
        return 0, 0

    whitelist, blacklist = load_lists()
    cfg = _load_config()
    model = cfg.get("stage1_model") or cfg.get("model") or "llama-3.3-70b-versatile"

    prompt = json.dumps(
        {
            "whitelist": whitelist[:800],
            "blacklist": blacklist[:800],
            "text": text,
        },
        ensure_ascii=False,
        indent=2,
    )

    out = _call_groq_json(prompt, model=model)
    add_w = [str(x).strip() for x in out.get("add_whitelist", []) if str(x).strip()]
    add_b = [str(x).strip() for x in out.get("add_blacklist", []) if str(x).strip()]

    def merge(base: List[str], add: List[str]) -> List[str]:
        seen = set(base)
        merged = list(base)
        for x in add:
            if x in seen:
                continue
            seen.add(x)
            merged.append(x)
        return merged

    new_w = merge(whitelist, add_w)
    new_b = merge(blacklist, add_b)
    n_w = len(new_w) - len(whitelist)
    n_b = len(new_b) - len(blacklist)

    if (n_w or n_b) and not dry_run:
        save_lists(new_w, new_b, message=f"AI update whitelist/blacklist ({n_w}W/{n_b}B)")
    return n_w, n_b
