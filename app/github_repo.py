"""
github_repo.py — minimal GitHub Contents API helper
Used to read/write whitelist/blacklist JSON files stored in a private repo.

Env vars (preferred):
  - GITHUB_PAT
  - GITHUB_OWNER
  - GITHUB_LISTS_REPO
  - GITHUB_WHITELIST_PATH (default: whitelist.json)
  - GITHUB_BLACKLIST_PATH (default: blacklist.json)
"""

from __future__ import annotations

import base64
import json
import urllib.request
from typing import Any, Dict, Optional, Tuple


def _req(url: str, *, pat: str, method: str = "GET", body: Optional[dict] = None) -> dict:
    data = None
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ai-pptx",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def get_file(owner: str, repo: str, path: str, pat: str) -> Tuple[str, str]:
    """
    Returns (text_content, sha). Raises on HTTP errors.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
    data = _req(url, pat=pat, method="GET")
    content_b64 = data.get("content", "")
    sha = data.get("sha", "")
    if not content_b64:
        return "", sha
    text = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
    return text, sha


def put_file(
    owner: str,
    repo: str,
    path: str,
    pat: str,
    *,
    text: str,
    message: str,
    sha: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
    body: Dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
    }
    if sha:
        body["sha"] = sha
    return _req(url, pat=pat, method="PUT", body=body)

