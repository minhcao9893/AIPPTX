"""
design_editor.py — Public API (thin wrapper)
=============================================
Được import bởi app.py để expose routes /api/design GET & POST.

Usage trong app.py:
    from .design_editor import get_design_json, save_design_json, get_design_schema
"""

from pathlib import Path
from .modules.design_editor_core import (
    load_design,
    save_design,
    get_schema,
    flatten_for_ui,
    apply_ui_patch,
)

# Re-export gọn cho app.py
__all__ = ["get_design_json", "save_design_json", "get_design_schema"]


def get_design_json(design_file: Path) -> dict:
    """Đọc file + flatten thành { field_key: value } cho frontend."""
    design = load_design(str(design_file))
    return {
        "schema": get_schema(),
        "values": flatten_for_ui(design),
    }


def save_design_json(design_file: Path, patch: dict) -> dict:
    """Nhận patch từ frontend, merge vào file, lưu lại."""
    design = load_design(str(design_file))
    updated = apply_ui_patch(design, patch)
    save_design(str(design_file), updated)
    return {"ok": True, "saved": len(patch)}
