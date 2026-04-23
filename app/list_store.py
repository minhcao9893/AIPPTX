"""
list_store.py — load/save whitelist/blacklist (local cache + optional GitHub)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from .github_repo import get_file, put_file


APP_DIR = Path(__file__).parent
CONFIG_FILE = APP_DIR / "config.json"
LOCAL_CACHE_DIR = APP_DIR.parent / ".lists_cache"
LOCAL_CACHE_DIR.mkdir(exist_ok=True)


@dataclass
class ListsConfig:
    pat: str
    owner: str
    repo: str
    whitelist_path: str = "whitelist.json"
    blacklist_path: str = "blacklist.json"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def load_lists_config_from_env() -> ListsConfig | None:
    pat = _env("GITHUB_PAT")
    owner = _env("GITHUB_OWNER")
    repo = _env("GITHUB_LISTS_REPO")
    if not (pat and owner and repo):
        return None
    return ListsConfig(
        pat=pat,
        owner=owner,
        repo=repo,
        whitelist_path=_env("GITHUB_WHITELIST_PATH", "whitelist.json") or "whitelist.json",
        blacklist_path=_env("GITHUB_BLACKLIST_PATH", "blacklist.json") or "blacklist.json",
    )


def load_lists_config_from_config() -> ListsConfig | None:
    if not CONFIG_FILE.exists():
        return None
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None
    gh = cfg.get("github_lists") if isinstance(cfg.get("github_lists"), dict) else None
    if not gh:
        return None
    owner = str(gh.get("owner", "")).strip()
    repo = str(gh.get("repo", "")).strip()
    if not (owner and repo):
        return None
    pat = str(gh.get("pat", "")).strip()  # prefer env; optional fallback
    return ListsConfig(
        pat=pat,
        owner=owner,
        repo=repo,
        whitelist_path=str(gh.get("whitelist_path", "whitelist.json")).strip() or "whitelist.json",
        blacklist_path=str(gh.get("blacklist_path", "blacklist.json")).strip() or "blacklist.json",
    )


def _parse_json_list(text: str) -> List[str]:
    if not text.strip():
        return []
    data = json.loads(text)
    if isinstance(data, list):
        return [str(x) for x in data if str(x).strip()]
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        return [str(x) for x in data["items"] if str(x).strip()]
    raise ValueError("Expected JSON array (or {items: [...]})")


def _dump_json_list(items: List[str]) -> str:
    # stable, de-dup, keep order
    seen = set()
    out: List[str] = []
    for s in items:
        s = str(s).strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return json.dumps(out, ensure_ascii=False, indent=2)


def load_lists() -> Tuple[List[str], List[str]]:
    """
    Returns (whitelist, blacklist) from GitHub (if configured) else local cache files.
    """
    cfg = load_lists_config_from_env() or load_lists_config_from_config()
    if cfg and cfg.pat:
        w_text, _ = get_file(cfg.owner, cfg.repo, cfg.whitelist_path, cfg.pat)
        b_text, _ = get_file(cfg.owner, cfg.repo, cfg.blacklist_path, cfg.pat)
        return _parse_json_list(w_text), _parse_json_list(b_text)

    w_path = LOCAL_CACHE_DIR / "whitelist.json"
    b_path = LOCAL_CACHE_DIR / "blacklist.json"
    w = _parse_json_list(w_path.read_text(encoding="utf-8")) if w_path.exists() else []
    b = _parse_json_list(b_path.read_text(encoding="utf-8")) if b_path.exists() else []
    return w, b


def save_lists(whitelist: List[str], blacklist: List[str], *, message: str) -> None:
    """
    Saves lists to GitHub if env configured, else to local cache.
    """
    cfg = load_lists_config_from_env() or load_lists_config_from_config()
    w_text = _dump_json_list(whitelist)
    b_text = _dump_json_list(blacklist)

    if cfg and cfg.pat:
        _, w_sha = get_file(cfg.owner, cfg.repo, cfg.whitelist_path, cfg.pat)
        _, b_sha = get_file(cfg.owner, cfg.repo, cfg.blacklist_path, cfg.pat)
        put_file(cfg.owner, cfg.repo, cfg.whitelist_path, cfg.pat, text=w_text, message=message, sha=w_sha or None)
        put_file(cfg.owner, cfg.repo, cfg.blacklist_path, cfg.pat, text=b_text, message=message, sha=b_sha or None)
        return

    (LOCAL_CACHE_DIR / "whitelist.json").write_text(w_text, encoding="utf-8")
    (LOCAL_CACHE_DIR / "blacklist.json").write_text(b_text, encoding="utf-8")
