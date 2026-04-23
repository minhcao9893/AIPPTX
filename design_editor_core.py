"""
modules/design_editor_core.py — Logic đọc/ghi design_template.json
====================================================================
Được gọi bởi app/design_editor.py (thin wrapper).

Public API:
  load_design(path)           → dict
  save_design(path, data)     → None
  get_schema()                → dict   (mô tả field cho UI)
"""

import json
import copy
from pathlib import Path


# ── Schema mô tả từng field để UI biết render gì ─────────────────────────────
# type: "color"  → color picker
# type: "text"   → text input
# type: "number" → number input
# type: "bool"   → toggle
# type: "colors" → list of color pickers (chart_palette)

SCHEMA = {
    "Colors": {
        "_key": "colors",
        "fields": [
            {"key": "bg_dark",                "label": "Background tối (cover/header)",  "type": "color"},
            {"key": "bg_light",               "label": "Background sáng (content)",       "type": "color"},
            {"key": "accent",                 "label": "Màu Accent",                      "type": "color"},
            {"key": "heading",                "label": "Màu Heading",                     "type": "color"},
            {"key": "body",                   "label": "Màu Body text",                   "type": "color"},
            {"key": "bullet_dot",             "label": "Màu Bullet dot",                  "type": "color"},
            {"key": "table_header",           "label": "Table header bg",                 "type": "color"},
            {"key": "table_row_alt",          "label": "Table row xen kẽ",                "type": "color"},
            {"key": "insight_bg",             "label": "AI Insight background",           "type": "color"},
            {"key": "insight_border",         "label": "AI Insight border",               "type": "color"},
            {"key": "insight_label",          "label": "AI Insight label",                "type": "color"},
            {"key": "insight_body",           "label": "AI Insight body text",            "type": "color"},
            {"key": "divider_line",           "label": "Đường kẻ divider",                "type": "color"},
            {"key": "img_placeholder_fill",   "label": "Image placeholder fill",          "type": "color"},
            {"key": "img_placeholder_border", "label": "Image placeholder border",        "type": "color"},
            {"key": "chart_palette",          "label": "Chart palette (5 màu)",           "type": "colors"},
        ]
    },
    "Fonts": {
        "_key": "fonts",
        "fields": [
            {"key": "main",                 "label": "Font chính",              "type": "text"},
            {"key": "heading",              "label": "Font heading",            "type": "text"},
            {"key": "title_slide_size",     "label": "Title slide size (pt)",   "type": "number"},
            {"key": "subtitle_size",        "label": "Subtitle size (pt)",      "type": "number"},
            {"key": "header_band_size",     "label": "Header band size (pt)",   "type": "number"},
            {"key": "bullet_size",          "label": "Bullet size (pt)",        "type": "number"},
            {"key": "insight_label_size",   "label": "Insight label size (pt)", "type": "number"},
            {"key": "insight_body_size",    "label": "Insight body size (pt)",  "type": "number"},
            {"key": "table_header_size",    "label": "Table header size (pt)",  "type": "number"},
            {"key": "table_body_size",      "label": "Table body size (pt)",    "type": "number"},
        ]
    },
    "Layout": {
        "_key": None,  # mixed keys from root
        "fields": [
            {"key": "slide.width_inches",              "label": "Slide width (inches)",          "type": "number"},
            {"key": "slide.height_inches",             "label": "Slide height (inches)",         "type": "number"},
            {"key": "slide.margin_left_inches",        "label": "Margin trái (inches)",          "type": "number"},
            {"key": "slide.margin_right_inches",       "label": "Margin phải (inches)",          "type": "number"},
            {"key": "split_layout.split_ratio",        "label": "Split ratio left panel (0–1)",  "type": "number"},
            {"key": "divider.enabled",                 "label": "Hiện divider line",             "type": "bool"},
            {"key": "divider.width_inches",            "label": "Divider width (inches)",        "type": "number"},
        ]
    },
    "Slides": {
        "_key": None,
        "fields": [
            {"key": "title_slide.enabled",                  "label": "Hiện cover slide",               "type": "bool"},
            {"key": "title_slide.bg.enabled",               "label": "Vẽ background cover",            "type": "bool"},
            {"key": "title_slide.accent_bar.enabled",       "label": "Hiện accent bar (cover)",        "type": "bool"},
            {"key": "title_slide.title.font_size",          "label": "Cover title size (pt)",          "type": "number"},
            {"key": "title_slide.title.align",              "label": "Cover title align (left/center/right)", "type": "text"},
            {"key": "title_slide.subtitle.enabled",         "label": "Hiện subtitle (cover)",          "type": "bool"},
            {"key": "title_slide.subtitle.font_size",       "label": "Cover subtitle size (pt)",       "type": "number"},
            {"key": "header_band.enabled",                  "label": "Hiện header band",               "type": "bool"},
            {"key": "header_band.height_inches",            "label": "Header band height (inches)",    "type": "number"},
            {"key": "content_slide.content_top_inches",     "label": "Content top margin (inches)",    "type": "number"},
        ]
    },
    "Panels": {
        "_key": None,
        "fields": [
            {"key": "right_panel.enabled",               "label": "Hiện AI Insight panel",         "type": "bool"},
            {"key": "right_panel.padding_inches",        "label": "Insight padding (inches)",      "type": "number"},
            {"key": "right_panel.label.enabled",         "label": "Hiện label 'AI Insight'",       "type": "bool"},
            {"key": "right_panel.label.text",            "label": "Text label insight",            "type": "text"},
            {"key": "right_panel.label.font_size",       "label": "Label font size (pt)",          "type": "number"},
            {"key": "bullet_slide.bullet_dot_char",      "label": "Ký tự bullet",                  "type": "text"},
            {"key": "bullet_slide.bullet_size",          "label": "Bullet size (pt)",              "type": "number"},
            {"key": "bullet_slide.footer_insight.enabled","label": "Hiện footer insight",          "type": "bool"},
            {"key": "bullet_slide.footer_insight.font_size","label": "Footer insight size (pt)",   "type": "number"},
            {"key": "table.header.font_size",            "label": "Table header size (pt)",        "type": "number"},
            {"key": "table.body.font_size",              "label": "Table body size (pt)",          "type": "number"},
            {"key": "chart.has_legend",                  "label": "Hiện chart legend",             "type": "bool"},
            {"key": "chart.show_data_labels",            "label": "Hiện data labels trên chart",   "type": "bool"},
        ]
    },
}


