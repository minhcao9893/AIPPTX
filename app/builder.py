"""
builder.py — PPTX Builder
========================
Combines layout_plan + mask_map + raw_data → output.pptx.
"""

import json

from .modules.builder_core import build as _build


def build(layout_plan: dict, mask_map: dict, raw_data: dict,
        scale_map: dict = None,
        template_path: str = None,
        output_path: str = "output.pptx",
        design: dict = None) -> None:
    """Build PPTX from layout_plan + real data."""
    _build(layout_plan, mask_map, raw_data, scale_map, template_path, output_path, design)


# ── CLI helper ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    layout_plan = json.load(open("layout_plan.json", encoding="utf-8"))
    mask_map = json.load(open("mask_map.json", encoding="utf-8"))
    raw_data = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "input.json",
                         encoding="utf-8"))
    build(layout_plan, mask_map, raw_data)