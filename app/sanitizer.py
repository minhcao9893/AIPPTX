"""
sanitizer.py — Data Privacy Layer v4.1
=======================================
Name-Preserving Masking for data privacy.

Usage:
    from sanitizer import sanitize, unmask, unmask_names
    skeleton, name_map = sanitize(raw_data)
"""

import json
from copy import deepcopy

try:
    from .list_store import load_lists
except Exception:
    load_lists = None


# ── Import from modules ───────────────────────────────────────────────────────────

from .modules.sanitizer_core import (
    NameMasker,
    sanitize as _sanitize_core,
    unmask as _unmask_core,
    unmask_names,
    unmask_data,
    build_skeleton_metadata,
    get_masker,
)


def sanitize(raw_data: dict) -> tuple[dict, dict]:
    """Main entry — Name-Preserving Masking."""
    return _sanitize_core(raw_data)


def unmask(text: str, mask_map: dict = None, scale_map: dict = None,
         slide_index: int = None) -> str:
    """Unmask text using mask_map."""
    return _unmask_core(text, mask_map, scale_map, slide_index)


# ── CLI helper ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    test_cases = [
        ("Intel", "Company-A"),
        ("Samsung", "Company-?"),
        ("Hà Nội", "Region-?"),
        ("TP.HCM", "Region-?"),
        ("Nguyễn Văn A", "Person-?"),
    ]

    from app.modules.sanitizer_core import NameMasker
    
    masker = NameMasker()
    print("=" * 60)
    print("SANITIZER v4.1 — inline test")
    print("=" * 60)
    
    all_pass = True
    for original, expected_hint in test_cases:
        result = masker.mask_value(original)
        changed = result != original
        tag = "MASK" if changed else "KEEP"
        ok = "✅" if (("?" in expected_hint and changed) or (expected_hint == original)) else "❌"
        if ok == "❌":
            all_pass = False
        print(f"  {ok} [{tag}]  {original!r:45s} → {result!r}")

    print()
    print("Result:", "✅ ALL PASS" if all_pass else "❌ SOME FAILED")

    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        with open(input_path, encoding="utf-8") as f:
            raw = json.load(f)
        skeleton, name_map = sanitize(raw)
        skeleton = build_skeleton_metadata(skeleton)
        with open("skeleton.json", "w", encoding="utf-8") as f:
            json.dump(skeleton, f, ensure_ascii=False, indent=2)
        with open("name_map.json", "w", encoding="utf-8") as f:
            json.dump(name_map, f, ensure_ascii=False, indent=2)
        print(f"\n✅ {input_path} → skeleton.json + name_map.json")