"""
design_theme.py — Theme + 5 màu → design_template.json
=========================================================
Nhận design config từ Step II frontend (theme + custom colors)
và merge vào design_template.json theo đúng schema hiện tại.
"""

from pathlib import Path
from datetime import datetime
import json
from typing import TypedDict


DESIGN_FILE = Path(__file__).resolve().parents[1] / "design_template.json"


class DesignInput(TypedDict):
    theme: str          # 'corporate' | 'minimal' | 'bold' | 'dark' | 'pastel'
    colors: dict        # { primary, secondary, accent, bg, text }


# ── Theme → font mapping ──────────────────────────────────────────────────────
THEME_FONT_MAP = {
    "corporate": {"main": "Calibri",      "heading": "Calibri",      "title_slide_size": 32},
    "minimal":   {"main": "Arial",        "heading": "Arial",        "title_slide_size": 28},
    "bold":      {"main": "Trebuchet MS", "heading": "Trebuchet MS", "title_slide_size": 36},
    "dark":      {"main": "Segoe UI",     "heading": "Segoe UI",     "title_slide_size": 30},
    "pastel":    {"main": "Georgia",      "heading": "Georgia",      "title_slide_size": 28},
    "sunrise":   {"main": "Calibri",      "heading": "Calibri",      "title_slide_size": 32},
    "autumn":    {"main": "Georgia",      "heading": "Georgia",      "title_slide_size": 32},
    "terracotta":{"main": "Trebuchet MS", "heading": "Trebuchet MS", "title_slide_size": 34},
    "tropical":  {"main": "Arial",        "heading": "Arial",        "title_slide_size": 32},
    "desert":    {"main": "Segoe UI",     "heading": "Segoe UI",     "title_slide_size": 30},
}

# Mapping từ 5 màu UI → fields trong design_template.json (dot notation)
COLOR_FIELD_MAP = {
    "primary":   ["colors.bg_dark", "colors.heading", "colors.table_header", "header_band.color", "title_slide.bg.color"],
    "secondary": ["colors.divider_line", "colors.insight_border", "colors.img_placeholder_border", "divider.color"],
    "accent":    ["colors.accent", "colors.bullet_dot", "colors.insight_label", "title_slide.accent_bar.color", "bullet_slide.bullet_dot_color"],
    "bg":        ["colors.bg_light", "colors.insight_bg", "colors.img_placeholder_fill", "colors.table_row_alt", "content_slide.bg.color", "right_panel.bg_color"],
    "text":      ["colors.body", "colors.insight_body", "bullet_slide.body_color", "right_panel.body.color"],
}


def _set_nested(d: dict, dotpath: str, value) -> None:
    """Set giá trị theo dot notation: 'colors.title_text' → d['colors']['title_text']."""
    keys = dotpath.split('.')
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def apply_theme_to_design(design_input: dict) -> dict:
    """
    Merge theme + custom colors vào design dict hiện tại.
    Return design dict đã merge (chưa save).
    """
    current = load_design_template()

    theme  = design_input.get('theme', 'corporate')
    colors = design_input.get('colors', {})

    # Apply font settings
    font_cfg = THEME_FONT_MAP.get(theme, THEME_FONT_MAP['corporate'])
    fonts = current.setdefault('fonts', {})
    for k, v in font_cfg.items():
        fonts[k] = v

    # Apply colors — dùng .get() với fallback để tránh KeyError
    # Guard: colors=None khi theme='template_default' → bỏ qua override màu
    if not colors:
        colors = {}
    for color_key, color_val in colors.items():
        if not color_val:
            continue
        for field in COLOR_FIELD_MAP.get(color_key, []):
            _set_nested(current, field, color_val)

    # Set chart_palette
    if colors:
        palette = [
            colors.get("primary", "#1E2761"),
            colors.get("secondary", "#028090"),
            colors.get("accent", "#F9A825"),
            colors.get("text", "#333333"),
            "#888888"
        ]
        _set_nested(current, "colors.chart_palette", palette)

    # Meta
    meta = current.setdefault('meta', {})
    meta['theme'] = theme
    meta['updated_at'] = datetime.now().isoformat()

    return current


def save_design(design_dict: dict) -> None:
    """Ghi design_dict vào DESIGN_FILE. Backup file cũ trước khi ghi."""
    if DESIGN_FILE.exists():
        bak = DESIGN_FILE.with_suffix('.bak.json')
        bak.write_text(DESIGN_FILE.read_text(encoding='utf-8'), encoding='utf-8')
    DESIGN_FILE.write_text(
        json.dumps(design_dict, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


def load_design_template() -> dict:
    """Load design_template.json. Return {} nếu không tồn tại."""
    if DESIGN_FILE.exists():
        try:
            return json.loads(DESIGN_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def hex_to_rgb_tuple(hex_color: str) -> tuple:
    """'#003366' → (0, 51, 102)."""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def apply_transparency_to_design(design: dict, transparency_pct: int) -> dict:
    """
    Gán giá trị transparency (0-100) vào các nến thành phần:
    header_band, insight panel, content bg, table row alt
    0 = đặc hoàn toàn, 100 = trong suốt hoàn toàn.
    Được lưu vào design['transparency'] để builder đọc khi vẽ.
    """
    pct = max(0, min(100, int(transparency_pct)))
    # lưu vào cấu trúc riêng — builder_components sẽ đọc _cfg('transparency', ...)
    tr = design.setdefault('transparency', {})
    tr['header_band_alpha']  = pct   # 0=đặc, 100=trong suốt
    tr['insight_panel_alpha']= pct
    tr['content_bg_alpha']   = pct
    tr['table_row_alpha']    = pct
    return design
