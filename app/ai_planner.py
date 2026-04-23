"""
ai_planner.py — AI Layout Planner v5
=====================================
AI nhận alias (Company-A, Region-1…) thay vì §STR§.
"""

import json
import os

from .modules.ai_planner_core import plan_layout as _plan_layout


def plan_layout(skeleton: dict, design_hints: dict = None) -> dict:
    """Send skeleton to Groq → layout_plan."""
    return _plan_layout(skeleton, design_hints)


# ── CLI helper ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    skeleton_path = sys.argv[1] if len(sys.argv) > 1 else "skeleton.json"
    with open(skeleton_path, encoding="utf-8") as f:
        skeleton = json.load(f)

    print("📡 Sending skeleton to Groq...")
    layout_plan = plan_layout(skeleton)

    with open("layout_plan.json", "w", encoding="utf-8") as f:
        json.dump(layout_plan, f, ensure_ascii=False, indent=2)

    n = len(layout_plan.get("slides", []))
    print(f"✅ layout_plan.json saved — {n} slide(s) planned.")
    for s in layout_plan["slides"]:
        print(f"  [{s['index']}] {s['layout']} | chart={s.get('chart_type','none')} "
              f"| {s.get('color_scheme')} | insight: {s.get('insight_text','')[:60]}…")