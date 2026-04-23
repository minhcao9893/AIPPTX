"""
routes_design.py — Flask routes cho Step II (Design + Generate)
================================================================
API endpoints:
  POST /api/apply-theme    → Nhận theme + colors → update design_template.json
  POST /api/generate       → Nhận full config → tạo PPTX (async thread)
  GET  /api/progress       → Poll tiến trình generate
  GET  /api/download/<fn>  → Tải file PPTX về
"""

from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import threading, shutil, re
from datetime import datetime

from .design_theme  import apply_theme_to_design, save_design
from .layout_engine import compute_layout

bp_design = Blueprint('design', __name__)

ROOT_DIR   = Path(__file__).resolve().parents[2]
APP_DIR    = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Progress state (in-memory, single-user)
_progress = {
    "status":   "idle",
    "pct":      0,
    "message":  "",
    "detail":   "",
    "filename": "",
    "output_path": ""
}


def _set_progress(pct: int, message: str, status: str = "running", **kwargs):
    _progress.update({"pct": pct, "message": message, "status": status, **kwargs})


# ── Routes ────────────────────────────────────────────────────────────────────

@bp_design.route('/api/apply-theme', methods=['POST'])
def apply_theme():
    """
    Nhận: { theme: str, colors: { primary, secondary, accent, bg, text } }
    Trả:  { ok: True }
    """
    try:
        data = request.get_json() or {}
        design_dict = apply_theme_to_design(data)
        save_design(design_dict)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@bp_design.route('/api/generate', methods=['POST'])
def generate():
    """
    Nhận: {
      slides:     [...],
      configs:    [...],
      design:     { theme, colors },
      layout:     { layout_type, pct, margin },
      input_text: str,
      input_mode: int
    }
    Khởi async thread → trả ngay { ok: True }
    """
    try:
        data = request.get_json() or {}

        input_text = data.get('input_text', '')
        if not input_text:
            # Thử lấy từ session text (routes_input)
            from .routes_input import _SESSION_TEXT
            session_data = _SESSION_TEXT.get('current', {})
            input_text = session_data.get('text', '')

        if not input_text:
            return jsonify({"ok": False, "error": "Không có input text"}), 400

        _set_progress(0, "Đang khởi động pipeline...", status="running")

        t = threading.Thread(
            target=_run_generate,
            args=(data, input_text),
            daemon=True
        )
        t.start()

        return jsonify({"ok": True, "message": "Đang xử lý..."})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@bp_design.route('/api/progress')
def get_progress():
    return jsonify(_progress)


@bp_design.route('/api/download/<path:filename>')
def download_file(filename):
    path = OUTPUT_DIR / filename
    if not path.exists():
        return "File không tồn tại", 404
    return send_file(str(path), as_attachment=True)


@bp_design.route('/api/media/<path:filename>')
def serve_media(filename):
    media_dir = APP_DIR / "input" / "media"
    path = media_dir / filename
    if not path.exists():
        return "File không tồn tại", 404
    return send_file(str(path))


# ── UI Override helper ──────────────────────────────────────────────────────

