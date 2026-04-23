"""
docx_parser.py — Word Document Parser v2
==========================================
Parses a .docx file into slide dicts using {Slide N} triggers.
Now uses modularized code from modules/
"""

import re
from pathlib import Path
from docx import Document


SLIDE_TRIGGER = re.compile(r"\{Slide\s*(\d+)\}", re.IGNORECASE)
CHART_TRIGGER = re.compile(r"\{Chart\}", re.IGNORECASE)


# ── Import from modules ───────────────────────────────────────────────────────────

from .modules.docx_parser_core import parse_docx as _parse_docx_core


def parse_docx(docx_path: str) -> list:
    """Parse Word file → list of slide dicts."""
    return _parse_docx_core(docx_path, SLIDE_TRIGGER, CHART_TRIGGER)


def docx_to_input_json(docx_path: str, presentation_title: str = "") -> dict:
    """Convert .docx → input dict for sanitizer/builder pipeline."""
    slides = parse_docx(docx_path)
    title = presentation_title or Path(docx_path).stem.replace("_", " ").title()

    return {
        "presentation_title": title,
        "slides": [
            {
                "index": s["index"] - 1,
                "title": s["title"],
                "type": s["type"],
                "chart_hint": s.get("chart_hint", False),
                "chart_type_hint": s.get("chart_type_hint", "none"),
                "content": s["content"],
                "raw_text": s.get("raw_text", ""),
                "images": s.get("images", []),
                "image_count": s.get("image_count", 0),
            }
            for s in slides
        ]
    }


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json
    path = sys.argv[1] if len(sys.argv) > 1 else "input/sample.docx"
    data = docx_to_input_json(path)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\n✅ {len(data['slides'])} slides parsed from {path}")
    chart_slides = [s for s in data['slides'] if s.get('chart_hint')]
    print(f"   {len(chart_slides)} slide(s) with {{Chart}} trigger")
    for s in chart_slides:
        print(f"   → Slide {s['index']+1}: {s['title']} → {s['chart_type_hint']}")