# ── Helpers để đọc/ghi giá trị theo dotted path ───────────────────────────────

def _get_dotted(d: dict, dotted_key: str):
    """Get value từ dict bằng key dạng 'a.b.c'."""
    parts = dotted_key.split(".")
    cur = d
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _set_dotted(d: dict, dotted_key: str, value):
    """Set value vào dict bằng key dạng 'a.b.c'."""
    parts = dotted_key.split(".")
    cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


# ── Public API ────────────────────────────────────────────────────────────────

def load_design(path: str) -> dict:
    """Đọc design_template.json, trả về dict."""
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_design(path: str, data: dict) -> None:
    """Ghi dict vào design_template.json (pretty-print)."""
    p = Path(path)
    p.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_schema() -> dict:
    """Trả về SCHEMA để frontend biết cách render từng tab/field."""
    return SCHEMA


def flatten_for_ui(design: dict) -> dict:
    """
    Chuyển design dict sang flat dict { "dotted.key": value }
    để frontend dễ đọc/ghi theo field key trong SCHEMA.
    """
    flat = {}
    for tab_info in SCHEMA.values():
        for field in tab_info["fields"]:
            dk = field["key"]
            # colors tab: key ngắn (vd "bg_dark") → map vào colors.bg_dark
            section_key = tab_info.get("_key")
            if section_key and "." not in dk:
                full_key = f"{section_key}.{dk}"
            else:
                full_key = dk
            val = _get_dotted(design, full_key)
            flat[dk] = val  # UI dùng key ngắn theo SCHEMA
    return flat


def apply_ui_patch(design: dict, patch: dict) -> dict:
    """
    Nhận patch = { "dotted.key": new_value } từ frontend,
    áp lên design dict và trả về bản mới.
    Tự động convert type (bool, number) theo SCHEMA.
    """
    result = copy.deepcopy(design)

    # Build lookup: field_key → (full_dotted_path, type)
    field_map = {}
    for tab_info in SCHEMA.values():
        section_key = tab_info.get("_key")
        for field in tab_info["fields"]:
            dk = field["key"]
            if section_key and "." not in dk:
                full_key = f"{section_key}.{dk}"
            else:
                full_key = dk
            field_map[dk] = (full_key, field["type"])

    for ui_key, raw_val in patch.items():
        if ui_key not in field_map:
            continue
        full_key, ftype = field_map[ui_key]

        # Type coercion
        if ftype == "bool":
            val = bool(raw_val)
        elif ftype == "number":
            try:
                val = float(raw_val)
                if val == int(val):
                    val = int(val)
            except (ValueError, TypeError):
                val = raw_val
        elif ftype == "colors":
            # Expect list of hex strings
            val = raw_val if isinstance(raw_val, list) else raw_val
        else:
            val = str(raw_val)

        _set_dotted(result, full_key, val)

    return result