def _apply_ui_overrides(layout_plan: dict, ui_configs: list, ui_layout: dict,
                        layouts_cfg: list = None):
    """
    Áp dụng config từ UI lên từng slide_plan trong layout_plan.
    - useChart=False  → xoá chart_type, đặt về 'none'
    - genInsight=False → xoá insight_text
    - hasContent=False → tắt content section
    - layout_type: dùng layouts_cfg[i] per-slide, fallback về ui_layout (global)
    """
    if not ui_configs:
        return

    layout_type_map = {
        'horizontal': 'split_left',
        'vertical':   'one_col',
        'table2':     'table2',
        'table3':     'table3',
    }
    layouts_cfg = layouts_cfg or []

    for slide_plan in layout_plan.get('slides', []):
        idx = slide_plan.get('index', 1)
        if idx > 0:
            idx -= 1
        slide_plan['index'] = idx
        if idx < 0 or idx >= len(ui_configs):
            continue
        cfg = ui_configs[idx]

        # Chart: nếu user tắt → xoá chart
        use_chart = cfg.get('useChart', True)
        if not use_chart:
            slide_plan['chart_type'] = 'none'
            # Nếu layout đang là full_chart → đổi về split_left
            if slide_plan.get('layout') == 'full_chart':
                slide_plan['layout'] = 'split_left'

        # Insight: nếu user tắt → xoá insight_text
        gen_insight = cfg.get('genInsight', True)
        if not gen_insight:
            slide_plan['insight_text'] = ''
            slide_plan['show_insight'] = False

        # Content: nếu user tắt → đánh dấu để builder bỏ qua content
        has_content = cfg.get('hasContent', True)
        if not has_content:
            slide_plan['show_content'] = False

        # Layout type: ưu tiên per-slide từ layouts_cfg[idx], fallback về global ui_layout
        per_slide_layout = layouts_cfg[idx] if idx < len(layouts_cfg) else None
        raw_layout_type = (
            (per_slide_layout or {}).get('layout_type')
            or (per_slide_layout or {}).get('layout')
            or ui_layout.get('layout_type', '')
        )
        builder_layout = layout_type_map.get(raw_layout_type, '')
        if builder_layout:
            slide_plan['layout'] = builder_layout


# ── Background pipeline ───────────────────────────────────────────────────────

