"""
stage1_list_updater.py — Stage 1: Whitelist/Blacklist Auto-Update
==================================================================
Goal:
  - Extract privacy-minimized text from data (remove numbers + insight words)
  - Send text + current whitelist/blacklist to AI via Groq
  - AI suggests updates to whitelist/blacklist
  - Save back to GitHub private repo (or local cache)

Features:
  ✅ Auto-rotate keys when hitting API restrictions (400, 401, 429, etc.)
  ✅ Graceful degradation (skip Stage 1 if all keys fail)
  ✅ Designed to run DURING pipeline (after docx parse, before sanitize)
  ✅ Integrated into main flow, not background startup
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from groq import Groq

from .key_pool import get_key_pool
from .list_store import load_lists, save_lists


BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"


class Stage1Error(Exception):
    pass

class Stage1ApiError(Stage1Error):
    pass

class Stage1ConfigError(Stage1Error):
    pass


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


def _extract_text_from_data(raw_data: dict) -> str:
    """
    Extract minimized text from raw_data dict (already parsed from DOCX).
    Chạy NGAY SAU parse, không cần scan folder.
    """
    parts: List[str] = []

    title = raw_data.get("presentation_title", "")
    if title:
        parts.append(_minimize_text(str(title)))

    for slide in raw_data.get("slides", []):
        slide_title = slide.get("title", "")
        if slide_title:
            parts.append(_minimize_text(str(slide_title)))

        c = slide.get("content")
        if isinstance(c, str):
            parts.append(_minimize_text(c))
        elif isinstance(c, list):
            for it in c:
                parts.append(_minimize_text(str(it)))
        elif isinstance(c, dict):
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


def _is_retryable_error(error: Exception) -> bool:
    """Retryable: rate limit, org restricted, timeout. Non-retryable: auth fail, format error."""
    err_str = str(error).lower()
    non_retryable = ["invalid request error", "model not found", "authentication failed", "not authorized"]
    for p in non_retryable:
        if p in err_str:
            return False
    retryable = ["429", "rate limit", "organization_restricted", "organization has been restricted",
                 "restricted", "503", "timeout", "connection reset"]
    for p in retryable:
        if p in err_str:
            return True
    return False


def _call_groq_json(
    user_prompt: str,
    *,
    model: str,
    max_retries: int = 3
) -> Optional[Dict]:
    """
    Call Groq API với auto key rotation khi bị restrict/rate limit.
    Returns Dict nếu thành công, None nếu tất cả keys fail.
    Raises Stage1ApiError nếu lỗi non-retryable.
    """
    pool = get_key_pool(force_reload=True)

    if len(pool) == 0:
        raise Stage1ConfigError("No API keys available (check config.json or keys.txt)")

    last_retryable_err: Optional[Exception] = None

    for attempt in range(max_retries):
        key = pool.next_key()
        try:
            client = Groq(api_key=key)
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
            if _is_retryable_error(e):
                last_retryable_err = e
                print(f"  ⚠️ Stage 1 key bị restrict, rotating... ({str(e)[:80]})", file=sys.stderr)
                time.sleep(1.0 + 0.5 * attempt)
                continue
            else:
                raise Stage1ApiError(f"Non-retryable API error: {e}") from e

    # Tất cả keys fail
    print(f"  ⚠️ Stage 1 skipped: All keys exhausted", file=sys.stderr)
    return None


def run_stage1_update(
    raw_data: dict,
    *,
    dry_run: bool = False,
    verbose: bool = True
) -> Tuple[int, int]:
    """
    Chạy Stage 1 update trên raw_data đã parse từ DOCX.
    Returns (n_added_whitelist, n_added_blacklist).
    Nếu tất cả keys fail → return (0, 0) không crash pipeline.
    """
    try:
        text = _extract_text_from_data(raw_data)
        if not text.strip():
            if verbose:
                print("🧠 Stage 1: No text to analyze, skipping", file=sys.stderr)
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

        if out is None:
            # Tất cả keys fail với retryable error → graceful skip
            return 0, 0

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

    except Stage1ConfigError as e:
        if verbose:
            print(f"❌ Stage 1 config error: {e}", file=sys.stderr)
        raise

    except Stage1ApiError as e:
        if verbose:
            print(f"❌ Stage 1 API error: {e}", file=sys.stderr)
        raise

    except Exception as e:
        if verbose:
            print(f"❌ Stage 1 unexpected error: {e}", file=sys.stderr)
        raise Stage1Error(f"Unexpected: {e}") from e
