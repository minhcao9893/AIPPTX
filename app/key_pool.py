"""
key_pool.py — Groq API key pool + rotation
=========================================
Applies the idea from the provided legacy project:
- Keep multiple Groq API keys in a `keys.txt`
- Rotate keys when hitting rate limit (HTTP 429)

Key sources (highest → lowest priority):
  1) Local keys file configured via `config.json` (`groq_keys_file`)
     or env `GROQ_KEYS_FILE`
  2) GitHub private repo file via Contents API (optional):
       env: GITHUB_PAT, GITHUB_OWNER, GITHUB_KEY_REPO, GITHUB_KEYS_PATH
       or config.json: github_keys.{pat,owner,repo,path}
  3) Single key via env `GROQ_API_KEY` (Groq client default)

This module never uploads keys anywhere.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


APP_DIR = Path(__file__).parent
CONFIG_FILE = APP_DIR / "config.json"


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def _normalize_keys(lines: List[str]) -> List[str]:
    keys: List[str] = []
    for raw in lines:
        s = (raw or "").strip()
        if not s or s.startswith("#"):
            continue
        # Allow `KEY=...` formats too
        if "=" in s and not s.lower().startswith("gsk_"):
            _, s = s.split("=", 1)
            s = s.strip()
        if len(s) < 10:
            continue
        keys.append(s)
    # De-dup while preserving order
    seen = set()
    out = []
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def load_keys_from_file(path: str | Path) -> List[str]:
    p = Path(path)
    if not p.is_absolute():
        # interpret relative to repo root (sibling of app/)
        p = (APP_DIR.parent / p).resolve()
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8", errors="ignore")
    return _normalize_keys(text.splitlines())


def load_keys_from_github_repo(
    *,
    owner: str,
    repo: str,
    path: str = "keys.txt",
    pat: str,
) -> List[str]:
    """
    Fetch a file via GitHub Contents API:
      GET /repos/{owner}/{repo}/contents/{path}
    Works for private repos if PAT has `repo` scope.
    """
    if not (owner and repo and path and pat):
        return []

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {pat}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ai-pptx",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    content_b64 = data.get("content", "")
    if not content_b64:
        return []
    decoded = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
    return _normalize_keys(decoded.splitlines())


@dataclass
class KeyPool:
    keys: List[str]
    _idx: int = 0
    _lock: threading.Lock = threading.Lock()

    def next_key(self) -> Optional[str]:
        with self._lock:
            if not self.keys:
                return None
            key = self.keys[self._idx % len(self.keys)]
            self._idx = (self._idx + 1) % len(self.keys)
            return key

    def __len__(self) -> int:
        return len(self.keys)


_POOL: Optional[KeyPool] = None
_POOL_LOCK = threading.Lock()
_LAST_GITHUB_ERROR: str = ""


def get_key_pool(force_reload: bool = False) -> KeyPool:
    global _POOL, _LAST_GITHUB_ERROR
    with _POOL_LOCK:
        if _POOL is not None and not force_reload:
            return _POOL

        cfg = _load_config()

        # 1) Local keys file
        keys_file = cfg.get("groq_keys_file") or os.environ.get("GROQ_KEYS_FILE", "")
        keys: List[str] = []
        if keys_file:
            keys = load_keys_from_file(keys_file)

        # 2) GitHub private repo (optional)
        if not keys:
            gh = cfg.get("github_keys") if isinstance(cfg.get("github_keys"), dict) else {}
            owner = os.environ.get("GITHUB_OWNER") or gh.get("owner", "")
            repo = os.environ.get("GITHUB_KEY_REPO") or gh.get("repo", "")
            path = os.environ.get("GITHUB_KEYS_PATH") or gh.get("path", "keys.txt")
            pat = os.environ.get("GITHUB_PAT") or gh.get("pat", "")
            try:
                keys = load_keys_from_github_repo(owner=owner, repo=repo, path=path, pat=pat)
            except Exception as gh_err:
                # Log chi tiết để debug
                import sys
                print(f"[key_pool] GitHub fetch FAILED: {gh_err}", file=sys.stderr)
                keys = []
                # Lưu lỗi để báo cáo
                _LAST_GITHUB_ERROR = str(gh_err)

        _POOL = KeyPool(keys=keys)
        return _POOL