def _run_generate(data: dict, input_text: str):
    try:
        import json

        # 1. Apply theme
        _set_progress(5, "Đang áp dụng design theme...")
        design_cfg = data.get('design', {})
        # Khi theme='template_default': giữ nguyên design_template.json, không override
        _theme_val = design_cfg.get('theme', '') if design_cfg else ''
        if design_cfg and _theme_val != 'template_default':
            design_dict = apply_theme_to_design(design_cfg)
            save_design(design_dict)

        # Load design file
        design_file = APP_DIR / "design_template.json"
        design = json.loads(design_file.read_text(encoding='utf-8')) if design_file.exists() else {}

        # Áp dụng transparency từ UI (nếu có) vào design dict người dùng mới chỉnh
        # Giá trị này được lưu riêng vì nó không thuộc thème standard
        _adv_patch = data.get('adv_values', {})
        if _adv_patch:
            # Unflat patch và merge vào design
            def _unflat(flat):
                r = {}
                for k, v in flat.items():
                    parts = k.split('.')
                    cur = r
                    for p in parts[:-1]:
                        cur = cur.setdefault(p, {})
                    cur[parts[-1]] = v
                return r
            _nested_patch = _unflat(_adv_patch)
            def _deep_merge(base, patch):
                for k, v in patch.items():
                    if isinstance(v, dict) and isinstance(base.get(k), dict):
                        _deep_merge(base[k], v)
                    else:
                        base[k] = v
            _deep_merge(design, _nested_patch)

        # Apply transparency nếu user đã chỉnh slider ở Advanced panel
        _trans_pct = None
        if _adv_patch:
            _trans_pct = _adv_patch.get('slide.bg_transparency')
        if _trans_pct is None:
            _trans_pct = design.get('slide', {}).get('bg_transparency')
        if _trans_pct is not None:
            from .design_theme import apply_transparency_to_design
            apply_transparency_to_design(design, int(_trans_pct))

        # 2. Parse slides từ input_text
        _set_progress(15, "Đang parse slides từ text...")
        from .docx_parser_core import parse_docx_from_text
        raw_data = parse_docx_from_text(input_text)
        n_slides = len(raw_data.get('slides', []))
        _set_progress(22, f"Đọc xong — {n_slides} slides")

        # 2b. Stage 1: Classify — auto-update whitelist/blacklist
        _set_progress(23, "🧠 Stage 1: Cập nhật whitelist/blacklist...")
        _s1_whitelist = None
        _s1_blacklist = None
        try:
            from ..stage1_list_updater import run_stage1_update
            import sys as _sys1
            _n_w, _n_b, _s1_whitelist, _s1_blacklist = run_stage1_update(
                raw_data, dry_run=False, verbose=False
            )
            print(f"✅ [Stage 1] Xong: +{_n_w} whitelist, +{_n_b} blacklist (tổng {len(_s1_whitelist)}W / {len(_s1_blacklist)}B)", flush=True)
            _set_progress(24, f"✅ Stage 1: +{_n_w} whitelist, +{_n_b} blacklist")
        except Exception as _s1_err:
            import sys as _sys1
            print(f"⚠️ Stage 1 failed (continuing): {_s1_err}", flush=True)
            _set_progress(24, "⚠️ Stage 1 skipped (tiếp tục pipeline...)")

        # 3. Sanitize
        _set_progress(25, "Đang mask dữ liệu nhạy cảm...")
        from .sanitizer_core import sanitize, build_skeleton_metadata
        skeleton, name_map = sanitize(raw_data, whitelist=_s1_whitelist, blacklist=_s1_blacklist)
        skeleton = build_skeleton_metadata(skeleton)
        _set_progress(35, f"Đã mask {len(name_map)} tên")

        # 4. Compute layout — per-slide nếu có layouts[], ngược lại dùng global layout
        _set_progress(40, "Đang tính layout...")
        layout_cfg    = data.get('layout', {})
        layouts_cfg   = data.get('layouts', [])  # per-slide list
        global_rects  = compute_layout(layout_cfg)

        # Tính block_rects cho từng slide (nếu layouts[] đủ dài, dùng per-slide)
        n_slides      = len(raw_data.get('slides', []))
        per_slide_rects = []
        for i in range(n_slides):
            if i < len(layouts_cfg) and layouts_cfg[i]:
                per_slide_rects.append(compute_layout(layouts_cfg[i]))
            else:
                per_slide_rects.append(global_rects)

        # block_rects vẫn giữ global cho backward-compat (slide 0 hoặc fallback)
        block_rects = per_slide_rects[0] if per_slide_rects else global_rects

        # 5. AI layout planning
        _set_progress(45, "AI đang lên kế hoạch layout...")
        from .ai_planner_core import plan_layout
        layout_plan = plan_layout(skeleton, design_hints=design)
        _set_progress(70, "AI hoàn thành layout")

        # 5b. Override layout_plan từ UI configs (useChart, genInsight, hasContent)
        ui_configs  = data.get('configs', [])   # list of {useChart, hasContent, genInsight}
        ui_layout   = data.get('layout', {})    # global fallback {layout_type, pct, margin}
        layouts_cfg = data.get('layouts', [])   # per-slide list [{layout_type, pct, margin}]
        _apply_ui_overrides(layout_plan, ui_configs, ui_layout, layouts_cfg=layouts_cfg)

        # 6. Build PPTX
        stem     = datetime.now().strftime("AIPPTX_%Y%m%d_%H%M%S")
        out_name = f"{stem}.pptx"
        out_path = str(OUTPUT_DIR / out_name)

        template_dir = ROOT_DIR / "template"
        default_tpl  = template_dir / "template.pptx"

        # Ưu tiên template_name từ UI, fallback về default
        template_name = data.get('template_name')
        if template_name:
            tpl_path = str(template_dir / template_name) if (template_dir / template_name).exists() else None
        else:
            tpl_path = str(default_tpl) if default_tpl.exists() else None

        _set_progress(75, "Đang build PPTX...")
        from .builder_core import build
        build(layout_plan, name_map, raw_data,
              output_path=out_path,
              template_path=tpl_path,
              design=design,
              block_rects=block_rects,
              per_slide_rects=per_slide_rects,
              layouts_cfg=layouts_cfg)

        # 7. Copy lên Desktop/output
        _set_progress(93, "Đang copy sang Desktop...")
        desktop_out = Path.home() / 'Desktop' / 'output'
        desktop_out.mkdir(parents=True, exist_ok=True)
        dest = desktop_out / out_name
        shutil.copy2(out_path, dest)

        _set_progress(100, f"✅ Hoàn tất! → {out_name}", status="done",
                      filename=out_name, file=out_name, output_path=str(dest))

    except Exception as e:
        import traceback
        _set_progress(0, str(e) + "\n" + traceback.format_exc(), status="error")
